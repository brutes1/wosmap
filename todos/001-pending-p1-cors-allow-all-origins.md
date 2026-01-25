---
status: pending
priority: p1
issue_id: "001"
tags: [code-review, security, backend]
---

# CORS Allow All Origins Vulnerability

## Problem Statement

The backend CORS configuration allows requests from ANY origin (`*`) while also enabling credentials. This is a dangerous combination that allows malicious websites to make authenticated requests to the API.

**Why it matters:** Any malicious website can make API calls to the backend, submit map jobs, configure printers, and download files on behalf of users.

## Findings

**Location:** `backend/main.py:38`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # VULNERABLE
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Evidence:** Security review identified this as a critical vulnerability enabling CSRF attacks.

## Proposed Solutions

### Option A: Restrict to Frontend Origin (Recommended)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
- **Pros:** Simple fix, immediate protection
- **Cons:** Hardcoded URL
- **Effort:** Small
- **Risk:** Low

### Option B: Environment Variable Configuration
```python
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    ...
)
```
- **Pros:** Flexible for different environments
- **Cons:** Requires env var management
- **Effort:** Small
- **Risk:** Low

## Acceptance Criteria

- [ ] CORS only allows specific frontend origins
- [ ] Configuration works for both dev and production
- [ ] Verify cross-origin requests from other domains are blocked

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-01-25 | Created from code review | Critical security issue |
