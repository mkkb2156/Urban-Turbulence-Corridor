/**
 * WindLayer — WebGL2 GPU particle wind field renderer
 *
 * Implements the Agafonkin ping-pong texture technique for rendering
 * 100K+ wind particles at 60 fps as a MapLibre GL custom layer.
 *
 * Wind data is encoded in a PNG texture:
 *   R channel = U component (eastward), 0-255 mapped to [windMin, windMax]
 *   G channel = V component (northward), 0-255 mapped to [windMin, windMax]
 *
 * Particle state is stored in a pair of float textures (ping-pong).
 * Each texel holds (lng_norm, lat_norm) in RG channels.
 * A fragment shader "computes" new positions; GL_POINTS renders them.
 * Trail effect is achieved by blending the current frame onto a screen
 * texture with a configurable fade opacity.
 */

import maplibregl from "maplibre-gl";

// ---------------------------------------------------------------------------
// Shader sources
// ---------------------------------------------------------------------------

/** Full-screen quad vertex shader (shared by update & screen passes) */
const QUAD_VS = /* glsl */ `#version 300 es
in vec2 a_position;
out vec2 v_tex_coord;
void main() {
  v_tex_coord = a_position * 0.5 + 0.5;
  gl_Position = vec4(a_position, 0.0, 1.0);
}
`;

/** Particle state update fragment shader */
const UPDATE_FS = /* glsl */ `#version 300 es
precision highp float;

uniform sampler2D u_particles;   // current state texture
uniform sampler2D u_wind;        // wind data PNG
uniform float u_rand_seed;
uniform float u_speed_factor;
uniform float u_drop_rate;
uniform float u_drop_rate_bump;
uniform float u_wind_min;
uniform float u_wind_max;

in vec2 v_tex_coord;
out vec4 fragColor;

// Pseudo-random helper
float rand(vec2 co) {
  return fract(sin(dot(co, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
  vec4 state = texture(u_particles, v_tex_coord);
  vec2 pos = state.rg; // normalised [0,1] position

  // Sample wind at current position
  vec2 windRaw = texture(u_wind, pos).rg;
  vec2 wind = windRaw * (u_wind_max - u_wind_min) + u_wind_min;

  // Move particle (scale wind so visuals look good)
  float distortion = cos(radians(mix(-90.0, 90.0, pos.y)));
  vec2 offset = vec2(wind.x / distortion, wind.y) / 50.0 * u_speed_factor;
  vec2 newPos = fract(1.0 + pos + offset);

  // --- Random reset (drop) -------------------------------------------------
  float seed = (v_tex_coord.x + v_tex_coord.y * 97.0) + u_rand_seed;
  float r1 = rand(vec2(seed, seed * 1.3));
  float drop = step(1.0 - u_drop_rate, r1);

  // Boost drop rate in calm areas
  float speed = length(wind);
  float r2 = rand(vec2(seed * 1.7, seed * 2.1));
  drop = max(drop, step(1.0 - u_drop_rate_bump, r2) * step(speed, 0.5));

  // Random new position
  vec2 randomPos = vec2(
    rand(vec2(seed * 2.3, seed * 3.7)),
    rand(vec2(seed * 4.1, seed * 5.3))
  );

  newPos = mix(newPos, randomPos, drop);

  fragColor = vec4(newPos, 0.0, 1.0);
}
`;

/** Particle draw vertex shader — one vertex per particle */
const DRAW_VS = /* glsl */ `#version 300 es
precision highp float;

uniform sampler2D u_particles;   // particle state texture
uniform sampler2D u_wind;        // wind data
uniform float u_wind_min;
uniform float u_wind_max;
uniform vec4 u_bounds;           // (lngMin, latMin, lngMax, latMax)
uniform mat4 u_matrix;           // MapLibre mercator matrix
uniform float u_particle_tex_size;

out float v_speed;

void main() {
  // Compute the texel coordinate for this vertex
  float col = mod(float(gl_VertexID), u_particle_tex_size);
  float row = floor(float(gl_VertexID) / u_particle_tex_size);
  vec2 uv = (vec2(col, row) + 0.5) / u_particle_tex_size;

  vec2 pos = texture(u_particles, uv).rg; // [0,1]

  // Map to lng/lat
  float lng = u_bounds.x + pos.x * (u_bounds.z - u_bounds.x);
  float lat = u_bounds.y + pos.y * (u_bounds.w - u_bounds.y);

  // Convert lng/lat to Mercator 0-1 (Web Mercator tile coordinate)
  float x = (lng + 180.0) / 360.0;
  float latRad = radians(lat);
  float y = (1.0 - log(tan(latRad) + 1.0 / cos(latRad)) / 3.141592653589793) / 2.0;

  gl_Position = u_matrix * vec4(x, y, 0.0, 1.0);
  gl_PointSize = 1.5;

  // Wind speed for colouring
  vec2 windRaw = texture(u_wind, pos).rg;
  vec2 wind = windRaw * (u_wind_max - u_wind_min) + u_wind_min;
  v_speed = length(wind);
}
`;

