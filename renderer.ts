/**
 * WebGL point-sprite renderer.
 *
 * Draws all particles in a single gl.drawArrays(POINTS, …) call.
 * Positions are uploaded each frame via bufferSubData into a pre-allocated
 * Float32Array. The vertex shader maps from reference-space coordinates to
 * clip space using a uniform projection, so no per-point JS transform is needed.
 */

export interface RendererOptions {
  /** Canvas element to render into. */
  canvas: HTMLCanvasElement;
  /** Maximum number of particles that will ever be drawn. */
  maxParticles: number;
  /** Background colour as CSS hex string, e.g. '#191A1C'. */
  background: string;
  /** Point colour as CSS hex string, e.g. '#ffffff'. */
  pointColor: string;
  /** Point alpha [0, 1]. */
  pointAlpha: number;
  /** Point radius in reference-space units. */
  pointRadius: number;
  /** Reference coordinate system width. */
  refWidth: number;
  /** Reference coordinate system height. */
  refHeight: number;
}

// ─── Shaders ────────────────────────────────────────────────────────────────

const VERT_SRC = `
attribute vec2 a_pos;
uniform vec2 u_refSize;    // (refWidth, refHeight)
uniform vec2 u_canvasSize; // (canvas.width, canvas.height)
uniform float u_pointSize;

void main() {
  // Uniform-scale fit: reference → screen
  float scaleX = u_canvasSize.x / u_refSize.x;
  float scaleY = u_canvasSize.y / u_refSize.y;
  float scale  = min(scaleX, scaleY);

  vec2 offset = (u_canvasSize - u_refSize * scale) * 0.5;
  vec2 screen = a_pos * scale + offset;

  // screen → clip (NDC)
  vec2 ndc = (screen / u_canvasSize) * 2.0 - 1.0;
  ndc.y = -ndc.y; // flip Y — canvas Y grows down, GL Y grows up

  gl_Position  = vec4(ndc, 0.0, 1.0);
  gl_PointSize = u_pointSize * scale;
}
`;

const FRAG_SRC = `
precision mediump float;
uniform vec4 u_color;

void main() {
  gl_FragColor = u_color;
}
`;

// ─── Helpers ────────────────────────────────────────────────────────────────

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [
    parseInt(h.substring(0, 2), 16) / 255,
    parseInt(h.substring(2, 4), 16) / 255,
    parseInt(h.substring(4, 6), 16) / 255,
  ];
}

function compileShader(gl: WebGLRenderingContext, type: number, src: string): WebGLShader {
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

function linkProgram(gl: WebGLRenderingContext, vs: WebGLShader, fs: WebGLShader): WebGLProgram {
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

// ─── Renderer ───────────────────────────────────────────────────────────────

export interface Renderer {
  /** Resize the viewport (call on window resize). */
  resize(): void;
  /** Draw particles from a Particle[] array (idle / resolved states). */
  drawParticles(particles: { x: number; y: number }[], count: number): void;
  /** Draw particles directly from Float64Array pair (homing state — zero copy from optimizer). */
  drawFromArrays(px: Float64Array, py: Float64Array, count: number): void;
}

export function createRenderer(opts: RendererOptions): Renderer {
  const { canvas, maxParticles, refWidth, refHeight } = opts;

  const gl = canvas.getContext('webgl', {
    alpha: false,
    antialias: false,
    depth: false,
    stencil: false,
    preserveDrawingBuffer: false,
    powerPreference: 'high-performance',
  })!;

  // ── Compile program ──
  const vs = compileShader(gl, gl.VERTEX_SHADER, VERT_SRC);
  const fs = compileShader(gl, gl.FRAGMENT_SHADER, FRAG_SRC);
  const prog = linkProgram(gl, vs, fs);

  // ── Locations ──
  const aPos = gl.getAttribLocation(prog, 'a_pos');
  const uRefSize = gl.getUniformLocation(prog, 'u_refSize')!;
  const uCanvasSize = gl.getUniformLocation(prog, 'u_canvasSize')!;
  const uPointSize = gl.getUniformLocation(prog, 'u_pointSize')!;
  const uColor = gl.getUniformLocation(prog, 'u_color')!;

  // ── Buffers ──
  // Pre-allocate a Float32Array for position data (2 floats per particle).
  // We copy into this from Float64 sources each frame.
  const posBuf = gl.createBuffer()!;
  const posData = new Float32Array(maxParticles * 2);

  gl.bindBuffer(gl.ARRAY_BUFFER, posBuf);
  gl.bufferData(gl.ARRAY_BUFFER, posData.byteLength, gl.DYNAMIC_DRAW);

  // ── Static state ──
  const [bgR, bgG, bgB] = hexToRgb(opts.background);
  const [ptR, ptG, ptB] = hexToRgb(opts.pointColor);
  const ptA = opts.pointAlpha;
  const pointSize = opts.pointRadius * 2; // diameter in reference units

  gl.useProgram(prog);
  gl.uniform2f(uRefSize, refWidth, refHeight);
  gl.uniform4f(uColor, ptR, ptG, ptB, ptA);
  gl.uniform1f(uPointSize, pointSize);

  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

  gl.enableVertexAttribArray(aPos);
  gl.bindBuffer(gl.ARRAY_BUFFER, posBuf);
  gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

  function resize(): void {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.useProgram(prog);
    gl.uniform2f(uCanvasSize, canvas.width, canvas.height);
  }

  // Initial size
  resize();

  function draw(count: number): void {
    gl.clearColor(bgR, bgG, bgB, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);

    gl.bindBuffer(gl.ARRAY_BUFFER, posBuf);
    gl.bufferSubData(gl.ARRAY_BUFFER, 0, posData.subarray(0, count * 2));

    gl.drawArrays(gl.POINTS, 0, count);
  }

  function drawParticles(particles: { x: number; y: number }[], count: number): void {
    for (let i = 0, j = 0; i < count; i++, j += 2) {
      posData[j] = particles[i].x;
      posData[j + 1] = particles[i].y;
    }
    draw(count);
  }

  function drawFromArrays(px: Float64Array, py: Float64Array, count: number): void {
    for (let i = 0, j = 0; i < count; i++, j += 2) {
      posData[j] = px[i];
      posData[j + 1] = py[i];
    }
    draw(count);
  }

  return { resize, drawParticles, drawFromArrays };
}
