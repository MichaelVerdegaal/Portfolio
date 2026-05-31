/**
 * Per-particle optimisers: SGD with momentum, Adam, and PSO.
 * All work in canvas pixel space. No normalisation needed.
 *
 * Settling: at a constant step size none of these lands cleanly on its target.
 * Adam keeps stepping at roughly its learning rate even as the gradient vanishes
 * (the m/sqrt(v) ratio tends to sign(g)), so it oscillates at an lr-scale
 * amplitude; PSO redraws r1/r2 every step, so its stochastic forcing never dies
 * and it holds a noisy floor. Both read on screen as fuzzy, thickened glyphs.
 * The fix is a single shared schedule: hold the step size at full strength while
 * the cloud travels, then taper it to zero over the back of the reveal. As the
 * step goes to zero the oscillation amplitude collapses with it and every
 * particle coasts onto its target, where the caller's convergence snap takes over.
 */

// Fraction of the reveal spent at full step size before the taper to a stop begins.
const SETTLE_START = 0.95;

/**
 * Global settle gain over the reveal: 1.0 until SETTLE_START, then a cosine
 * taper to 0.0 by the end. Each optimiser multiplies its driving term (learning
 * rate, or the PSO force coefficients) by this so the motion stops on target
 * instead of orbiting it.
 *
 * @param {number} progress step / totalSteps, clamped to [0, 1].
 * @returns {number} Gain in [0, 1].
 */
function settleGain(progress) {
  if (progress <= SETTLE_START) return 1;
  const t = (progress - SETTLE_START) / (1 - SETTLE_START);
  return 0.5 * (1 + Math.cos(Math.PI * Math.min(1, t)));
}

/**
 * Create optimiser state for each particle.
 *
 * @param {Array<{x:number,y:number}>} particles Current positions.
 * @param {Array<{x:number,y:number}>} targets   Assigned target positions.
 * @param {object} optimizerConfig                From config.optimizer.
 * @returns {object} Optimiser state object.
 */
export function createOptimizer(particles, targets, optimizerConfig) {
  const n = particles.length;
  const type = optimizerConfig.type;

  // Per-particle state arrays (x and y interleaved)
  const state = {
    type,
    n,
    // Current positions (mutable, updated each step)
    px: new Float64Array(n),
    py: new Float64Array(n),
    // Fixed targets
    tx: new Float64Array(n),
    ty: new Float64Array(n),
    step: 0,
    totalSteps: 0,
    // Reveal progress and settle gain, refreshed each step in optimizerStep.
    progress: 0,
    gain: 1,
  };

  for (let i = 0; i < n; i++) {
    state.px[i] = particles[i].x;
    state.py[i] = particles[i].y;
    state.tx[i] = targets[i].x;
    state.ty[i] = targets[i].y;
  }

  if (type === 'sgd') {
    const cfg = optimizerConfig.sgd;
    state.lr = cfg.learningRate;
    state.momentum = cfg.momentum;
    // Velocity buffers
    state.vx = new Float64Array(n);
    state.vy = new Float64Array(n);
  } else if (type === 'adam') {
    const cfg = optimizerConfig.adam;
    state.lr = cfg.learningRate;
    state.beta1 = cfg.beta1;
    state.beta2 = cfg.beta2;
    state.epsilon = cfg.epsilon;
    // First moment
    state.mx = new Float64Array(n);
    state.my = new Float64Array(n);
    // Second moment
    state.vx = new Float64Array(n);
    state.vy = new Float64Array(n);
    // Per-particle step counter (all start at 0)
    state.t = new Float64Array(n);
  } else if (type === 'pso') {
    const cfg = optimizerConfig.pso;
    state.inertiaStart = cfg.inertiaStart;
    state.inertiaEnd = cfg.inertiaEnd;
    state.cognitive = cfg.cognitive;
    state.social = cfg.social;
    state.maxSpeed = cfg.maxSpeed;
    // Velocity buffers
    state.vx = new Float64Array(n);
    state.vy = new Float64Array(n);
    // Compute target centroid for social term
    let cx = 0, cy = 0;
    for (let i = 0; i < n; i++) {
      cx += state.tx[i];
      cy += state.ty[i];
    }
    state.centroidX = cx / n;
    state.centroidY = cy / n;
  }

  return state;
}

