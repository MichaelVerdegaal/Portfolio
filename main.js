/**
 * Main application: orchestrates idle drift, optimiser-driven homing, rendering,
 * and logo transitions. No neural network — particles move directly toward their
 * targets under a selectable optimiser (SGD, Adam, or PSO).
 */
import config from './config.js';
import { generateTargets } from './targets.js';
import { createOptimizer, setTotalSteps, optimizerStep, readPositions } from './optimizers.js';

// ─── State ──────────────────────────────────────────────────────────────────
let canvas, ctx;
let particles = [];
let state = 'idle'; // 'idle' | 'homing' | 'resolved'
let animationId = null;

// Homing state
let optimizer = null;
let targetPositions = null;
let logoPositions = null;
let homingStep = 0;
let totalHomingSteps = 0;

// Logo fade state
let logoElements = [];

// Post-convergence micro-drift
let resolvedPositions = null;
let resolvedTime = 0;

// ─── Initialisation ─────────────────────────────────────────────────────────

export function init() {
  canvas = document.getElementById('point-canvas');
  ctx = canvas.getContext('2d');
  resizeCanvas();

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    showStaticFallback();
    return;
  }

  initParticles();
  startIdleDrift();

  const btn = document.getElementById('reveal-btn');
  btn.addEventListener('click', startReveal);
  btn.addEventListener('touchend', (e) => {
    e.preventDefault();
    startReveal();
  });

  window.addEventListener('resize', handleResize);
}

function resizeCanvas() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}

function handleResize() {
  const oldWidth = canvas.width;
  const oldHeight = canvas.height;
  resizeCanvas();

  if (oldWidth === 0 || oldHeight === 0) return;

  const scaleX = canvas.width / oldWidth;
  const scaleY = canvas.height / oldHeight;
  for (const p of particles) {
    p.x *= scaleX;
    p.y *= scaleY;
  }

  if (resolvedPositions) {
    for (const p of resolvedPositions) {
      p.x *= scaleX;
      p.y *= scaleY;
    }
  }

  if (state === 'resolved') {
    positionLogoOverlays();
  }
}

// ─── Particles ──────────────────────────────────────────────────────────────

function initParticles() {
  const count = getParticleCount();
  particles = [];
  for (let i = 0; i < count; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * config.particles.driftSpeed,
      vy: (Math.random() - 0.5) * config.particles.driftSpeed,
    });
  }
}

function getParticleCount() {
  const area = window.innerWidth * window.innerHeight;
  const refArea = 1920 * 1080;
  const scale = Math.min(1, Math.sqrt(area / refArea));
  return Math.max(800, Math.floor(config.particles.count * scale));
}

// ─── Idle Drift ─────────────────────────────────────────────────────────────

function startIdleDrift() {
  state = 'idle';
  function driftFrame() {
    if (state !== 'idle') return;
    updateDrift();
    renderParticles();
    animationId = requestAnimationFrame(driftFrame);
  }
  animationId = requestAnimationFrame(driftFrame);
}

function updateDrift() {
  const w = canvas.width;
  const h = canvas.height;
  const speed = config.particles.driftSpeed;

  for (const p of particles) {
    p.x += p.vx;
    p.y += p.vy;

    const margin = 50;
    if (p.x < -margin) p.x = w + margin;
    if (p.x > w + margin) p.x = -margin;
    if (p.y < -margin) p.y = h + margin;
    if (p.y > h + margin) p.y = -margin;

    p.vx += (Math.random() - 0.5) * 0.02 * speed;
    p.vy += (Math.random() - 0.5) * 0.02 * speed;
    p.vx *= 0.99;
    p.vy *= 0.99;
  }
}

// ─── Rendering ──────────────────────────────────────────────────────────────

function renderParticles() {
  ctx.fillStyle = config.palette.background;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

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
}

// ─── Loss Display ───────────────────────────────────────────────────────────

