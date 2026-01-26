---
title: "Docker Cross-Platform Build: Architecture-Specific Binary Installation"
category: build-errors
tags:
  - docker
  - appimage
  - flatpak
  - arm64
  - x86_64
  - cross-platform
  - orcaslicer
  - graceful-degradation
  - capability-detection
severity: high
component: backend
date: 2026-01-26
symptoms:
  - "Exec format error when running x86_64 AppImage on ARM64"
  - "Flatpak user namespace permission errors in Docker containers"
  - "squashfs extraction failures: Can't find a valid SQUASHFS superblock"
resolution: "Make binary installation optional with runtime capability detection"
---

# Docker Cross-Platform Build: Architecture-Specific Binary Installation

## Problem

When building a Docker image that includes OrcaSlicer (a 3D slicer for generating 3MF files), the build fails on ARM64 hosts (Apple Silicon Macs, AWS Graviton) due to architecture incompatibility.

### Symptoms

```
# AppImage on ARM64
/bin/sh: 1: ./orca-slicer.AppImage: Exec format error

# Flatpak in Docker
bwrap: Creating new namespace failed: Operation not permitted

# Manual squashfs extraction
FATAL ERROR: Can't find a valid SQUASHFS superblock
```

### Root Cause

Three compounding issues:

1. **AppImage Architecture Mismatch**: OrcaSlicer is distributed only as x86_64 AppImage. ARM64 hosts cannot execute these binaries, even with `--platform linux/amd64` because QEMU emulation cannot run AppImages (they require FUSE).

2. **Flatpak Namespace Restriction**: Flatpak requires user namespaces (`unshare`) which are disabled during Docker `RUN` instructions for security.

3. **squashfs Offset Variability**: Attempting to manually extract the AppImage's embedded squashfs fails because offset calculation differs between AppImage versions.

## Solution

Make OrcaSlicer installation **optional** with runtime capability detection and graceful UI degradation.

### 1. Simplified Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Note: OrcaSlicer is not included in Docker due to cross-platform complexity.
# 3MF download requires OrcaSlicer installed on host or via ORCASLICER_PATH.
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/*.py .
COPY backend/profiles ./profiles

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Capability Detection Function

```python
# backend/printer.py
def find_orcaslicer() -> Optional[str]:
    """Find OrcaSlicer executable."""
    # Check environment variable first
    orca_path = os.environ.get("ORCASLICER_PATH")
    if orca_path and os.path.exists(orca_path):
        return orca_path

    # Common installation locations
    locations = [
        "/usr/local/bin/orca-slicer",
        "/opt/OrcaSlicer/orca-slicer",
        "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer",
        os.path.expanduser("~/.local/bin/orca-slicer"),
    ]

    for loc in locations:
        if os.path.exists(loc):
            return loc

    # Try PATH
    result = subprocess.run(["which", "orca-slicer"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()

    return None
```

### 3. Capabilities API Endpoint

```python
# backend/main.py
@app.get("/api/capabilities")
async def get_capabilities():
    """Get server capabilities including available features."""
    from printer import find_orcaslicer

    orca_path = find_orcaslicer()

    return {
        "slicer_available": orca_path is not None,
        "slicer_path": orca_path,
        "download_formats": ["stl", "svg"] + (["3mf"] if orca_path else []),
    }
```

### 4. Frontend Conditional Rendering

```vue
<!-- frontend/src/App.vue -->
<script>
export default {
  data() {
    return {
      slicerAvailable: false,
    }
  },

  async mounted() {
    await this.loadCapabilities()
  },

  methods: {
    async loadCapabilities() {
      try {
        const response = await fetch('/api/capabilities')
        const data = await response.json()
        this.slicerAvailable = data.slicer_available
      } catch (err) {
        this.slicerAvailable = false
      }
    },
  },
}
</script>

<template>
  <!-- Only show 3MF button when slicer is available -->
  <a v-if="slicerAvailable" :href="download3mfUrl" class="btn-secondary" download>
    Download 3MF
  </a>
</template>
```

## Key Files Modified

| File | Change |
|------|--------|
| `backend/Dockerfile` | Removed OrcaSlicer installation, added documentation |
| `backend/main.py` | Added `/api/capabilities` endpoint |
| `backend/printer.py` | Added `find_orcaslicer()` detection function |
| `frontend/src/App.vue` | Conditional 3MF button based on capabilities |

## Usage

**Docker (no 3MF support):**
```bash
docker compose up
# 3MF button hidden in UI
```

**Local development with OrcaSlicer:**
```bash
# macOS
export ORCASLICER_PATH="/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer"

# Linux
export ORCASLICER_PATH="/opt/OrcaSlicer/orca-slicer"

# Run backend
uvicorn main:app
# 3MF button appears in UI
```

## Prevention Strategies

### 1. Check Architecture Availability Before Adding Dependencies

Before adding platform-specific binaries:
- [ ] Verify binary available for all target architectures (amd64, arm64)
- [ ] Check if binary requires FUSE, user namespaces, or other restricted features
- [ ] Plan graceful degradation if unavailable

### 2. Use Capability Detection Pattern

```python
@dataclass
class Capabilities:
    has_slicer: bool
    has_openscad: bool
    architecture: str

@lru_cache(maxsize=1)
def detect_capabilities() -> Capabilities:
    return Capabilities(
        has_slicer=shutil.which("orca-slicer") is not None,
        has_openscad=shutil.which("openscad") is not None,
        architecture=platform.machine(),
    )
```

### 3. Document Limitations Prominently

Add comments at the top of Dockerfile explaining architecture limitations:
```dockerfile
# SUPPORTED ARCHITECTURES:
# - linux/amd64: Full functionality including OrcaSlicer
# - linux/arm64: Core functionality only (no native slicer)
```

### 4. Multi-Architecture CI Testing

```yaml
# .github/workflows/docker.yml
jobs:
  build:
    strategy:
      matrix:
        platform: [linux/amd64, linux/arm64]
    steps:
      - uses: docker/build-push-action@v5
        with:
          platforms: ${{ matrix.platform }}
```

## Related Documentation

- [Blender ARM64 Compatibility](../integration-issues/blender-python-arm64-compatibility.md)
- [3MF Download Feature Plan](../../plans/2026-01-25-feat-3mf-download-with-tactile-settings-plan.md)
- [OrcaSlicer GitHub](https://github.com/SoftFever/OrcaSlicer)
- [AppImage ARM64 Discussion](https://github.com/AppImage/AppImageKit/issues/1079)

## Why This Works

1. **No Breaking Changes**: Core STL/SVG functionality always works
2. **Runtime Detection**: Features checked at startup, not build time
3. **User Control**: `ORCASLICER_PATH` enables custom installations
4. **Clear Feedback**: UI shows what's available, no cryptic errors
5. **Future-Proof**: If ARM64 OrcaSlicer released, feature auto-enables
