/**
 * Main application: orchestrates idle drift, optimiser-driven homing, rendering,
 * and logo transitions. All particle positions live in a fixed reference
 * coordinate system (config.canvas.referenceWidth × referenceHeight) and are
 * uniformly scaled to the actual canvas at render time, so the layout looks
 * identical on every screen size.
 */
import config from './config';
import type { OptimizerType } from './config';
import { generateTargets } from './targets';
import type { Point, LogoPosition } from './targets';
import { createOptimizer, setTotalSteps, optimizerStep } from './optimizers';
import type { OptimizerState } from './optimizers';
import { createRenderer } from './renderer';
import type { Renderer } from './renderer';

// ─── Types ──────────────────────────────────────────────────────────────────

type AppState = 'idle' | 'homing' | 'resolved';

// ─── State ──────────────────────────────────────────────────────────────────

let canvas: HTMLCanvasElement;
let renderer: Renderer;
// Particle state as parallel Float32Arrays — zero-copy GPU uploads
let particleX = new Float32Array(0);
let particleY = new Float32Array(0);
let particleVX = new Float32Array(0);
let particleVY = new Float32Array(0);
let particleCount = 0;
let state: AppState = 'idle';
let animationId: number | null = null;

// Reference dimensions (from config)
const REF_W = config.canvas.referenceWidth;
const REF_H = config.canvas.referenceHeight;

// Homing state
let optimizer: OptimizerState | null = null;
let targetPositions: Point[] | null = null;
let logoPositions: LogoPosition[] | null = null;
let homingStep = 0;
let totalHomingSteps = 0;

// Logo fade state
let logoElements: HTMLAnchorElement[] = [];

// Post-convergence micro-drift
let resolvedX: Float32Array | null = null;
let resolvedY: Float32Array | null = null;
let resolvedTime = 0;

// ─── FPS tracking ───────────────────────────────────────────────────────────

let fpsFrameCount = 0;
let fpsLastTime = performance.now();
const FPS_LOG_INTERVAL = 2000; // log average FPS every 2 seconds

function trackFps(): void {
  fpsFrameCount++;
  const now = performance.now();
  const elapsed = now - fpsLastTime;
  if (elapsed >= FPS_LOG_INTERVAL) {
    const avgFps = (fpsFrameCount / elapsed) * 1000;
    console.log(`FPS: ${avgFps.toFixed(1)}`);
    fpsFrameCount = 0;
    fpsLastTime = now;
  }
}

// ─── Reference → Screen transform ──────────────────────────────────────────

/** Cached transform — recomputed only on resize. */
let cachedScale = 1;
let cachedOffsetX = 0;
let cachedOffsetY = 0;

// Visible area in reference-space coordinates — extends beyond [0, REF_W] × [0, REF_H]
// on non-16:9 viewports so idle particles fill the entire screen, not just the
// letterboxed center.
let visibleLeft = 0;
let visibleRight = REF_W;
let visibleTop = 0;
let visibleBottom = REF_H;

function updateCachedTransform(): void {
  const scaleX = canvas.width / REF_W;
  const scaleY = canvas.height / REF_H;
  cachedScale = Math.min(scaleX, scaleY);
  cachedOffsetX = (canvas.width - REF_W * cachedScale) / 2;
  cachedOffsetY = (canvas.height - REF_H * cachedScale) / 2;

  // Invert the ref→screen mapping to find what ref-space rectangle the full
  // viewport covers. On a 16:9 monitor this equals [0,REF_W]×[0,REF_H];
  // on an ultrawide the horizontal range is wider, etc.
  visibleLeft = -cachedOffsetX / cachedScale;
  visibleRight = (canvas.width - cachedOffsetX) / cachedScale;
  visibleTop = -cachedOffsetY / cachedScale;
  visibleBottom = (canvas.height - cachedOffsetY) / cachedScale;
}

/** Map a reference-space point to screen pixels. */
function refToScreen(rx: number, ry: number): { x: number; y: number } {
  return { x: rx * cachedScale + cachedOffsetX, y: ry * cachedScale + cachedOffsetY };
}

// ─── Initialisation ─────────────────────────────────────────────────────────

