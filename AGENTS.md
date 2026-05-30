# Agent brief: neural point-cloud name reveal (portfolio landing page)

How to use this: drop it into the repo as the task description for the Copilot coding agent, or save
it as `.github/copilot-instructions.md`. Fill in the placeholders in the last section first, since
the agent needs the name, the logo list, and the links to build anything real.

## What we are building

A single-page personal landing site. The page opens on a black field with a few thousand points
drifting slowly, and one button in the centre. Clicking the button starts a small neural network
training live in the browser. Over a few seconds the point cloud migrates out of its drift and
settles into the shape of my name, while a small set of brand logos resolve alongside it as
clickable links. The convergence is the whole experience, so it has to look like a network learning,
not like an animation playing.

## The one rule that decides whether this works

The convergence must be driven by a real neural network doing real gradient descent. The points on
screen each frame are the network's current output. This is non-negotiable and it is the single most
likely thing for an agent to "simplify" into something cheaper, so to be explicit:

Do not replace the network with tweening, easing, lerp-to-target, GSAP, spring physics, or any
interpolation between a start position and an end position. A loss curve drawn over an interpolation
is not acceptable. The audience for this site is ML engineers and they will be able to tell.

The reason it has to be real is also why it looks good. Because every point's position is produced
by the same shared network weights, the points do not move independently. Early in training the
whole cloud lurches together, then differentiates as the weights specialise, with the natural
overshoot-and-settle wobble of SGD. The cloud behaves like one organism finding its shape. That
coordinated motion is the payoff and it is impossible to fake with per-point interpolation.

## Stack and constraints

- Vanilla HTML, CSS, and JavaScript. No React, Vue, Svelte, or any framework.
- No TensorFlow.js, ONNX runtime, or any ML library. The network and its backprop are hand-written
  in plain JS. A 3-layer MLP is a couple hundred lines and we want full control over per-frame
  rendering, plus we are not shipping a multi-megabyte dependency onto a landing page where first
  paint matters.
- Rendering is Canvas 2D. WebGL is allowed only if the agent has a strong reason and keeps it
  dependency-free; Canvas 2D handles a few thousand points at 60fps and is the default.
- Prefer no build step. A single `index.html` plus a small number of JS modules is ideal. If a
  bundler is genuinely warranted keep it minimal (esbuild or Vite, nothing heavier).
- Modern JS (ES modules, no transpilation target gymnastics).
- All editable content (name, font, logos, links, palette, particle count, reveal duration) lives in
  one config file, not hardcoded in the logic. See the configuration section.
- The site ships with a Dockerfile and runs as a static container. See the Docker section.

## How the reveal works

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

Assign each particle a target. A one-to-one assignment is fine. To avoid ugly trajectory crossings,
an optional nicety is to sort particles and targets along a shared axis (or do a cheap greedy
nearest assignment) so the cloud folds into shape rather than scrambling, but this is polish, not a
requirement.

### The network

This is the part most likely to be built naively and then fail to produce sharp text, so read this
carefully.

- Per particle, fix an input code at load time: a small random vector (for example 2 to 4
  dimensions, sampled once from a normal distribution). A nice alternative is to use each particle's
  drift position captured at the moment of the click as its input; either works, pick one and keep
  it fixed during training.
- Encode that input with random Fourier features before the MLP. This matters: a plain small MLP
  will blur, because mapping arbitrary input codes to the high-frequency target function that sharp
  glyphs require is exactly what plain MLPs are bad at. Random Fourier features (project the input
  through a fixed random matrix, then take sines and cosines) are the standard fix and let a small
  network fit crisp targets. Without this the name will come out as a fuzzy blob and the effect is
  ruined. Around 32 to 64 frequencies is a reasonable start.
- MLP: 2 hidden layers, around 64 units each, tanh or ReLU activations, 2 outputs.
- Output activation is tanh so outputs are bounded to (-1, 1).
- Normalise target coordinates into roughly [-1, 1] for training, and map the network's normalised
  output back to canvas pixels for rendering. Training MSE directly on raw pixel coordinates against
  a tanh output will not converge; this normalisation step is mandatory.
- Loss is mean squared error between network output and the particle's normalised target.
- Optimiser is hand-written: SGD with momentum is enough and simplest; a small hand-rolled Adam is
  fine too. No optimiser library.

### Training loop, paced for the eye

The convergence is a UX element, not a benchmark. Do not optimise it to finish instantly.

- Run a small number of gradient steps per animation frame (start with a handful per frame).
- Tune the learning rate and steps-per-frame so the cloud takes roughly 3 to 6 seconds to resolve.
  This duration is a deliberate knob; expose it as a constant.
- Each frame, after the step(s), render every particle at the network's current output position. The
  visible motion is the network's trajectory, which is the entire point.

### Resolved state and links

- The name stays rendered as the fuzzy point cloud once converged. Leaving it as points is the
  aesthetic.
- The logos should resolve into crisp, clickable SVGs rather than staying as point clusters. Once
  training settles, fade the sampled logo points out and fade clean vector logos in at the logo
  positions, each wrapped in an anchor to its link. Crisp vector logos look better and link far more
  reliably than trying to make a cluster of particles clickable.
