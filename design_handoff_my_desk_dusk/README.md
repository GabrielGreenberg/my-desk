# Handoff: My Desk — Dusk

## Overview

"My Desk" is a personal daily-focus surface: a glanceable clock, a weather pill, a **Today** list that mixes plain to-dos with *timer to-dos* (tasks with a target duration and a scrubbable progress bar), and a **Backlog** section pulled from Notion.

The **Dusk** direction is an atmospheric, time-of-day-aware theme: the whole UI re-tints as the day progresses (dawn → afternoon → golden hour → night), while a single user-controllable accent hue threads through every surface, border, and timer state. The intent is a calm, cinematic "desk lamp glowing at your screen" feel that changes subtly across the day but stays legible and non-distracting.

## About the Design Files

The files in `prototype/` are **design references created in HTML/CSS/vanilla JS** — a working prototype showing intended look and behavior. They are **not** production code to drop in as-is.

Your job is to **recreate this design inside the target codebase's environment** (React, Next, Vue, SwiftUI, whatever the real app is built in) using that codebase's existing patterns, state management, styling system, component library, data layer, etc. If no environment exists yet, pick the framework most appropriate for the project and implement there.

Use the prototype as a precise visual + behavioral spec:
- Open `prototype/My Desk - Dusk.html` in a browser to interact with it.
- `dusk-theme.js` contains the exact color-derivation math per time-of-day and hue. **This file's logic should be ported faithfully** — it's the heart of the design.
- `dusk-app.js` contains the interaction logic (timers, scrubbing, drag reorder, edit-in-place). Port the *behavior*, rewrite the *mechanics* in the target framework's idioms.
- `tweaks-panel.jsx` and `dusk-tweaks.jsx` are a scaffold used only for design-time tweaking in the prototype. **Do not ship these.**

## Fidelity

**High-fidelity.** Colors, typography, spacing, radii, animation timings, and interactions are all final. Recreate pixel-perfectly using the target codebase's styling system. The single source of truth for color values is the `duskPalette()` function in `prototype/dusk-theme.js` — port its logic exactly; do not approximate with static tokens.

## Screens / Views

There is one primary view: **the desk** (desktop + mobile responsive, same layout, tightened paddings on mobile).

### Desk (single-page)

**Purpose.** A calm daily surface the user lands on to see time, weather, today's tasks with timers, and backlog items pulled from Notion.

**Layout.**
- Centered column: `max-width: 680px`, padded `56px 28px 80px` (top, sides, bottom). On viewport ≤ 720px: padding tightens to `~36px 18px 60px`.
- A fixed, decorative **glow** sits behind everything: `60vw × 60vw` (capped 700×700), radial gradient of `--accent-glow`, positioned `top: -15%; right: -15%`, `filter: blur(40px)`, `z-index: 0`, `pointer-events: none`.
- Content stacks: **Header** → **Today section** → **Backlog section**.

**Header (top row).**
- Flex row, `justify-content: space-between`, `margin-bottom: 36px`.
- Left:
  - **Clock** — current time, `HH:MM` 24h or 12h per locale. Font: **Fraunces**, weight 300, size `clamp(44px, 7vw, 60px)`, line-height 1, letter-spacing −0.5, `font-variant-numeric: tabular-nums`, `font-variation-settings: '"SOFT" 100, "opsz" 144'` (Fraunces optical-size + soft axes). Color: `--text`.
  - **Date line** — below clock, `margin-top: 4px`. Font: Fraunces italic, 14px, color `--text-dim`. Format: `"Thursday, October 16"` followed by a `.phase` span that reads the current time-of-day phase ("DAWN" / "AFTERNOON" / "GOLDEN HOUR" / "NIGHT"). The phase span is **Geist 11px**, uppercase, letter-spacing 1.5, weight 500, colored `--accent`, left-margin 8px.
- Right:
  - **Weather pill** — 8×14 padding, background `--surface`, `backdrop-filter: blur(12px)`, 1px border `--border`, fully rounded (`border-radius: 999px`). Geist 11px, weight 500, tabular-nums, color `--text-dim`. Format: `◐  58° · cloudy · sunset 7:42`. The leading glyph is 13px and colored `--accent`.

