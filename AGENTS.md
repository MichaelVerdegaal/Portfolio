# Agent brief: particle-swarm name reveal (portfolio landing page)

How to use this: drop it into the repo as the task description for the Copilot coding agent, or save
it as `.github/copilot-instructions.md`. Fill in the placeholders in the last section first, since
the agent needs the name, the logo list, and the links to build anything real.

## What we are building

A single-page personal landing site. The page opens on a black field with a few thousand points
drifting slowly, and one button in the centre. Clicking the button sends every point homing toward
an assigned target. Over a few seconds the cloud settles out of its drift into the shape of my name,
while a small set of brand logos resolve alongside it as clickable links. The motion is the whole
experience, so it has to feel like a swarm finding its shape, not a slideshow crossfading between
two states.

An earlier version of this project drove the convergence with a live neural network trained in the
browser. That approach is dropped. We now optimise the particle positions directly, with a
selectable optimiser. There is no network, no backprop, and no ML library anywhere in this build.

## How the motion works (the part that decides whether this looks good)

Each point is a particle with a position and a velocity. On click, each particle is assigned one
fixed target coordinate, and from then on it moves to reduce the distance to that target under a
chosen optimiser. The optimiser is selectable from config: SGD, Adam, or PSO.

Two things make this read as a swarm finding its shape rather than a pile of dots sliding on rails,
and both are mandatory.

Assignment is load-bearing. With no shared model coordinating the points, each trajectory is
independent, and a careless assignment produces an ugly scramble where paths cross everywhere.
Assign particles to targets so the cloud folds into shape: sort both particles and targets along a
shared axis (x, or distance from centre) and pair them by rank, or do a cheap greedy
nearest-neighbour assignment. This was optional polish in the old design; here it is what sells the
effect, so do not skip it.

The optimiser is the aesthetic. The three optimisers are genuinely different dynamical systems and
must be implemented as the real update rules, not three eased lerps behind a dropdown, otherwise
there is no reason to offer the choice. Their characters:

- SGD with momentum: a clean ease toward the target. With momentum near zero it is a straight glide;
  with momentum around 0.8 to 0.9 it overshoots slightly and settles.
- Adam: per-axis adaptive steps, so far and near particles arrive on a more uniform schedule. Crisp,
  even, slightly mechanical convergence.
- PSO: inertia plus a pull toward the target, which gives the springy, drifting overshoot-and-settle
  that makes swarm visualisations look alive. This is the showpiece, and the inertia term is the
  knob that produces the wobble.

### The per-particle update, concretely

Work in canvas pixel space throughout. There is no network here, so there is no need to normalise
coordinates into any bounded range; targets and positions are both pixels, and the optimiser
coefficients are expressed in pixels (or as fractions of canvas size so they scale across
viewports).

Per particle with position `p` (2D) and assigned target `t` (2D), define the error `e = p - t`. All
three optimisers minimise `0.5 * |e|^2`, whose gradient is simply `e`. The difference between them
is entirely in how that gradient becomes a step.

SGD: `v = momentum * v - learningRate * e` then `p = p + v`. Momentum zero is a pure glide; higher
momentum gives overshoot.

Adam: maintain per-particle, per-axis first and second moment vectors `m` and `v`, plus a
per-particle step counter. Each step set `g = e`, run the standard Adam moment updates with bias
correction, and step `p` down the resulting direction. Each particle carries its own moments, so a
particle near its target and one far away both take well-scaled steps.

PSO: maintain a velocity per particle. `v = inertia * v + cognitive * r1 * (t - p) + social * r2 *
(cohesionTarget - p)` then `p = p + v`, with `v` clamped to a maximum speed. `r1` and `r2` are
per-step uniform random scalars in `[0, 1)`. The cognitive term pulls the particle to its own
target, which is its personal best by construction. The social term is optional cohesion that keeps
the cloud moving as one body: use the global target centroid, or set `social` to zero for pure
cognitive PSO, which already looks good as a damped spring. If you use a social term it must fade
fully to zero over the reveal, otherwise the swarm settles on a version of the name contracted
toward the centroid rather than on the true targets. Anneal `inertia` from roughly 0.9 down to 0.4
over the reveal so it drifts early and settles cleanly.

### Pace it for the eye, not the clock

The convergence is a UX element, not a benchmark. Do not tune it to finish instantly.

- Run a small number of optimiser steps per animation frame (start with a handful).
- Tune the learning rate or inertia and the steps-per-frame so the cloud takes roughly 3 to 6
  seconds to resolve. This duration is a deliberate knob; expose it as a constant in config.
- Each frame, after the step(s), render every particle at its current position. The visible motion
  is the optimiser's trajectory, which is the entire point.
- Taper the effective step size to zero over the back of the reveal (hold at full strength while the
  cloud travels, then a cosine taper to zero for, say, the last 40 percent). This is not optional.
  At a constant step size none of the three optimisers lands on its target: Adam keeps stepping at
  roughly its learning rate even as the gradient vanishes, and PSO's per-step random forcing never
  dies, so both hold a nonzero oscillation amplitude that thickens and fuzzes the glyphs. Driving
  the step to zero collapses that amplitude so the points settle exactly on their targets.

