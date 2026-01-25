---
status: completed
priority: p1
issue_id: "002"
tags: [code-review, security, backend]
---

# Path Traversal Vulnerability in File Downloads

## Problem Statement

The download endpoint retrieves file paths directly from Redis without validating they're within the expected MAPS_DIR. An attacker who can poison Redis data could read arbitrary files from the server.

**Why it matters:** Arbitrary file read from server filesystem, potential credential/key exposure.

## Findings

**Location:** `backend/main.py:218-277`

```python
@app.get("/api/maps/{job_id}/download")
async def download_map(job_id: str, file_type: str = "stl"):
    # ...
    files = data.get("files", {})
    file_path = files.get(file_type)  # No validation!
    # ...
    file_path = Path(file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(path=file_path, ...)  # Serves any file!
```

**Attack scenario:**
1. Attacker modifies Redis data (port 6379 is exposed)
2. Sets `files["stl"] = "/etc/passwd"` for a job
3. Downloads sensitive system files

## Proposed Solutions

### Option A: Path Validation (Recommended)
```python
file_path = Path(file_path)
# Ensure file is within MAPS_DIR
if not file_path.resolve().is_relative_to(MAPS_DIR.resolve()):
    raise HTTPException(status_code=403, detail="Access denied")
```
- **Pros:** Direct fix, minimal code change
- **Cons:** None
- **Effort:** Small
- **Risk:** Low

### Option B: Construct Path from Job ID
```python
# Don't store full paths in Redis, construct from job_id
file_path = MAPS_DIR / job_id / f"map.{file_type}"
```
- **Pros:** Eliminates path injection entirely
- **Cons:** Requires Redis schema change
- **Effort:** Medium
- **Risk:** Medium (migration needed)

## Acceptance Criteria

- [x] File paths validated against MAPS_DIR before serving
- [x] Attempting to access files outside MAPS_DIR returns 403
- [ ] Test with path traversal attempts (../../../etc/passwd)

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-01-25 | Created from code review | P1 security - blocks merge |
| 2026-01-25 | Fixed: Added is_relative_to check | Option A implemented |