/** Particle draw fragment shader — 6-stop colour ramp */
const DRAW_FS = /* glsl */ `#version 300 es
precision highp float;

in float v_speed;
out vec4 fragColor;

uniform sampler2D u_color_ramp;
uniform float u_speed_range; // max display speed (m/s)

void main() {
  float t = clamp(v_speed / u_speed_range, 0.0, 1.0);
  // Built-in 6-stop ramp: calm blue → teal → green → yellow → orange → red
  vec3 c;
  if (t < 0.2) {
    c = mix(vec3(0.15, 0.30, 0.60), vec3(0.20, 0.53, 0.74), t / 0.2);
  } else if (t < 0.4) {
    c = mix(vec3(0.20, 0.53, 0.74), vec3(0.30, 0.70, 0.50), (t - 0.2) / 0.2);
  } else if (t < 0.6) {
    c = mix(vec3(0.30, 0.70, 0.50), vec3(0.90, 0.85, 0.30), (t - 0.4) / 0.2);
  } else if (t < 0.8) {
    c = mix(vec3(0.90, 0.85, 0.30), vec3(0.90, 0.50, 0.20), (t - 0.6) / 0.2);
  } else {
    c = mix(vec3(0.90, 0.50, 0.20), vec3(0.84, 0.24, 0.31), (t - 0.8) / 0.2);
  }
  fragColor = vec4(c, 0.85);
}
`;

/** Screen-blend vertex shader (full-screen quad) */
const SCREEN_VS = QUAD_VS;

/** Screen-blend fragment shader — fade previous frame */
const SCREEN_FS = /* glsl */ `#version 300 es
precision highp float;

uniform sampler2D u_screen;
uniform float u_opacity;

in vec2 v_tex_coord;
out vec4 fragColor;

void main() {
  vec4 color = texture(u_screen, v_tex_coord);
  fragColor = vec4(color.rgb, color.a * u_opacity);
}
`;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WindLayerOptions {
  id?: string;
  numParticles?: number;
  particleSpeed?: number;
  fadeOpacity?: number;
  dropRate?: number;
  dropRateBump?: number;
  bounds?: [number, number, number, number];
  windMin?: number;
  windMax?: number;
  speedRange?: number;
  renderingMode?: "2d" | "3d";
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function compileShader(
  gl: WebGL2RenderingContext,
  type: number,
  source: string,
): WebGLShader {
  const shader = gl.createShader(type);
  if (!shader) throw new Error("Failed to create shader");
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const info = gl.getShaderInfoLog(shader);
    gl.deleteShader(shader);
    throw new Error(`Shader compile error: ${info}`);
  }
  return shader;
}

function createProgram(
  gl: WebGL2RenderingContext,
  vsSource: string,
  fsSource: string,
): WebGLProgram {
  const vs = compileShader(gl, gl.VERTEX_SHADER, vsSource);
  const fs = compileShader(gl, gl.FRAGMENT_SHADER, fsSource);
  const program = gl.createProgram();
  if (!program) throw new Error("Failed to create program");
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const info = gl.getProgramInfoLog(program);
    gl.deleteProgram(program);
    throw new Error(`Program link error: ${info}`);
  }
  // Shaders can be detached after linking
  gl.detachShader(program, vs);
  gl.detachShader(program, fs);
  gl.deleteShader(vs);
  gl.deleteShader(fs);
  return program;
}

function createFloatTexture(
  gl: WebGL2RenderingContext,
  size: number,
  data: Float32Array | null,
): WebGLTexture {
  const tex = gl.createTexture();
  if (!tex) throw new Error("Failed to create texture");
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  gl.texImage2D(
    gl.TEXTURE_2D,
    0,
    gl.RGBA32F,
    size,
    size,
    0,
    gl.RGBA,
    gl.FLOAT,
    data,
  );
  gl.bindTexture(gl.TEXTURE_2D, null);
  return tex;
}

