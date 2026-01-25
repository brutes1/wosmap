---
title: Multi-City STL Generation Validation Test
type: test
date: 2026-01-25
---

# Multi-City STL Generation Validation Test

## Overview

Validate the map generation workflow by creating STL files for 3 different USA cities using both data sources (OSM and Overture) and verify the files are unique and correctly generated.

## Test Cities

| City | Latitude | Longitude | Data Source |
|------|----------|-----------|-------------|
| Salt Lake City, UT | 40.7608 | -111.8910 | osm |
| Austin, TX | 30.2672 | -97.7431 | overture |
| Portland, OR | 45.5152 | -122.6784 | osm |

## Acceptance Criteria

- [x] All 3 jobs complete successfully (status: "completed")
- [x] Each STL file has a unique file size (size_bytes differ)
- [x] Each STL file has different triangle counts
- [x] Each STL file has different bounding box coordinates
- [x] Files from different data sources (OSM vs Overture) show variation
- [x] Downloaded filenames include the city location name
- [x] All files are valid binary STL format (can be parsed)

## Test Results (2026-01-25)

| City | Data Source | Filename | Size | Triangles | MD5 Hash |
|------|-------------|----------|------|-----------|----------|
| Salt Lake City | OSM | wosmap_salt-lake-city_2026-01-25.stl | 1.5 MB | 31,340 | 770d5c34d23b1952d25c0efc04363111 |
| Austin | Overture | wosmap_austin_2026-01-25.stl | 2.0 MB | 41,796 | 9b556605e51e5bf04f4b4e73e431b8dc |
| Portland | OSM | wosmap_portland_2026-01-25.stl | 5.2 MB | 107,984 | 04e0419dd469a6d6f231e2d7aeb1b7aa |

**All tests passed.** Files are unique, from different geographic locations, and use different data sources.

## Test Execution Steps

### 1. Submit Jobs

```bash
# Salt Lake City - OSM
curl -X POST http://localhost:8000/api/maps \
  -H "Content-Type: application/json" \
  -d '{"latitude": 40.7608, "longitude": -111.8910, "scale": 3463, "size_cm": 23, "data_source": "osm"}'

# Austin - Overture
curl -X POST http://localhost:8000/api/maps \
  -H "Content-Type: application/json" \
  -d '{"latitude": 30.2672, "longitude": -97.7431, "scale": 3463, "size_cm": 23, "data_source": "overture"}'

# Portland - OSM
curl -X POST http://localhost:8000/api/maps \
  -H "Content-Type: application/json" \
  -d '{"latitude": 45.5152, "longitude": -122.6784, "scale": 3463, "size_cm": 23, "data_source": "osm"}'
```

### 2. Poll for Completion

```bash
# Poll each job until completed
curl http://localhost:8000/api/maps/{job_id}
```

### 3. Compare Results

Compare `file_info` from each completed job:
- `size_bytes` - should all be different
- `triangles` - should all be different
- `dimensions` - should vary based on terrain
- `bounding_box` - should be different locations

### 4. Download and Verify Files

```bash
# Download each STL
curl -o slc.stl "http://localhost:8000/api/maps/{slc_job_id}/download?file_type=stl"
curl -o austin.stl "http://localhost:8000/api/maps/{austin_job_id}/download?file_type=stl"
curl -o portland.stl "http://localhost:8000/api/maps/{portland_job_id}/download?file_type=stl"

# Compare file hashes - should all be different
md5 slc.stl austin.stl portland.stl
```

## Expected Results

| City | Expected Location Name | Data Source | Expected Size Range |
|------|----------------------|-------------|-------------------|
| Salt Lake City | salt-lake-city | OSM | 5-50 MB |
| Austin | austin | Overture | 5-50 MB (likely larger with Overture buildings) |
| Portland | portland | OSM | 5-50 MB |

## Failure Conditions

- Any job returns status "failed"
- Two or more files have identical MD5 hashes
- Two or more files have identical size_bytes
- file_info.filename does not include location name
- Triangle count is 0 or dimensions are all zeros

## References

- API endpoint: `backend/main.py:137-203` (POST /api/maps)
- Status model: `backend/main.py:89-99` (JobStatus with file_info)
- STL parsing: `converter/stl_utils.py:9-127`
- Data sources: `converter/osm_sources.py` (OSM vs Overture)
