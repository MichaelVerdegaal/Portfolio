/**
 * Main application: orchestrates idle drift, training, rendering, and transitions.
 */
import config from './config.js';
import { createFourierMatrix, fourierEncode, createNetwork, forwardRender, backward } from './network.js';
import { generateTargets, normaliseTargets, denormalise } from './targets.js';

// ─── State ──────────────────────────────────────────────────────────────────
let canvas, ctx;
let particles = [];
let state = 'idle'; // 'idle' | 'training' | 'resolved'
let animationId = null;

// Network state
let network = null;
let fourierMatrix = null;
let inputCodes = null;
let encodedInputs = null;
let normalisedTargets = null;
let targetPositions = null;
let logoPositions = null;

// Training state
let trainingStep = 0;
let lastLoss = Infinity;
let emaLoss = Infinity;
let convergenceFrames = 0;

// Mini-batch state
const MINI_BATCH_SIZE = 512;
let batchIndices = null;
let batchOffset = 0;

// Logo fade state
let logoElements = [];

// Post-convergence subtle drift
let resolvedPositions = null;

// ─── Initialisation ─────────────────────────────────────────────────────────

export function init() {
  canvas = document.getElementById('point-canvas');
  ctx = canvas.getContext('2d');
  resizeCanvas();

  // Check reduced motion preference
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    showStaticFallback();
    return;
  }

  initParticles();
  startIdleDrift();

  // Button handler
  const btn = document.getElementById('reveal-btn');
  btn.addEventListener('click', startReveal);
  btn.addEventListener('touchend', (e) => {
    e.preventDefault();
    startReveal();
  });

  // Resize handler
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

  // Scale particle positions to new dimensions
  const scaleX = canvas.width / oldWidth;
  const scaleY = canvas.height / oldHeight;
  for (const p of particles) {
    p.x *= scaleX;
    p.y *= scaleY;
  }

  // If resolved, re-position logo overlays
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
  // Scale particle count for mobile
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

    // Soft wrapping with margin
    const margin = 50;
    if (p.x < -margin) p.x = w + margin;
    if (p.x > w + margin) p.x = -margin;
    if (p.y < -margin) p.y = h + margin;
    if (p.y > h + margin) p.y = -margin;

    // Gentle random perturbation
    p.vx += (Math.random() - 0.5) * 0.02 * speed;
    p.vy += (Math.random() - 0.5) * 0.02 * speed;

    // Damping to keep velocities bounded
    p.vx *= 0.99;
    p.vy *= 0.99;
  }
}

// ─── Rendering ──────────────────────────────────────────────────────────────

function renderParticles() {
  ctx.fillStyle = config.palette.background;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const radius = config.particles.radius;
  const color = config.palette.points;
  const alpha = config.palette.pointsAlpha;
  const diameter = radius * 2;

  ctx.fillStyle = color;
  ctx.globalAlpha = alpha;

  // Batch all particles into a single path for performance
  ctx.beginPath();
  for (const p of particles) {
    ctx.moveTo(p.x + radius, p.y);
    ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
  }
  ctx.fill();

  ctx.globalAlpha = 1;
}

// ─── Training / Reveal ──────────────────────────────────────────────────────

async function startReveal() {
  if (state !== 'idle') return;
  state = 'training';

  // Hide button with fade
  const btn = document.getElementById('reveal-btn');
  btn.style.opacity = '0';
  btn.style.pointerEvents = 'none';

  // Cancel idle animation
  if (animationId) cancelAnimationFrame(animationId);

  // Generate targets matching actual particle count
  const result = await generateTargets(config, canvas.width, canvas.height, particles.length);
  targetPositions = result.targets;
  logoPositions = result.logoPositions;

  // Ensure particle count matches target count
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

  // Sort particles by x for better assignment (reduces crossing)
  particles.sort((a, b) => a.x - b.x || a.y - b.y);

  // Normalise targets for training
  normalisedTargets = normaliseTargets(targetPositions, canvas.width, canvas.height);

  // Create input codes from current particle positions (captured at click time)
  const inputDim = config.network.inputDim;
  const numParticles = particles.length;
  inputCodes = new Float32Array(numParticles * inputDim);

  for (let i = 0; i < numParticles; i++) {
    // Use normalised current position as first 2 dims, random for rest
    inputCodes[i * inputDim] = (particles[i].x / canvas.width) * 2 - 1;
    inputCodes[i * inputDim + 1] = (particles[i].y / canvas.height) * 2 - 1;
    for (let d = 2; d < inputDim; d++) {
      const u1 = Math.random();
      const u2 = Math.random();
      inputCodes[i * inputDim + d] = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    }
  }

  // Create Fourier matrix and encode ALL inputs (fixed for entire training)
  fourierMatrix = createFourierMatrix(inputDim, config.network.fourierFeatures);
  encodedInputs = fourierEncode(fourierMatrix, inputCodes, numParticles);

  // Create shuffled index array for mini-batching
  batchIndices = new Uint32Array(numParticles);
  for (let i = 0; i < numParticles; i++) batchIndices[i] = i;
  shuffleArray(batchIndices);
  batchOffset = 0;

  // Create network
  network = createNetwork(config.network);

  // Start training loop
  trainingStep = 0;
  convergenceFrames = 0;
  lastLoss = Infinity;
  emaLoss = Infinity;
  trainFrame();
}

function shuffleArray(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const tmp = arr[i];
    arr[i] = arr[j];
    arr[j] = tmp;
  }
}

