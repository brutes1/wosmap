---
status: pending
priority: p2
issue_id: "013"
tags: [code-review, architecture, backend, redis]
---

# No Job Cleanup Strategy

## Problem Statement

No TTL on job results in Redis, no cleanup of old map files. Redis and disk will grow indefinitely.

## Findings

Jobs and files accumulate without cleanup:
- Redis `result:{job_id}` keys persist forever
- Map files in `/data/maps` never deleted

## Proposed Solutions

### Option A: TTL on Redis Keys (Recommended)
```python
r.set(f"result:{job_id}", json.dumps({...}))
r.expire(f"result:{job_id}", 60 * 60 * 24 * 7)  # 7 days
```
- **Effort:** Small
- **Risk:** Low

### Option B: Cleanup Worker
- Separate worker to delete old files
- **Effort:** Medium
- **Risk:** Low

## Acceptance Criteria

- [ ] Old job data automatically cleaned up
- [ ] Disk usage bounded