function createScreenTexture(
  gl: WebGL2RenderingContext,
  width: number,
  height: number,
): WebGLTexture {
  const tex = gl.createTexture();
  if (!tex) throw new Error("Failed to create texture");
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texImage2D(
    gl.TEXTURE_2D,
    0,
    gl.RGBA8,
    width,
    height,
    0,
    gl.RGBA,
    gl.UNSIGNED_BYTE,
    null,
  );
  gl.bindTexture(gl.TEXTURE_2D, null);
  return tex;
}

// ---------------------------------------------------------------------------
// WindLayer — MapLibre CustomLayerInterface
// ---------------------------------------------------------------------------

export class WindLayer implements maplibregl.CustomLayerInterface {
  readonly id: string;
  readonly type = "custom" as const;
  readonly renderingMode: "2d" | "3d";

  // Configuration
  private numParticles: number;
  private particleTexSize: number;
  private particleSpeed: number;
  private fadeOpacity: number;
  private dropRate: number;
  private dropRateBump: number;
  private bounds: [number, number, number, number];
  private windMin: number;
  private windMax: number;
  private speedRange: number;

  // Wind texture source
  private windImage: HTMLImageElement | ImageBitmap | null = null;
  private windTextureDirty = false;

  // WebGL resources (initialised in onAdd)
  private gl: WebGL2RenderingContext | null = null;
  private map: maplibregl.Map | null = null;

  // Programs
  private updateProgram: WebGLProgram | null = null;
  private drawProgram: WebGLProgram | null = null;
  private screenProgram: WebGLProgram | null = null;

  // Textures
  private particleStateA: WebGLTexture | null = null;
  private particleStateB: WebGLTexture | null = null;
  private windTexture: WebGLTexture | null = null;
  private screenTexture: WebGLTexture | null = null;
  private backgroundTexture: WebGLTexture | null = null;

  // Framebuffers
  private framebuffer: WebGLFramebuffer | null = null;

  // Geometry
  private quadVAO: WebGLVertexArrayObject | null = null;
  private quadBuffer: WebGLBuffer | null = null;
  private drawVAO: WebGLVertexArrayObject | null = null;

  // State
  private pingPong = 0; // 0 = read A / write B, 1 = read B / write A
  private screenWidth = 0;
  private screenHeight = 0;

  constructor(options: WindLayerOptions = {}) {
    this.id = options.id ?? "wind-particles";
    this.renderingMode = options.renderingMode ?? "2d";
    this.numParticles = options.numParticles ?? 65536;
    this.particleTexSize = Math.ceil(Math.sqrt(this.numParticles));
    this.numParticles = this.particleTexSize * this.particleTexSize;
    this.particleSpeed = options.particleSpeed ?? 0.35;
    this.fadeOpacity = options.fadeOpacity ?? 0.995;
    this.dropRate = options.dropRate ?? 0.003;
    this.dropRateBump = options.dropRateBump ?? 0.01;
    this.bounds = options.bounds ?? [121.45, 24.96, 121.67, 25.21];
    this.windMin = options.windMin ?? -25;
    this.windMax = options.windMax ?? 25;
    this.speedRange = options.speedRange ?? 15;
  }

  // ── Public API ────────────────────────────────────────────────

  /** Set or replace the wind data texture */
  setWindTexture(image: HTMLImageElement | ImageBitmap): void {
    this.windImage = image;
    this.windTextureDirty = true;
    this.map?.triggerRepaint();
  }

  /** Update the geographic bounds covered by the wind texture */
  updateBounds(bounds: [number, number, number, number]): void {
    this.bounds = bounds;
    this.map?.triggerRepaint();
  }

  /** Adjust particle speed multiplier */
  setSpeed(speed: number): void {
    this.particleSpeed = speed;
    this.map?.triggerRepaint();
  }

  /** Change active particle count (re-creates state textures) */
  setParticleCount(n: number): void {
    this.numParticles = n;
    this.particleTexSize = Math.ceil(Math.sqrt(n));
    this.numParticles = this.particleTexSize * this.particleTexSize;
    if (this.gl) {
      this.initParticleTextures(this.gl);
    }
    this.map?.triggerRepaint();
  }

  // ── MapLibre CustomLayerInterface ─────────────────────────────

