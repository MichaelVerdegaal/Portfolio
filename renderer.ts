/**
 * WebGL2 point renderer with Transform Feedback GPU optimizers.
 *
 * Two rendering paths:
 * 1. Simple: CPU-uploaded split X/Y buffers (idle drift, resolved state, Muon fallback)
 * 2. GPU TF: Transform Feedback ping-pong with interleaved particle state
 *    (SGD, Adam, PSO, RMSProp — zero per-frame CPU→GPU position upload)
 */

// ─── Types ──────────────────────────────────────────────────────────────────

export interface RendererOptions {
  canvas: HTMLCanvasElement;
  maxParticles: number;
  background: string;
  pointColor: string;
  pointAlpha: number;
  pointRadius: number;
  refWidth: number;
  refHeight: number;
}

export interface Renderer {
  resize(): void;
  /** CPU-upload draw path (idle drift, resolved micro-drift, Muon fallback). */
  drawFromArrays(px: Float32Array, py: Float32Array, count: number): void;
  /** Whether the given optimizer type can run on GPU via Transform Feedback. */
  supportsGPU(type: string): boolean;
  /** Upload initial state + targets and prepare GPU optimizer. */
  initHoming(
    px: Float32Array, py: Float32Array,
    tx: Float32Array, ty: Float32Array,
    count: number, type: string,
    params: Record<string, number>,
    totalSteps: number,
  ): void;
  /** Run N optimizer steps on GPU and render. */
  stepAndDraw(stepsPerFrame: number): void;
  /** Clean up GPU homing resources. */
  disposeHoming(): void;
}

// ─── Shader Sources ─────────────────────────────────────────────────────────

// Simple path: split X/Y buffers, CPU upload (WebGL2 / GLSL 300 es)
const SIMPLE_VERT = `#version 300 es
in float a_x;
in float a_y;
uniform vec2  u_refSize;
uniform vec2  u_canvasSize;
uniform float u_pointSize;
void main() {
  float scaleX = u_canvasSize.x / u_refSize.x;
  float scaleY = u_canvasSize.y / u_refSize.y;
  float scale  = min(scaleX, scaleY);
  vec2  offset = (u_canvasSize - u_refSize * scale) * 0.5;
  vec2  screen = vec2(a_x, a_y) * scale + offset;
  vec2  ndc    = (screen / u_canvasSize) * 2.0 - 1.0;
  ndc.y        = -ndc.y;
  gl_Position  = vec4(ndc, 0.0, 1.0);
  gl_PointSize = u_pointSize * scale;
}
`;

// Shared fragment shader for both paths
const FRAG = `#version 300 es
precision mediump float;
uniform vec4 u_color;
out vec4 fragColor;
void main() { fragColor = u_color; }
`;

// No-op fragment shader for TF update pass (required but unused)
const NOOP_FRAG = `#version 300 es
precision mediump float;
out vec4 fragColor;
void main() { fragColor = vec4(0.0); }
`;

// TF render: read position from interleaved buffer
const TF_RENDER_VERT = `#version 300 es
layout(location = 0) in vec2 a_pos;
uniform vec2  u_refSize;
uniform vec2  u_canvasSize;
uniform float u_pointSize;
void main() {
  float scaleX = u_canvasSize.x / u_refSize.x;
  float scaleY = u_canvasSize.y / u_refSize.y;
  float scale  = min(scaleX, scaleY);
  vec2  offset = (u_canvasSize - u_refSize * scale) * 0.5;
  vec2  screen = a_pos * scale + offset;
  vec2  ndc    = (screen / u_canvasSize) * 2.0 - 1.0;
  ndc.y        = -ndc.y;
  gl_Position  = vec4(ndc, 0.0, 1.0);
  gl_PointSize = u_pointSize * scale;
}
`;

