"""
Multi-color 3MF file generation for tactile maps.

Combines separate STL files into a single 3MF with color/material assignments
for each feature type, enabling multi-material printing on printers like
Bambu X1C with AMS.
"""
import os
import zipfile
import tempfile
import struct
from pathlib import Path
from typing import Dict, Optional
import xml.etree.ElementTree as ET


# Feature colors for multi-color printing (RRGGBBAA format, FF = fully opaque)
FEATURE_COLORS = {
    'buildings': {'name': 'Buildings', 'color': '#CC4444FF'},
    'roads': {'name': 'Roads', 'color': '#808080FF'},
    'trails': {'name': 'Trails', 'color': '#8B4513FF'},  # Brown/saddle brown for trails
    'water': {'name': 'Water', 'color': '#4488CCFF'},
    'parks': {'name': 'Parks', 'color': '#44AA44FF'},
    'rails': {'name': 'Rails', 'color': '#444444FF'},
    'base': {'name': 'Base', 'color': '#FFFFFFFF'},
}


def read_stl_binary(stl_path: str) -> tuple:
    """
    Read a binary STL file and return vertices and triangles.

    Returns:
        (vertices, triangles) where vertices is list of (x,y,z) and
        triangles is list of (v1_idx, v2_idx, v3_idx)
    """
    vertices = []
    triangles = []
    vertex_map = {}  # Map (x,y,z) -> index for deduplication

    with open(stl_path, 'rb') as f:
        # Skip 80-byte header
        f.read(80)

        # Read triangle count (4 bytes, little-endian uint32)
        num_triangles = struct.unpack('<I', f.read(4))[0]

        for _ in range(num_triangles):
            # Skip normal vector (12 bytes)
            f.read(12)

            tri_indices = []
            for _ in range(3):
                # Read vertex (3 floats, 12 bytes)
                x, y, z = struct.unpack('<3f', f.read(12))
                vertex = (x, y, z)

                if vertex not in vertex_map:
                    vertex_map[vertex] = len(vertices)
                    vertices.append(vertex)

                tri_indices.append(vertex_map[vertex])

            triangles.append(tuple(tri_indices))

            # Skip attribute byte count (2 bytes)
            f.read(2)

    return vertices, triangles


def read_stl_ascii(stl_path: str) -> tuple:
    """
    Read an ASCII STL file and return vertices and triangles.
    """
    vertices = []
    triangles = []
    vertex_map = {}

    with open(stl_path, 'r') as f:
        current_tri = []
        for line in f:
            line = line.strip()
            if line.startswith('vertex'):
                parts = line.split()
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                vertex = (x, y, z)

                if vertex not in vertex_map:
                    vertex_map[vertex] = len(vertices)
                    vertices.append(vertex)

                current_tri.append(vertex_map[vertex])

                if len(current_tri) == 3:
                    triangles.append(tuple(current_tri))
                    current_tri = []

    return vertices, triangles


def read_stl(stl_path: str) -> tuple:
    """Read STL file (auto-detect binary vs ASCII)."""
    with open(stl_path, 'rb') as f:
        header = f.read(80)

    # Check if ASCII (starts with "solid")
    try:
        if header[:5].decode('ascii') == 'solid':
            # Could still be binary with "solid" in header, check further
            with open(stl_path, 'r') as f:
                first_lines = f.read(1000)
                if 'facet normal' in first_lines:
                    return read_stl_ascii(stl_path)
    except:
        pass

    return read_stl_binary(stl_path)


def compute_centering_offsets(objects: list, plate_size_mm: float = 256.0) -> tuple:
    """
    Compute (tx, ty) to translate all objects to the center of the print bed.

    Returns millimeter offsets to be baked directly into vertex coordinates.
    Baking is more reliable than using the 3MF transform attribute, which some
    slicer versions ignore or override with auto-positioning.
    """
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    for obj in objects:
        for v in obj['vertices']:
            min_x = min(min_x, v[0])
            max_x = max(max_x, v[0])
            min_y = min(min_y, v[1])
            max_y = max(max_y, v[1])

    plate_center = plate_size_mm / 2
    tx = plate_center - (min_x + max_x) / 2
    ty = plate_center - (min_y + max_y) / 2
    return tx, ty