function init(): void {
  canvas = document.getElementById('point-canvas') as HTMLCanvasElement;

  renderer = createRenderer({
    canvas,
    maxParticles: config.particles.count + 1000, // headroom for target mismatch
    background: config.palette.background,
    pointColor: config.palette.points,
    pointAlpha: config.palette.pointsAlpha,
    pointRadius: config.particles.radius,
    refWidth: REF_W,
    refHeight: REF_H,
  });

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    showStaticFallback();
    return;
  }

  initParticles();
  startIdleDrift();

  const btn = document.getElementById('reveal-btn')!;
  btn.addEventListener('click', startReveal);
  btn.addEventListener('touchend', (e) => {
    e.preventDefault();
    startReveal();
  });

  window.addEventListener('resize', handleResize);
}

function resizeCanvas(): void {
  renderer.resize();
  updateCachedTransform();
}

function handleResize(): void {
  resizeCanvas();
  // Particles live in reference space — no position rescaling needed.
  // Just reposition DOM overlays if resolved.
  if (state === 'resolved') {
    positionLogoOverlays();
  }
}

// ─── Particles ──────────────────────────────────────────────────────────────

function initParticles(): void {
  const count = getParticleCount();
  particleCount = count;
  particleX = new Float32Array(count);
  particleY = new Float32Array(count);
  particleVX = new Float32Array(count);
  particleVY = new Float32Array(count);
  const speed = config.particles.driftSpeed;
  const vw = visibleRight - visibleLeft;
  const vh = visibleBottom - visibleTop;
  for (let i = 0; i < count; i++) {
    particleX[i] = visibleLeft + Math.random() * vw;
    particleY[i] = visibleTop + Math.random() * vh;
    particleVX[i] = (Math.random() - 0.5) * speed;
    particleVY[i] = (Math.random() - 0.5) * speed;
  }
}

function getParticleCount(): number {
  const area = window.innerWidth * window.innerHeight;
  const refArea = 1920 * 1080;
  const scale = Math.min(1, Math.sqrt(area / refArea));
  return Math.max(800, Math.floor(config.particles.count * scale));
}

// ─── Idle Drift ─────────────────────────────────────────────────────────────

function startIdleDrift(): void {
  state = 'idle';
  function driftFrame(): void {
    if (state !== 'idle') return;
    updateDrift();
    renderParticles();
    trackFps();
    animationId = requestAnimationFrame(driftFrame);
  }
  animationId = requestAnimationFrame(driftFrame);
}

// xorshift128 PRNG — Math.random() has measurable overhead when called
// hundreds of thousands of times per frame in the drift loop. This
// deterministic PRNG is ~3× faster and good enough for jitter.
let _s0 = 123456789 | 0;
let _s1 = 362436069 | 0;
let _s2 = 521288629 | 0;
let _s3 = 88675123 | 0;
function fastRandom(): number {
  const t = _s3 ^ (_s3 << 11);
  _s3 = _s2; _s2 = _s1; _s1 = _s0;
  _s0 = (_s0 ^ (_s0 >>> 19)) ^ (t ^ (t >>> 8));
  return (_s0 >>> 0) / 4294967296; // unsigned shift → [0, 1)
}

function updateDrift(): void {
  const margin = 50;
  const jitter = 0.02 * config.particles.driftSpeed;
  const n = particleCount;
  const left = visibleLeft - margin;
  const right = visibleRight + margin;
  const top = visibleTop - margin;
  const bottom = visibleBottom + margin;
  for (let i = 0; i < n; i++) {
    particleX[i] += particleVX[i];
    particleY[i] += particleVY[i];

    // Wrap around the full visible area so particles cover the entire screen
    if (particleX[i] < left) particleX[i] = right;
    if (particleX[i] > right) particleX[i] = left;
    if (particleY[i] < top) particleY[i] = bottom;
    if (particleY[i] > bottom) particleY[i] = top;

    particleVX[i] += (fastRandom() - 0.5) * jitter;
    particleVY[i] += (fastRandom() - 0.5) * jitter;
    particleVX[i] *= 0.99;
    particleVY[i] *= 0.99;
  }
}

// ─── Rendering ──────────────────────────────────────────────────────────────

function renderParticles(): void {
  renderer.drawFromArrays(particleX, particleY, particleCount);
}

// ─── Loss Display ───────────────────────────────────────────────────────────

let lossFrameCounter = 0;
let lastLoss = 0;

/** Compute loss directly from optimizer typed arrays. */
function computeLossFromArrays(px: Float32Array, py: Float32Array, tx: Float32Array, ty: Float32Array, n: number): number {
  let total = 0;
  for (let i = 0; i < n; i++) {
    const dx = px[i] - tx[i];
    const dy = py[i] - ty[i];
    total += dx * dx + dy * dy;
  }
  return total / n;
}

