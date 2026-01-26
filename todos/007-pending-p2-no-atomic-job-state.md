---
status: pending
priority: p2
issue_id: "007"
tags: [code-review, architecture, backend, redis]
---

# No Atomic Job State Transitions

## Problem Statement

Job creation and status updates use separate Redis operations without atomicity. If the server crashes between operations, data can be inconsistent.

## Findings

**Location:** `backend/main.py:178-188`

```python
r.lpush("map_jobs", json.dumps(job))  # Operation 1
r.set(f"result:{job_id}", json.dumps({...}))  # Operation 2
# If crash between these, job in queue but no status!
```

## Proposed Solutions

### Option A: Redis Pipeline (Recommended)
```python
pipe = r.pipeline()
pipe.lpush("map_jobs", json.dumps(job))
pipe.set(f"result:{job_id}", json.dumps(initial_status))
pipe.execute()
```
- **Effort:** Small
- **Risk:** Low

## Acceptance Criteria

- [ ] Job creation is atomic
- [ ] No orphaned jobs possible
