---
title: "feat: Search-First Hero UI Redesign"
type: feat
status: completed
date: 2026-03-03
origin: docs/brainstorms/2026-03-03-search-first-ui-redesign-brainstorm.md
---

# feat: Search-First Hero UI Redesign

## Overview

Restructure the WOSMap frontend layout so the address search input is the clear entry point, the map is the dominant visual, and settings are compact and accessible. This follows the "search-first hero" pattern (Google Maps, Mapbox Studio) while keeping code changes minimal (see brainstorm: docs/brainstorms/2026-03-03-search-first-ui-redesign-brainstorm.md).

**Target layout:**
```
┌──────────────────────────────────────────────────┐
│  WOSMap                                  [history]│
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │  🔍  Enter an address or place...          │  │
│  └────────────────────────────────────────────┘  │
│  [inline error if search fails]                  │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │                                            │  │
│  │              LEAFLET MAP                   │  │
│  │          (tall, full-width)                │  │
│  │                                            │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  Scale [1:3463 ▾]  Size [20 cm ▸ warning?]       │
│  ▼ Advanced settings (layers, data source)       │
│                                                  │
│  [  Generate Map  ]                              │
│                                                  │
├──────────────────────────────────────────────────┤
│  [progress / results / history here]             │
└──────────────────────────────────────────────────┘
```

## Problem Statement

- The search input is buried inside `MapSelector.vue` with no heading or label — new users don't know where to type
- `max-w-4xl` (896px) container clips content too close to the viewport edge on common screen sizes
- The 2-column settings grid (`PrintSettings` + `LayerSettings`) takes as much visual weight as the map
- `alert()` is used for search errors — jarring and inconsistent with the design system

## Proposed Solution

**Approach A** (see brainstorm: minimal restructuring, not a full rewrite):

1. **Container widening** — `max-w-4xl` → `max-w-5xl` in `App.vue` and `AppHeader.vue` (must stay in sync)
2. **Search hero promotion** — add section heading above the search bar; improve placeholder; replace `alert()` with inline error
3. **Map height increase** — all four responsive breakpoints explicitly updated
4. **Settings toolbar** — compress `PrintSettings` to a compact flex row (Scale + Size) with clamping warning inline
5. **LayerSettings** → collapsible accordion, always accessible but not competing with the map
6. **Data source toggle** → stays below the settings row but styled more compactly

## Technical Considerations

### Files Changed

| File | Change |
|------|--------|
| `frontend/src/App.vue:5` | `max-w-4xl` → `max-w-5xl`; adjust `space-y-6` as needed |
| `frontend/src/components/layout/AppHeader.vue:3` | `max-w-4xl` → `max-w-5xl` (must stay in sync with App.vue) |
| `frontend/src/components/location/LocationSection.vue` | Add section heading above MapSelector; increase map height breakpoints |
| `frontend/src/components/MapSelector.vue` | Improve search input placeholder, label; replace `alert()` with inline error |
| `frontend/src/components/settings/PrintSettings.vue` | Compress to compact flex row; keep `sizeClamped` warning adjacent to input |
| `frontend/src/App.vue` (settings layout section) | Replace `grid grid-cols-1 lg:grid-cols-2 gap-6` with compact row + collapsible LayerSettings |

### Key Constraints

- **Do not extract search logic out of `MapSelector.vue`** — Nominatim API call, state, and Leaflet interaction are tightly coupled there. Making it visually prominent in-place is lower risk
- **`sizeClamped` warning must remain visible** — it's the only feedback that the size input was silently adjusted to the 5–25.6 cm range
- **`GenerateButton`** remains a separate full-width CTA below the settings row (not merged into the toolbar)
- **Header and main container `max-w` must always match** — a mismatch creates a visible misalignment at 896–1024px viewport widths

### Map Height Breakpoints

Update all four breakpoints explicitly (current → target):

| Breakpoint | Current | Target |
|------------|---------|--------|
| default (mobile) | `h-[300px]` | `h-[320px]` |
| `sm` (640px+) | `h-[350px]` | `h-[380px]` |
| `md` (768px+) | `h-[400px]` | `h-[460px]` |
| `lg` (1024px+) | `h-[450px]` | `h-[560px]` |