function formatLoss(v: number): string {
  if (v >= 10000) return v.toExponential(2);
  if (v >= 100) return v.toFixed(1);
  if (v >= 1) return v.toFixed(3);
  return v.toFixed(5);
}

function updateLossDisplay(loss: number): void {
  const el = document.getElementById('loss-counter');
  if (!el) return;
  const name = config.optimizer.type.toUpperCase();
  el.textContent = `${name} · Loss: ${formatLoss(loss)}`;
  el.style.opacity = '1';
}

function hideLossDisplay(): void {
  const el = document.getElementById('loss-counter');
  if (el) {
    el.textContent = '';
    el.style.opacity = '0';
  }
}

// ─── Homing / Reveal ────────────────────────────────────────────────────────

async function startReveal(): Promise<void> {
  if (state !== 'idle') return;
  state = 'homing';

  // Hide button
  const btn = document.getElementById('reveal-btn')!;
  btn.style.opacity = '0';
  btn.style.pointerEvents = 'none';

  if (animationId) cancelAnimationFrame(animationId);

  // Generate targets in reference space
  const result = await generateTargets(config, particleCount);
  targetPositions = result.targets;
  logoPositions = result.logoPositions;

  // Match particle count to target count
  const targetN = targetPositions!.length;
  if (targetN !== particleCount) {
    const newX = new Float32Array(targetN);
    const newY = new Float32Array(targetN);
    newX.set(particleX.subarray(0, Math.min(particleCount, targetN)));
    newY.set(particleY.subarray(0, Math.min(particleCount, targetN)));
    for (let i = particleCount; i < targetN; i++) {
      newX[i] = visibleLeft + Math.random() * (visibleRight - visibleLeft);
      newY[i] = visibleTop + Math.random() * (visibleBottom - visibleTop);
    }
    particleX = newX;
    particleY = newY;
    particleVX = new Float32Array(targetN);
    particleVY = new Float32Array(targetN);
    particleCount = targetN;
  }

  // Sort both particles and targets along x so pairing them by rank produces a
  // coherent fold-into-shape motion instead of a scramble of crossing paths.
  // This assignment strategy is cheap and visually load-bearing.
  const sortIdx = new Int32Array(particleCount);
  for (let i = 0; i < particleCount; i++) sortIdx[i] = i;
  sortIdx.sort((a, b) => particleX[a] - particleX[b] || particleY[a] - particleY[b]);
  const sortedX = new Float32Array(particleCount);
  const sortedY = new Float32Array(particleCount);
  for (let i = 0; i < particleCount; i++) {
    sortedX[i] = particleX[sortIdx[i]];
    sortedY[i] = particleY[sortIdx[i]];
  }
  particleX.set(sortedX);
  particleY.set(sortedY);

  // Create optimiser
  const stepsPerFrame = config.reveal.stepsPerFrame;
  const fps = 60;
  totalHomingSteps = config.reveal.durationSeconds * fps * stepsPerFrame;
  homingStep = 0;

  const optType = config.optimizer.type;

  if (renderer.supportsGPU(optType)) {
    // GPU Transform Feedback path: particle state stays on GPU, zero per-frame
    // CPU→GPU position upload. Muon is excluded because its Newton-Schulz
    // orthogonalization requires global dot-product reductions across all
    // particles, which can't run in a single Transform Feedback pass.
    const txArray = new Float32Array(particleCount);
    const tyArray = new Float32Array(particleCount);
    for (let i = 0; i < particleCount; i++) {
      txArray[i] = targetPositions![i].x;
      tyArray[i] = targetPositions![i].y;
    }
    const params = config.optimizer[optType] as unknown as Record<string, number>;
    renderer.initHoming(
      particleX, particleY, txArray, tyArray,
      particleCount, optType, params, totalHomingSteps,
    );
    gpuHomingFrame();
  } else {
    // CPU fallback (Muon or unsupported type)
    optimizer = createOptimizer(particleX, particleY, targetPositions!, config.optimizer);
    setTotalSteps(optimizer, totalHomingSteps);
    homingFrame();
  }
}