**Section heads.**
- "TODAY" and "BACKLOG" labels — Geist 10px, letter-spacing 2, uppercase, weight 500, color `--text-dim`, `margin-bottom: 12px`.
- Right side of section head contains a meta readout (e.g. `3 of 5 · 42m left`). Geist 10px, tabular-nums, color `--text-mute`.

**Today list — list container.** Flex column, `gap: 6px`.

**Today list — item row (the core component).**

Each row is a horizontally laid out card:

- Container `.item`:
  - `position: relative`, `background: var(--surface)` (semi-transparent, see color section), `backdrop-filter: blur(12px)`.
  - `border: 1px solid var(--border)`, `border-radius: 10px`, `overflow: hidden`, `min-height: 48px`.
  - On `:hover` → `border-color: var(--border-hi)`.
  - On `.running` → `border-color: var(--accent-mid)`.
  - On drag → `opacity: 0.4` (while being reordered).
- **Timer track layers**, z-stacked inside the item (only present when the item is a timer):
  - `.bar-fill` — `position: absolute; inset: 0; width: <pct>%`, background `--bar-fill`, `transition: width 0.35s ease, background 0.6s ease`, `pointer-events: none`, `z-index: 0/1`.
  - `.playhead` — a 2px-wide vertical line at the current elapsed %, absolute top/bottom, background `--accent`, `pointer-events: none`. When item is `.running`, add box-shadow `0 0 12px var(--accent), 0 0 3px var(--accent)` for a "live" glow. Hidden on `.done` and rows with no progress yet.
  - `.scrub-handle` — absolute, 18px wide (invisible hit target), `cursor: ew-resize`, `touch-action: none`, `z-index: 2`. Its `::before` pseudo is the visible grip: 4×20px rounded rect, background `--accent`, box-shadow `0 0 0 1.5px var(--bg-solid), 0 1px 4px rgba(0,0,0,0.25)`, opacity 0.85, scales to 1.15 on row hover, 1.25 on active drag.
  - `.item.done .bar-fill { background: var(--bar-done) }` — completed rows show a calm, flat fill.
- **Row content** `.item-content`:
  - `position: relative; z-index: 3` so it sits above the track layers.
  - Flex row, `gap: 10px`, padding `10px 13px` (mobile: `9px 10px`, gap 7).
  - Children in order:
    1. **Check button** `.check-btn` — 18×18, circular, 1.5px border `--text-mute`, transparent background. When `.on`: filled with `--accent`, shows a ✓ glyph in `--bg-solid`. Hover: border → `--accent`.
    2. **Label input** `.item-label` — transparent, borderless, flex: 1, 14px (mobile 13.5), color `--text`. Placeholder color `--text-mute`. When row is `.done`: opacity 0.5. When row is `.checked` and **not** a timer: adds `text-decoration: line-through`.
    3. **Play button** `.play-btn` (timer rows only) — small transport-style control with ▶ / ❚❚ glyphs.
    4. **Time readout** `.timer-display` — Geist 11px (mobile 10), weight 500, tabular-nums, color `--text-dim`, format `MM:SS / MM:SS` (elapsed / total). The elapsed value is actually a tiny editable input so users can type a time.
    5. **±30 min buttons**, **notes toggle**, and overflow actions appear on hover.
  - Optional **notes area** expands below when toggled: a multiline textarea styled to match the surface.
- **Drag-to-reorder indicator** `.drop-indicator` — 2px accent-colored bar that appears between items during drag.

**Backlog section.** Same visual vocabulary as today rows, but non-interactive timer wise. Each row shows a title and a `.due` readout on the right (Geist 10px, tabular-nums, color `--text-mute`, letter-spacing 0.3). Overdue items use a warmer color (rough target: `oklch(0.65 0.18 30)` for dusk/night, `#b85a3a` tone for light phases).

## Interactions & Behavior

### Time-of-day auto-phase