function computeLoss() {
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

function formatLoss(v) {
  if (v >= 10000) return v.toExponential(2);
  if (v >= 100) return v.toFixed(1);
  if (v >= 1) return v.toFixed(3);
  return v.toFixed(5);
}

function updateLossDisplay(loss) {
  const el = document.getElementById('loss-counter');
  if (!el) return;
  const name = config.optimizer.type.toUpperCase();
  el.textContent = `${name} · Loss: ${formatLoss(loss)}`;
  el.style.opacity = '1';
}

function hideLossDisplay() {
  const el = document.getElementById('loss-counter');
  if (el) {
    el.textContent = '';
    el.style.opacity = '0';
  }
}

// ─── Homing / Reveal ────────────────────────────────────────────────────────

async function startReveal() {
  if (state !== 'idle') return;
  state = 'homing';

  // Hide button
  const btn = document.getElementById('reveal-btn');
  btn.style.opacity = '0';
  btn.style.pointerEvents = 'none';

  if (animationId) cancelAnimationFrame(animationId);

  // Generate targets
  const result = await generateTargets(config, canvas.width, canvas.height, particles.length);
  targetPositions = result.targets;
  logoPositions = result.logoPositions;

  // Match particle count to target count
  while (particles.length < targetPositions.length) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
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

function homingFrame() {
  if (state !== 'homing') return;

  const stepsPerFrame = config.reveal.stepsPerFrame;

  for (let s = 0; s < stepsPerFrame; s++) {
    optimizerStep(optimizer);
    homingStep++;
  }

  // Copy positions from optimiser into particles for rendering
  readPositions(optimizer, particles);
  renderParticles();

  // Update loss display
  const loss = computeLoss();
  updateLossDisplay(loss);

  // Check convergence
  if (loss < 1.0) {
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

function resolveHoming() {
  state = 'resolved';
  hideLossDisplay();
  // Snap to targets for crispness
  for (let i = 0; i < particles.length; i++) {
    particles[i].x = targetPositions[i].x;
    particles[i].y = targetPositions[i].y;
  }
  resolvedPositions = particles.map(p => ({ x: p.x, y: p.y }));
  fadeInLogos();
}

// ─── Logo Fade-In ───────────────────────────────────────────────────────────

function fadeInLogos() {
  const container = document.getElementById('logo-overlay');
  container.innerHTML = '';
  logoElements = [];

  // The point cluster is the visible logo now. Each anchor is an invisible
  // clickable box laid over its cluster, so the hit target sits on the points
  // and there is nothing to size-match.
  config.logos.forEach((logo, i) => {
    if (!logoPositions[i]) return;
    const pos = logoPositions[i];

    const a = document.createElement('a');
    a.href = logo.href;
    if (!logo.href.startsWith('mailto:')) {
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
    }
    a.className = 'logo-link';
    a.setAttribute('aria-label', logo.label);
    a.style.position = 'absolute';
    a.style.left = `${pos.x}px`;
    a.style.top = `${pos.y}px`;
    a.style.width = `${pos.width}px`;
    a.style.height = `${pos.height}px`;

    container.appendChild(a);
    logoElements.push(a);
  });

  resolvedTime = 0;
  renderLoop();
}

function renderLoop() {
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
  animationId = requestAnimationFrame(renderLoop);
}

function positionLogoOverlays() {
  if (!logoPositions || logoElements.length === 0) return;

  const isMobile = canvas.width < 768;
  const logoScale = isMobile ? 1.8 : 1;
  const logoHeight = canvas.height * config.layout.logoHeight * logoScale;
  const logoWidth = canvas.width * config.layout.logoWidth * logoScale;
  const logoPadding = canvas.width * config.layout.logoPadding * (isMobile ? 1.5 : 1);
  const totalLogosWidth = config.logos.length * logoWidth + (config.logos.length - 1) * logoPadding;
  const logoStartX = (canvas.width - totalLogosWidth) / 2;
  const logoY = canvas.height * (0.42 + config.layout.nameScale / 2 + config.layout.logoGap);

  logoElements.forEach((el, i) => {
    const lx = logoStartX + i * (logoWidth + logoPadding);
    el.style.left = `${lx}px`;
    el.style.top = `${logoY}px`;
    el.style.width = `${logoWidth}px`;
    el.style.height = `${logoHeight}px`;
  });
}

// ─── Reduced Motion Fallback ────────────────────────────────────────────────

function showStaticFallback() {
  canvas.style.display = 'none';
  document.getElementById('reveal-btn').style.display = 'none';
  document.getElementById('sr-content').style.display = 'none';
  document.getElementById('controls').style.display = 'none';
  const fallback = document.getElementById('static-fallback');
  fallback.setAttribute('role', 'main');
  fallback.style.display = 'flex';
}

// ─── Reset ──────────────────────────────────────────────────────────────────

function resetSimulation() {
  // Cancel any running animation
  if (animationId) cancelAnimationFrame(animationId);
  animationId = null;

  // Reset state
  state = 'idle';
  optimizer = null;
  targetPositions = null;
  logoPositions = null;
  resolvedPositions = null;
  homingStep = 0;
  resolvedTime = 0;
  hideLossDisplay();

  // Clear logo overlay
  const container = document.getElementById('logo-overlay');
  container.innerHTML = '';
  logoElements = [];

  // Restore button
  const btn = document.getElementById('reveal-btn');
  btn.style.opacity = '1';
  btn.style.pointerEvents = 'auto';

  // Re-init particles and restart drift
  initParticles();
  startIdleDrift();
}

// ─── Controls Panel ─────────────────────────────────────────────────────────

const PARAM_DEFS = {
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

function initControls() {
  const select = document.getElementById('ctrl-optimizer');
  const paramsDiv = document.getElementById('param-fields');
  const resetBtn = document.getElementById('ctrl-reset');

  // Set initial selection from config
  select.value = config.optimizer.type;
  renderParams(config.optimizer.type);

  select.addEventListener('change', () => {
    config.optimizer.type = select.value;
    renderParams(select.value);
  });

  resetBtn.addEventListener('click', resetSimulation);

  function renderParams(type) {
    paramsDiv.innerHTML = '';
    const defs = PARAM_DEFS[type];
    if (!defs) return;

    for (const def of defs) {
      const label = document.createElement('label');
      const span = document.createElement('span');
      span.textContent = def.label;
      const input = document.createElement('input');
      input.type = 'number';
      input.step = def.step;
      input.value = config.optimizer[type][def.key];
      input.addEventListener('input', () => {
        const val = parseFloat(input.value);
        if (!isNaN(val)) {
          config.optimizer[type][def.key] = val;
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