function gpuHomingFrame(): void {
  if (state !== 'homing') return;

  const stepsPerFrame = config.reveal.stepsPerFrame;
  renderer.stepAndDraw(stepsPerFrame);
  homingStep += stepsPerFrame;

  // Progress display (throttled)
  lossFrameCounter++;
  if (lossFrameCounter >= 10) {
    lossFrameCounter = 0;
    const pct = Math.min(100, (homingStep / totalHomingSteps) * 100);
    const name = config.optimizer.type.toUpperCase();
    const el = document.getElementById('loss-counter');
    if (el) {
      el.textContent = `${name} [GPU] · ${pct.toFixed(1)}%`;
      el.style.opacity = '1';
    }
  }
  trackFps();

  if (homingStep >= totalHomingSteps) {
    resolveHoming();
    return;
  }

  animationId = requestAnimationFrame(gpuHomingFrame);
}

function homingFrame(): void {
  if (state !== 'homing') return;

  const stepsPerFrame = config.reveal.stepsPerFrame;

  for (let s = 0; s < stepsPerFrame; s++) {
    optimizerStep(optimizer!);
    homingStep++;
  }

  // Render directly from optimizer arrays — Float32Array, zero-copy
  renderer.drawFromArrays(optimizer!.px, optimizer!.py, optimizer!.n);

  // Throttle loss computation to every 10th frame
  lossFrameCounter++;
  if (lossFrameCounter >= 10) {
    lossFrameCounter = 0;
    lastLoss = computeLossFromArrays(optimizer!.px, optimizer!.py, optimizer!.tx, optimizer!.ty, optimizer!.n);
    updateLossDisplay(lastLoss);
  }
  trackFps();

  // Check convergence (using last computed loss)
  if (lastLoss < 0.01 && lossFrameCounter === 0) {
    resolveHoming();
    return;
  }

  // Safety: resolve after exceeding step budget
  if (homingStep > totalHomingSteps * 2) {
    resolveHoming();
    return;
  }

  animationId = requestAnimationFrame(homingFrame);
}

function resolveHoming(): void {
  state = 'resolved';
  renderer.disposeHoming();
  // Snap to targets for crispness
  const targets = targetPositions!;
  for (let i = 0; i < particleCount; i++) {
    particleX[i] = targets[i].x;
    particleY[i] = targets[i].y;
  }
  resolvedX = new Float32Array(particleX.subarray(0, particleCount));
  resolvedY = new Float32Array(particleY.subarray(0, particleCount));
  fadeInLogos();
}

// ─── Logo Fade-In ───────────────────────────────────────────────────────────

function fadeInLogos(): void {
  const container = document.getElementById('logo-overlay')!;
  container.innerHTML = '';
  logoElements = [];

  config.logos.forEach((logo, i) => {
    if (!logoPositions![i]) return;
    const pos = logoPositions![i];

    // Convert reference-space logo rect to screen pixels
    const screenTopLeft = refToScreen(pos.x, pos.y);
    const scale = cachedScale;

    const a = document.createElement('a');
    a.href = logo.href;
    if (!logo.href.startsWith('mailto:')) {
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
    }
    a.className = 'logo-link';
    a.setAttribute('aria-label', logo.label);
    a.style.position = 'absolute';
    a.style.left = `${screenTopLeft.x}px`;
    a.style.top = `${screenTopLeft.y}px`;
    a.style.width = `${pos.width * scale}px`;
    a.style.height = `${pos.height * scale}px`;

    container.appendChild(a);
    logoElements.push(a);
  });

  resolvedTime = 0;
  renderLoop();
}

function renderLoop(): void {
  if (state !== 'resolved') return;

  // Subtle micro-drift around settled positions keeps the resolved text from
  // looking frozen. Uses a cheap triangle wave (no trig) per particle.
  resolvedTime += 0.01;
  if (resolvedX && resolvedY) {
    const amp = 0.3;
    const t = resolvedTime;
    const n = particleCount;
    for (let i = 0; i < n; i++) {
      const phase = i * 0.01 + t;
      const dpx = ((phase % 6.2832) / 3.1416) - 1;
      const dpy = (((phase * 0.7) % 6.2832) / 3.1416) - 1;
      particleX[i] = resolvedX[i] + dpx * amp;
      particleY[i] = resolvedY[i] + dpy * amp;
    }
  }

  renderer.drawFromArrays(particleX, particleY, particleCount);
  trackFps();
  animationId = requestAnimationFrame(renderLoop);
}

function positionLogoOverlays(): void {
  if (!logoPositions || logoElements.length === 0) return;

  const scale = cachedScale;

  logoElements.forEach((el, i) => {
    const pos = logoPositions![i];
    if (!pos) return;
    const screenTopLeft = refToScreen(pos.x, pos.y);
    el.style.left = `${screenTopLeft.x}px`;
    el.style.top = `${screenTopLeft.y}px`;
    el.style.width = `${pos.width * scale}px`;
    el.style.height = `${pos.height * scale}px`;
  });
}

