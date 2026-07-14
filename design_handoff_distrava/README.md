# Handoff: DISTRAVA — local-first training analysis app

## Overview
DISTRAVA is a desktop web app for a single technical user: a runner/gym-goer who wants deep
analysis of his own training, self-hosted and free, with no data leaving his machine. The core
promise is **"you vs. your past self"** — Strava's paywalled analysis (best efforts, fitness
trends, PRs) without the subscription or the cloud. It must feel like a serious analysis tool,
not a motivational app: no social feed, no onboarding funnel, no growth mechanics.

## About the Design Files
The `.dc.html` files in this bundle are **design references** — HTML prototypes showing the
intended look and behavior. They are **not** production code to copy directly. They were authored
in a component runtime (`support.js`) purely to make the prototypes interactive; ignore that
runtime entirely.

**Your task is to recreate these designs in the target stack:**
- **Flask + Jinja2 templates** for markup
- **Vanilla hand-written CSS** (no Tailwind, no CSS framework)
- **Chart.js 4.x via CDN** for all charts
- **No React, no Vue, no npm, no build step**

Every chart in the mocks is deliberately a Chart.js line or bar chart — nothing here requires a
chart type Chart.js can't render. Interactivity in the prototypes (sorting, filtering, tab
toggles, import progress) should be reimplemented as small vanilla-JS handlers or server-side
Jinja logic as appropriate.

## Fidelity
**High-fidelity (hifi).** Colors, typography, spacing, and interactions are final. Recreate the UI
pixel-accurately using the hex values, type specs, and measurements documented below.

---

## Design Tokens

### Color
| Token | Hex | Role |
|-------|-----|------|
| bg-base | `#0B0B0F` | App background |
| bg-sidebar | `#0D0D12` | Sidebar background |
| surface | `#16161C` | Card / panel |
| surface-2 | `#1E1E26` | Elevated surface, pills, inputs-hover |
| surface-input | `#101015` | Input / dropzone / segmented-control track |
| row-hover | `#1A1A21` | Table row hover / active fill |
| border | `#22222A` | Card border |
| border-strong | `#2C2C36` / `#33333D` | Pill border / button border |
| divider | `#1C1C22` / `#17171D` / `#26262E` | Dividers (outer / inner-row / header-rule) |
| nav-active-bg | `#17171D` | Active sidebar item background |
| accent | `#C4F82A` | Electric lime — progress, active state, primary actions, positive delta. **Only accent in the app.** |
| accent-hover | `#d6ff5c` | Lime hover (links, chart hover bars) |
| negative | `#E0685A` | Negative delta / destructive only — never brand |
| text-primary | `#ECECEF` | Primary text |
| text-secondary | `#9C9CA6` | Secondary text |
| text-muted | `#5E5E68` | Labels, captions, muted numbers |
| text-faint | `#3A3A42` | Disabled controls |

Type-pill accent dots: Run `#7FB2E8`, Ride `#8FD1B0`, Gym `#C9A46B`.
HR-zone bar colors: Z1 `#3A6B4A`, Z2 `#4E7FB0`, Z3 `#B0A24E`, Z4 `#C08A4E`, Z5 `#C4F82A`.

### Typography
Two families, loaded from Google Fonts:
- **Inter** (400/500/600/700/800) — all UI text.
- **JetBrains Mono** (400/500/600/700) — **every number and datum** (stats, table cells, dates,
  paces, HR, axis ticks, code-like labels). Numbers are the product; give them their own voice.

Always set `font-variant-numeric: tabular-nums` on numeric mono text so columns align.

Scale:
| Role | Family / weight / size | Notes |
|------|------------------------|-------|
| display | Inter 700 · 56px · `-0.03em` | hero empty-state headlines |
| page-title | Inter 700 · 32px · `-0.025em` | activity title |
| heading | Inter 600 · 24px / 16–17px | panel + section titles |
| body | Inter 400 · 15px · line-height 1.55 | prose |
| caption | Inter 500 · 12px · `0.10–0.14em` uppercase | stat-card labels |
| numeric-lg | JetBrains Mono 500 · 42–64px · `-0.02em` | key stats |
| numeric-table | JetBrains Mono 500 · 13–15px | table/data cells |
| mono-label | JetBrains Mono · 10–11px · `0.06–0.16em` uppercase | eyebrows, axis, meta |

