---
title: Enhanced Job Progress Feedback and STL File Details
type: feat
date: 2026-01-25
---

# Enhanced Job Progress Feedback and STL File Details

## Overview

Currently, users see minimal feedback during map generation ("Job queued", "Generating tactile map..."). This plan adds detailed progress stages and rich STL file information when the job completes.

## Problem Statement

1. **During processing**: Users only see "Generating tactile map..." with no indication of which step is happening or how long it might take
2. **After completion**: Users only see "Map Ready" with a download button - no file size, dimensions, or other useful STL metadata

## Proposed Solution

### Part 1: Detailed Processing Stages

Add granular status updates that the frontend polls and displays:

| Stage | Status Message |
|-------|---------------|
| `queued` | "Job queued, waiting for worker..." |
| `fetching_osm` | "Fetching map data from OpenStreetMap..." |
| `fetching_overture` | "Fetching building data from Overture Maps..." |
| `converting` | "Converting to 3D model (OSM2World)..." |
| `rendering` | "Rendering tactile features (Blender)..." |
| `finalizing` | "Finalizing STL file..." |
| `completed` | "Map generation complete!" |

### Part 2: STL File Metadata

When job completes, return rich file information:

```json
{
  "status": "completed",
  "files": {
    "stl": "/data/maps/uuid/map.stl"
  },
  "file_info": {
    "filename": "wosmap_salt-lake-city_2026-01-25.stl",
    "size_bytes": 13421772,
    "size_human": "12.8 MB",
    "triangles": 284532,
    "vertices": 142266,
    "dimensions": {
      "x_mm": 230.0,
      "y_mm": 230.0,
      "z_mm": 15.2
    },
    "bounding_box": {
      "min": [0.0, 0.0, 0.0],
      "max": [230.0, 230.0, 15.2]
    }
  }
}
```

## Technical Approach

### Files to Modify

1. **`converter/worker.py`** - Pass Redis client to process_request for stage updates
2. **`converter/process_request.py`** - Add stage callbacks, compute STL metadata
3. **`backend/main.py`** - Extend JobStatus model with file_info
4. **`frontend/src/App.vue`** - Display stages and file details

### Implementation

#### 1. Add STL metadata parser (`converter/stl_utils.py`)

```python
import struct
from pathlib import Path

def get_stl_info(stl_path: str) -> dict:
    """
    Parse STL file and extract metadata.
    Handles binary STL format (most common from Blender).
    """
    path = Path(stl_path)
    size_bytes = path.stat().st_size

    # Binary STL: 80-byte header + 4-byte triangle count + triangles
    with open(stl_path, 'rb') as f:
        header = f.read(80)
        triangle_count = struct.unpack('<I', f.read(4))[0]

        # Calculate bounding box by reading all vertices
        min_coords = [float('inf')] * 3
        max_coords = [float('-inf')] * 3

        for _ in range(triangle_count):
            # Skip normal (12 bytes), read 3 vertices (36 bytes), skip attribute (2 bytes)
            f.read(12)  # normal
            for _ in range(3):  # 3 vertices
                x, y, z = struct.unpack('<fff', f.read(12))
                min_coords = [min(min_coords[i], v) for i, v in enumerate([x, y, z])]
                max_coords = [max(max_coords[i], v) for i, v in enumerate([x, y, z])]
            f.read(2)  # attribute byte count

    dimensions = [max_coords[i] - min_coords[i] for i in range(3)]

    return {
        "size_bytes": size_bytes,
        "size_human": format_bytes(size_bytes),
        "triangles": triangle_count,
        "vertices": triangle_count * 3,  # Each triangle has 3 unique vertices in STL
        "dimensions": {
            "x_mm": round(dimensions[0], 1),
            "y_mm": round(dimensions[1], 1),
            "z_mm": round(dimensions[2], 1),
        },
        "bounding_box": {
            "min": [round(v, 2) for v in min_coords],
            "max": [round(v, 2) for v in max_coords],
        }
    }

def format_bytes(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
```

#### 2. Update worker to pass status callback