def create_3mf_model_xml(objects: list, materials: list, tx: float = 0, ty: float = 0) -> str:
    """
    Create the 3D Model XML content for the 3MF file.

    Args:
        objects: List of dicts with 'id', 'vertices', 'triangles', 'material_id'
        materials: List of dicts with 'id', 'name', 'color'
        tx: X translation (mm) baked into vertex coordinates
        ty: Y translation (mm) baked into vertex coordinates
    """
    # Create root element with namespaces
    root = ET.Element('model')
    root.set('unit', 'millimeter')
    root.set('xmlns', 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02')
    root.set('xmlns:m', 'http://schemas.microsoft.com/3dmanufacturing/material/2015/02')

    # Add metadata
    metadata = ET.SubElement(root, 'metadata')
    metadata.set('name', 'Application')
    metadata.text = 'WOSMap Tactile Map Generator'

    # Create resources section
    resources = ET.SubElement(root, 'resources')

    # Add base materials
    basematerials = ET.SubElement(resources, 'm:basematerials')
    basematerials.set('id', '1')

    for mat in materials:
        base = ET.SubElement(basematerials, 'm:base')
        base.set('name', mat['name'])
        base.set('displaycolor', mat['color'])

    # Add mesh objects
    for obj in objects:
        obj_elem = ET.SubElement(resources, 'object')
        obj_elem.set('id', str(obj['id']))
        obj_elem.set('name', obj['feature_type'].capitalize())  # e.g., "Buildings", "Roads"
        obj_elem.set('type', 'model')
        obj_elem.set('pid', '1')  # Reference to basematerials
        obj_elem.set('pindex', str(obj['material_index']))

        mesh = ET.SubElement(obj_elem, 'mesh')

        # Add vertices — translation baked in so position is correct regardless
        # of how the slicer handles the 3MF transform attribute
        vertices_elem = ET.SubElement(mesh, 'vertices')
        for v in obj['vertices']:
            vert = ET.SubElement(vertices_elem, 'vertex')
            vert.set('x', f'{v[0] + tx:.6f}')
            vert.set('y', f'{v[1] + ty:.6f}')
            vert.set('z', f'{v[2]:.6f}')

        # Add triangles
        triangles_elem = ET.SubElement(mesh, 'triangles')
        for t in obj['triangles']:
            tri = ET.SubElement(triangles_elem, 'triangle')
            tri.set('v1', str(t[0]))
            tri.set('v2', str(t[1]))
            tri.set('v3', str(t[2]))

    # Create a single composite assembly object whose components reference each
    # mesh. Bambu Studio then treats the whole map as ONE item on the plate
    # rather than N separate models to auto-arrange side-by-side.
    assembly_id = max(obj['id'] for obj in objects) + 1
    assembly_elem = ET.SubElement(resources, 'object')
    assembly_elem.set('id', str(assembly_id))
    assembly_elem.set('type', 'model')
    assembly_elem.set('name', 'WOSMap')
    components_elem = ET.SubElement(assembly_elem, 'components')
    identity = '1 0 0 0 1 0 0 0 1 0 0 0'
    for obj in objects:
        comp = ET.SubElement(components_elem, 'component')
        comp.set('objectid', str(obj['id']))
        comp.set('transform', identity)

    # Single build item for the whole assembly (centering is baked into vertices)
    build = ET.SubElement(root, 'build')
    item = ET.SubElement(build, 'item')
    item.set('objectid', str(assembly_id))

    # Generate XML string
    ET.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='unicode')


def create_content_types_xml() -> str:
    """Create [Content_Types].xml for 3MF package."""
    root = ET.Element('Types')
    root.set('xmlns', 'http://schemas.openxmlformats.org/package/2006/content-types')

    default1 = ET.SubElement(root, 'Default')
    default1.set('Extension', 'rels')
    default1.set('ContentType', 'application/vnd.openxmlformats-package.relationships+xml')

    default2 = ET.SubElement(root, 'Default')
    default2.set('Extension', 'model')
    default2.set('ContentType', 'application/vnd.ms-package.3dmanufacturing-3dmodel+xml')

    # Add config extension for Bambu/OrcaSlicer metadata
    default3 = ET.SubElement(root, 'Default')
    default3.set('Extension', 'config')
    default3.set('ContentType', 'text/plain')

    ET.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='unicode')


def create_rels_xml() -> str:
    """Create _rels/.rels for 3MF package."""
    root = ET.Element('Relationships')
    root.set('xmlns', 'http://schemas.openxmlformats.org/package/2006/relationships')

    rel = ET.SubElement(root, 'Relationship')
    rel.set('Target', '/3D/3dmodel.model')
    rel.set('Id', 'rel0')
    rel.set('Type', 'http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel')

    ET.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='unicode')