// Common prefix for all TF update vertex shaders.
// Per-particle interleaved layout: [pos.xy, vel.xy, mom.xy, extra.xy] = 8 floats = 32 bytes
const UPDATE_PREFIX = `#version 300 es
precision highp float;
layout(location = 0) in vec2 a_pos;
layout(location = 1) in vec2 a_vel;
layout(location = 2) in vec2 a_mom;
layout(location = 3) in vec2 a_extra;
out vec2 v_pos;
out vec2 v_vel;
out vec2 v_mom;
out vec2 v_extra;
uniform sampler2D u_targets;
uniform int u_texWidth;
uniform float u_gain;
`;

const SGD_BODY = `
uniform float u_lr;
uniform float u_momentum;
void main() {
  ivec2 tc = ivec2(gl_VertexID % u_texWidth, gl_VertexID / u_texWidth);
  vec2 target = texelFetch(u_targets, tc, 0).xy;
  vec2 grad = a_pos - target;
  float effLr = u_lr * u_gain;
  vec2 vel = u_momentum * a_vel - effLr * grad;
  v_pos = a_pos + vel;
  v_vel = vel;
  v_mom = a_mom;
  v_extra = a_extra;
}
`;

const ADAM_BODY = `
uniform float u_lr;
uniform float u_beta1;
uniform float u_beta2;
uniform float u_epsilon;
uniform float u_bc1;
uniform float u_bc2;
void main() {
  ivec2 tc = ivec2(gl_VertexID % u_texWidth, gl_VertexID / u_texWidth);
  vec2 target = texelFetch(u_targets, tc, 0).xy;
  vec2 grad = a_pos - target;
  float effLr = u_lr * u_gain;
  vec2 m = u_beta1 * a_mom + (1.0 - u_beta1) * grad;
  vec2 v = u_beta2 * a_vel + (1.0 - u_beta2) * grad * grad;
  vec2 mHat = m / u_bc1;
  vec2 vHat = v / u_bc2;
  v_pos = a_pos - effLr * mHat / (sqrt(vHat) + u_epsilon);
  v_vel = v;
  v_mom = m;
  v_extra = a_extra;
}
`;

const PSO_BODY = `
uniform float u_inertia;
uniform float u_cognitive;
uniform float u_social;
uniform float u_maxSpeed;
uniform vec2 u_centroid;
uniform float u_seed;
float hash(float n) {
  return fract(sin(n * 12.9898 + 78.233) * 43758.5453);
}
void main() {
  ivec2 tc = ivec2(gl_VertexID % u_texWidth, gl_VertexID / u_texWidth);
  vec2 target = texelFetch(u_targets, tc, 0).xy;
  float r1 = hash(float(gl_VertexID) + u_seed);
  float r2 = hash(float(gl_VertexID) + u_seed + 10000.0);
  float effInertia = u_inertia * u_gain;
  float effSocial = u_social * u_gain;
  vec2 vel = effInertia * a_vel
           + u_cognitive * r1 * (target - a_pos)
           + effSocial * r2 * (u_centroid - a_pos);
  float speedSq = dot(vel, vel);
  float maxSpeedSq = u_maxSpeed * u_maxSpeed;
  if (speedSq > maxSpeedSq) {
    vel *= u_maxSpeed / sqrt(speedSq);
  }
  v_pos = a_pos + vel;
  v_vel = vel;
  v_mom = a_mom;
  v_extra = a_extra;
}
`;

const RMSPROP_BODY = `
uniform float u_lr;
uniform float u_alpha;
uniform float u_epsilon;
uniform float u_mom;
void main() {
  ivec2 tc = ivec2(gl_VertexID % u_texWidth, gl_VertexID / u_texWidth);
  vec2 target = texelFetch(u_targets, tc, 0).xy;
  vec2 grad = a_pos - target;
  float effLr = u_lr * u_gain;
  vec2 v = u_alpha * a_vel + (1.0 - u_alpha) * grad * grad;
  vec2 buf;
  if (u_mom > 0.0) {
    buf = u_mom * a_mom + grad / (sqrt(v) + u_epsilon);
  } else {
    buf = grad / (sqrt(v) + u_epsilon);
  }
  v_pos = a_pos - effLr * buf;
  v_vel = v;
  v_mom = buf;
  v_extra = a_extra;
}
`;

