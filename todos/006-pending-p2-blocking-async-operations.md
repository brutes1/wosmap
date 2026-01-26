---
status: pending
priority: p2
issue_id: "006"
tags: [code-review, architecture, backend, performance]
---

# Blocking Operations in Async Context

## Problem Statement

The `slice_and_print()` function is synchronous and blocking (slicing can take 5 minutes), but it's called directly in an async endpoint, blocking the entire event loop.

## Findings

**Location:** `backend/main.py:396-401`

```python
# This BLOCKS the entire async event loop!
result = slice_and_print(
    stl_path=stl_path,
    printer_config=config,
    profile_path=None
)
```

## Proposed Solutions

### Option A: Queue Print Jobs (Recommended)
```python
@app.post("/api/maps/{job_id}/print")
async def send_to_printer(job_id: str):
    # Queue the print job, don't execute it
    r.lpush("print_jobs", json.dumps({"job_id": job_id, ...}))
    return {"status": "queued", "message": "Print job queued"}
```
- **Effort:** Medium (requires new worker)
- **Risk:** Low

### Option B: Thread Pool Executor
```python
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=2)

result = await asyncio.get_event_loop().run_in_executor(
    executor, slice_and_print, stl_path, config, None
)
```
- **Effort:** Small
- **Risk:** Medium (still consumes server resources)

## Acceptance Criteria

- [ ] Print operations don't block API requests
- [ ] Multiple API requests can be handled during printing