### Spacing / shape
- Card radius `14px`; pill radius `20px`; button/input radius `8–9px`; small chips `7px`.
- Card padding `20–24px`; content gutter `32px`; content max-width `1160px` (Import/Settings `680–720px`).
- Sidebar width `248px`, fixed. Top bar height `64px`, fixed.
- Card border always `1px solid #22222A`.
- Accent glow used sparingly: `box-shadow: 0 0 8px rgba(196,248,42,0.6)` on the small lime status dots.

---

## App Shell (persistent layout)
Two-column flex: fixed `248px` sidebar + fluid content column. Content column is
`display:flex; flex-direction:column` with a fixed `64px` top bar and an independently
scrolling body (`flex:1; overflow-y:auto`). The sidebar and top bar never scroll.

**Sidebar contents (top → bottom):**
1. Wordmark (see below), padding `8px 12px 22px`.
2. Nav, `gap:2px`. Item = `padding:10px 14px; border-radius:9px`. Label Inter 500/14px.
   - **Default:** label `#9C9CA6`.
   - **Hover:** background `#15151B`.
   - **Active:** background `#17171D`, label `#ECECEF` weight 600, plus a `3px` lime bar
     absolutely positioned at the left edge (`top:8px; bottom:8px; border-radius:2px`).
   - **Coming soon:** whole row `opacity:0.5`, plus a right-aligned `SOON` pill (JetBrains Mono
     9px, `#5E5E68`, `1px solid #2C2C36`, radius 20px, padding `2px 7px`). Not clickable.
3. Nav order with `1px #1C1C22` dividers (`margin:12px 14px`) between groups:
   `Dashboard`, `Activities` — divider — `Routes (SOON)`, `Strength (SOON)` — divider —
   `Coach (SOON)`, `Insights (SOON)` — divider — `Import`, `Settings`.
   > NOTE: the original brief listed `Best Efforts (SOON)` and `Training Load (SOON)` after
   > Activities; the user removed both during design. Final nav is as listed above.
4. Footer pinned to bottom (`margin-top:auto`): lime status dot + two-line JetBrains Mono 11px
   `#5E5E68` "Local-only · nothing leaves this machine".

**Wordmark:** the string `DISTRAVA` set in Inter 800, `letter-spacing:-0.03em`. The single
typographic twist: the **"I" is colored `#C4F82A`** (`D<span lime>I</span>STRAVA`), read as a lime
rule — the only mark in the app. On a lime background it reverses to solid `#0B0B0F` with no color
split. Sidebar size 22px; hero/style-tile 44–72px; about-row 20px.

---

## Screens

### 1. Dashboard
**Purpose:** answer "how is my training going?" at a glance. Content max-width 1160px, padding 32px.

- **Top bar:** title "Dashboard" (Inter 600/17px); right side JetBrains Mono 12px "Last import ·
  Jul 11, 2026" + lime "Import" button (Inter 600/13px, bg `#C4F82A`, text `#0B0B0F`, radius 8px,
  padding `9px 16px`).
- **Stat cards:** 4-col grid, `gap:16px`. Each card: surface, border, radius 14px, padding 22px.
  Contents: uppercase caption label (`#9C9CA6`, 12px, `0.10em`); big number (JetBrains Mono 500,
  42px, `-0.02em`, tabular-nums) with a small muted unit; a delta row (JetBrains Mono 12px) with a
  `▲`/`▼` glyph — **lime `#C4F82A` for positive, `#E0685A` for negative** — plus muted "vs last
  week" text. Values: Distance 42.6 km ▲12.4%; Time 4:12 h ▲8.1%; Activities 6 ▼1; Training load
  312 ▲5.0% (7-day trend).
- **Training calendar (added post-brief):** one card. Header "Training calendar" + JetBrains Mono
  sub "Last 5 weeks · N-day streak", and a right-aligned legend (Rest → Hard) of five `12px`
  swatches: `#1E1E26`, `rgba(196,248,42,0.35)`, `rgba(196,248,42,0.65)`, `#C4F82A`. Below: a single
  horizontal row of 35 day cells (`display:flex; gap:5px`; each `flex:1; aspect-ratio:1;
  border-radius:3px`), colored by that day's training intensity (level 0 = rest = `#1E1E26` with a
  `1px #26262E` border; levels 1–3 use the three lime opacities). `title` tooltip per cell = date +
  rest/trained. Start/end date captions beneath, JetBrains Mono 10px muted.
