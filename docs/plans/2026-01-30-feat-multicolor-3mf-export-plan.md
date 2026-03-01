---
title: Multi-Color 3MF Export for Tactile Maps
type: feat
date: 2026-01-30
---

# Multi-Color 3MF Export for Tactile Maps

## Overview

Add support for multi-color 3MF file generation that color-codes map features:
- **Green** - Parks, forests, trees
- **Blue** - Rivers, lakes, water bodies
- **Gray** - Streets and roads
- **Red/Brown** - Buildings
- **Terrain** - Base topography (future)

This enables multi-material printing on Bambu X1C with AMS, producing tactile maps that are both touchable AND visually distinct by feature type.

## Problem Statement

Currently, all map features are merged into a single monochrome STL. The existing OrcaSlicer integration produces single-color 3MF files. Users with multi-material printers (like Bambu X1C with AMS) cannot leverage color-coding to distinguish features visually.

## Proposed Solution

### Architecture

```
Current Flow:
OSM → OSM2World → Blender (merged) → Single STL → OrcaSlicer → Mono 3MF

New Flow:
OSM → OSM2World → Blender (separate objects) → Multiple STLs → Python 3MF Assembly → Multi-color 3MF
                                                                     ↓
                                                              OrcaSlicer (optional pre-slice)
```

### Color Mapping

| Feature Type | Color | Hex Code | Filament |
|--------------|-------|----------|----------|
| Buildings | Red | #CC4444 | Red PLA |
| Roads | Gray | #808080 | Gray PLA |
| Water Bodies | Blue | #4488CC | Blue PLA |
| Rivers/Streams | Dark Blue | #2255AA | Blue PLA |
| Parks/Forests | Green | #44AA44 | Green PLA |
| Base/Border | White | #FFFFFF | White PLA |

## Technical Approach

### Phase 1: Export Separate STLs by Feature Type

Modify `obj-to-tactile.py` to export each feature category as a separate STL file instead of merging everything.

**Current code (line ~221):**
```python
def export_stl(base_path, scale):
    bpy.ops.object.select_all(action='SELECT')
    _export_stl(base_path + '.stl', scale)
```

**New approach:**
```python
def export_stl_by_type(base_path, scale):
    """Export separate STL files for each feature type."""
    feature_groups = {
        'buildings': ['Buildings', 'Building'],
        'roads': ['CarRoads', 'PedestrianRoads', 'CarRoadAreas', 'PedestrianRoadAreas'],
        'rails': ['Rails'],
        'water': ['ClippedWaterAreas', 'InnerWaterAreas', 'JoinedWaterways', 'ClippedWaterways'],
        'parks': ['Forests', 'Parks', 'GrassAreas'],
        'base': ['Base', 'Borders'],
    }

    stl_files = {}
    for group_name, prefixes in feature_groups.items():
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.context.scene.objects:
            if any(obj.name.startswith(p) for p in prefixes):
                obj.select_set(True)

        if bpy.context.selected_objects:
            stl_path = f"{base_path}.{group_name}.stl"
            _export_stl(stl_path, scale)
            stl_files[group_name] = stl_path

    # Also export combined STL for backwards compatibility
    bpy.ops.object.select_all(action='SELECT')
    _export_stl(base_path + '.stl', scale)

    return stl_files
```

### Phase 2: Create Multi-Color 3MF Assembly

New file: `converter/multicolor_3mf.py`

```python
"""
Combine multiple STL files into a single multi-color 3MF.
Uses lib3mf for proper material/color support.
"""
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from stl import mesh as numpy_stl

FEATURE_COLORS = {
    'buildings': {'name': 'Buildings', 'color': '#CC4444'},
    'roads': {'name': 'Roads', 'color': '#808080'},
    'water': {'name': 'Water', 'color': '#4488CC'},
    'parks': {'name': 'Parks', 'color': '#44AA44'},
    'rails': {'name': 'Rails', 'color': '#444444'},
    'base': {'name': 'Base', 'color': '#FFFFFF'},
}

def create_multicolor_3mf(stl_files: dict, output_path: str) -> str:
    """
    Combine multiple STL files into a multi-color 3MF.

    Args:
        stl_files: Dict of {feature_type: stl_path}
        output_path: Output 3MF file path

    Returns:
        Path to created 3MF file
    """
    # Build 3MF XML structure with materials and colored meshes
    # ... implementation details ...
    pass
```

### Phase 3: Update Backend Integration

**Modify `backend/printer.py`:**

```python
def create_multicolor_3mf(stl_files: dict, output_path: str) -> str:
    """Create multi-color 3MF from separate feature STLs."""
    from converter.multicolor_3mf import create_multicolor_3mf as _create
    return _create(stl_files, output_path)
```

**Modify `backend/main.py` download endpoint:**

```python
@app.get("/api/maps/{job_id}/download")
async def download_map(job_id: str, file_type: str = "stl", multicolor: bool = False):
    # ... existing code ...

    if file_type == "3mf" and multicolor:
        multicolor_path = stl_path.with_suffix(".multicolor.3mf")
        if not multicolor_path.exists():
            stl_files = {
                'buildings': files.get('stl_buildings'),
                'roads': files.get('stl_roads'),
                # ... etc
            }
            create_multicolor_3mf(stl_files, str(multicolor_path))
        file_path = multicolor_path
```

### Phase 4: Frontend Download Option

Add multi-color download button in `GeneratorResults.vue`:

```vue
<a
  v-if="slicerAvailable"
  :href="multicolor3mfUrl"
  download
  class="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-green-500 to-blue-500 text-white rounded-xl"
>
  <span>Download Multi-Color 3MF</span>
</a>
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `converter/obj-to-tactile.py` | Modify | Export separate STLs by feature type |
| `converter/multicolor_3mf.py` | Create | 3MF assembly with color/material support |
| `converter/process_request.py` | Modify | Track separate STL files in output |
| `backend/printer.py` | Modify | Add multi-color 3MF creation function |
| `backend/main.py` | Modify | Add multicolor query param to download |
| `frontend/src/components/generator/GeneratorResults.vue` | Modify | Add multi-color download button |
| `frontend/src/api.js` | Modify | Add multicolor URL helper |

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| lib3mf | ^2.0.0 | Official 3MF library for Python |
| numpy-stl | (existing) | STL file reading |

## Acceptance Criteria

- [x] Separate STL files generated for each feature type
- [x] Multi-color 3MF combines all features with correct colors
- [x] OrcaSlicer recognizes materials when opening 3MF
- [x] Download button available in UI (always available, no slicer required)
- [x] Backwards compatible - single STL still generated
- [ ] File size reasonable (< 2x single STL) - to be verified

## Future Enhancements

- **Terrain/Topo**: Add elevation data as base layer with gradient coloring
- **Pre-sliced multi-color**: Generate G-code with AMS tool changes
- **Custom color picker**: Let users choose their own feature colors
- **Material presets**: "High contrast", "Nature", "Grayscale" themes

## References

### Internal
- Current STL export: `converter/obj-to-tactile.py:219-229`
- OrcaSlicer integration: `backend/printer.py:76-141`
- Download endpoint: `backend/main.py:293-387`

### External
- [3MF Materials Specification](https://github.com/3MFConsortium/spec_materials)
- [lib3mf Python Bindings](https://github.com/3MFConsortium/lib3mf)
- [OrcaSlicer Multi-Material Guide](https://github.com/SoftFever/OrcaSlicer/wiki)