- The fuzzy-name-plus-crisp-logos contrast is intentional visual hierarchy; keep it.

### Accessibility, SEO, reduced motion, mobile

These are easy to skip and annoying to retrofit, so build them in from the start.

- The page must contain the real name and the real links in the DOM as actual text and anchor
  elements, so the site is crawlable by search engines and usable by screen readers. They can be
  visually hidden (off-screen, not `display: none`, so assistive tech still reads them). The canvas
  is decoration; the DOM is the real content.
- Respect `prefers-reduced-motion`. When it is set, skip the drift and the training animation
  entirely and present the resolved name and clickable logos statically.
- Make it work on a phone. The canvas is responsive, the particle count and layout scale to the
  viewport, the name fits, and a tap triggers the reveal. Test a narrow viewport.

## Configuration: keep the content easy to edit

Everything I will want to change later must live in one place, not scattered through the logic.
Build a single config file. A `config.js` ES module exporting a plain object is ideal for a no-build
setup, since it needs no fetch and no parsing; a `config.json` loaded at runtime is an acceptable
alternative. The config holds:

- the name string and the font
- the palette (point colour, background, button and logo accents)
- the particle count and the reveal duration
- the logo list, where each entry is a label, a path to an SVG file, and a link href

Logos live as standalone SVG files in an assets folder, for example `assets/logos/`, and the config
references them by path. Adding or swapping a logo is then dropping an SVG into that folder and
editing one entry in config, with no code changes.

Targets are sampled from these config values at load time, so editing the name string or the logo
list automatically reflows the whole reveal; the sampling and training pipeline reads from config
and never needs touching to change content. Use each logo's SVG file for both jobs: rasterise it to
sample its points, and display that same file as the crisp clickable logo at the end, so there is
one asset per logo and no duplication.

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
   cloud, and the centre button, reading the name and palette from config. No network yet. Verify
   the drift looks good and is performant.
2. Target generation: render the name to an offscreen canvas and sample ink points, then draw those
   target points statically on the main canvas to confirm sampling and layout look right before any
   training exists.
3. The network and backprop in isolation: implement the MLP, Fourier features, and the optimiser,
   and confirm on a toy fit that the loss actually decreases. This is where to catch the
   normalisation and Fourier-feature issues.
4. Wire training to the button click, render per-frame outputs, and tune the pacing so it resolves
   in 3 to 6 seconds with correlated, organic motion.
5. Logos: sample them, lay them out, and implement the resolve-to-SVG transition with working
   clickable links.
6. Accessibility DOM fallback, reduced-motion path, responsive and mobile behaviour, then visual
   polish (palette, easing on the fades, button states, the drift feel).
7. Containerise: add the Dockerfile, docker-compose.yml, and .dockerignore, and confirm
   `docker compose up` serves the site on the mapped port.

## Acceptance criteria

- Clicking the button visibly trains a network whose live output positions are what is drawn;
  removing the training loop must break the convergence (proof it is not interpolation).
- The name resolves sharp and legible, not blurred.
- The cloud moves in correlated waves with SGD-like settling, not as independent dots sliding to
  fixed endpoints.
- Logos end as crisp clickable SVGs that navigate to the correct links.
- The name and all links exist as real text and anchors in the DOM.
- `prefers-reduced-motion` yields a static, fully usable page.
- It works and is legible on a narrow mobile viewport at a smooth frame rate.
- No ML library and no UI framework are present in the dependencies.
- All content (name, links, logos, colours, counts) is read from the single config file; changing
  the name or adding a logo means editing only config and the assets folder.
- The site builds and runs as a Docker container and is reachable on a mapped host port.

## Do not

- Do not substitute interpolation, tweening, easing, or physics for the network.
- Do not add TensorFlow.js or any ML or animation library.
- Do not use a frontend framework.
- Do not make the convergence instant; keep the paced 3 to 6 second reveal.
- Do not skip the random Fourier features; the text will blur without them.
- Do not skip coordinate normalisation into the tanh range.
- Do not rely on the canvas for content; the DOM must carry the name and links.
- Do not make logo links depend on clicking a cluster of particles.
- Do not hardcode the name, links, logo references, or colours into the logic; they come from the
  config file.

## You need to fill in

These are the values that go in the config file, with the logos as SVG files in the assets folder:

- NAME: «Firstname Lastname» as it should render.
- FONT: «which font for the name», and whether it is self-hosted or a web font.
- LOGOS AND LINKS: for each logo, drop an SVG file in the assets folder and give its path and link
  in config, for example «GitHub -> assets/logos/github.svg -> https://github.com/...», «LinkedIn ->
  ... -> https://...», «email -> ... -> mailto:...».
- PALETTE: point colour(s) against the black background, and any accent colour for the button and
  logos. Default is white points on black if unspecified.
- PARTICLE COUNT and REVEAL DURATION if you want something other than the ~3000 / ~4 second
  defaults.


## Git
Work on a feature branch, use conventional commits, and commit for every isolated change. The commit
history should tell the story of the build, with each commit representing a meaningful step in the
process. For example:
- `feat: add config file and load name and palette`
- `feat: implement idle drift of points`
- `refactor: extract target sampling to separate module` =
  `fix: correct coordinate normalisation for training`