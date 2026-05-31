# Portfolio — Particle Swarm Name Reveal

A single-page personal landing site where thousands of particles drift on a dark canvas until you
click a button. On click, every particle homes toward an assigned target under a real optimisation
algorithm, and the cloud resolves into the shape of my name with clickable social links beneath it.

The motion is the whole experience: the three families of optimisers (gradient descent, adaptive,
swarm) produce visibly different convergence dynamics — clean glides, even arrivals, or springy
overshoot-and-settle — and each runs as a genuine per-particle update rule, not an eased tween.

## Quick start

```bash
npm install
npm run dev        # http://localhost:5173
```

## Production build

```bash
npm run build      # outputs to dist/
npm run preview    # serve the build locally
```

## Docker

```bash
docker compose up --build    # serves on http://localhost:8080
```

The Dockerfile uses a Bun build stage followed by `nginx:alpine` to serve the static output. To
live-edit config or logos without rebuilding, uncomment the bind-mount volumes in
`docker-compose.yml`.

## Configuration

All content and behaviour is centralised in [`config.ts`](config.ts):

| Section           | What it controls                                        |
| ----------------- | ------------------------------------------------------- |
| `name`            | The text rendered as the particle target                |
| `font`            | Font family, weight, and Google Fonts URL                |
| `palette`         | Background colour, point colour, button & logo accents  |
| `particles`       | Count, point radius, drift speed                        |
| `optimizer`       | Active type + per-optimizer hyperparameters              |
| `reveal`          | Duration (seconds) and optimizer steps per frame         |
| `logos`            | Array of `{ label, svg, href }` entries                 |
| `layout`          | Name scale, logo size/gap/padding (fractions of canvas)  |
| `canvas`          | Reference resolution (default 1920×1080)                |

Changing the name, swapping a logo SVG, or switching the optimizer only requires editing this file
and the `public/assets/logos/` folder — no code changes.

## Optimisers

Five optimisers are implemented as real per-particle update rules:

| Type       | Character                                                          | GPU |
| ---------- | ------------------------------------------------------------------ | --- |
| **SGD**    | Clean glide; momentum adds slight overshoot and settle             | ✓   |
| **Adam**   | Adaptive per-axis steps; uniform arrival schedule, slightly mechanical | ✓ |
| **PSO**    | Inertia + cognitive/social pull; springy, drifting, swarm-like     | ✓   |
| **RMSProp** | Running-average gradient scaling; smooth and even                 | ✓   |
| **Muon**   | Momentum + Newton-Schulz orthogonalisation; distinctive trajectories | CPU only |

SGD, Adam, PSO, and RMSProp run entirely on the GPU via WebGL2 Transform Feedback — particle state
never leaves VRAM during the reveal. Muon requires global reductions (dot products across all
particles) that cannot run in a single Transform Feedback pass, so it falls back to CPU with
per-frame buffer uploads.

Select the optimizer in the on-screen controls panel or by changing `optimizer.type` in config.

## Project structure

```
config.ts          — all tunable parameters (name, palette, optimizers, logos)
main.ts            — application orchestrator (idle → homing → resolved)
renderer.ts        — WebGL2 point renderer with Transform Feedback GPU path
optimizers.ts      — CPU optimizer implementations (Muon fallback + reference)
targets.ts         — target generation (text sampling + logo SVG sampling)
index.html         — page shell, styles, controls panel, accessibility DOM
public/assets/logos/  — logo SVG files referenced by config
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for a deeper technical walkthrough.

## Accessibility & SEO

- The real name and all links exist as DOM text and anchors (visually hidden, readable by screen
  readers and crawlers).
- `prefers-reduced-motion` skips all animation and shows a static fallback.
- A `<noscript>` block displays a message when JS is disabled.
- The canvas is marked `aria-hidden="true"`.

## Stack

- **Vanilla TypeScript** — no framework, no animation library, no ML library.
- **WebGL2** (Canvas 2D fallback not needed; WebGL2 handles 100k+ points at 60 fps).
- **Vite** — dev server and production bundler (< 30 kB gzipped output).
- **nginx:alpine** — production container.

## License

Personal project. All rights reserved.
