# Portfolio Site Architecture

## Rendering
- WebGL2 renderer in `renderer.ts` with two paths:
  - **Simple path**: split X/Y Float32Array buffers, CPU upload via `bufferSubData` → used for idle
    drift, resolved micro-drift, Muon fallback
  - **GPU TF path**: Transform Feedback ping-pong with 8-float interleaved buffers (pos.xy, vel.xy,
    mom.xy, extra.xy = 32 bytes/particle) → used for SGD, Adam, PSO, RMSProp during homing
- Targets stored in RG32F texture, sampled via
  `texelFetch(u_targets, ivec2(gl_VertexID % 1024, gl_VertexID / 1024), 0)`
- Settle gain taper (last 5% of reveal) drives `u_gain` uniform → multiplied into learning rates in
  shaders

## Optimizer GPU support
- SGD, Adam, PSO, RMSProp: GPU TF shaders (zero per-frame CPU→GPU position upload)
- Muon: CPU fallback only (requires global Newton-Schulz reductions that can't run in single TF
  pass)
- Adam bias correction: `bc1Acc *= beta1` must happen BEFORE setting u_bc1 uniform (not after!) to
  avoid division by zero on first step

## Key files
- `renderer.ts` — WebGL2 + TF renderer (both paths)
- `optimizers.ts` — CPU optimizer implementations (used for Muon fallback)
- `main.ts` — orchestrates state machine (idle → homing → resolved)
- `config.ts` — all tunable parameters
- `targets.ts` — text/logo sampling to point targets

## Build
- Vite + TypeScript, no framework
- `npm run dev` / `npm run build`