### Idle state

A few thousand points (start around 3000, make it a constant that is easy to change) drift slowly on
a black background, with a single centred button. The drift should be gentle and endless, for
example each point given a small random velocity with soft wrapping or a slow noise field. The
button is the only affordance.

### Targets from text and logos

Generate the target positions by rendering, not by hand-placing coordinates.

- Render the name to an offscreen canvas in the chosen font and size, read the pixel data, and
  sample the dark (inked) pixels to produce target coordinates. Sample roughly as many ink points as
  you have particles. Weight sampling by ink so strokes are evenly covered.
- Do the same for each logo: rasterise its SVG (or load its PNG) to an offscreen canvas and sample
  its filled pixels.
- Lay out the name and logos in a composition (name centred, logos in a row beneath it, or similar)
  and collect all target points into one set in canvas coordinates.

Then assign each particle a target as described above, sorting or greedily pairing so the cloud
folds rather than scrambles.

### Resolved state and links

- The name stays rendered as the point cloud once converged. Leaving it as points is the aesthetic.
  A very subtle micro-drift around the settled positions keeps it from looking frozen.
- The logos should resolve into crisp, clickable SVGs rather than staying as point clusters. Once
  the cloud settles, fade the sampled logo points out and fade clean vector logos in at the logo
  positions, each wrapped in an anchor to its link. Crisp vector logos look better and link far more
  reliably than trying to make a cluster of particles clickable.
- The fuzzy-name-plus-crisp-logos contrast is intentional visual hierarchy; keep it.

### Accessibility, SEO, reduced motion, mobile

These are easy to skip and annoying to retrofit, so build them in from the start.

- The page must contain the real name and the real links in the DOM as actual text and anchor
  elements, so the site is crawlable by search engines and usable by screen readers. They can be
  visually hidden (off-screen, not `display: none`, so assistive tech still reads them). The canvas
  is decoration; the DOM is the real content.
- Respect `prefers-reduced-motion`. When it is set, skip the drift and the homing animation entirely
  and present the resolved name and clickable logos statically.
- Make it work on a phone. The canvas is responsive, the particle count and layout scale to the
  viewport, the name fits, and a tap triggers the reveal. Test a narrow viewport.

## Configuration: keep the content easy to edit

Everything I will want to change later must live in one place, not scattered through the logic.
Build a single config file. A `config.js` ES module exporting a plain object is ideal for a no-build
setup, since it needs no fetch and no parsing; a `config.json` loaded at runtime is an acceptable
alternative. The config holds:

- the name string and the font
- the palette (point colour, background, button and logo accents)
- the particle count and the reveal duration and steps-per-frame
- the optimiser selection and its parameters
- the logo list, where each entry is a label, a path to an SVG file, and a link href

The optimiser block selects one of the three and carries each one's tunables, for example:

```js
optimizer: {
  type: 'pso', // 'pso' | 'adam' | 'sgd'

  sgd: {
    learningRate: 0.15, // fraction of remaining distance per step
    momentum: 0.85,     // 0 = pure glide, ~0.85 = overshoot and settle
  },

  adam: {
    learningRate: 5,    // pixels per step (Adam normalises the gradient)
    beta1: 0.9,
    beta2: 0.999,
    epsilon: 1e-8,
  },

  pso: {
    inertiaStart: 0.9,  // annealed to inertiaEnd over the reveal
    inertiaEnd: 0.4,
    cognitive: 0.12,    // pull toward the particle's own target
    social: 0.03,       // cohesion toward target centroid; 0 disables
    maxSpeed: 60,       // velocity clamp, pixels per step
  },
},

reveal: {
  durationSeconds: 5,
  stepsPerFrame: 3,
},
```

Logos live as standalone SVG files in an assets folder, for example `assets/logos/`, and the config
references them by path. Adding or swapping a logo is then dropping an SVG into that folder and
editing one entry in config, with no code changes. Targets are sampled from these config values at
load time, so editing the name string or the logo list automatically reflows the whole reveal. Use
each logo's SVG file for both jobs: rasterise it to sample its points, and display that same file as
the crisp clickable logo at the end, so there is one asset per logo and no duplication.

## Stack and constraints

- Vanilla HTML, CSS, and JavaScript. No React, Vue, Svelte, or any framework.
- No ML library and no animation library. The optimisers are a few lines of hand-written vector
  maths each, and we want full control over per-frame rendering.
- Rendering is Canvas 2D. WebGL is allowed only if there is a strong reason and it stays
  dependency-free; Canvas 2D handles a few thousand points at 60fps and is the default.
- Prefer no build step. A single `index.html` plus a small number of JS modules is ideal. If a
  bundler is genuinely warranted keep it minimal (esbuild or Vite, nothing heavier).
- Modern JS (ES modules, no transpilation target gymnastics).
- All editable content and behaviour (name, font, logos, links, palette, particle count, reveal
  duration, optimiser and its parameters) lives in the one config file, not hardcoded in the logic.
