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
let ctx: CanvasRenderingContext2D;
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

/** Compute the uniform scale and centering offsets for reference → screen. */
function getTransform(): { scale: number; offsetX: number; offsetY: number } {
  const scaleX = canvas.width / REF_W;
  const scaleY = canvas.height / REF_H;
  const scale = Math.min(scaleX, scaleY);
  return {
    scale,
    offsetX: (canvas.width - REF_W * scale) / 2,
    offsetY: (canvas.height - REF_H * scale) / 2,
  };
}

/** Map a reference-space point to screen pixels. */
function refToScreen(rx: number, ry: number): { x: number; y: number } {
  const { scale, offsetX, offsetY } = getTransform();
  return { x: rx * scale + offsetX, y: ry * scale + offsetY };
}

// ─── Initialisation ─────────────────────────────────────────────────────────

export function init(): void {
  canvas = document.getElementById('point-canvas') as HTMLCanvasElement;
  ctx = canvas.getContext('2d')!;
  resizeCanvas();

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
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
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

function updateDrift(): void {
  const speed = config.particles.driftSpeed;
  const margin = 50;

  for (const p of particles) {
    p.x += p.vx;
    p.y += p.vy;

    // Wrap in reference space
    if (p.x < -margin) p.x = REF_W + margin;
    if (p.x > REF_W + margin) p.x = -margin;
    if (p.y < -margin) p.y = REF_H + margin;
    if (p.y > REF_H + margin) p.y = -margin;

    p.vx += (Math.random() - 0.5) * 0.02 * speed;
    p.vy += (Math.random() - 0.5) * 0.02 * speed;
    p.vx *= 0.99;
    p.vy *= 0.99;
  }
}

// ─── Rendering ──────────────────────────────────────────────────────────────

function renderParticles(): void {
  // Clear the full canvas (in screen space)
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = config.palette.background;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Apply uniform scale transform: reference space → screen space
  const { scale, offsetX, offsetY } = getTransform();
  ctx.setTransform(scale, 0, 0, scale, offsetX, offsetY);

  const radius = config.particles.radius;
  ctx.fillStyle = config.palette.points;
  ctx.globalAlpha = config.palette.pointsAlpha;

  ctx.beginPath();
  for (const p of particles) {
    ctx.moveTo(p.x + radius, p.y);
    ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
  }
  ctx.fill();
  ctx.globalAlpha = 1;

  // Reset transform
  ctx.setTransform(1, 0, 0, 1, 0, 0);
}

// ─── Loss Display ───────────────────────────────────────────────────────────

function computeLoss(): number {
  if (!targetPositions) return 0;
  let total = 0;
  const n = particles.length;
  for (let i = 0; i < n; i++) {
    const dx = particles[i].x - targetPositions[i].x;
    const dy = particles[i].y - targetPositions[i].y;
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

  // Copy positions from optimiser into particles for rendering
  readPositions(optimizer!, particles);
  renderParticles();

  // Update loss display
  const loss = computeLoss();
  updateLossDisplay(loss);
  trackFps();

  // Check convergence
  if (loss < 0.01) {
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
    const { scale } = getTransform();

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
    for (let i = 0; i < particles.length; i++) {
      const phase = i * 0.01 + resolvedTime;
      particles[i].x = resolvedPositions[i].x + Math.sin(phase) * amp;
      particles[i].y = resolvedPositions[i].y + Math.cos(phase * 0.7) * amp;
    }
  }

  renderParticles();
  trackFps();
  animationId = requestAnimationFrame(renderLoop);
}

function positionLogoOverlays(): void {
  if (!logoPositions || logoElements.length === 0) return;

  const { scale } = getTransform();

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
