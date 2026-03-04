# UI Redesign: Search-First Hero Layout

**Date:** 2026-03-03
**Status:** Draft
**Scope:** Frontend UI layout restructure

---

## What We're Building

A redesigned layout for WOSMap that puts the address search front and center, makes the map the primary visual element, and keeps settings accessible without cluttering the experience.

**Current problems:**
- Address input is buried inside `MapSelector.vue` — hard to discover
- Container is too close to the side on some viewports, causing content to be clipped
- Settings grid (2-col) takes up as much visual weight as the map
- No clear visual hierarchy guiding the user from "enter address" → "see map" → "generate"

---

## Why This Approach

The **search-first hero** pattern is established by tools like Google Maps and Mapbox Studio:
- Users understand "search bar = where I type my address"
- Map is the confirmation step, not the entry point
- Settings below map feel like "fine-tuning after I've chosen my spot"

---

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Entry point | Prominent search bar above map | Eliminates discoverability problem |
| Map size | Taller, full container width | Map is the primary interaction surface |
| Settings visibility | Always-visible compact toolbar below map | No hidden friction; scale + size are essential to preview the coverage rectangle |
| Container width | Wider (max-w-5xl or 6xl) + better horizontal padding | Fix the "too close to side" clipping issue |
| Generate button | Inline in settings toolbar or as a full-width CTA below toolbar | Keeps flow linear: search → map → tweak → generate |

---

## Layout Sketch

```
┌──────────────────────────────────────────────────┐
│  WOSMap                                  [history]│
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │  🔍  Enter an address or place...          │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │                                            │  │
│  │              LEAFLET MAP                   │  │
│  │          (tall, full-width)                │  │
│  │                                            │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  Scale [1:3463 ▾]  Size [20cm]  [▸ Generate]    │
│                                                  │
├──────────────────────────────────────────────────┤
│  [progress / results appear here]               │
└──────────────────────────────────────────────────┘
```

---

## Approaches Considered

### Approach A: Restructure existing components (Recommended)

Move the search input out of `MapSelector.vue` into a dedicated hero section in `App.vue`. Keep all existing Leaflet logic — only change layout and visual presentation.

- Extract search bar from MapSelector as a prop-driven callback
- Add clear label/placeholder: "Enter an address or place"
- Increase map height (450px → 550px+ on desktop)
- Replace 2-column settings grid with a single compact flex row: `Scale | Size | Layers toggle | Generate`
- Widen container to `max-w-5xl` and ensure consistent padding

**Pros:** Minimal logic change, preserves all Leaflet behavior
**Cons:** MapSelector component boundary gets a bit fuzzy

### Approach B: Full layout rewrite

Redesign the page sections completely. New top-level sections: `<HeroSearch>`, `<MapView>`, `<SettingsBar>`, `<ActionBar>`.

**Pros:** Clean separation of concerns, easier to extend
**Cons:** More refactoring, higher risk of regressions

### Approach C: Floating search card on full-viewport map

Map fills 100vh, search + settings float as a card panel.

**Pros:** Most immersive, very modern
**Cons:** Difficult to integrate with progress/results display; conflicts with page scroll

---

## Recommended Approach

**Approach A** — restructure existing components without a full rewrite.

The existing component boundaries are mostly fine. The main changes are:
1. Promote the search bar to the top of the page with clear visual hierarchy
2. Increase map height
3. Compress settings into a single-row toolbar
4. Fix container padding/width

This is the minimum change to solve the stated problems.

---

## Open Questions

_None — all resolved during brainstorm._

## Resolved Questions

- **What's the biggest pain point?** → Address input is buried
- **Preferred layout?** → Search-first hero (prominent search at top, map below)
- **Settings visibility?** → Always visible below map as a compact toolbar

---

## Out of Scope

- Redesigning the progress/results section (works fine)
- Mobile-specific bottom sheet patterns
- Any new features or backend changes