- The site ships with a Dockerfile and runs as a static container. See the Docker section.

## Running it as a Docker container

The site is static with no backend, so serving it is simple.

- Provide a `Dockerfile` that serves the site with a lightweight static server. With no build step,
  a single stage on `nginx:alpine` that copies the site into `/usr/share/nginx/html` and exposes
  port 80 is enough. If a build step exists, use a multi-stage build: a Node stage to produce the
  static output, then the nginx stage to serve it, so the final image carries no build tooling.
- Provide a `docker-compose.yml` that builds the image and maps a host port to the container, so it
  runs with a single `docker compose up`.
- Add a `.dockerignore` so node_modules, git, and local cruft stay out of the image.
- Because I will want to edit content without rebuilding, the compose file should optionally
  bind-mount the config file and the logo assets folder into the container (read-only is fine), so
  editing `config.js` or swapping a logo SVG on the host shows up on refresh with no image rebuild.
  Keep this as a documented, commented-out option in the compose file.

## Suggested build order

Build in milestones and keep each one verifiable before moving on.

1. Establish the config file first, then scaffold the page: black canvas, the drifting idle point
   cloud, and the centre button, reading the name, palette, and optimiser selection from config. No
   homing yet. Verify the drift looks good and is performant.
2. Target generation: render the name to an offscreen canvas and sample ink points, then draw those
   target points statically on the main canvas to confirm sampling and layout look right.
3. The optimisers in isolation: implement SGD, Adam, and PSO as per-particle position updates and
   confirm on a toy (a handful of particles homing to fixed points) that each produces a distinct,
   stable trajectory. This is where to catch coefficient scaling in pixel space and the PSO velocity
   clamp.
4. Wire homing to the button click: assign particles to targets (sorted-axis or greedy nearest), run
   the chosen optimiser per frame, render per-frame positions, and tune the pacing so it resolves in
   3 to 6 seconds with correlated folding motion.
5. Logos: sample them, lay them out, and implement the resolve-to-SVG transition with working
   clickable links.
6. Accessibility DOM fallback, reduced-motion path, responsive and mobile behaviour, then visual
   polish (palette, easing on the fades, button states, the drift feel).
7. Containerise: add the Dockerfile, docker-compose.yml, and .dockerignore, and confirm
   `docker compose up` serves the site on the mapped port.

## Acceptance criteria

- Clicking the button sends the cloud homing to its targets under the configured optimiser, and the
  name resolves sharp and legible.
- The three optimisers are implemented as real, visibly different update rules; changing
  `optimizer.type` in config changes the character of the motion (glide, even arrival, springy
  overshoot).
- The cloud folds into shape via a sane particle-to-target assignment, not a scramble of crossing
  paths.
- Logos end as crisp clickable SVGs that navigate to the correct links.
- The name and all links exist as real text and anchors in the DOM.
- `prefers-reduced-motion` yields a static, fully usable page.
- It works and is legible on a narrow mobile viewport at a smooth frame rate.
- No ML library, no animation library, and no UI framework are present in the dependencies.
- All content and behaviour (name, links, logos, colours, counts, optimiser and its parameters) is
  read from the single config file; changing the name or adding a logo means editing only config and
  the assets folder.
- The site builds and runs as a Docker container and is reachable on a mapped host port.

## Do not

- Do not collapse the three optimisers into a single eased tween with a relabelled dropdown;
  implement the real update rules so they actually differ.
- Do not skip the particle-to-target assignment; without it the reveal scrambles instead of folding.
- Do not make the convergence instant; keep the paced 3 to 6 second reveal.
- Do not add a UI framework, an animation library, or any ML library.
- Do not rely on the canvas for content; the DOM must carry the name and links.
- Do not make logo links depend on clicking a cluster of particles.
- Do not hardcode the name, links, logo references, colours, or optimiser parameters into the logic;
  they come from the config file.

## You need to fill in

These are the values that go in the config file, with the logos as SVG files in the assets folder:

- NAME: «Firstname Lastname» as it should render.
- FONT: «which font for the name», and whether it is self-hosted or a web font.
- LOGOS AND LINKS: for each logo, drop an SVG file in the assets folder and give its path and link
  in config, for example «GitHub -> assets/logos/github.svg -> https://github.com/...», «LinkedIn ->
  ... -> https://...», «email -> ... -> mailto:...».
- PALETTE: point colour(s) against the black background, and any accent colour for the button and
  logos. Default is white points on black if unspecified.
- PARTICLE COUNT and REVEAL DURATION if you want something other than the ~3000 / ~5 second
  defaults.
- OPTIMISER: which of `pso`, `adam`, `sgd` is the default, and any non-default coefficients.

## Git

Work on a feature branch, use conventional commits, and commit for every isolated change. The commit
history should tell the story of the build, with each commit representing a meaningful step in the
process. For example:

- `feat: add config file and load name, palette, and optimiser selection`
- `feat: implement idle drift of points`
- `refactor: extract target sampling to separate module`
- `feat: add SGD, Adam, and PSO per-particle optimisers`
- `fix: clamp PSO velocity to stop particles overshooting off-canvas`