// Map optimizer type → shader body
const OPTIMIZER_SHADERS: Record<string, string> = {
  sgd: UPDATE_PREFIX + SGD_BODY,
  adam: UPDATE_PREFIX + ADAM_BODY,
  pso: UPDATE_PREFIX + PSO_BODY,
  rmsprop: UPDATE_PREFIX + RMSPROP_BODY,
};

// Uniform names per optimizer (common uniforms handled separately)
const OPTIMIZER_UNIFORMS: Record<string, string[]> = {
  sgd: ['u_lr', 'u_momentum'],
  adam: ['u_lr', 'u_beta1', 'u_beta2', 'u_epsilon', 'u_bc1', 'u_bc2'],
  pso: ['u_inertia', 'u_cognitive', 'u_social', 'u_maxSpeed', 'u_centroid', 'u_seed'],
  rmsprop: ['u_lr', 'u_alpha', 'u_epsilon', 'u_mom'],
};

const COMMON_UPDATE_UNIFORMS = ['u_targets', 'u_texWidth', 'u_gain'];
const TF_VARYINGS = ['v_pos', 'v_vel', 'v_mom', 'v_extra'];

// ─── Settle Gain (replicated from optimizers.ts) ────────────────────────────

const SETTLE_START = 0.95;

function settleGain(progress: number): number {
  if (progress <= SETTLE_START) return 1;
  const t = (progress - SETTLE_START) / (1 - SETTLE_START);
  return 0.5 * (1 + Math.cos(Math.PI * Math.min(1, t)));
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [
    parseInt(h.substring(0, 2), 16) / 255,
    parseInt(h.substring(2, 4), 16) / 255,
    parseInt(h.substring(4, 6), 16) / 255,
  ];
}

function compileShader(gl: WebGL2RenderingContext, type: number, src: string): WebGLShader {
  const s = gl.createShader(type)!;
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(s);
    gl.deleteShader(s);
    throw new Error(`Shader compile error: ${log}`);
  }
  return s;
}

function linkProgram(gl: WebGL2RenderingContext, vs: WebGLShader, fs: WebGLShader): WebGLProgram {
  const p = gl.createProgram()!;
  gl.attachShader(p, vs);
  gl.attachShader(p, fs);
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
    const log = gl.getProgramInfoLog(p);
    gl.deleteProgram(p);
    throw new Error(`Program link error: ${log}`);
  }
  return p;
}

function createTFProgram(
  gl: WebGL2RenderingContext,
  vsSrc: string,
  fsSrc: string,
  varyings: string[],
): WebGLProgram {
  const vs = compileShader(gl, gl.VERTEX_SHADER, vsSrc);
  const fs = compileShader(gl, gl.FRAGMENT_SHADER, fsSrc);
  const prog = gl.createProgram()!;
  gl.attachShader(prog, vs);
  gl.attachShader(prog, fs);
  gl.transformFeedbackVaryings(prog, varyings, gl.INTERLEAVED_ATTRIBS);
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
    const log = gl.getProgramInfoLog(prog);
    gl.deleteProgram(prog);
    throw new Error(`TF program link error: ${log}`);
  }
  gl.deleteShader(vs);
  gl.deleteShader(fs);
  return prog;
}

// ─── Internal State Types ───────────────────────────────────────────────────

interface UpdateProgramInfo {
  program: WebGLProgram;
  locs: Record<string, WebGLUniformLocation | null>;
}

interface GPUState {
  active: boolean;
  type: string;
  count: number;
  currentBuf: 0 | 1;
  step: number;
  totalSteps: number;
  params: Record<string, number>;
  bc1Acc: number;
  bc2Acc: number;
  texWidth: number;
  centroidX: number;
  centroidY: number;
}

// ─── Constants ──────────────────────────────────────────────────────────────

const FLOATS_PER_PARTICLE = 8; // pos.xy + vel.xy + mom.xy + extra.xy
const STRIDE = FLOATS_PER_PARTICLE * 4; // 32 bytes
const TARGET_TEX_WIDTH = 1024;