```python
# converter/worker.py

def make_status_callback(r: redis.Redis, job_id: str):
    """Create a callback function for updating job status."""
    def update_stage(stage: str, message: str = None):
        update_job_status(r, job_id, stage, {"stage_message": message} if message else None)
    return update_stage

# In main loop:
status_callback = make_status_callback(r, job_id)
result = process_map_request(job, WORK_DIR, status_callback=status_callback)
```

#### 3. Update process_request with stages

```python
# converter/process_request.py

def process_map_request(job: dict, work_dir: str, status_callback=None) -> dict:
    def update_stage(stage: str, message: str = None):
        if status_callback:
            status_callback(stage, message)
        print(f"Stage: {stage}" + (f" - {message}" if message else ""))

    # ... existing setup code ...

    # Step 1: Fetch OSM data
    update_stage("fetching_osm", "Fetching map data from OpenStreetMap...")
    osm_data = get_map_data(lat, lon, diameter, data_source, work_dir=str(job_dir))

    if data_source in ("overture", "osm_ms"):
        update_stage("fetching_overture", "Fetching building data from Overture Maps...")

    # Step 2: Convert to 3D
    update_stage("converting", "Converting to 3D model...")
    # ... osm-to-tactile.py call ...

    update_stage("rendering", "Rendering tactile features...")
    # ... blender processing ...

    update_stage("finalizing", "Computing file metadata...")

    # Step 3: Get STL info
    from stl_utils import get_stl_info
    stl_info = get_stl_info(str(stl_path))

    return {
        "status": "completed",
        "files": output_files,
        "file_info": {
            "filename": f"wosmap_{location_name}_{date_str}.stl",
            **stl_info
        },
        "metadata": metadata,
    }
```

#### 4. Update frontend display

```vue
<!-- Status section with stage details -->
<section v-if="status" class="card status-card" :class="statusClass">
  <h3>Status</h3>
  <p class="status-message">{{ stageMessage || statusMessage }}</p>
  <div v-if="isProcessing" class="progress-stages">
    <div v-for="stage in stages" :key="stage.id"
         class="stage" :class="{ active: currentStage === stage.id, done: stageCompleted(stage.id) }">
      <span class="stage-icon">{{ stageCompleted(stage.id) ? '✓' : (currentStage === stage.id ? '◉' : '○') }}</span>
      <span class="stage-label">{{ stage.label }}</span>
    </div>
  </div>
</section>

<!-- Results section with file details -->
<section v-if="completed" class="card results-card">
  <h3>Map Ready</h3>

  <div class="file-details">
    <p class="filename">{{ fileInfo.filename }}</p>
    <div class="file-stats">
      <span><strong>Size:</strong> {{ fileInfo.size_human }}</span>
      <span><strong>Triangles:</strong> {{ fileInfo.triangles?.toLocaleString() }}</span>
      <span><strong>Dimensions:</strong> {{ fileInfo.dimensions?.x_mm }} × {{ fileInfo.dimensions?.y_mm }} × {{ fileInfo.dimensions?.z_mm }} mm</span>
    </div>
  </div>

  <div class="button-row">
    <a :href="downloadUrl" class="btn-secondary" download>Download STL</a>
    <button class="btn-secondary" @click="showPrinterModal = true">Send to Printer</button>
  </div>
</section>
```

## Acceptance Criteria

- [x] Status updates show current processing stage (fetching_osm, converting, rendering, etc.)
- [x] Frontend displays visual progress through stages
- [x] Completed jobs show filename that will be downloaded
- [x] Completed jobs show file size in human-readable format
- [x] Completed jobs show triangle count
- [x] Completed jobs show dimensions (X × Y × Z in mm)
- [x] Stage updates appear within 2 seconds of stage change
- [x] Works for both OSM-only and Overture data sources

## References

- Current status handling: `frontend/src/App.vue:214-230`
- Worker status updates: `converter/worker.py:34-49`
- Process request: `converter/process_request.py`
- JobStatus model: `backend/main.py:89-97`
