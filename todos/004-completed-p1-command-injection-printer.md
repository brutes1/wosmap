---
status: completed
priority: p1
issue_id: "004"
tags: [code-review, security, backend, printer]
---

# Command Injection Risk in Printer Module

## Problem Statement

File paths passed to subprocess commands without validation. If an attacker can control Redis data, they could inject commands via malicious file paths.

**Why it matters:** Remote code execution on the server.

## Findings

**Location:** `backend/printer.py:85-111`

```python
def slice_stl(self, stl_path: str, output_path: str, profile_path: Optional[str] = None):
    cmd = [orca_path, "--export-3mf", output_path]

    if profile_path and os.path.exists(profile_path):
        cmd.extend(["--load-settings", profile_path])

    cmd.append(stl_path)  # User-controllable path!

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
```

**Note:** Using list format (not `shell=True`) provides some protection, but path validation is still missing.

## Proposed Solutions

### Option A: Path Validation (Recommended)
```python
def slice_stl(self, stl_path: str, output_path: str, ...):
    stl_path = Path(stl_path)
    output_path = Path(output_path)

    # Validate paths are within expected directories
    if not stl_path.resolve().is_relative_to(MAPS_DIR):
        raise PrinterError("Invalid STL path")
    if not output_path.resolve().is_relative_to(MAPS_DIR):
        raise PrinterError("Invalid output path")

    # Validate file exists and is correct type
    if not stl_path.exists() or not stl_path.suffix == '.stl':
        raise PrinterError("Invalid STL file")
```
- **Pros:** Prevents path manipulation
- **Cons:** None
- **Effort:** Small
- **Risk:** Low

### Option B: Sandbox OrcaSlicer Process
- Run slicer in container/sandbox
- Mount only necessary directories
- **Effort:** Large
- **Risk:** Medium

## Acceptance Criteria

- [x] All file paths validated before subprocess execution
- [x] Paths must be within MAPS_DIR
- [x] File extensions validated
- [ ] Test with malicious path inputs

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-01-25 | Created from code review | List format subprocess safer but still validate |
| 2026-01-25 | Fixed: Added validate_file_path() in printer.py | Option A implemented |
