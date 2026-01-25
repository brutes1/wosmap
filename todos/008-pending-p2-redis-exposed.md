---
status: pending
priority: p2
issue_id: "008"
tags: [code-review, security, infrastructure, redis]
---

# Redis Port Exposed Without Authentication

## Problem Statement

Redis port 6379 is exposed on the host without authentication, allowing direct access to all stored data including job data and printer credentials.

## Findings

**Location:** `docker-compose.yml:56-57`

```yaml
redis:
  ports:
    - "6379:6379"  # Exposed!
```

## Proposed Solutions

### Option A: Remove Port Mapping (Recommended)
```yaml
redis:
  # Remove ports section - only accessible within Docker network
  # ports:
  #   - "6379:6379"
```
- **Effort:** Small
- **Risk:** Low

### Option B: Add Redis Auth
```yaml
redis:
  command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
```
- **Effort:** Small
- **Risk:** Low (update clients too)

## Acceptance Criteria

- [ ] Redis not accessible from host network
- [ ] OR Redis requires authentication