### LayerSettings Placement

LayerSettings will become a collapsible accordion section (using the same `<details>` / expand pattern as `HistoryList` in the codebase). It sits below the compact settings row, expanded by default on first load, collapsed after. Layers are not hidden — just below the fold.

### `alert()` Replacement

`MapSelector.vue` lines ~302, ~304 use `alert()` for search failures. Replace with a reactive `searchError` ref rendered as an inline error message below the search input, styled with `text-danger-400 text-sm`.

## System-Wide Impact

- **No backend changes** — purely frontend layout restructuring
- **No prop/event API changes** — component interfaces stay the same
- **Leaflet behavior unchanged** — only the wrapper heights and labels change
- **Results/history sections** — inherit the wider `max-w-5xl` container; the `sm:grid-cols-3` download button layout in results may reflow earlier (at lower viewport widths) — verify this looks correct

## Acceptance Criteria

### Layout
- [x] Main content container uses `max-w-5xl` (not `max-w-4xl`)
- [x] `AppHeader` container width matches the main container exactly
- [ ] No content is clipped or too close to viewport edges on a 1080px-wide screen

### Search Hero
- [x] There is a visible heading or label above the search input ("Find your place")
- [x] Search input placeholder reads "Enter an address or place..."
- [x] Search failures display inline error text below the input (not `alert()`)
- [ ] Searching by address still geocodes correctly via Nominatim and centers the map

### Map
- [x] Map height at `lg` breakpoint is 560px
- [x] All four responsive height values are explicitly set (no unspecified breakpoints)
- [ ] Leaflet map still renders, can be clicked to set location, and the coverage rectangle updates when scale/size changes

### Settings
- [x] Scale and Size controls appear in a compact single-row flex layout
- [x] `sizeClamped` warning text remains visible adjacent to the Size input when triggered
- [x] LayerSettings is accessible via a collapsible section below the compact row
- [x] Data source toggle (OSM/Overture) remains functional and visible
- [x] `GenerateButton` remains a full-width CTA below the settings area

### Regression
- [ ] Generate flow still works end-to-end (address → generate → download)
- [ ] Progress stages still display correctly below the generate button
- [ ] Results section (download, print buttons) displays correctly at the new container width
- [ ] HistoryList still displays correctly

## Dependencies & Risks

| Risk | Mitigation |
|------|-----------|
| Header/container width mismatch | Update both `App.vue` and `AppHeader.vue` in the same commit |
| `sizeClamped` warning lost in toolbar compression | Keep the warning as a conditional `<p>` below the Size input, not elsewhere |
| LayerSettings accordion UX regression | Default to expanded; add a clear toggle label |
| iOS scroll trap on taller map | Leaflet `scrollWheelZoom: false` already set; verify iOS Safari after height change |
| Results grid reflow at max-w-5xl | Manual test at 1024–1280px viewport |

## Sources & References

### Origin

- **Brainstorm document:** [docs/brainstorms/2026-03-03-search-first-ui-redesign-brainstorm.md](../brainstorms/2026-03-03-search-first-ui-redesign-brainstorm.md)
  - Key decisions carried forward: (1) Approach A — minimal restructure, not rewrite; (2) search-first hero layout; (3) settings always visible as compact toolbar

### Internal References

- Main container layout: `frontend/src/App.vue:5`
- Header container: `frontend/src/components/layout/AppHeader.vue:3`
- Map height breakpoints: `frontend/src/components/location/LocationSection.vue:8`
- Search bar implementation: `frontend/src/components/MapSelector.vue:4-47`
- Settings form: `frontend/src/components/settings/PrintSettings.vue`
- `sizeClamped` warning logic: `frontend/src/components/settings/PrintSettings.vue`
- Search `alert()` calls: `frontend/src/components/MapSelector.vue:~302,~304`
- Leaflet coverage rectangle solution: `docs/solutions/feature-implementation/leaflet-square-coverage-preview.md`
