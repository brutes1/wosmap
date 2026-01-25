---
status: pending
priority: p3
issue_id: "014"
tags: [code-review, quality, frontend, ux]
---

# Improve Frontend Error Handling

## Problem Statement

Using browser `alert()` for error messages is poor UX. Should use proper Vue notification component.

## Findings

**Location:** `frontend/src/components/MapSelector.vue:323,327`

```javascript
alert('Address not found. Try a different search.')
alert('Search failed. Please try again.')
```

## Proposed Solutions

### Option A: Emit Error Events (Recommended)
```javascript
this.$emit('error', { message: 'Address not found', type: 'warning' })
```
Parent component handles display with toast/notification.

- **Effort:** Small
- **Risk:** Low

## Acceptance Criteria

- [ ] No browser alert() calls
- [ ] Proper toast/notification for errors