- **Weekly volume chart:** one card. Header "Weekly volume" + mono sub "Last 12 weeks · kilometers"
  + a legend chip (12px lime square + "Distance"). Plot area height 240px. **Chart.js bar chart**,
  12 bars, `backgroundColor:#C4F82A`, `hoverBackgroundColor:#d6ff5c`, `borderRadius:4`,
  `barPercentage:0.62`. X grid hidden, axis border `#26262E`; Y grid `#1A1A20`, no border,
  `stepSize:15`. Ticks JetBrains Mono 10px `#5E5E68`. Tooltip: bg `#1E1E26`, border `#2C2C36`, body
  lime, mono font, no color box, label `"<v> km"`.
- **Bottom row:** 2-col grid `1.6fr / 1fr`, `gap:24px`.
  - *Recent activities* — surface card. Header row "Recent activities" + lime "View all →" link.
    5 compact rows, grid `64px 1fr 92px 78px`, `padding:13px 22px`, `border-bottom:1px #17171D`,
    row hover `#1A1A21`. Columns: mono date; type pill + title (ellipsis); right-aligned mono
    distance; right-aligned muted mono pace. Each row links to Activity Detail.
  - *Recent PRs* — surface card, restrained/celebratory. Header lime dot + "Recent PRs". Rows of
    label + mono date on the left, big lime mono value on the right. Sample: Fastest 5K 21:04,
    Best 1K 4:02, Longest run 21.1 km, Highest weekly load 312.
- **Empty state (fresh install, no data):** centered column — 52px rounded-square icon placeholder,
  Inter 700/24px "Nothing imported yet", body copy about local parsing, then a lime "Import data"
  button + secondary "Load sample set" button (transparent, `1px #33333D`). This is the toggled
  alternative to the populated dashboard.

### 2. Activity Detail (hero screen — most important)
**Purpose:** everything Strava charges for, on one page. Max-width 1160px.

- **Top bar:** breadcrumb "← Activities / Jul 11, 2026" in JetBrains Mono 12px muted.
- **Title block:** row with left = type pill (Run, blue dot) + mono "Jul 11, 2026 · 06:42 · Garmin
  Forerunner 265", then title "Morning tempo along the river" (Inter 700/32px, `-0.025em`); right =
  secondary "Edit" and "Export .gpx" buttons.
- **Summary strip:** one surface card, 6-col grid, dividers `1px #22222A` between columns. Each cell:
  mono 10px uppercase label + value (JetBrains Mono 500/26px tabular) + small muted unit. Cells:
  Distance 12.4 km · Duration 56:41 · Avg pace 4:34 /km · Avg HR 158 bpm · Max HR 174 bpm ·
  Elev gain +186 m.
- **Map + charts:** 2-col grid `1fr / 1.35fr`, `gap:24px`, stretch.
  - *Route panel* — header "Route" + mono "12.4 km loop". Body is a **placeholder** (will be
    Leaflet/OSM): `#101015` with a crosshatch of two `repeating-linear-gradient`s at ±45°, min-height
    340px, centered marker circle + mono "GPS ROUTE · Leaflet / OSM".
  - *Stacked time-series* — one card holding three stacked **Chart.js line charts sharing one
    x-axis** (distance in km): **Pace** (lime line), **Heart rate** (lime line), **Elevation** (grey
    `#6C6C78` line, area fill `rgba(60,60,72,0.35)`). Each plot 96px tall, separated by `1px #1C1C22`
    rules, each with a mono eyebrow label + unit. Only the **bottom (elevation) chart shows x ticks**
    (`4.1 km`… last tick appends " km"); pace/HR hide their x axis so the axis reads as shared. Points
    radius 0, `tension:0.35`, index-mode shared tooltip (bg `#1E1E26`, border `#2C2C36`, mono, no color
    box). Pace Y ticks format as `m:ss`; HR rounds to int; max 3 Y ticks each, grid `#17171D`.