- Default mode: the theme automatically picks a phase from `new Date().getHours()`:
  - `5..8` → `dawn`
  - `9..16` → `day` (labeled "AFTERNOON" in the UI)
  - `17..19` → `dusk` (labeled "GOLDEN HOUR")
  - otherwise → `night`
- When the hour crosses a boundary, all CSS variables transition smoothly (body `transition: background 2s ease, color 0.8s ease`; glow 1.5s ease).
- The user can override with a Time-of-Day control (Auto / Dawn / Afternoon / Golden hour / Night). This override persists.

### Hue dial

- A single numeric value `accentHue` (0–360) threads through the palette. Every color in the palette is derived from this hue via `oklch()`, so shifting it re-tints the entire UI coherently. Default: ~35 (warm amber/orange).
- The dial lives in the Tweaks panel in the prototype; in production this should live somewhere out of the way (a settings drawer or hidden preference) — it's a personalization knob, not a primary control.

### Timer rows — full interaction set

- **Start / pause:** click `.play-btn`. Toggles `item.running`.
- **Running state tick:** while running, `item.elapsed` increments (once per second). Update `.bar-fill` width and playhead left to `(elapsed / totalSeconds) * 100%`.
- **Done state:** when `elapsed >= totalSeconds`, auto-stop, set `.done`, play a soft bell sound (unless mute). `.bar-fill` color swaps to `--bar-done`.
- **Scrub:** mousedown / touchstart on `.scrub-handle` begins a drag. While dragging, track pointer X against row's bounding rect; `elapsed = clamp(ratio * totalSeconds)`. If the row was running when drag started, pause on grab and resume on release (unless scrubbed past the end).
- **Edit elapsed by typing:** the elapsed side of `.timer-display` is an input. Typing a `MM:SS` and blurring sets `elapsed`.
- **Edit total duration:** small pencil affordance on hover → inline input.
- **±30 min buttons** — hover-revealed, adjust `totalSeconds` by 1800s.
- **Notes toggle** — per-item toggle that reveals a textarea under the row.
- **Drag to reorder** — HTML5 DnD on `.item`. The `.scrub-handle` must suppress `dragstart` (the prototype does this with `e.target.closest('.scrub-handle')` check; replicate the equivalent in whatever framework you use).
- **Check off a task:** clicking `.check-btn` toggles `checked`. For non-timer rows this applies line-through; for timer rows it collapses progress and sets the row to a calm "done" state.
- **Archive done:** a section action clears checked rows.

### Sounds

- A soft completion bell when a timer reaches 100%. Mutable via a Tweaks toggle in the prototype; in production wire to user preferences.

### Responsive

- Single breakpoint at 720px: tighter paddings, slightly smaller clock (`42px`), smaller timer readout (10px), tighter item padding.
- Everything is a single column — no grid changes between desktop and mobile.

## State Management

Minimum state shape:

```ts
type Item = {
  id: string;
  label: string;
  kind: 'todo' | 'timer';
  checked: boolean;                  // plain check-off
  // timer-only:
  totalSeconds?: number;
  elapsed?: number;
  running?: boolean;
  done?: boolean;                    // elapsed >= total
  notes?: string;
  notesOpen?: boolean;
};

type Theme = {
  hue: number;                        // 0..360
  phaseMode: 'auto' | 'dawn' | 'day' | 'dusk' | 'night';
  muteBell: boolean;
};

type AppState = {
  today: Item[];                     // ordered, drag-reorderable
  backlog: BacklogItem[];            // fetched from Notion
  theme: Theme;
};
```

Persistence in the prototype is `localStorage`. In production:
- `theme` → user preferences (server or local).
- `today` → whatever the app's task store is (Notion, custom, etc.).
- `backlog` → read-through from Notion with a sensible cache.

## Design Tokens

**Do not hardcode hex values.** Every runtime color is computed from `(phase, hue)` by `duskPalette()` in `prototype/dusk-theme.js` — port that function and its per-phase table exactly. Applying a theme means writing these CSS custom properties (or the framework equivalent) on the root:

