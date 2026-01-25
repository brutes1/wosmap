# Blender 2.7 to 3.0 API + ARM64 Docker Compatibility

---
title: Blender 2.7 to 3.0 API Migration + ARM64 Docker Compatibility
category: integration-issues
tags:
  - blender
  - python
  - arm64
  - docker
  - api-migration
  - apple-silicon
components:
  - converter/obj-to-tactile.py
  - converter/Dockerfile
  - converter/osm_sources.py
date_solved: 2026-01-24
severity: blocking
symptoms:
  - "AttributeError: module 'time' has no attribute 'clock'"
  - "TypeError: Element-wise multiplication not supported between Matrix and Vector"
  - "AttributeError: 'Object' object has no attribute 'select'"
  - "rosetta error: failed to open elf at /lib64/ld-linux-x86-64.so.2"
  - "Modifier returned error, skipping apply"
root_cause: Multiple API breaking changes between Blender 2.78 and 3.0, plus x86_64 binary incompatibility on ARM64
---

## Problem Summary

When deploying a tactile map generator (based on touch-mapper.org) in Docker on Apple Silicon (ARM64), Blender scripts written for Blender 2.78 failed with multiple API compatibility errors when running on Blender 3.0.

## Symptoms Observed

### 1. Rosetta Translation Failure
```
rosetta error: failed to open elf at /lib64/ld-linux-x86-64.so.2
```

### 2. Python 3.8+ Compatibility
```
AttributeError: module 'time' has no attribute 'clock'
```

### 3. Blender Matrix API Change
```
TypeError: Element-wise multiplication: not supported between 'Matrix' and 'Vector' types
```

### 4. Selection API Change
```
AttributeError: 'Object' object has no attribute 'select'
```

### 5. Modifier API Change
```
TypeError: Converting py args to operator properties: keyword "apply_as" unrecognized
```

### 6. BMesh API Change
```
TypeError: 'tessface' is an invalid keyword argument for update_edit_mesh()
TypeError: update_edit_mesh() takes at most 1 positional argument (2 given)
```

## Root Causes

1. **ARM64 Binary Incompatibility**: Blender official releases only provide x86_64 Linux binaries. Running these on Apple Silicon via Rosetta in Docker fails.

2. **Python API Deprecations**: `time.clock()` was deprecated in Python 3.3 and removed in Python 3.8.

3. **Blender 2.80 API Overhaul**: Blender 2.80 introduced breaking changes to the Python API for selection, active objects, matrix operations, modifiers, and bmesh.

## Solution

### Fix 1: Use Ubuntu-Packaged Blender for ARM64 Support

**Before (Dockerfile):**
```dockerfile
ENV BLENDER_VERSION=3.6.5
ENV BLENDER_URL=https://download.blender.org/release/Blender3.6/blender-${BLENDER_VERSION}-linux-x64.tar.xz
RUN wget -q ${BLENDER_URL} -O /tmp/blender.tar.xz \
    && tar -xf /tmp/blender.tar.xz -C /opt/blender --strip-components=1
```

**After:**
```dockerfile
# Install Blender from Ubuntu repository (supports ARM64)
RUN apt-get update && apt-get install -y blender && rm -rf /var/lib/apt/lists/*

ENV BLENDER_PATH=/usr/bin/blender
```

### Fix 2: time.clock() → time.perf_counter()

**Before:**
```python
t = time.clock()
print("operation took " + str(time.clock() - t))
```

**After:**
```python
t = time.perf_counter()
print("operation took " + str(time.perf_counter() - t))
```

### Fix 3: Matrix Multiplication Operator

**Before (Blender 2.7):**
```python
world_coord = ob.matrix_world * vert.co
```

**After (Blender 2.8+):**
```python
world_coord = ob.matrix_world @ vert.co
```

### Fix 4: Selection API

**Before:**
```python
ob.select = True
bpy.context.scene.objects.active = ob
```

**After:**
```python
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
```

### Fix 5: Scene Update API

**Before:**
```python
bpy.context.scene.update()
```

**After:**
```python
bpy.context.view_layer.update()
```

### Fix 6: Modifier Apply API

**Before:**
```python
bpy.ops.object.modifier_apply(apply_as='DATA', modifier=modifier.name)
```

**After:**
```python
try:
    bpy.ops.object.modifier_apply(modifier=modifier.name)
except RuntimeError as e:
    print(f"Warning: Could not apply modifier: {e}")
```

### Fix 7: BMesh update_edit_mesh()

**Before:**
```python
bmesh.update_edit_mesh(object.data, tessface=False, destructive=False)
bmesh.update_edit_mesh(bpy.context.object.data, True)
```

**After:**
```python
bmesh.update_edit_mesh(object.data, destructive=False)
bmesh.update_edit_mesh(bpy.context.object.data)
```

## Complete Migration Checklist

When migrating Blender 2.7x scripts to 3.x:

- [ ] Replace `time.clock()` with `time.perf_counter()`
- [ ] Replace matrix `*` with `@` for matrix-vector multiplication
- [ ] Replace `ob.select = True/False` with `ob.select_set(True/False)`
- [ ] Replace `scene.objects.active` with `view_layer.objects.active`
- [ ] Replace `scene.update()` with `view_layer.update()`
- [ ] Remove `apply_as='DATA'` from `modifier_apply()`
- [ ] Remove `tessface` parameter from `update_edit_mesh()`
- [ ] Change positional args to keyword args in `update_edit_mesh()`
- [ ] Add try/except around `modifier_apply()` calls
- [ ] For ARM64 Docker: Use distro-packaged Blender instead of official binaries

## Prevention Strategies

### 1. Version Check at Script Start
```python
import bpy
if bpy.app.version < (2, 80, 0):
    raise RuntimeError("This script requires Blender 2.80 or newer")
```

### 2. Docker Multi-Architecture Builds
```dockerfile
# Detect architecture and handle appropriately
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ]; then \
        apt-get install -y blender; \
    else \
        # Download official binary for x86_64
        wget ... blender-linux-x64.tar.xz; \
    fi
```

### 3. Compatibility Wrapper Functions
```python
def select_object(ob, state=True):
    """Cross-version object selection"""
    if hasattr(ob, 'select_set'):
        ob.select_set(state)
    else:
        ob.select = state

def set_active_object(context, ob):
    """Cross-version active object setting"""
    if hasattr(context, 'view_layer'):
        context.view_layer.objects.active = ob
    else:
        context.scene.objects.active = ob
```

## Related Resources

- [Blender 2.80 Python API Changes](https://wiki.blender.org/wiki/Reference/Release_Notes/2.80/Python_API)
- [Python 3.8 time.clock() removal](https://docs.python.org/3/whatsnew/3.8.html#removed)
- [Blender ARM64 Linux status](https://developer.blender.org/docs/handbook/building_blender/platforms/)

## Files Modified

- `converter/Dockerfile` - ARM64 Blender installation
- `converter/obj-to-tactile.py` - All Blender API compatibility fixes
- `converter/osm_sources.py` - Overpass API query format fixes (separate issue)

## Verification

After applying fixes:
```bash
# Test Blender works in container
docker-compose exec converter blender --version

# Submit test job
curl -X POST http://localhost:8000/api/maps \
  -H "Content-Type: application/json" \
  -d '{"address": "White House, Washington DC", "scale": 5000, "size_cm": 10}'

# Check for STL generation
docker-compose logs converter | grep "completed successfully"
```