// ─── Reduced Motion Fallback ────────────────────────────────────────────────

function showStaticFallback(): void {
  canvas.style.display = 'none';
  document.getElementById('reveal-btn')!.style.display = 'none';
  document.getElementById('sr-content')!.style.display = 'none';
  document.getElementById('controls')!.style.display = 'none';
  const fallback = document.getElementById('static-fallback')!;
  fallback.setAttribute('role', 'main');
  fallback.style.display = 'flex';
}

// ─── Reset ──────────────────────────────────────────────────────────────────

function resetSimulation(): void {
  if (animationId) cancelAnimationFrame(animationId);
  animationId = null;

  state = 'idle';
  renderer.disposeHoming();
  optimizer = null;
  targetPositions = null;
  logoPositions = null;
  resolvedX = null;
  resolvedY = null;
  homingStep = 0;
  resolvedTime = 0;
  hideLossDisplay();

  const container = document.getElementById('logo-overlay')!;
  container.innerHTML = '';
  logoElements = [];

  const btn = document.getElementById('reveal-btn')!;
  btn.style.opacity = '1';
  btn.style.pointerEvents = 'auto';

  initParticles();
  startIdleDrift();
}

// ─── Controls Panel ─────────────────────────────────────────────────────────

interface ParamDef {
  key: string;
  label: string;
  step: number;
}

const PARAM_DEFS: Record<OptimizerType, ParamDef[]> = {
  sgd: [
    { key: 'learningRate', label: 'Learning Rate', step: 0.01 },
    { key: 'momentum', label: 'Momentum', step: 0.01 },
  ],
  adam: [
    { key: 'learningRate', label: 'Learning Rate', step: 0.5 },
    { key: 'beta1', label: 'Beta1', step: 0.01 },
    { key: 'beta2', label: 'Beta2', step: 0.001 },
    { key: 'epsilon', label: 'Epsilon', step: 0.0000001 },
  ],
  pso: [
    { key: 'inertiaStart', label: 'Inertia Start', step: 0.01 },
    { key: 'inertiaEnd', label: 'Inertia End', step: 0.01 },
    { key: 'cognitive', label: 'Cognitive', step: 0.01 },
    { key: 'social', label: 'Social', step: 0.01 },
    { key: 'maxSpeed', label: 'Max Speed', step: 1 },
  ],
  rmsprop: [
    { key: 'learningRate', label: 'Learning Rate', step: 0.01 },
    { key: 'alpha', label: 'Alpha', step: 0.01 },
    { key: 'epsilon', label: 'Epsilon', step: 0.0000001 },
    { key: 'momentum', label: 'Momentum', step: 0.01 },
  ],
  muon: [
    { key: 'learningRate', label: 'Learning Rate', step: 1 },
    { key: 'momentum', label: 'Momentum', step: 0.01 },
    { key: 'nsSteps', label: 'NS Steps', step: 1 },
  ],
};

function initControls(): void {
  const select = document.getElementById('ctrl-optimizer') as HTMLSelectElement;
  const paramsDiv = document.getElementById('param-fields')!;
  const resetBtn = document.getElementById('ctrl-reset')!;

  select.value = config.optimizer.type;
  renderParams(config.optimizer.type);

  select.addEventListener('change', () => {
    config.optimizer.type = select.value as OptimizerType;
    renderParams(select.value as OptimizerType);
  });

  resetBtn.addEventListener('click', resetSimulation);

  function renderParams(type: OptimizerType): void {
    paramsDiv.innerHTML = '';
    const defs = PARAM_DEFS[type];
    if (!defs) return;

    const params = config.optimizer[type] as Record<string, number>;

    for (const def of defs) {
      const label = document.createElement('label');
      const span = document.createElement('span');
      span.textContent = def.label;
      const input = document.createElement('input');
      input.type = 'number';
      input.step = String(def.step);
      input.value = String(params[def.key]);
      input.addEventListener('input', () => {
        const val = parseFloat(input.value);
        if (!isNaN(val)) {
          params[def.key] = val;
        }
      });
      label.appendChild(span);
      label.appendChild(input);
      paramsDiv.appendChild(label);
    }
  }
}

// ─── Start ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  if (document.fonts) {
    document.fonts.ready.then(() => {
      init();
      initControls();
    });
  } else {
    init();
    initControls();
  }
});
