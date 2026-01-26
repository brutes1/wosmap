---
status: pending
priority: p2
issue_id: "009"
tags: [code-review, security, backend, printer, tls]
---

# Insecure TLS Configuration for Printer Communication

## Problem Statement

Certificate validation is completely disabled for MQTT and FTP connections to the printer, making connections vulnerable to MITM attacks.

## Findings

**Location:** `backend/printer.py:267-268`

```python
client.tls_set(cert_reqs=ssl.CERT_NONE)
client.tls_insecure_set(True)
```

## Proposed Solutions

### Option A: Enable Certificate Validation
```python
client.tls_set(cert_reqs=ssl.CERT_REQUIRED, ca_certs="/path/to/ca.crt")
client.tls_insecure_set(False)
```
- **Effort:** Medium (need printer CA cert)
- **Risk:** Low

### Option B: Document as Known Limitation
- Bambu printers use self-signed certs
- Add warning in README
- **Effort:** Small
- **Risk:** Medium (accepted risk)

## Acceptance Criteria

- [ ] TLS validation enabled OR risk documented
- [ ] No silent MITM vulnerability
