# overfit.dev — design system

## Context

**overfit.dev** is a personal infrastructure domain. The single artifact provided is
`uploads/index.html`: a self-hosted **homelab index page** that lists 17 services running on a
LAN box (`192.168.2.14`) alongside their Cloudflare-exposed `*.overfit.dev` subdomains.
Services span infra (Dozzle, Glances), media (Jellyfin, the \*arr stack, qBittorrent, SABnzbd),
photos (Immich), books (Grimmory), music (Navidrome, Pinchflat) and tools (Mealie).

The page is hand-maintained: a commented `SECTIONS` array at the top of the file is the
edit surface, and a 20-line renderer below it writes tables. That is the whole product ethos —
**one file, no build step, no framework, no chrome**. This design system generalises that page's
visual language so new overfit.dev surfaces look like they came from the same hand.

### Sources given

- `uploads/index.html` — the homelab index page (inline `<style>` + inline data + renderer).
  This file is the sole ground truth for every colour, size and interaction in this system.
- No Figma file, no repository, no logo files, no font binaries, no decks were provided.
- Brief: *"sleek and minimalist, pleasant to the eyes. No gradients, JetBrains Mono, dark
  colours with a bright contrast colour."* All of which the source page already does.

### Substitutions and gaps — please confirm

- **JetBrains Mono is loaded from Google Fonts** (`tokens/fonts.css`). No binaries were
  supplied. Swap the `@import` for self-hosted `@font-face` rules if you have the files.
- **There is no logo.** The source renders the brand as plain lowercase bold text (`homelab`),
  so this system does the same: wordmark = the name, set in JetBrains Mono Bold, white or
  `#5cf07c`. Nothing was drawn. `assets/` is therefore empty by design.
- **There is no icon set.** The source uses single emoji glyphs (see Iconography).
- The `--green-*` accent scale and the warn/error/info colours are **derived** — the source
  defines only `#5cf07c`. Everything else in `tokens/colors.css` is verbatim from it.

## Index

| Path | What it holds |
| --- | --- |
| `styles.css` | Root entry. `@import` list only — link this one file. |
| `tokens/` | `fonts` · `colors` · `typography` · `spacing` · `borders` · `motion` · `base`. |
| `components/core/` | `Link` `Button` `Badge` `StatusDot` `Panel` |
| `components/forms/` | `Input` |
| `components/data/` | `PageHeader` `SectionTitle` `DataTable` |
| `ui_kits/homelab/` | Recreation of the homelab index. See its own README. |
| `guidelines/*.card.html` | 16 foundation specimen cards (Colors, Type, Spacing, Brand). |
| `thumbnail.html` | Homepage tile. |
| `SKILL.md` | Agent-skill entry point. |

### Component provenance

Derived directly from the source page: `Link` (the inverted-hover anchor), `DataTable` (the
fixed-layout dense table incl. the dim `.` empty mark), `SectionTitle` (the tracked uppercase
group label), `PageHeader` (title + muted count over a hairline).

**Intentional additions** — the source is one read-only page, so these were added to make the
system buildable-with. Each stays inside the source's rules (square, hairline, one accent):

- `Button` — the page has no controls at all; any new surface needs actions.
- `Input` — same reason; needed for search/config surfaces.
- `Badge` — a square hairline label for the port/state strings the page shows as bare text.
- `StatusDot` — health, implied by a service list but not rendered in the source.
- `Panel` — a hairline container to group content where a table isn't right.

## Content fundamentals

**Lowercase, terse, factual.** The page title is `homelab`, not "Homelab" or "My Homelab
Dashboard". Service names keep their upstream casing exactly (`qBittorrent`, `SABnzbd`,
`Immich public proxy`) — never re-cased, never "prettified".

- **Group labels are the one uppercase form**: `INFRA`, `MEDIA`, `PHOTOS`, `BOOKS`, `MUSIC`,
  `TOOLS`. Single words, no "&", no articles.
- **Counts are bare and pluralised plainly**: `17 services`. No "Total:", no icon, no framing.
- **Column headers are sentence case single words**: `Name`, `Localhost`, `Hosted`.
- **URLs and addresses are shown, not hidden behind labels.** `192.168.2.14:8096` and
  `https://jellyfin.overfit.dev` appear as their own link text. Never "Open" or "Launch".
- **Absence is marked, not explained.** A service with no public hostname gets a dim `.` —
  not "Not exposed", not an empty cell.
- **Instructions read as imperative comments**, addressing a future self: *"EDIT HERE. To add a
  service, drop a new object into the right section."* / *"You should not need to touch
  anything below."* First person is absent; second person is used only in that instructional
  register. No marketing voice, no exclamation marks.
