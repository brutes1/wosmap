---
status: pending
priority: p1
issue_id: "003"
tags: [code-review, security, backend, authentication]
---

# No Authentication on API Endpoints

## Problem Statement

None of the API endpoints require authentication. All functionality is publicly accessible including printer configuration, file downloads, and job management.

**Why it matters:**
- Anyone can enumerate job IDs and download other users' maps
- Anyone can reconfigure the printer or send malicious files
- Printer access codes retrievable via GET endpoint
- Unlimited job submissions without rate limiting

## Findings

**Affected endpoints:**
- `POST /api/maps` - Submit map generation jobs
- `GET /api/maps/{job_id}` - View any job status
- `GET /api/maps/{job_id}/download` - Download any job's files
- `POST /api/printer/config` - Configure printer with credentials
- `GET /api/printer/config` - Retrieve printer config (exposes IP/serial)
- `POST /api/maps/{job_id}/print` - Send files to printer

## Proposed Solutions

### Option A: API Key Authentication (Recommended for MVP)
```python
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != os.environ.get("API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key

@app.post("/api/maps")
async def create_map(request: MapRequest, _: str = Depends(verify_api_key)):
    ...
```
- **Pros:** Simple, works for single-user/internal use
- **Cons:** No multi-user support
- **Effort:** Small
- **Risk:** Low

### Option B: Session-Based Auth
- Implement login endpoint
- Use secure cookies for session
- Associate jobs with user sessions
- **Effort:** Medium
- **Risk:** Medium

### Option C: OAuth2/JWT (Production)
- Full OAuth2 flow
- JWT tokens with expiry
- User management
- **Effort:** Large
- **Risk:** Low (but complex)

## Acceptance Criteria

- [ ] All sensitive endpoints require authentication
- [ ] Unauthorized requests return 401
- [ ] Jobs associated with authenticated user
- [ ] Users can only access their own jobs

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-01-25 | Created from code review | Decide auth strategy based on use case |