def create_bambu_model_settings(objects: list) -> str:
    """
    Create Bambu/OrcaSlicer model_settings.config for extruder assignments.

    This tells Bambu Studio which filament slot (extruder) to use for each object.
    Extruder 1 = first AMS slot, Extruder 2 = second slot, etc.
    """
    lines = ['; generated by WOSMap for Bambu Studio / OrcaSlicer']

    for obj in objects:
        # Bambu uses 1-indexed extruders, material_index is 0-indexed
        extruder = obj['material_index'] + 1
        lines.append(f"[object:id_{obj['id']}]")
        lines.append(f"extruder = {extruder}")
        lines.append("")

    return '\n'.join(lines)


def create_bambu_project_settings(objects: list) -> str:
    """Create Bambu project settings with plate configuration."""
    # Build object list for the plate
    object_ids = ','.join(str(obj['id']) for obj in objects)

    return f"""; generated by WOSMap for Bambu Studio / OrcaSlicer
[plate:0]
objects = {object_ids}
bed_type = 0
print_sequence = 0

[filament]
filament_count = {len(objects)}
"""


def create_bambu_slice_info(objects: list) -> str:
    """Create slice_info.config for BambuStudio."""
    return """; generated by WOSMap
[plate_0]
slice_status = 0
"""


def create_multicolor_3mf(stl_files: Dict[str, str], output_path: str) -> str:
    """
    Create a multi-color 3MF file from separate STL files.

    Args:
        stl_files: Dict mapping feature type to STL file path
                   e.g., {'buildings': '/path/to/map.buildings.stl', ...}
        output_path: Output 3MF file path

    Returns:
        Path to created 3MF file
    """
    objects = []
    materials = []
    obj_id = 2  # Start at 2 (1 is reserved for basematerials)

    # Build materials list
    material_index = 0
    feature_to_material = {}

    for feature_type in FEATURE_COLORS:
        if feature_type in stl_files and os.path.exists(stl_files[feature_type]):
            config = FEATURE_COLORS[feature_type]
            materials.append({
                'id': material_index,
                'name': config['name'],
                'color': config['color'],
            })
            feature_to_material[feature_type] = material_index
            material_index += 1

    # Load each STL and create object
    for feature_type, stl_path in stl_files.items():
        if not os.path.exists(stl_path):
            print(f"Skipping {feature_type}: {stl_path} not found")
            continue

        if feature_type not in FEATURE_COLORS:
            print(f"Skipping unknown feature type: {feature_type}")
            continue

        print(f"Loading {feature_type} from {stl_path}")
        vertices, triangles = read_stl(stl_path)

        if len(triangles) == 0:
            print(f"Skipping {feature_type}: no triangles")
            continue

        objects.append({
            'id': obj_id,
            'vertices': vertices,
            'triangles': triangles,
            'material_index': feature_to_material[feature_type],
            'feature_type': feature_type,
        })
        obj_id += 1
        print(f"  Loaded {len(vertices)} vertices, {len(triangles)} triangles")

    if not objects:
        raise ValueError("No valid STL files found to combine")

    # Create 3MF package
    print(f"Creating 3MF with {len(objects)} objects and {len(materials)} materials")

    # Bake centering translation into vertex coords so position is always correct
    # regardless of how the slicer handles the 3MF transform attribute
    tx, ty = compute_centering_offsets(objects)
    print(f"  Centering offsets: tx={tx:.2f}mm, ty={ty:.2f}mm")

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add content types
        zf.writestr('[Content_Types].xml', create_content_types_xml())

        # Add relationships
        zf.writestr('_rels/.rels', create_rels_xml())

        # Add 3D model
        model_xml = create_3mf_model_xml(objects, materials, tx, ty)
        zf.writestr('3D/3dmodel.model', model_xml)

        # Add Bambu/OrcaSlicer metadata for extruder assignments
        zf.writestr('Metadata/model_settings.config', create_bambu_model_settings(objects))
        zf.writestr('Metadata/project_settings.config', create_bambu_project_settings(objects))
        zf.writestr('Metadata/slice_info.config', create_bambu_slice_info(objects))

    print(f"Created multi-color 3MF: {output_path}")
    return output_path


if __name__ == '__main__':
    # Test with sample files
    import sys

    if len(sys.argv) < 3:
        print("Usage: python multicolor_3mf.py <base_path> <output.3mf>")
        print("  Looks for files like <base_path>.buildings.stl, <base_path>.roads.stl, etc.")
        sys.exit(1)

    base_path = sys.argv[1]
    output_path = sys.argv[2]

    stl_files = {}
    for feature_type in FEATURE_COLORS:
        stl_path = f"{base_path}.{feature_type}.stl"
        if os.path.exists(stl_path):
            stl_files[feature_type] = stl_path

    if stl_files:
        create_multicolor_3mf(stl_files, output_path)
    else:
        print(f"No feature STL files found at {base_path}.*")
