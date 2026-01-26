---
status: completed
priority: p1
issue_id: "005"
tags: [code-review, security, backend, credentials]
---

# Printer Credentials Stored in Plain Text

## Problem Statement

Printer access codes (8-digit credentials) are stored in Redis as plain JSON without encryption. Combined with exposed Redis port and no authentication, credentials are easily retrievable.

**Why it matters:** Unauthorized printer access, potential for malicious print jobs, physical security risk.

## Findings

**Location:** `backend/main.py:284-289`

```python
@app.post("/api/printer/config")
async def configure_printer(config: PrinterConfig):
    r = get_redis()
    r.set("printer_config", json.dumps(config.dict()))  # Plain text!
```

**Compounding factors:**
- Redis port 6379 exposed in docker-compose.yml
- GET endpoint returns printer IP and serial (lines 334-349)
- No authentication on endpoints

## Proposed Solutions

### Option A: Encrypt at Rest (Recommended)
```python
from cryptography.fernet import Fernet

ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
fernet = Fernet(ENCRYPTION_KEY)

@app.post("/api/printer/config")
async def configure_printer(config: PrinterConfig):
    encrypted = fernet.encrypt(json.dumps(config.dict()).encode())
    r.set("printer_config", encrypted)
```
- **Pros:** Credentials protected even if Redis accessed
- **Cons:** Requires key management
- **Effort:** Small
- **Risk:** Low

### Option B: Environment Variables Only
- Don't store in Redis at all
- Use env vars: `PRINTER_IP`, `PRINTER_CODE`, `PRINTER_SERIAL`
- **Pros:** Simpler, standard secrets management
- **Cons:** No runtime configuration
- **Effort:** Small
- **Risk:** Low

### Option C: Secrets Manager
- Use HashiCorp Vault or cloud secrets manager
- **Pros:** Enterprise-grade security
- **Cons:** Infrastructure overhead
- **Effort:** Large
- **Risk:** Low

## Acceptance Criteria

- [x] Printer access code not stored in plain text
- [x] Credentials not exposed via GET endpoint
- [x] Redis access restricted (remove port exposure)

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-01-25 | Created from code review | Consider env vars for simplicity |
| 2026-01-25 | Fixed: Env vars + short TTL Redis storage | Option B + hybrid approach |