function getMiniBatch() {
  const numParticles = particles.length;
  const fourierDim = config.network.fourierFeatures * 2;
  const batchSize = Math.min(MINI_BATCH_SIZE, numParticles);

  // If we've exhausted the indices, reshuffle
  if (batchOffset + batchSize > numParticles) {
    shuffleArray(batchIndices);
    batchOffset = 0;
  }

  const batchInput = new Float32Array(batchSize * fourierDim);
  const batchTargets = new Float32Array(batchSize * 2);

  for (let b = 0; b < batchSize; b++) {
    const idx = batchIndices[batchOffset + b];
    // Copy Fourier-encoded input for this particle
    const srcOff = idx * fourierDim;
    const dstOff = b * fourierDim;
    for (let d = 0; d < fourierDim; d++) {
      batchInput[dstOff + d] = encodedInputs[srcOff + d];
    }
    // Copy target
    batchTargets[b * 2] = normalisedTargets[idx * 2];
    batchTargets[b * 2 + 1] = normalisedTargets[idx * 2 + 1];
  }

  batchOffset += batchSize;
  return { batchInput, batchTargets, batchSize };
}

function trainFrame() {
  if (state !== 'training') return;

  const numParticles = particles.length;
  const stepsPerFrame = config.reveal.stepsPerFrame;
  const lr = config.reveal.learningRate;

  // Run mini-batch gradient steps
  for (let s = 0; s < stepsPerFrame; s++) {
    const { batchInput, batchTargets, batchSize } = getMiniBatch();
    // Cosine decay learning rate: starts high for the dramatic lurch, decays for sharp convergence
    const progress = Math.min(1, trainingStep / (config.reveal.durationSeconds * 60 * stepsPerFrame));
    const currentLr = lr * (0.3 + 0.7 * Math.cos(progress * Math.PI * 0.5));
    lastLoss = backward(network, batchInput, batchTargets, batchSize, currentLr);
    // Exponential moving average for stable convergence detection
    emaLoss = emaLoss === Infinity ? lastLoss : 0.9 * emaLoss + 0.1 * lastLoss;
    trainingStep++;
  }

  // Full forward pass for rendering (no gradient storage needed)
  const output = forwardRender(network, encodedInputs, numParticles);

  // Update particle positions from network output
  for (let i = 0; i < numParticles; i++) {
    const nx = output[i * 2];
    const ny = output[i * 2 + 1];
    const pos = denormalise(nx, ny, canvas.width, canvas.height);
    particles[i].x = pos.x;
    particles[i].y = pos.y;
  }

  // Render
  renderParticles();

  // Check convergence using EMA loss
  if (emaLoss < 0.003) {
    convergenceFrames++;
  } else {
    convergenceFrames = Math.max(0, convergenceFrames - 2);
  }

  // Resolve after sustained low loss
  if (convergenceFrames > 30) {
    resolveTraining(numParticles);
    return;
  }

  // Safety: resolve after max duration regardless
  const targetFrames = config.reveal.durationSeconds * 60;
  const maxSteps = targetFrames * stepsPerFrame * 2.5;
  if (trainingStep > maxSteps) {
    resolveTraining(numParticles);
    return;
  }

  animationId = requestAnimationFrame(trainFrame);
}

function resolveTraining(numParticles) {
  state = 'resolved';
  // Store final positions for micro-drift reference
  resolvedPositions = particles.map(p => ({ x: p.x, y: p.y }));
  fadeInLogos();
}

// ─── Logo Fade-In ───────────────────────────────────────────────────────────

function fadeInLogos() {
  const container = document.getElementById('logo-overlay');
  container.innerHTML = '';
  logoElements = [];

  config.logos.forEach((logo, i) => {
    if (!logoPositions[i]) return;
    const pos = logoPositions[i];

    const a = document.createElement('a');
    a.href = logo.href;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.className = 'logo-link';
    a.setAttribute('aria-label', logo.label);
    a.style.position = 'absolute';
    a.style.left = `${pos.x}px`;
    a.style.top = `${pos.y}px`;
    a.style.width = `${pos.width}px`;
    a.style.height = `${pos.height}px`;
    a.style.opacity = '0';
    a.style.transition = 'opacity 1.2s ease-in';

    const img = document.createElement('img');
    img.src = logo.svg;
    img.alt = logo.label;
    img.style.width = '100%';
    img.style.height = '100%';
    img.style.filter = 'brightness(0) invert(1)';

    a.appendChild(img);
    container.appendChild(a);
    logoElements.push(a);
  });

  // Trigger fade-in on next frame
  requestAnimationFrame(() => {
    for (const el of logoElements) {
      el.style.opacity = '1';
    }
  });

  // Continue rendering the static point cloud (subtle drift at convergence)
  renderLoop();
}

let resolvedTime = 0;

function renderLoop() {
  if (state !== 'resolved') return;

  // Subtle breathing effect: tiny oscillation around resolved positions
  resolvedTime += 0.01;
  if (resolvedPositions) {
    const amp = 0.3; // sub-pixel drift amplitude
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

  const logoHeight = canvas.height * config.layout.logoHeight;
  const logoWidth = canvas.width * config.layout.logoWidth;
  const logoPadding = canvas.width * config.layout.logoPadding;
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
  // Hide the sr-only content to avoid duplicate landmarks
  document.getElementById('sr-content').style.display = 'none';
  const fallback = document.getElementById('static-fallback');
  fallback.setAttribute('role', 'main');
  fallback.style.display = 'flex';
}

// ─── Start ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  if (document.fonts) {
    document.fonts.ready.then(init);
  } else {
    init();
  }
});