// ─── createRenderer ─────────────────────────────────────────────────────────

export function createRenderer(opts: RendererOptions): Renderer {
  const { canvas, maxParticles, refWidth, refHeight } = opts;

  // ── WebGL2 context ────────────────────────────────────────────────────
  const gl = canvas.getContext('webgl2', {
    alpha: false,
    antialias: false,
    depth: false,
    stencil: false,
    preserveDrawingBuffer: false,
    powerPreference: 'high-performance',
  }) as WebGL2RenderingContext;

  if (!gl) throw new Error('WebGL2 not supported');

  // ── Colors & sizing ───────────────────────────────────────────────────
  const [bgR, bgG, bgB] = hexToRgb(opts.background);
  const [ptR, ptG, ptB] = hexToRgb(opts.pointColor);
  const pointSize = opts.pointRadius * 2;

  // ── Global GL state ───────────────────────────────────────────────────
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

  // ══════════════════════════════════════════════════════════════════════
  // Simple path: split X/Y buffers, CPU upload
  // ══════════════════════════════════════════════════════════════════════

  const simpleVS = compileShader(gl, gl.VERTEX_SHADER, SIMPLE_VERT);
  const simpleFS = compileShader(gl, gl.FRAGMENT_SHADER, FRAG);
  const simpleProg = linkProgram(gl, simpleVS, simpleFS);

  const sAX = gl.getAttribLocation(simpleProg, 'a_x');
  const sAY = gl.getAttribLocation(simpleProg, 'a_y');
  const sRefSize = gl.getUniformLocation(simpleProg, 'u_refSize')!;
  const sCanvasSize = gl.getUniformLocation(simpleProg, 'u_canvasSize')!;
  const sPointSize = gl.getUniformLocation(simpleProg, 'u_pointSize')!;
  const sColor = gl.getUniformLocation(simpleProg, 'u_color')!;

  // Static uniforms
  gl.useProgram(simpleProg);
  gl.uniform2f(sRefSize, refWidth, refHeight);
  gl.uniform4f(sColor, ptR, ptG, ptB, opts.pointAlpha);
  gl.uniform1f(sPointSize, pointSize);

  // Simple VAO with split X/Y buffers
  const simpleVAO = gl.createVertexArray()!;
  gl.bindVertexArray(simpleVAO);

  const byteSize = maxParticles * 4;

  const simpleXBuf = gl.createBuffer()!;
  gl.bindBuffer(gl.ARRAY_BUFFER, simpleXBuf);
  gl.bufferData(gl.ARRAY_BUFFER, byteSize, gl.DYNAMIC_DRAW);
  gl.vertexAttribPointer(sAX, 1, gl.FLOAT, false, 0, 0);
  gl.enableVertexAttribArray(sAX);

  const simpleYBuf = gl.createBuffer()!;
  gl.bindBuffer(gl.ARRAY_BUFFER, simpleYBuf);
  gl.bufferData(gl.ARRAY_BUFFER, byteSize, gl.DYNAMIC_DRAW);
  gl.vertexAttribPointer(sAY, 1, gl.FLOAT, false, 0, 0);
  gl.enableVertexAttribArray(sAY);

  gl.bindVertexArray(null);

  // ══════════════════════════════════════════════════════════════════════
  // TF path: interleaved buffers, GPU optimizer
  // ══════════════════════════════════════════════════════════════════════

  // ── TF update programs (one per supported optimizer) ──────────────────
  const updateProgs: Record<string, UpdateProgramInfo> = {};

  for (const [type, vertSrc] of Object.entries(OPTIMIZER_SHADERS)) {
    const prog = createTFProgram(gl, vertSrc, NOOP_FRAG, TF_VARYINGS);
    const allNames = [...COMMON_UPDATE_UNIFORMS, ...(OPTIMIZER_UNIFORMS[type] || [])];
    const locs: Record<string, WebGLUniformLocation | null> = {};
    for (const name of allNames) {
      locs[name] = gl.getUniformLocation(prog, name);
    }
    updateProgs[type] = { program: prog, locs };
  }

  // ── TF render program ─────────────────────────────────────────────────
  const tfRenderVS = compileShader(gl, gl.VERTEX_SHADER, TF_RENDER_VERT);
  const tfRenderFS = compileShader(gl, gl.FRAGMENT_SHADER, FRAG);
  const tfRenderProg = linkProgram(gl, tfRenderVS, tfRenderFS);

  const trCanvasSize = gl.getUniformLocation(tfRenderProg, 'u_canvasSize')!;

  // Static uniforms for TF render
  gl.useProgram(tfRenderProg);
  gl.uniform2f(gl.getUniformLocation(tfRenderProg, 'u_refSize')!, refWidth, refHeight);
  gl.uniform4f(gl.getUniformLocation(tfRenderProg, 'u_color')!, ptR, ptG, ptB, opts.pointAlpha);
  gl.uniform1f(gl.getUniformLocation(tfRenderProg, 'u_pointSize')!, pointSize);

  // ── Interleaved ping-pong buffers ─────────────────────────────────────
  const bufferByteSize = maxParticles * STRIDE;

  const particleBufs: [WebGLBuffer, WebGLBuffer] = [gl.createBuffer()!, gl.createBuffer()!];
  for (const buf of particleBufs) {
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, bufferByteSize, gl.DYNAMIC_COPY);
  }

  // ── VAOs for update pass (read all 4 interleaved attributes) ──────────
  const updateVAOs: [WebGLVertexArrayObject, WebGLVertexArrayObject] = [
    gl.createVertexArray()!,
    gl.createVertexArray()!,
  ];

  for (let i = 0; i < 2; i++) {
    gl.bindVertexArray(updateVAOs[i]);
    gl.bindBuffer(gl.ARRAY_BUFFER, particleBufs[i]);
    for (let loc = 0; loc < 4; loc++) {
      gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, STRIDE, loc * 8);
      gl.enableVertexAttribArray(loc);
    }
  }

  // ── VAOs for render pass (read only a_pos at location 0) ──────────────
  const renderVAOs: [WebGLVertexArrayObject, WebGLVertexArrayObject] = [
    gl.createVertexArray()!,
    gl.createVertexArray()!,
  ];

  for (let i = 0; i < 2; i++) {
    gl.bindVertexArray(renderVAOs[i]);
    gl.bindBuffer(gl.ARRAY_BUFFER, particleBufs[i]);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, STRIDE, 0);
    gl.enableVertexAttribArray(0);
  }

  gl.bindVertexArray(null);
  gl.bindBuffer(gl.ARRAY_BUFFER, null);

  // ── Transform Feedback objects ────────────────────────────────────────
  const tfs: [WebGLTransformFeedback, WebGLTransformFeedback] = [
    gl.createTransformFeedback()!,
    gl.createTransformFeedback()!,
  ];

  for (let i = 0; i < 2; i++) {
    gl.bindTransformFeedback(gl.TRANSFORM_FEEDBACK, tfs[i]);
    gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, particleBufs[i]);
    gl.bindTransformFeedback(gl.TRANSFORM_FEEDBACK, null);
  }

  // ── Target texture ────────────────────────────────────────────────────
  let targetTex: WebGLTexture | null = null;

  // ── GPU state ─────────────────────────────────────────────────────────
  const gpu: GPUState = {
    active: false,
    type: '',
    count: 0,
    currentBuf: 0,
    step: 0,
    totalSteps: 0,
    params: {},
    bc1Acc: 1,
    bc2Acc: 1,
    texWidth: TARGET_TEX_WIDTH,
    centroidX: 0,
    centroidY: 0,
  };

  // ══════════════════════════════════════════════════════════════════════
  // Methods
  // ══════════════════════════════════════════════════════════════════════

  function resize(): void {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    gl.viewport(0, 0, canvas.width, canvas.height);

    gl.useProgram(simpleProg);
    gl.uniform2f(sCanvasSize, canvas.width, canvas.height);

    gl.useProgram(tfRenderProg);
    gl.uniform2f(trCanvasSize, canvas.width, canvas.height);
  }

  resize();

  function drawFromArrays(px: Float32Array, py: Float32Array, count: number): void {
    gl.clearColor(bgR, bgG, bgB, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);

    gl.bindBuffer(gl.ARRAY_BUFFER, simpleXBuf);
    gl.bufferSubData(gl.ARRAY_BUFFER, 0, px.subarray(0, count));
    gl.bindBuffer(gl.ARRAY_BUFFER, simpleYBuf);
    gl.bufferSubData(gl.ARRAY_BUFFER, 0, py.subarray(0, count));

    gl.useProgram(simpleProg);
    gl.bindVertexArray(simpleVAO);
    gl.drawArrays(gl.POINTS, 0, count);
    gl.bindVertexArray(null);
  }

  function supportsGPU(type: string): boolean {
    return type in updateProgs;
  }

  function initHoming(
    px: Float32Array, py: Float32Array,
    tx: Float32Array, ty: Float32Array,
    count: number, type: string,
    params: Record<string, number>,
    totalSteps: number,
  ): void {
    if (!(type in updateProgs)) {
      throw new Error(`GPU optimizer "${type}" not supported`);
    }

    // Pack initial positions into interleaved buffer
    const data = new Float32Array(count * FLOATS_PER_PARTICLE);
    for (let i = 0; i < count; i++) {
      const off = i * FLOATS_PER_PARTICLE;
      data[off] = px[i];
      data[off + 1] = py[i];
      // vel, mom, extra all zeroed (Float32Array default)
    }

    // Upload to read buffer (buffer 0)
    gl.bindBuffer(gl.ARRAY_BUFFER, particleBufs[0]);
    gl.bufferSubData(gl.ARRAY_BUFFER, 0, data);
    gl.bindBuffer(gl.ARRAY_BUFFER, null);

    // Create target texture (RG32F, one texel per particle)
    const texWidth = TARGET_TEX_WIDTH;
    const texHeight = Math.ceil(count / texWidth);
    const texData = new Float32Array(texWidth * texHeight * 2);
    for (let i = 0; i < count; i++) {
      texData[i * 2] = tx[i];
      texData[i * 2 + 1] = ty[i];
    }

    if (targetTex) gl.deleteTexture(targetTex);
    targetTex = gl.createTexture()!;
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, targetTex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RG32F, texWidth, texHeight, 0, gl.RG, gl.FLOAT, texData);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

    // Compute target centroid (for PSO cohesion)
    let cxSum = 0, cySum = 0;
    for (let i = 0; i < count; i++) {
      cxSum += tx[i];
      cySum += ty[i];
    }

    // Set GPU state
    gpu.active = true;
    gpu.type = type;
    gpu.count = count;
    gpu.currentBuf = 0;
    gpu.step = 0;
    gpu.totalSteps = totalSteps;
    gpu.params = { ...params };
    gpu.bc1Acc = 1;
    gpu.bc2Acc = 1;
    gpu.texWidth = texWidth;
    gpu.centroidX = cxSum / count;
    gpu.centroidY = cySum / count;

    // Set static uniforms on the update program
    const prog = updateProgs[type];
    gl.useProgram(prog.program);
    gl.uniform1i(prog.locs.u_targets, 0); // texture unit 0
    gl.uniform1i(prog.locs.u_texWidth, texWidth);

    // Set optimizer-specific static uniforms
    if (type === 'sgd') {
      gl.uniform1f(prog.locs.u_lr, params.learningRate);
      gl.uniform1f(prog.locs.u_momentum, params.momentum);
    } else if (type === 'adam') {
      gl.uniform1f(prog.locs.u_lr, params.learningRate);
      gl.uniform1f(prog.locs.u_beta1, params.beta1);
      gl.uniform1f(prog.locs.u_beta2, params.beta2);
      gl.uniform1f(prog.locs.u_epsilon, params.epsilon);
    } else if (type === 'pso') {
      gl.uniform1f(prog.locs.u_cognitive, params.cognitive);
      gl.uniform1f(prog.locs.u_maxSpeed, params.maxSpeed);
      gl.uniform2f(prog.locs.u_centroid, gpu.centroidX, gpu.centroidY);
    } else if (type === 'rmsprop') {
      gl.uniform1f(prog.locs.u_lr, params.learningRate);
      gl.uniform1f(prog.locs.u_alpha, params.alpha);
      gl.uniform1f(prog.locs.u_epsilon, params.epsilon);
      gl.uniform1f(prog.locs.u_mom, params.momentum);
    }
  }

  function setPerStepUniforms(
    prog: UpdateProgramInfo,
    gain: number,
    progress: number,
  ): void {
    gl.uniform1f(prog.locs.u_gain, gain);

    if (gpu.type === 'adam') {
      gl.uniform1f(prog.locs.u_bc1, 1 - gpu.bc1Acc);
      gl.uniform1f(prog.locs.u_bc2, 1 - gpu.bc2Acc);
    } else if (gpu.type === 'pso') {
      const inertia = gpu.params.inertiaStart
        + (gpu.params.inertiaEnd - gpu.params.inertiaStart) * progress;
      gl.uniform1f(prog.locs.u_inertia, inertia);
      const socialBase = gpu.params.social * (1 - progress);
      gl.uniform1f(prog.locs.u_social, socialBase);
      gl.uniform1f(prog.locs.u_seed, gpu.step * 1.618033988749);
    }
  }

  function stepAndDraw(stepsPerFrame: number): void {
    if (!gpu.active) return;

    const prog = updateProgs[gpu.type];

    // Bind target texture
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, targetTex!);

    // Activate update program
    gl.useProgram(prog.program);

    // Unbind ARRAY_BUFFER to avoid TF dual-binding conflict
    gl.bindBuffer(gl.ARRAY_BUFFER, null);

    // Enable rasterizer discard for all update steps
    gl.enable(gl.RASTERIZER_DISCARD);

    for (let s = 0; s < stepsPerFrame; s++) {
      const progress = gpu.totalSteps > 0
        ? Math.min(1, gpu.step / gpu.totalSteps)
        : 0;
      const gain = settleGain(progress);

      // Adam: advance bias correction BEFORE setting uniforms
      // (bc1Acc starts at 1; multiplying first avoids division by zero)
      if (gpu.type === 'adam') {
        gpu.bc1Acc *= gpu.params.beta1;
        gpu.bc2Acc *= gpu.params.beta2;
      }

      setPerStepUniforms(prog, gain, progress);

      const readIdx = gpu.currentBuf;
      const writeIdx = (1 - readIdx) as 0 | 1;

      gl.bindVertexArray(updateVAOs[readIdx]);
      gl.bindTransformFeedback(gl.TRANSFORM_FEEDBACK, tfs[writeIdx]);
      gl.beginTransformFeedback(gl.POINTS);
      gl.drawArrays(gl.POINTS, 0, gpu.count);
      gl.endTransformFeedback();
      gl.bindTransformFeedback(gl.TRANSFORM_FEEDBACK, null);

      gpu.currentBuf = writeIdx;
      gpu.step++;
    }

    gl.disable(gl.RASTERIZER_DISCARD);
    gl.bindVertexArray(null);

    // Render from the buffer that has the latest state
    gl.clearColor(bgR, bgG, bgB, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);

    gl.useProgram(tfRenderProg);
    gl.bindVertexArray(renderVAOs[gpu.currentBuf]);
    gl.drawArrays(gl.POINTS, 0, gpu.count);
    gl.bindVertexArray(null);
  }

  function disposeHoming(): void {
    gpu.active = false;
    if (targetTex) {
      gl.deleteTexture(targetTex);
      targetTex = null;
    }
  }

  return { resize, drawFromArrays, supportsGPU, initHoming, stepAndDraw, disposeHoming };
}