- `--bg` — background gradient (per-phase)
- `--bg-solid` — flat fallback / used where alpha blending over the gradient isn't desired
- `--text`, `--text-dim`, `--text-mute` — primary / secondary / tertiary text
- `--surface`, `--surface-hi` — card backgrounds (semi-transparent so the gradient shows through)
- `--border`, `--border-hi` — subtle / hovered borders
- `--accent`, `--accent-mid`, `--accent-glow` — accent triplet (the glow is used in the decorative background and running-timer shadow)
- `--bar-fill` — timer progress fill
- `--bar-done` — completed-row fill (desaturated version of `--bar-fill`)

**Timer-bar contrast rule (important).** On light phases (`dawn`, `day`) the fill is a *dark* oklch (L ≈ 0.40) against a near-white surface; on dark phases (`dusk`, `night`) the fill is a *light* oklch (L ≈ 0.68–0.70) against a dark surface. In both cases the filled portion should read as the more-present, more-saturated region and the empty track as the airier one. Do not flip this.

### Spacing scale (observed)
- 4, 6, 8, 10, 12, 13, 14, 18, 20, 28, 36, 48, 56, 80 px — not a strict 4/8 system; reflect the prototype's numbers.

### Typography
- **Fraunces** (300; SOFT=100, opsz=144) — clock, date (italic for date).
- **Geist** (300–600) — all UI text: labels, times, pills, buttons.
- **No monospace.** Use Geist with `font-variant-numeric: tabular-nums` wherever digits need to align.

### Radii
- Items: 10px
- Weather pill / other pills: 999px (full)
- Small controls (check button): 50%
- Scrub grip: 2px

### Shadows / glows
- Running-playhead glow: `0 0 12px var(--accent), 0 0 3px var(--accent)`
- Scrub grip: `0 0 0 1.5px var(--bg-solid), 0 1px 4px rgba(0,0,0,0.25)`
- Ambient background glow: `radial-gradient(circle, var(--accent-glow), transparent 70%)` blurred 40px

### Animation timings
- Body background phase transition: 2s ease
- Body color transition: 0.8s ease
- Ambient glow transition: 1.5s ease
- `.bar-fill` width: 0.35s ease; color: 0.6s ease
- Border/hover transitions: 0.15–0.2s

## Assets

- **Fonts** — Google Fonts: Fraunces (opsz + SOFT axes + 300–600), Geist (300–600). Keep the JetBrains Mono import out of production; it is no longer used.
- **No bitmap images.** The only "imagery" is the ambient radial-gradient glow, which is CSS.
- **Icons** — the prototype uses Unicode glyphs (◐ ▶ ❚❚ ✓). Replace with the codebase's icon system if one exists; keep glyphs tiny and monochrome, no decorative color.

## Files

In `prototype/`:

- `My Desk - Dusk.html` — the single-page prototype. Structure + CSS + script includes.
- `dusk-theme.js` — **primary reference.** `window.duskPalette(phase, hue)` → token bag; `window.applyDuskTheme(phase, hue)` writes CSS custom properties. Port the math.
- `dusk-app.js` — interaction logic: timer tick, scrubbing, drag reorder, inline editing, localStorage persistence. Port the behavior; rewrite in your framework.
- `dusk-tweaks.jsx`, `tweaks-panel.jsx` — design-time-only controls used in the prototype. **Do not ship.**
- `shared-data.js` — seed data used by the prototype. Replace with real data sources.

## Notes for the implementer

- Keep the theme engine *pure*: `palette(phase, hue) → token bag`. Apply once on mount and on every phase/hue change. Don't couple palette math to component code.
- The timer row is the most reused component in the design — build it once, well, and compose the list from it.
- The scrub handle lives above the drag-to-reorder surface. In React, this usually means stopping propagation on pointerdown/dragstart at the handle.
- Treat the time-of-day phase transition as a top-level concern: the *body* animates, not individual components, so a framework-level theme provider that writes CSS custom properties is the right shape.
- Resist the urge to add more colors. The whole design runs on a single hue + luminance shifts across phases. That's the point.
