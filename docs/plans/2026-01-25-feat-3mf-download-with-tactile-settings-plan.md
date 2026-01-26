---
title: 3MF Download with Tactile Map Slicer Settings
type: feat
date: 2026-01-25
---

# 3MF Download with Tactile Map Slicer Settings

## Overview

Add a "Download 3MF" option that provides a pre-sliced 3MF file with optimized settings for tactile map printing:
- Layer height: 0.3mm
- Top surface ironing: enabled at 20% speed
- Ironing spacing: 0.08mm (extra fine)

This allows users to download a print-ready file they can transfer directly to their printer without needing to configure slicer settings themselves.

## Problem Statement

Currently users can:
1. Download raw STL and slice it themselves (requires slicer knowledge)
2. Send directly to a configured Bambu X1C printer (requires network printer setup)

Missing: A middle ground for users who have a printer but don't have network printing configured, or use a different printer brand. They need a pre-sliced 3MF with optimal tactile map settings.

## Proposed Solution

### Slicer Profile Settings

Create a new OrcaSlicer profile `tactile_map_ironing.json`:

```json
{
  "layer_height": 0.3,
  "first_layer_height": 0.35,
  "wall_loops": 3,
  "top_shell_layers": 4,
  "bottom_shell_layers": 3,
  "sparse_infill_density": "15%",
  "ironing_type": "top",
  "ironing_flow": "20%",
  "ironing_spacing": 0.08,
  "enable_support": false,
  "brim_type": "auto_brim"
}
```

### Implementation Changes

1. **New endpoint**: `GET /api/maps/{job_id}/download?file_type=3mf`
2. **On-demand slicing**: When 3MF is requested, slice the STL if not already cached
3. **Cache the result**: Store 3MF alongside STL to avoid re-slicing
4. **Frontend**: Add "Download 3MF" button in results and history

## Technical Approach

### Backend Changes

#### 1. Add ironing profile (`backend/profiles/tactile_map_ironing.json`)

```json
{
  "layer_height": 0.3,
  "first_layer_height": 0.35,
  "wall_loops": 3,
  "top_shell_layers": 4,
  "bottom_shell_layers": 3,
  "sparse_infill_density": "15%",
  "ironing_type": "top",
  "ironing_flow": "20%",
  "ironing_spacing": 0.08,
  "enable_support": false,
  "brim_type": "auto_brim"
}
```

#### 2. Modify download endpoint (`backend/main.py`)

Add 3MF handling to the download endpoint:

```python
# In content_types dict
"3mf": "application/vnd.ms-package.3dmanufacturing-3dmodel+xml",

# In download_map function - check if 3MF requested
if file_type == "3mf":
    # Check if 3MF already exists
    stl_path = files.get("stl")
    threemf_path = Path(stl_path).with_suffix(".3mf")

    if not threemf_path.exists():
        # Slice on demand
        from printer import BambuPrinter
        profile_path = Path(__file__).parent / "profiles" / "tactile_map_ironing.json"
        printer = BambuPrinter("", "", "")  # Just need slice method
        printer.slice_stl(stl_path, str(threemf_path), str(profile_path))

    file_path = threemf_path
```

#### 3. Add slicing utility function (`backend/printer.py`)

Extract slicing to a standalone function that doesn't require printer config:

```python
def slice_to_3mf(stl_path: str, output_path: str, profile_path: str) -> str:
    """Slice STL to 3MF without printer connection."""
    orca_path = _find_orcaslicer()
    if orca_path is None:
        raise PrinterError("OrcaSlicer not found")

    cmd = [orca_path, "--export-3mf", output_path]
    if profile_path:
        cmd.extend(["--load-settings", profile_path])
    cmd.append(stl_path)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise PrinterError(f"Slicing failed: {result.stderr}")

    return output_path
```

### Frontend Changes

#### 1. Add 3MF download button (`frontend/src/App.vue`)

In results section:
```vue
<div class="button-row">
  <a :href="downloadUrl" class="btn-secondary" download>
    Download STL
  </a>
  <a :href="download3mfUrl" class="btn-secondary" download>
    Download 3MF (Print-Ready)
  </a>
  <button class="btn-secondary" @click="showPrinterModal = true">
    Send to Printer
  </button>
</div>
```

Add computed property:
```javascript
download3mfUrl() {
  if (!this.jobId) return '#'
  return getDownloadUrl(this.jobId, '3mf')
}
```

#### 2. Add 3MF to history items

```vue
<div class="history-buttons">
  <a :href="getJobDownloadUrl(job.job_id)" class="btn-small" download>STL</a>
  <a :href="getJob3mfUrl(job.job_id)" class="btn-small" download>3MF</a>
</div>
```

## Acceptance Criteria

- [x] New slicer profile with 0.3mm layers, ironing at 20%, 0.08mm spacing
- [x] GET /api/maps/{job_id}/download?file_type=3mf returns sliced 3MF
- [x] 3MF is cached after first generation (not re-sliced each download)
- [x] Frontend shows "Download 3MF" button alongside STL download
- [x] History items have both STL and 3MF download options
- [x] Graceful error if OrcaSlicer is not installed
- [x] 3MF filename follows pattern: wosmap_{location}_{date}.3mf

## Dependencies & Risks

**Dependencies:**
- OrcaSlicer must be installed and accessible via PATH or ORCASLICER_PATH env var
- 3MF button is conditionally shown based on /api/capabilities endpoint

**Risks:**
- Slicing can take 30-60 seconds - first 3MF download will be slow
- OrcaSlicer settings format may differ between versions

**Mitigations:**
- Frontend checks /api/capabilities and only shows 3MF button when slicer is available
- Pre-slice 3MF during job completion (optional optimization)
- Document required OrcaSlicer version

## Implementation Notes

**OrcaSlicer in Docker:** Due to cross-platform complexity (AppImages require x86_64, Flatpak requires user namespaces), OrcaSlicer is not included in the Docker image. To enable 3MF downloads:
1. Install OrcaSlicer locally and set ORCASLICER_PATH
2. Or run the backend outside Docker with OrcaSlicer installed
3. The frontend gracefully hides 3MF buttons when slicer is unavailable

## References

- OrcaSlicer integration: `backend/printer.py:88-139`
- Current download endpoint: `backend/main.py:279-346`
- Existing slicer profile: `backend/profiles/tactile_map.json`
- STL generation: `converter/obj-to-tactile.py:219-229`