- **Splits + best efforts:** 2-col grid `1.7fr / 1fr`, `gap:24px`.
  - *Splits* — surface card, one row per km. Header grid `44px 1.4fr 62px 62px 64px`
    (KM / Pace / HR / Elev / Time), mono 10px uppercase. Rows: mono km index; pace value (42px fixed
    width) **+ an inline relative-pace bar** — a `6px` track `#1E1E26` with a fill whose width scales
    with how fast the split was (faster = longer). The **fastest split** is highlighted: pace text and
    bar fill both lime `#C4F82A`; all other bars are muted green `#3A6B4A`. Then right-aligned mono HR,
    elevation delta (signed, `+`/`−`), and split time. Row hover `#1A1A21`.
  - *Best efforts (in this activity)* — surface card, lime-dot header + mono "in this activity". Rows:
    label + mono note (e.g. "km 11 · 06:19–10:21") on left; big lime mono value on right, with an
    optional `SEASON BEST` badge (mono 9px, solid lime bg, black text) when it's a season best.
    Sample: Fastest 1K 4:02 (season best), Fastest 5K 21:48, Fastest 10K 45:12.

### 3. Activities (list)
**Purpose:** dense, filterable, sortable table of every activity; each row opens Activity Detail.
Max-width 1160px.

- **Top bar:** "Activities" + mono "N total"; lime Import button.
- **Filter bar** (compact, above the table — not a separate panel), `display:flex; gap:16px`:
  - Type segmented control: pills All / Run / Ride / Gym in a `#131319` track (`1px #22222A`,
    radius 10px, padding 4px). Selected pill = lime bg, black text; others transparent, `#9C9CA6`.
  - "RANGE" mono label + a native `<select>` (All time / Last 30 days / Last 3 months / This year),
    styled `#131319`, `1px #22222A`, radius 8px.
  - Right-aligned mono "N results".
- **Table:** surface card. Header grid `110px 90px 1fr 100px 100px 96px 80px`
  (Date / Type / Title / Distance / Duration / Pace / HR), mono 10px uppercase, `border-bottom:1px
  #26262E`. Sortable columns (Date, Title, Distance, Duration, Pace, HR) show a `↑`/`↓` arrow on the
  active sort column; clicking toggles direction. Rows: mono date; type pill; title (ellipsis);
  right-aligned mono distance / duration / pace / HR (`—` where not applicable, e.g. gym has no
  distance/pace). Row hover `#1A1A21`; whole row is a link to Activity Detail.
- **Pagination:** 10 rows per page. Footer: left mono "Showing X–Y of N"; right "← Prev" / "N / M" /
  "Next →" buttons (`1px #22222A`, radius 8px). Disabled arrows use `#3A3A42`.
- **Empty:** "No activities match these filters." centered, muted.

### 4. Import
**Purpose:** clear, reassuring data import. Max-width 680px, centered.

- **Privacy banner** (always visible, top): lime-tinted box (`rgba(196,248,42,0.05)` bg,
  `rgba(196,248,42,0.25)` border, radius 12px), lime dot + copy: **"Parsed entirely on this
  machine."** Files read locally by the Flask process; nothing uploaded; no network request leaves
  the computer.
- **Three states** (mutually exclusive):
  - *Idle — dropzone:* `1.5px dashed #33333D`, `#101015` bg, radius 16px, padding `56px 40px`,
    centered. Down-arrow tile, "Drop your Apple Health export", sub "Drag `export.zip` here, or click
    to browse", lime "Choose file" button, mono footnote "Also accepts .gpx · .csv · .fit". Hover:
    border → lime, bg `#121418`.
  - *Processing:* surface card. Spinner (22px ring, `#26262E` track, lime top, 0.8s linear
    `@keyframes spin`) + "Parsing export.zip" + mono stage label. An **8px progress bar** (track
    `#1E1E26`, lime fill, width = %, `transition:width 0.3s`). Below: mono "N / 1,284 activities" +
    lime "%". Reassurance copy: large exports can take a minute; parsing continues locally. Stage
    labels cycle: Unzipping archive → Reading export.xml → Parsing workout records → Matching GPS
    routes → De-duplicating against database → Building indexes.
  - *Done — summary:* surface card. Header lime check-circle + "Import complete" + mono
    "export.zip · 148 MB · 41s". 3-col grid: **Imported** 1,284 activities (lime 34px), **Skipped** 37
    duplicates, **Range** Mar 2019 → Jul 2026. Footer: lime "Go to dashboard" link-button + secondary
    "Import another".
- The prototype includes a small "PREVIEW STATE" idle/processing/done switcher — that's a **design
  aid only**; drop it in production. Real state comes from the upload/parse flow.

