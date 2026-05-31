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
  } else if (type === 'rmsprop') {
    const cfg = optimizerConfig.rmsprop;
    state.lr = cfg.learningRate;
    state.alpha = cfg.alpha;
    state.epsilon = cfg.epsilon;
    state.mom = cfg.momentum;
    // Running average of squared gradient
    state.vx = new Float64Array(n);
    state.vy = new Float64Array(n);
    // Momentum buffer (used only when momentum > 0)
    state.bx = new Float64Array(n);
    state.by = new Float64Array(n);
  } else if (type === 'muon') {
    const cfg = optimizerConfig.muon;
    state.lr = cfg.learningRate;
    state.momentum = cfg.momentum;
    state.nsSteps = cfg.nsSteps;
    // Momentum buffer
    state.bufX = new Float64Array(n);
    state.bufY = new Float64Array(n);
    // Pre-allocated scratch arrays for Newton-Schulz iteration
    state.nsX0 = new Float64Array(n);
    state.nsX1 = new Float64Array(n);
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
    case 'rmsprop': stepRMSProp(state); break;
    case 'muon': stepMuon(state); break;
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

  // Apply gain to inertia so velocity memory dies during settle, but keep
  // cognitive force alive so particles keep being pulled toward their targets.
  // As particles approach their targets the cognitive term (proportional to
  // distance) naturally vanishes, giving a clean stop.
  const effInertia = inertia * gain;
  const socialWeight = social * (1 - progress);
  const cog = cognitive;
  const soc = socialWeight * gain;

  for (let i = 0; i < n; i++) {
    const r1 = Math.random();
    const r2 = Math.random();

    vx[i] = effInertia * vx[i]
           + cog * r1 * (tx[i] - px[i])
           + soc * r2 * (centroidX - px[i]);
    vy[i] = effInertia * vy[i]
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

// ─── RMSProp ────────────────────────────────────────────────────────────────

function stepRMSProp(s) {
  const { n, px, py, tx, ty, vx, vy, bx, by, lr, alpha, epsilon, mom, gain } = s;
  const effLr = lr * gain;

  for (let i = 0; i < n; i++) {
    const gx = px[i] - tx[i];
    const gy = py[i] - ty[i];

    // Running average of squared gradient
    vx[i] = alpha * vx[i] + (1 - alpha) * gx * gx;
    vy[i] = alpha * vy[i] + (1 - alpha) * gy * gy;

    if (mom > 0) {
      // Momentum variant
      bx[i] = mom * bx[i] + gx / (Math.sqrt(vx[i]) + epsilon);
      by[i] = mom * by[i] + gy / (Math.sqrt(vy[i]) + epsilon);
      px[i] -= effLr * bx[i];
      py[i] -= effLr * by[i];
    } else {
      px[i] -= effLr * gx / (Math.sqrt(vx[i]) + epsilon);
      py[i] -= effLr * gy / (Math.sqrt(vy[i]) + epsilon);
    }
  }
}

// ─── Muon (Momentum + Newton-Schulz Orthogonalisation) ─────────────────────

function stepMuon(s) {
  const { n, px, py, tx, ty, bufX, bufY, lr, momentum, nsSteps, gain,
          nsX0, nsX1 } = s;
  const effLr = lr * gain;

  // 1. Gradient + momentum accumulation
  for (let i = 0; i < n; i++) {
    const gx = px[i] - tx[i];
    const gy = py[i] - ty[i];
    bufX[i] = momentum * bufX[i] + gx;
    bufY[i] = momentum * bufY[i] + gy;
  }

  // 2. Newton-Schulz orthogonalisation of the N×2 momentum matrix.
  //    Since N >> 2 we work with the transpose (2×N rows in nsX0, nsX1).
  let normSq = 0;
  for (let i = 0; i < n; i++) {
    normSq += bufX[i] * bufX[i] + bufY[i] * bufY[i];
  }
  const norm = Math.sqrt(normSq) + 1e-7;

  for (let i = 0; i < n; i++) {
    nsX0[i] = bufX[i] / norm;
    nsX1[i] = bufY[i] / norm;
  }

  const ca = 3.4445, cb = -4.7750, cc = 2.0315;

  for (let step = 0; step < nsSteps; step++) {
    // A = X @ Xᵀ  (2×2, symmetric)
    let a00 = 0, a01 = 0, a11 = 0;
    for (let i = 0; i < n; i++) {
      a00 += nsX0[i] * nsX0[i];
      a01 += nsX0[i] * nsX1[i];
      a11 += nsX1[i] * nsX1[i];
    }

    // B = cb·A + cc·A² (2×2)
    const aa00 = a00 * a00 + a01 * a01;
    const aa01 = a00 * a01 + a01 * a11;
    const aa11 = a01 * a01 + a11 * a11;

    const b00 = cb * a00 + cc * aa00;
    const b01 = cb * a01 + cc * aa01;
    const b10 = b01; // symmetric
    const b11 = cb * a11 + cc * aa11;

    // X ← ca·X + B·X  (2×N)
    for (let i = 0; i < n; i++) {
      const tmp0 = ca * nsX0[i] + b00 * nsX0[i] + b01 * nsX1[i];
      const tmp1 = ca * nsX1[i] + b10 * nsX0[i] + b11 * nsX1[i];
      nsX0[i] = tmp0;
      nsX1[i] = tmp1;
    }
  }

  // 3. Apply the orthogonalised update
  for (let i = 0; i < n; i++) {
    px[i] -= effLr * nsX0[i];
    py[i] -= effLr * nsX1[i];
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