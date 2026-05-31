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
import { createOptimizer, setTotalSteps, optimizerStep, readPositions } from './optimizers';
import type { OptimizerState } from './optimizers';
import { createRenderer } from './renderer';
import type { Renderer } from './renderer';

// ─── Types ──────────────────────────────────────────────────────────────────

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

type AppState = 'idle' | 'homing' | 'resolved';

// ─── State ──────────────────────────────────────────────────────────────────

let canvas: HTMLCanvasElement;
let renderer: Renderer;
let particles: Particle[] = [];
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
let resolvedPositions: Point[] | null = null;
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

function updateCachedTransform(): void {
  const scaleX = canvas.width / REF_W;
  const scaleY = canvas.height / REF_H;
  cachedScale = Math.min(scaleX, scaleY);
  cachedOffsetX = (canvas.width - REF_W * cachedScale) / 2;
  cachedOffsetY = (canvas.height - REF_H * cachedScale) / 2;
}

/** Map a reference-space point to screen pixels. */
function refToScreen(rx: number, ry: number): { x: number; y: number } {
  return { x: rx * cachedScale + cachedOffsetX, y: ry * cachedScale + cachedOffsetY };
}

// ─── Initialisation ─────────────────────────────────────────────────────────

export function init(): void {
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
  particles = [];
  for (let i = 0; i < count; i++) {
    particles.push({
      x: Math.random() * REF_W,
      y: Math.random() * REF_H,
      vx: (Math.random() - 0.5) * config.particles.driftSpeed,
      vy: (Math.random() - 0.5) * config.particles.driftSpeed,
    });
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

// Fast xorshift128 PRNG — avoids overhead of Math.random() in hot loops
let _s0 = 123456789 | 0;
let _s1 = 362436069 | 0;
let _s2 = 521288629 | 0;
let _s3 = 88675123 | 0;
function fastRandom(): number {
  const t = _s3 ^ (_s3 << 11);
  _s3 = _s2; _s2 = _s1; _s1 = _s0;
  _s0 = (_s0 ^ (_s0 >>> 19)) ^ (t ^ (t >>> 8));
  // Map to [0, 1) — use unsigned shift to get positive value
  return (_s0 >>> 0) / 4294967296;
}

function updateDrift(): void {
  const speed = config.particles.driftSpeed;
  const margin = 50;
  const jitter = 0.02 * speed;

  for (const p of particles) {
    p.x += p.vx;
    p.y += p.vy;

    // Wrap in reference space
    if (p.x < -margin) p.x = REF_W + margin;
    if (p.x > REF_W + margin) p.x = -margin;
    if (p.y < -margin) p.y = REF_H + margin;
    if (p.y > REF_H + margin) p.y = -margin;

    p.vx += (fastRandom() - 0.5) * jitter;
    p.vy += (fastRandom() - 0.5) * jitter;
    p.vx *= 0.99;
    p.vy *= 0.99;
  }
}

// ─── Rendering ──────────────────────────────────────────────────────────────

function renderParticles(): void {
  renderer.drawParticles(particles, particles.length);
}

/** Render directly from optimizer typed arrays — avoids the readPositions copy. */
function renderFromArrays(px: Float64Array, py: Float64Array, n: number): void {
  renderer.drawFromArrays(px, py, n);
}

// ─── Loss Display ───────────────────────────────────────────────────────────

let lossFrameCounter = 0;
let lastLoss = 0;

/** Compute loss directly from optimizer typed arrays — avoids particle object access. */
function computeLossFromArrays(px: Float64Array, py: Float64Array, tx: Float64Array, ty: Float64Array, n: number): number {
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
  const result = await generateTargets(config, particles.length);
  targetPositions = result.targets;
  logoPositions = result.logoPositions;

  // Match particle count to target count
  while (particles.length < targetPositions.length) {
    particles.push({
      x: Math.random() * REF_W,
      y: Math.random() * REF_H,
      vx: 0,
      vy: 0,
    });
  }
  while (particles.length > targetPositions.length) {
    particles.pop();
  }

  // Sort particles by x for sorted-axis assignment (reduces crossing paths)
  particles.sort((a, b) => a.x - b.x || a.y - b.y);

  // Create optimiser
  const stepsPerFrame = config.reveal.stepsPerFrame;
  const fps = 60;
  totalHomingSteps = config.reveal.durationSeconds * fps * stepsPerFrame;
  optimizer = createOptimizer(particles, targetPositions, config.optimizer);
  setTotalSteps(optimizer, totalHomingSteps);
  homingStep = 0;

  homingFrame();
}

function homingFrame(): void {
  if (state !== 'homing') return;

  const stepsPerFrame = config.reveal.stepsPerFrame;

  for (let s = 0; s < stepsPerFrame; s++) {
    optimizerStep(optimizer!);
    homingStep++;
  }

  // Render directly from optimizer arrays — skip readPositions copy
  renderFromArrays(optimizer!.px, optimizer!.py, optimizer!.n);

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
    // Copy final positions to particles for resolved state
    readPositions(optimizer!, particles);
    resolveHoming();
    return;
  }

  // Safety: resolve after exceeding step budget
  if (homingStep > totalHomingSteps * 2) {
    readPositions(optimizer!, particles);
    resolveHoming();
    return;
  }

  animationId = requestAnimationFrame(homingFrame);
}

function resolveHoming(): void {
  state = 'resolved';
  // Snap to targets for crispness
  for (let i = 0; i < particles.length; i++) {
    particles[i].x = targetPositions![i].x;
    particles[i].y = targetPositions![i].y;
  }
  resolvedPositions = particles.map(p => ({ x: p.x, y: p.y }));
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

  // Subtle micro-drift around settled positions
  resolvedTime += 0.01;
  if (resolvedPositions) {
    const amp = 0.3;
    const t = resolvedTime;
    // Use a cheap triangle-wave approximation instead of sin/cos per particle
    // sin(x) ≈ triangle wave with same period, indistinguishable at 0.3px amplitude
    const n = particles.length;
    for (let i = 0; i < n; i++) {
      const phase = i * 0.01 + t;
      // Wrap to [0, 2π], then cheap triangle wave in [-1, 1]
      const px = ((phase % 6.2832) / 3.1416) - 1; // [-1, 1]
      const py = (((phase * 0.7) % 6.2832) / 3.1416) - 1;
      particles[i].x = resolvedPositions[i].x + px * amp;
      particles[i].y = resolvedPositions[i].y + py * amp;
    }
  }

  renderParticles();
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
  optimizer = null;
  targetPositions = null;
  logoPositions = null;
  resolvedPositions = null;
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