### 5. Settings
**Purpose:** profile, HR zones, units, data management, about. Max-width 720px, sections `gap:24px`.
Top bar shows a save-status string ("All changes saved" muted / "Unsaved changes · auto-saved
locally" lime).

- **Profile** card: rows (label + mono helper on left, right-aligned mono input `.fld`): Max heart
  rate (bpm, overrides 220−age), Resting HR (bpm), Weight (kg/lb per units), Birth date. Inputs:
  `#101015`, `1px #2C2C36`, radius 8px, right-aligned mono; focus border lime.
- **Heart rate zones** card: *the user emptied this section during design.* Intended content (from
  brief) = 5 editable zones, each a colored bar chip + name + description + %-of-max range + computed
  bpm range, all recalculated live from Max HR. Zone colors and %/bpm math are in the design tokens
  and the prototype's `_zones()` logic — **reinstate per that logic** unless the user says otherwise.
- **Units** card: "Measurement system" + a Metric·km / Imperial·mi segmented control (same styling as
  the Activities type control; selected = lime bg/black text). Switching updates weight unit/value.
- **Data** card: rows with a secondary action button each — Database location (`~/.distrava/
  distrava.db · 214 MB`, "Reveal"), Export data ("Export"), and **Wipe all data** (destructive:
  `#E0685A` text, `rgba(224,104,90,0.4)` border, hover tint `rgba(224,104,90,0.08)`).
- **About** card: wordmark + mono "v1.0.0" on the left; lime dot + "Your data never leaves this
  machine" on the right.

### 6. Design System (style tile)
`DISTRAVA Design System.dc.html` is the reference style tile — wordmark treatments, full color
swatch set with roles, the type scale, and every component primitive shown in isolation (stat card,
chart container, data-table row incl. hover, sidebar nav states, buttons, activity-type pills,
empty state, coming-soon state). Use it as the source of truth for any component styling not fully
spelled out in a screen above.

---

## Interactions & Behavior
- **Navigation:** sidebar links route between pages; active page shows the lime left-bar + bright
  label. Coming-soon items are inert.
- **Activities table:** click a header to sort (toggle asc/desc, arrow indicates active column +
  direction); type pills and range select filter; pagination 10/page. Clicking a row → Activity
  Detail. In production, sort/filter/paginate can be server-side (Jinja + query params) or a small
  vanilla-JS enhancement.
- **Import:** dropzone accepts `export.zip` (+ .gpx/.csv/.fit); on submit show the processing state
  with a real progress signal from the backend parse job, then the result summary. Never show a
  network/upload indicator — parsing is local.
- **Settings:** editing any field flips the save-status to the lime "unsaved / auto-saved" string;
  Max HR drives the HR-zone bpm ranges live; units toggle swaps weight unit + displayed values.
- **Charts:** all Chart.js. Line charts use `pointRadius:0`, `tension:0.35`, index-mode shared
  tooltips; the stacked activity charts fake a shared x-axis by hiding the upper charts' x ticks and
  showing only the bottom chart's.

## State Management
- Global: current route/active nav item; units (metric/imperial); "has data" (drives dashboard
  populated vs. empty).
- Activities list: active type filter, date range, sort key + direction, current page.
- Import: phase (idle / processing / done) + progress %.
- Settings: profile fields, max HR (recomputes zones), units, dirty/saved flag.
- Data fetching: all local — Flask serves activities from the SQLite DB (`~/.distrava/distrava.db`);
  no external APIs.

## Assets
No raster assets or icon libraries are used. All "icons" are CSS/box primitives (rounded squares,
dots, arrow glyphs, an inline `↓`/`✓`/`→`). The route map is a CSS crosshatch placeholder to be
replaced with Leaflet/OpenStreetMap. Fonts are Inter + JetBrains Mono from Google Fonts (swap in
self-hosted files if you want to preserve the offline/local-only promise).

## Files in this bundle
- `DISTRAVA Design System.dc.html` — style tile / component reference
- `DISTRAVA App Shell.dc.html` — sidebar + content shell
- `DISTRAVA Dashboard.dc.html` — dashboard (populated + empty state via `hasData`)
- `DISTRAVA Activity Detail.dc.html` — activity detail (hero screen)
- `DISTRAVA Activities.dc.html` — activities list/table
- `DISTRAVA Import.dc.html` — import flow (idle / processing / done)
- `DISTRAVA Settings.dc.html` — settings
- `support.js` — prototype runtime only; **do not port**

Open any file directly in a browser to see the intended result. The `{{ ... }}` holes and the
`<script data-dc-script>` class are prototype scaffolding — read them to understand the data and
logic, but reimplement in Jinja2 + vanilla JS.