  onAdd(map: maplibregl.Map, glAny: WebGLRenderingContext | WebGL2RenderingContext): void {
    const gl = glAny as WebGL2RenderingContext;
    this.map = map;
    this.gl = gl;

    // Check for float texture support
    const extFloat = gl.getExtension("EXT_color_buffer_float");
    if (!extFloat) {
      console.warn(
        "[WindLayer] EXT_color_buffer_float not supported — falling back to RGBA16F",
      );
    }

    // ── Compile programs ──────────────────────────────────────
    this.updateProgram = createProgram(gl, QUAD_VS, UPDATE_FS);
    this.drawProgram = createProgram(gl, DRAW_VS, DRAW_FS);
    this.screenProgram = createProgram(gl, SCREEN_VS, SCREEN_FS);

    // ── Full-screen quad geometry ─────────────────────────────
    this.quadBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
      gl.STATIC_DRAW,
    );

    // Quad VAO (used by update + screen passes)
    this.quadVAO = gl.createVertexArray();
    gl.bindVertexArray(this.quadVAO);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuffer);
    const aPos = gl.getAttribLocation(this.updateProgram, "a_position");
    gl.enableVertexAttribArray(aPos);
    gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(null);

    // Draw VAO (empty — we use gl_VertexID)
    this.drawVAO = gl.createVertexArray();

    // ── Framebuffer for off-screen rendering ──────────────────
    this.framebuffer = gl.createFramebuffer();

    // ── Particle state textures (ping-pong) ───────────────────
    this.initParticleTextures(gl);

    // ── Wind data texture (placeholder — replaced via setWindTexture) ─
    this.windTexture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, this.windTexture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    // 1x1 black pixel placeholder
    gl.texImage2D(
      gl.TEXTURE_2D,
      0,
      gl.RGBA8,
      1,
      1,
      0,
      gl.RGBA,
      gl.UNSIGNED_BYTE,
      new Uint8Array([0, 0, 0, 255]),
    );
    gl.bindTexture(gl.TEXTURE_2D, null);

    // ── Screen textures for trail effect ──────────────────────
    this.screenWidth = gl.drawingBufferWidth;
    this.screenHeight = gl.drawingBufferHeight;
    this.screenTexture = createScreenTexture(
      gl,
      this.screenWidth,
      this.screenHeight,
    );
    this.backgroundTexture = createScreenTexture(
      gl,
      this.screenWidth,
      this.screenHeight,
    );

    // Upload initial wind image if already set
    if (this.windImage) {
      this.windTextureDirty = true;
    }
  }

  render(glAny: WebGLRenderingContext | WebGL2RenderingContext, matrix: ArrayLike<number>): void {
    const gl = glAny as WebGL2RenderingContext;
    if (!this.updateProgram || !this.drawProgram || !this.screenProgram) return;
    if (!this.windImage) return; // nothing to render without wind data

    // Upload wind image if changed
    if (this.windTextureDirty && this.windTexture) {
      gl.bindTexture(gl.TEXTURE_2D, this.windTexture);
      gl.texImage2D(
        gl.TEXTURE_2D,
        0,
        gl.RGBA8,
        gl.RGBA,
        gl.UNSIGNED_BYTE,
        this.windImage,
      );
      gl.bindTexture(gl.TEXTURE_2D, null);
      this.windTextureDirty = false;
    }

    // Handle canvas resize
    if (
      gl.drawingBufferWidth !== this.screenWidth ||
      gl.drawingBufferHeight !== this.screenHeight
    ) {
      this.screenWidth = gl.drawingBufferWidth;
      this.screenHeight = gl.drawingBufferHeight;
      if (this.screenTexture) gl.deleteTexture(this.screenTexture);
      if (this.backgroundTexture) gl.deleteTexture(this.backgroundTexture);
      this.screenTexture = createScreenTexture(
        gl,
        this.screenWidth,
        this.screenHeight,
      );
      this.backgroundTexture = createScreenTexture(
        gl,
        this.screenWidth,
        this.screenHeight,
      );
    }

    // Save MapLibre GL state we need to restore
    const prevVAO = gl.getParameter(gl.VERTEX_ARRAY_BINDING) as WebGLVertexArrayObject | null;
    const prevProgram = gl.getParameter(gl.CURRENT_PROGRAM) as WebGLProgram | null;
    const prevActiveTexture = gl.getParameter(gl.ACTIVE_TEXTURE) as number;
    const prevBlend = gl.isEnabled(gl.BLEND);
    const prevDepthTest = gl.isEnabled(gl.DEPTH_TEST);
    const prevFramebuffer = gl.getParameter(gl.FRAMEBUFFER_BINDING) as WebGLFramebuffer | null;

    const readTex =
      this.pingPong === 0 ? this.particleStateA : this.particleStateB;
    const writeTex =
      this.pingPong === 0 ? this.particleStateB : this.particleStateA;

    // ═══════════════════════════════════════════════════════════
    // Pass 1: Update particle positions (render to writeTex)
    // ═══════════════════════════════════════════════════════════
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.framebuffer);
    gl.framebufferTexture2D(
      gl.FRAMEBUFFER,
      gl.COLOR_ATTACHMENT0,
      gl.TEXTURE_2D,
      writeTex,
      0,
    );
    gl.viewport(0, 0, this.particleTexSize, this.particleTexSize);

    gl.useProgram(this.updateProgram);
    gl.bindVertexArray(this.quadVAO);

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, readTex);
    gl.uniform1i(
      gl.getUniformLocation(this.updateProgram, "u_particles"),
      0,
    );

    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, this.windTexture);
    gl.uniform1i(gl.getUniformLocation(this.updateProgram, "u_wind"), 1);

    gl.uniform1f(
      gl.getUniformLocation(this.updateProgram, "u_rand_seed"),
      Math.random(),
    );
    gl.uniform1f(
      gl.getUniformLocation(this.updateProgram, "u_speed_factor"),
      this.particleSpeed,
    );
    gl.uniform1f(
      gl.getUniformLocation(this.updateProgram, "u_drop_rate"),
      this.dropRate,
    );
    gl.uniform1f(
      gl.getUniformLocation(this.updateProgram, "u_drop_rate_bump"),
      this.dropRateBump,
    );
    gl.uniform1f(
      gl.getUniformLocation(this.updateProgram, "u_wind_min"),
      this.windMin,
    );
    gl.uniform1f(
      gl.getUniformLocation(this.updateProgram, "u_wind_max"),
      this.windMax,
    );

    gl.disable(gl.BLEND);
    gl.disable(gl.DEPTH_TEST);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

    // ═══════════════════════════════════════════════════════════
    // Pass 2: Draw faded previous frame to screenTexture
    // ═══════════════════════════════════════════════════════════
    gl.framebufferTexture2D(
      gl.FRAMEBUFFER,
      gl.COLOR_ATTACHMENT0,
      gl.TEXTURE_2D,
      this.screenTexture,
      0,
    );
    gl.viewport(0, 0, this.screenWidth, this.screenHeight);

    // Blend previous background with fade
    gl.useProgram(this.screenProgram);
    gl.bindVertexArray(this.quadVAO);

    // Re-bind a_position attribute for screen program
    const screenAPos = gl.getAttribLocation(this.screenProgram, "a_position");
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuffer);
    gl.enableVertexAttribArray(screenAPos);
    gl.vertexAttribPointer(screenAPos, 2, gl.FLOAT, false, 0, 0);

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.backgroundTexture);
    gl.uniform1i(
      gl.getUniformLocation(this.screenProgram, "u_screen"),
      0,
    );
    gl.uniform1f(
      gl.getUniformLocation(this.screenProgram, "u_opacity"),
      this.fadeOpacity,
    );

    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

    // ═══════════════════════════════════════════════════════════
    // Pass 3: Draw particles onto screenTexture
    // ═══════════════════════════════════════════════════════════
    // Still rendering to screenTexture FBO
    gl.useProgram(this.drawProgram);
    gl.bindVertexArray(this.drawVAO);

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, writeTex);
    gl.uniform1i(
      gl.getUniformLocation(this.drawProgram, "u_particles"),
      0,
    );

    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, this.windTexture);
    gl.uniform1i(gl.getUniformLocation(this.drawProgram, "u_wind"), 1);

    gl.uniform1f(
      gl.getUniformLocation(this.drawProgram, "u_wind_min"),
      this.windMin,
    );
    gl.uniform1f(
      gl.getUniformLocation(this.drawProgram, "u_wind_max"),
      this.windMax,
    );
    gl.uniform1f(
      gl.getUniformLocation(this.drawProgram, "u_speed_range"),
      this.speedRange,
    );
    gl.uniform1f(
      gl.getUniformLocation(this.drawProgram, "u_particle_tex_size"),
      this.particleTexSize,
    );
    gl.uniform4f(
      gl.getUniformLocation(this.drawProgram, "u_bounds"),
      this.bounds[0],
      this.bounds[1],
      this.bounds[2],
      this.bounds[3],
    );

    // Projection matrix from MapLibre (mercator → clip space)
    gl.uniformMatrix4fv(
      gl.getUniformLocation(this.drawProgram, "u_matrix"),
      false,
      Array.from(matrix) as number[],
    );

    gl.disable(gl.BLEND);
    gl.drawArrays(gl.POINTS, 0, this.numParticles);

    // ═══════════════════════════════════════════════════════════
    // Pass 4: Composite screenTexture to the main framebuffer
    // ═══════════════════════════════════════════════════════════
    gl.bindFramebuffer(gl.FRAMEBUFFER, prevFramebuffer);
    gl.viewport(0, 0, this.screenWidth, this.screenHeight);

    gl.useProgram(this.screenProgram);
    gl.bindVertexArray(this.quadVAO);

    const compositeAPos = gl.getAttribLocation(this.screenProgram, "a_position");
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuffer);
    gl.enableVertexAttribArray(compositeAPos);
    gl.vertexAttribPointer(compositeAPos, 2, gl.FLOAT, false, 0, 0);

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.screenTexture);
    gl.uniform1i(
      gl.getUniformLocation(this.screenProgram, "u_screen"),
      0,
    );
    gl.uniform1f(
      gl.getUniformLocation(this.screenProgram, "u_opacity"),
      1.0,
    );

    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

    // ═══════════════════════════════════════════════════════════
    // Swap background = screenTexture for next frame's trail
    // ═══════════════════════════════════════════════════════════
    const tmp = this.backgroundTexture;
    this.backgroundTexture = this.screenTexture;
    this.screenTexture = tmp;

    // Flip ping-pong
    this.pingPong = 1 - this.pingPong;

    // ── Restore MapLibre GL state ─────────────────────────────
    gl.bindVertexArray(prevVAO);
    gl.useProgram(prevProgram);
    gl.activeTexture(prevActiveTexture);
    if (prevBlend) gl.enable(gl.BLEND); else gl.disable(gl.BLEND);
    if (prevDepthTest) gl.enable(gl.DEPTH_TEST); else gl.disable(gl.DEPTH_TEST);
    gl.bindFramebuffer(gl.FRAMEBUFFER, prevFramebuffer);

    // Request continuous repaint for animation
    this.map?.triggerRepaint();
  }

  onRemove(_map: maplibregl.Map, glAny: WebGLRenderingContext | WebGL2RenderingContext): void {
    const gl = glAny as WebGL2RenderingContext;
    // Clean up all WebGL resources
    if (this.updateProgram) gl.deleteProgram(this.updateProgram);
    if (this.drawProgram) gl.deleteProgram(this.drawProgram);
    if (this.screenProgram) gl.deleteProgram(this.screenProgram);
    if (this.particleStateA) gl.deleteTexture(this.particleStateA);
    if (this.particleStateB) gl.deleteTexture(this.particleStateB);
    if (this.windTexture) gl.deleteTexture(this.windTexture);
    if (this.screenTexture) gl.deleteTexture(this.screenTexture);
    if (this.backgroundTexture) gl.deleteTexture(this.backgroundTexture);
    if (this.framebuffer) gl.deleteFramebuffer(this.framebuffer);
    if (this.quadBuffer) gl.deleteBuffer(this.quadBuffer);
    if (this.quadVAO) gl.deleteVertexArray(this.quadVAO);
    if (this.drawVAO) gl.deleteVertexArray(this.drawVAO);

    this.updateProgram = null;
    this.drawProgram = null;
    this.screenProgram = null;
    this.particleStateA = null;
    this.particleStateB = null;
    this.windTexture = null;
    this.screenTexture = null;
    this.backgroundTexture = null;
    this.framebuffer = null;
    this.quadBuffer = null;
    this.quadVAO = null;
    this.drawVAO = null;
    this.gl = null;
    this.map = null;
  }

  // ── Internal helpers ──────────────────────────────────────────

  private initParticleTextures(gl: WebGL2RenderingContext): void {
    // Delete existing textures if re-initialising
    if (this.particleStateA) gl.deleteTexture(this.particleStateA);
    if (this.particleStateB) gl.deleteTexture(this.particleStateB);

    const size = this.particleTexSize;
    const totalPixels = size * size;
    const data = new Float32Array(totalPixels * 4);
    for (let i = 0; i < totalPixels; i++) {
      data[i * 4 + 0] = Math.random(); // lng normalised
      data[i * 4 + 1] = Math.random(); // lat normalised
      data[i * 4 + 2] = 0;
      data[i * 4 + 3] = 1;
    }

    this.particleStateA = createFloatTexture(gl, size, data);
    this.particleStateB = createFloatTexture(gl, size, null);
    this.pingPong = 0;
  }
}