- **Emoji appear as data, never as decoration or as sentence punctuation** (see Iconography).
- Vibe: a terminal that happens to render in a browser. If a sentence can be a table row,
  make it a table row.

## Visual foundations

**Colour.** Pure black `#000` canvas — not a soft charcoal. Body text is `#c5c5c5`; white
`#ffffff` is reserved for headings and section titles only. Two greys below body do the rest:
`#6a6a6a` for labels, counts and table headers, `#3a3a3a` for absent/disabled. Borders are one
value, `#2a2a2a`. Exactly one bright colour, `#5cf07c`, used for links, the primary button and
OK status — nothing else. Warn/error/info exist but are rare; a green-only screen is normal.

**Type.** JetBrains Mono throughout — UI, prose, numbers, headings. 13px/1.6 body. Weights are
400 and 700 only; 500 exists for rare inline emphasis. Italics are never used. Letter-spacing
is default everywhere except section titles (1.5px) and micro uppercase labels (0.08em).
Tabular alignment comes free from the monospace family, which is why numbers are never
right-aligned here.

**Layout.** One centred column, `max-width:1240px`, `padding:16px 20px`. Content is
left-aligned inside it; nothing is centred except the column itself. Nothing is fixed or
sticky — the page scrolls as one document. Tables use `table-layout:fixed` with an explicit
shared column template (28 / 200 / 280 / remainder) so every table on the page lines up
vertically. Sections are separated by 22px, headers by a hairline.

**Backgrounds.** Flat black. **No gradients** anywhere — not in buttons, not as scrims, not as
image protection. No background images, no patterns, no textures, no noise, no illustrations.
Elevation is expressed as a hairline plus, at most, a `rgba(255,255,255,.04)` overlay
(`#0a0a0a` / `#121212` / `#1a1a1a` are the only surface steps).

**Borders and corners.** `1px solid #2a2a2a`, square. `border-radius` is `0` on every element;
the only exception is the 6px status dot, which is fully round. `#3a3a3a` is available for a
stronger hairline. Frequently only one edge is drawn — a `border-bottom` under a header does
the work a full box would do elsewhere.

**Shadows.** None. There is no shadow system, inner or outer — `--shadow-none` exists so the
absence is explicit. Nothing floats; overlays, if needed, sit on `#0a0a0a` with a hairline.

**Cards.** A card is a square `#0a0a0a` rectangle with a `#2a2a2a` hairline, an optional header
row (bold white title left, muted metadata right) separated by another hairline, and 12px
padding. No shadow, no radius, no accent left-border, no hover lift.

**Transparency and blur.** Transparency only as the 4%/7% white hover and press overlays.
`backdrop-filter` is not used — a solid `#0a0a0a` panel is always preferred to a blurred one.

**Hover.** Links invert: green text becomes a green block with black text and a 3px horizontal
bleed (`padding:0 3px; margin:0 -3px`) so the highlight sits flush with the text baseline —
this inversion is the brand's signature gesture. Everything else hovers with a 4% white
overlay; the accent button hovers *lighter* (`#a6f8ba`).

**Press.** Colour only. Links and the primary button darken to `#2fae4d`; other controls go to
a 7% white overlay. Nothing scales, shifts, or shrinks on press.

**Focus.** `1px solid #5cf07c` outline at 1px offset. Inputs move their border to the accent.

**Motion.** 80ms linear on colour and background; 140ms `cubic-bezier(.2,0,.3,1)` on opacity
for view changes. No transforms, no bounce, no spring, no skeleton shimmer, no page
transitions, no entrance animations. If something needs to move to be understood, it's the
wrong design.

**Imagery.** There is none in the source, and none is added. If a photo ever has to appear,
keep it cool and desaturated and butt it against a hairline — no rounded corners, no gradient
scrim over it, no drop shadow.

## Iconography

The source uses **single emoji glyphs as data**, one per service, in a fixed 28px first column:
🗄 📜 📊 🎬 🎟 🎞 📺 🔍 🌀 📥 ⚙ 📷 📸 📚 🎵 🎶 🍳. They are set at body size with no colour
treatment, no background, no container. They are chosen literally (📷 for a photo service,
🍳 for a recipe manager) and they are the *only* place emoji appear — never in prose, never in
headings, never as bullets or sentence decoration.

Beyond that: **no icon font, no SVG sprite, no PNG icons exist in the source**, so none were
invented or imported. Unicode carries what little else is needed — the dim `.` empty mark,
`-->` and `::` in comments. If a UI genuinely needs stroke icons (chevrons, close, external),
use **Lucide** from CDN at `stroke-width:1.5`, 14px, coloured `currentColor` — flagged here as a
substitution, not something the brand has established.