/**
 * Set the total expected number of steps (for annealing schedules).
 */
export function setTotalSteps(state, totalSteps) {
  state.totalSteps = totalSteps;
}

/**
 * Run one optimiser step for all particles.
 */
export function optimizerStep(state) {
  // Refresh reveal progress and the shared settle gain before stepping.
  state.progress = state.totalSteps > 0 ? Math.min(1, state.step / state.totalSteps) : 0;
  state.gain = settleGain(state.progress);

  switch (state.type) {
    case 'sgd': stepSGD(state); break;
    case 'adam': stepAdam(state); break;
    case 'pso': stepPSO(state); break;
  }
  state.step++;
}

// ─── SGD with Momentum ─────────────────────────────────────────────────────

function stepSGD(s) {
  const { n, px, py, tx, ty, vx, vy, lr, momentum, gain } = s;
  const effLr = lr * gain;
  for (let i = 0; i < n; i++) {
    const gx = px[i] - tx[i];
    const gy = py[i] - ty[i];
    vx[i] = momentum * vx[i] - effLr * gx;
    vy[i] = momentum * vy[i] - effLr * gy;
    px[i] += vx[i];
    py[i] += vy[i];
  }
}

// ─── Adam ───────────────────────────────────────────────────────────────────

function stepAdam(s) {
  const { n, px, py, tx, ty, mx, my, vx, vy, t, lr, beta1, beta2, epsilon, gain } = s;
  const effLr = lr * gain;
  for (let i = 0; i < n; i++) {
    t[i]++;
    const gx = px[i] - tx[i];
    const gy = py[i] - ty[i];

    // Update biased first moment
    mx[i] = beta1 * mx[i] + (1 - beta1) * gx;
    my[i] = beta1 * my[i] + (1 - beta1) * gy;

    // Update biased second moment
    vx[i] = beta2 * vx[i] + (1 - beta2) * gx * gx;
    vy[i] = beta2 * vy[i] + (1 - beta2) * gy * gy;

    // Bias correction
    const bc1 = 1 - Math.pow(beta1, t[i]);
    const bc2 = 1 - Math.pow(beta2, t[i]);
    const mxHat = mx[i] / bc1;
    const myHat = my[i] / bc1;
    const vxHat = vx[i] / bc2;
    const vyHat = vy[i] / bc2;

    // Step, scaled by the settle gain so the lr-scale jitter dies at the end.
    px[i] -= effLr * mxHat / (Math.sqrt(vxHat) + epsilon);
    py[i] -= effLr * myHat / (Math.sqrt(vyHat) + epsilon);
  }
}

// ─── PSO ────────────────────────────────────────────────────────────────────

function stepPSO(s) {
  const { n, px, py, tx, ty, vx, vy, cognitive, social, maxSpeed,
          inertiaStart, inertiaEnd, progress, gain, centroidX, centroidY } = s;

  // Anneal inertia from start to end over the reveal.
  const inertia = inertiaStart + (inertiaEnd - inertiaStart) * progress;

  // Social fully fades to zero, so the swarm settles on the true targets rather
  // than on a version contracted toward the centroid. The settle gain then
  // tapers both forces to zero so inertia damps the residual velocity to a stop.
  const socialWeight = social * (1 - progress);
  const cog = cognitive * gain;
  const soc = socialWeight * gain;

  for (let i = 0; i < n; i++) {
    const r1 = Math.random();
    const r2 = Math.random();

    vx[i] = inertia * vx[i]
           + cog * r1 * (tx[i] - px[i])
           + soc * r2 * (centroidX - px[i]);
    vy[i] = inertia * vy[i]
           + cog * r1 * (ty[i] - py[i])
           + soc * r2 * (centroidY - py[i]);

    // Clamp velocity
    const speed = Math.sqrt(vx[i] * vx[i] + vy[i] * vy[i]);
    if (speed > maxSpeed) {
      const scale = maxSpeed / speed;
      vx[i] *= scale;
      vy[i] *= scale;
    }

    px[i] += vx[i];
    py[i] += vy[i];
  }
}

/**
 * Copy optimiser positions back into particle objects for rendering.
 */
export function readPositions(state, particles) {
  for (let i = 0; i < state.n; i++) {
    particles[i].x = state.px[i];
    particles[i].y = state.py[i];
  }
}