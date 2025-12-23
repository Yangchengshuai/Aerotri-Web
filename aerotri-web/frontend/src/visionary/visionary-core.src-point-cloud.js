import { vec3 as h, mat4 as c } from "gl-matrix";
import { U as d } from "./visionary-core.src-uniform.js";
import { A as S } from "./visionary-core.src-utils.js";
import "three/webgpu";
import "three/examples/jsm/loaders/RGBELoader.js";
import { T as y, a as g } from "./visionary-core.src-timeline.js";
const P = /* @__PURE__ */ new WeakMap(), p = /* @__PURE__ */ new WeakMap();
function m(u) {
  const e = P.get(u);
  if (e) return e;
  const t = u.createBindGroupLayout({
    label: "point cloud bind group layout",
    entries: [
      // 0: gaussians storage
      {
        binding: 0,
        visibility: GPUShaderStage.COMPUTE,
        buffer: { type: "read-only-storage" }
      },
      // 1: SH coeffs storage
      {
        binding: 1,
        visibility: GPUShaderStage.COMPUTE,
        buffer: { type: "read-only-storage" }
      },
      // 2: 2D splat buffer (output/indirect)
      {
        binding: 2,
        visibility: GPUShaderStage.COMPUTE,
        buffer: { type: "storage" }
      },
      // 3: uniforms
      {
        binding: 3,
        visibility: GPUShaderStage.COMPUTE,
        buffer: { type: "uniform" }
      }
    ]
  });
  return P.set(u, t), t;
}
function b(u) {
  const e = p.get(u);
  if (e) return e;
  const t = u.createBindGroupLayout({
    label: "Point Cloud Render Bind Group Layout",
    entries: [
      // Keep these entries EXACTLY matching your render shader's @group(0) expectations
      { binding: 2, visibility: GPUShaderStage.VERTEX, buffer: { type: "read-only-storage" } }
      // If you later add more bindings, append them here:
      // { binding: 1, visibility: GPUShaderStage.FRAGMENT, buffer: { type: "read-only-storage" } },
      // { binding: 2, visibility: GPUShaderStage.VERTEX | GPUShaderStage.FRAGMENT, buffer: { type: "storage" } },
      // { binding: 3, visibility: GPUShaderStage.VERTEX | GPUShaderStage.FRAGMENT, buffer: { type: "uniform" } },
    ]
  });
  return p.set(u, t), t;
}
const B = {
  SPLAT_STRIDE: 32
  // conservative placeholder; match WGSL struct size
};
class G {
  splat2DBuffer;
  // storage for projected splats / sort keys
  gaussianBufferGPU;
  // 3DGS attributes
  shBufferGPU;
  // SH coefficients
  _bindGroup;
  // general compute/prepare BG (if used)
  _renderBindGroup;
  // render pass BG (textures/samplers + storage)
  numPoints;
  shDeg;
  bbox;
  compressed;
  // Color mode: 'sh' for spherical harmonics, 'rgb' for direct RGB color
  colorMode = "sh";
  center;
  up;
  // Transform matrix for GPU rendering (4x4 column-major)
  // @deprecated - Transform should be managed externally (e.g., by GaussianModel/Object3D)
  // This property is kept for backward compatibility but should not be relied upon.
  // New code should pass transform explicitly to updateModelParamsBuffer()
  transform = new Float32Array([
    1,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    1
  ]);
  // Optional raster params (mirroring fields in Rust)
  mipSplatting;
  kernelSize;
  backgroundColor;
  // 高斯点缩放参数（独立于Three.js的scale属性）
  _gaussianScaling = 1;
  _maxShDeg = 3;
  _kernelSize = 0.1;
  _opacityScale = 1;
  _cutoffScale = 1;
  _rendermode = 0;
  // Uniforms used by both compute & render stages
  uniforms;
  // Per-model parameters uniform buffer (transform matrix + metadata)
  modelParamsUniforms;
  /**
   * Create bind group layout for point cloud compute shaders
   * @deprecated Use getBindGroupLayout from layouts.ts instead
   */
  static bindGroupLayout(e) {
    return m(e);
  }
  /**
   * Create bind group layout for point cloud render passes
   * @deprecated Use getRenderBindGroupLayout from layouts.ts instead
   */
  static renderBindGroupLayout(e) {
    return b(e);
  }
  constructor(e, t, s) {
    this.numPoints = t.numPoints(), this.shDeg = t.shDegree(), this._maxShDeg = this.shDeg, this.bbox = new S(t.bbox().min, t.bbox().max), this.center = t.center ? h.fromValues(t.center[0], t.center[1], t.center[2]) : h.fromValues(0, 0, 0), this.up = t.up ? h.fromValues(t.up[0], t.up[1], t.up[2]) : null, this.compressed = !1, s ? (this.gaussianBufferGPU = s.gaussianBuffer, this.shBufferGPU = s.shBuffer, console.log("🌟 PointCloud created with external GPU buffers (no CPU upload)")) : (this.gaussianBufferGPU = e.createBuffer({
      label: "gaussians/storage",
      size: t.gaussianBuffer().byteLength,
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST
    }), e.queue.writeBuffer(this.gaussianBufferGPU, 0, t.gaussianBuffer()), this.shBufferGPU = e.createBuffer({
      label: "sh/storage",
      size: t.shCoefsBuffer().byteLength,
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST
    }), e.queue.writeBuffer(this.shBufferGPU, 0, t.shCoefsBuffer())), this.splat2DBuffer = e.createBuffer({
      label: "splat2d/storage",
      size: Math.max(1, this.numPoints) * B.SPLAT_STRIDE,
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC | GPUBufferUsage.COPY_DST | GPUBufferUsage.INDIRECT
    });
    const r = new Uint32Array([this.numPoints, this.shDeg, 0, 0]);
    this.uniforms = new d(e, r, "pointcloud uniforms");
    const n = new ArrayBuffer(128), i = new Float32Array(n), o = new Uint32Array(n);
    for (let f = 0; f < 16; f++)
      i[f] = f % 5 === 0 ? 1 : 0;
    o[16] = 0, o[17] = this.numPoints, i[18] = this._gaussianScaling, o[19] = this._maxShDeg, i[20] = this._kernelSize, i[21] = this._opacityScale, i[22] = this._cutoffScale, o[23] = this._rendermode, o[24] = 1, o[25] = 1, i[26] = 1, i[27] = 0, i[28] = 1, i[29] = 0, this.modelParamsUniforms = new d(e, n, "model params");
    const a = m(e);
    this._bindGroup = e.createBindGroup({
      label: "pointcloud/bg",
      layout: a,
      entries: [
        { binding: 0, resource: { buffer: this.gaussianBufferGPU } },
        { binding: 1, resource: { buffer: this.shBufferGPU } },
        { binding: 2, resource: { buffer: this.splat2DBuffer } },
        { binding: 3, resource: { buffer: this.uniforms.buffer } }
      ]
    });
    const l = b(e);
    this._renderBindGroup = e.createBindGroup({
      label: "pointcloud/render/bg",
      layout: l,
      entries: [
        { binding: 2, resource: { buffer: this.splat2DBuffer } }
      ]
    });
  }
  bindGroup() {
    return this._bindGroup;
  }
  renderBindGroup() {
    return this._renderBindGroup;
  }
  /**
   * Replace gaussian/sh storage buffers and rebuild bind group.
   * Intended for runtime precision conversion (e.g., FP32→FP16).
   */
  replaceStorageBuffers(e, t) {
    this.gaussianBufferGPU = t.gaussianBuffer, this.shBufferGPU = t.shBuffer;
    const s = m(e);
    this._bindGroup = e.createBindGroup({
      label: "pointcloud/bg",
      layout: s,
      entries: [
        { binding: 0, resource: { buffer: this.gaussianBufferGPU } },
        { binding: 1, resource: { buffer: this.shBufferGPU } },
        { binding: 2, resource: { buffer: this.splat2DBuffer } },
        { binding: 3, resource: { buffer: this.uniforms.buffer } }
      ]
    });
  }
  /**
   * Get SplatBuffer interface for this point cloud
   */
  getSplatBuffer() {
    return {
      gaussianBuffer: this.gaussianBufferGPU,
      shBuffer: this.shBufferGPU,
      numPoints: this.numPoints,
      shDegree: this.shDeg,
      bbox: this.bbox
    };
  }
  /**
   * Update the model parameters uniform buffer with provided transform matrix
   * @param transformMatrix - 4x4 transform matrix
   * @param baseOffset - base offset for the model in global buffers
   */
  updateModelParamsBuffer(e, t = 0) {
    const s = new ArrayBuffer(128), r = new Float32Array(s), n = new Uint32Array(s);
    for (let i = 0; i < 16; i++)
      r[i] = e[i];
    n[16] = t, n[17] = this.numPoints, r[18] = this._gaussianScaling, n[19] = this._maxShDeg, r[20] = this._kernelSize, r[21] = this._opacityScale, r[22] = this._cutoffScale, n[23] = this._rendermode, n[24] = 1, n[25] = 1, r[26] = 1, r[27] = 0, r[28] = 1, r[29] = 0, this.modelParamsUniforms.setData(new DataView(s));
  }
  /**
   * Set the transform matrix for this point cloud
   * @param matrix - 4x4 transform matrix (Float32Array or number[])
   */
  setTransform(e) {
    const t = e instanceof Float32Array ? e : new Float32Array(e);
    this.transform.set(t), this.updateModelParamsBuffer(this.transform, 0);
  }
  /**
   * Update model parameters buffer with a specific baseOffset (called by preprocessor)
   * @param transformMatrix - 4x4 transform matrix
   * @param baseOffset - base offset for the model in global buffers
   */
  updateModelParamsWithOffset(e, t) {
    this.updateModelParamsBuffer(e, t);
  }
  /**
   * 设置高斯缩放参数
   * @param scale - 缩放因子
   */
  setGaussianScaling(e) {
    this._gaussianScaling = e, console.log(`[PointCloud] Gaussian scaling set to: ${e}`);
  }
  /**
   * 获取当前高斯缩放参数
   * @returns 当前缩放值
   */
  getGaussianScaling() {
    return this._gaussianScaling;
  }
  /**
   * 设置球谐等级
   * @param deg - 球谐等级 (0-3)
   */
  setMaxShDeg(e) {
    this._maxShDeg = Math.max(0, Math.min(3, e)), console.log(`[PointCloud] Max SH degree set to: ${this._maxShDeg}`);
  }
  /**
   * 获取当前球谐等级
   * @returns 当前球谐等级
   */
  getMaxShDeg() {
    return this._maxShDeg;
  }
  /**
   * 设置二维核大小
   * @param size - 核大小
   */
  setKernelSize(e) {
    this._kernelSize = Math.max(0, e), console.log(`[PointCloud] Kernel size set to: ${this._kernelSize}`);
  }
  /**
   * 获取当前二维核大小
   * @returns 当前核大小
   */
  getKernelSize() {
    return this._kernelSize;
  }
  /**
   * 设置透明度倍数
   * @param scale - 透明度倍数
   */
  setOpacityScale(e) {
    this._opacityScale = Math.max(0, e), console.log(`[PointCloud] Opacity scale set to: ${this._opacityScale}`);
  }
  /**
   * 获取当前透明度倍数
   * @returns 当前透明度倍数
   */
  getOpacityScale() {
    return this._opacityScale;
  }
  /**
   * 设置最大像素比例倍数
   * @param scale - 像素比例倍数
   */
  setCutoffScale(e) {
    this._cutoffScale = Math.max(0.1, e), console.log(`[PointCloud] Cutoff scale set to: ${this._cutoffScale}`);
  }
  /**
   * 获取当前最大像素比例倍数
   * @returns 当前像素比例倍数
   */
  getCutoffScale() {
    return this._cutoffScale;
  }
  /**
   * 设置渲染模式
   * @param mode - 渲染模式 (0=颜色, 1=法线, 2=深度)
   */
  setRenderMode(e) {
    this._rendermode = Math.max(0, Math.min(2, e)), console.log(`[PointCloud] Render mode set to: ${this._rendermode}`);
  }
  /**
   * 获取当前渲染模式
   * @returns 当前渲染模式
   */
  getRenderMode() {
    return this._rendermode;
  }
}
class M extends G {
  _countBuf;
  onnxGenerator;
  // Reference to ONNXGenerator for dynamic updates
  timeline;
  // Timeline controller for time management
  gaussianPrecision;
  colorPrecision;
  is_loop = !0;
  // Color mode information for renderer
  colorMode;
  colorChannels;
  constructor(e, t, s, r, n, i = 48, o) {
    let a;
    switch (i) {
      case 3:
        a = 0;
        break;
      // RGB direct color or degree 0 SH  
      case 12:
        a = 1;
        break;
      // Degree 1 SH
      case 27:
        a = 2;
        break;
      // Degree 2 SH  
      case 48:
        a = 3;
        break;
      // Degree 3 SH (default)
      default:
        console.warn(`⚠️ Unexpected color channels: ${i}, Maybe rgb channels`), a = 3;
    }
    console.log(`🎨 DynamicPointCloud: ${i} channels → SH degree ${a}`);
    const l = {
      numPoints: () => r,
      shDegree: () => a,
      bbox: () => ({ min: [-1, -1, -1], max: [1, 1, 1] }),
      center: [0, 0, 0],
      up: null,
      gaussianBuffer: () => new ArrayBuffer(0),
      // Will be overridden
      shCoefsBuffer: () => new ArrayBuffer(0)
      // Will be overridden
    };
    super(e, l, {
      gaussianBuffer: t,
      shBuffer: s
    }), this.colorChannels = i, this.colorMode = i === 4 ? "rgb" : "sh", console.log(`🎨 Color mode set: ${this.colorMode} (${this.colorChannels} channels)`), this._countBuf = n, this.gaussianPrecision = o?.gaussian, this.colorPrecision = o?.color, this.timeline = new y({
      timeScale: 1,
      timeOffset: 0,
      timeUpdateMode: "fixed_delta",
      animationSpeed: 1
    }), console.log("🌟 DynamicPointCloud created with direct GPU buffers (no CPU upload)");
  }
  countBuffer() {
    return this._countBuf;
  }
  /**
   * Set ONNX generator for dynamic updates
   */
  setOnnxGenerator(e) {
    this.onnxGenerator = e, console.log("🔗 ONNX generator linked for dynamic updates");
  }
  getGaussianPrecision() {
    return this.gaussianPrecision;
  }
  getColorPrecision() {
    return this.colorPrecision;
  }
  /**
   * Inject precision metadata into ModelParams uniform buffer so shader can adapt
   */
  setPrecisionForShader() {
    const e = this.modelParamsUniforms.data, t = new DataView(e), s = (r) => {
      switch (r) {
        case "float32":
          return 0;
        case "float16":
          return 1;
        case "int8":
          return 2;
        case "uint8":
          return 3;
        default:
          return 1;
      }
    };
    this.gaussianPrecision && (t.setUint32(96, s(this.gaussianPrecision.dataType), !0), typeof this.gaussianPrecision.scale == "number" && t.setFloat32(104, this.gaussianPrecision.scale, !0), typeof this.gaussianPrecision.zeroPoint == "number" && t.setFloat32(108, this.gaussianPrecision.zeroPoint, !0)), this.colorPrecision && (t.setUint32(100, s(this.colorPrecision.dataType), !0), typeof this.colorPrecision.scale == "number" && t.setFloat32(112, this.colorPrecision.scale, !0), typeof this.colorPrecision.zeroPoint == "number" && t.setFloat32(116, this.colorPrecision.zeroPoint, !0)), this.modelParamsUniforms.dataBytes = e;
  }
  /**
   * Mark precision as FP16 in model params and replace buffers (used by runtime conversion)
   */
  applyFP16(e, t, s) {
    this.replaceStorageBuffers(e, { gaussianBuffer: t, shBuffer: s }), this.gaussianPrecision = { dataType: "float16", bytesPerElement: 2 }, this.colorPrecision = { dataType: "float16", bytesPerElement: 2 }, this.setPrecisionForShader();
  }
  /**
   * Update method called by AnimationManager for dynamic inference
   * @param cameraMatrix - Camera view matrix
   * @param modelTransform - Model transform matrix (from GaussianModel/Object3D)
   * @param time - Optional time parameter for animation
   * @param projectionMatrix - Optional projection matrix
   * @param rafNow - Optional current time for variable delta mode
   */
  async update(e, t, s, r, n) {
    if (!this.onnxGenerator) {
      console.warn("⚠️ No ONNX generator available for dynamic update");
      return;
    }
    var i = 0;
    i = this.timeline.getCurrentTime(), i = i * 0.4 % 1, this.timeline.isFallbackPreviewMode() && (i = s ?? 0, i = i * 0.4, i = i % 1);
    try {
      const o = this.onnxGenerator.getInputNames(), a = c.create();
      c.multiply(a, e, t), this.is_loop ? i = i % 1 : i = Math.max(0, Math.min(i, 1));
      const l = {
        cameraMatrix: new Float32Array(a),
        // Use combined view*model matrix
        projectionMatrix: r ? new Float32Array(r) : void 0,
        time: i
        // Cycle 0-1 with time scaling and offset applied
      };
      await this.onnxGenerator.generate(l);
    } catch (o) {
      console.error("❌ Dynamic update failed:", o);
    }
  }
  /**
   * Animation control methods - delegate to timeline controller
   */
  startAnimation(e = 1) {
    this.timeline.startAnimation(e);
  }
  pauseAnimation() {
    this.timeline.pauseAnimation();
  }
  resumeAnimation() {
    this.timeline.resumeAnimation();
  }
  stopAnimation() {
    this.timeline.stopAnimation();
  }
  setAnimationTime(e) {
    this.timeline.setAnimationTime(e);
  }
  setAnimationSpeed(e) {
    this.timeline.setAnimationSpeed(e);
  }
  getAnimationSpeed() {
    return this.timeline.getAnimationSpeed();
  }
  get isAnimationRunning() {
    return this.timeline.isPlaying();
  }
  get isAnimationPaused() {
    return this.timeline.isPaused();
  }
  get isAnimationStopped() {
    return this.timeline.isStopped();
  }
  /**
   * Time control methods - delegate to timeline controller
   */
  /**
   * Set time scaling factor
   * @param scale - Time scaling factor (1.0 = normal speed, 2.0 = 2x faster, 0.5 = 2x slower)
   */
  setTimeScale(e) {
    this.timeline.setTimeScale(e);
  }
  /**
   * Get current time scaling factor
   * @returns Current time scale value
   */
  getTimeScale() {
    return this.timeline.getTimeScale();
  }
  /**
   * Set time offset
   * @param offset - Time offset in seconds
   */
  setTimeOffset(e) {
    this.timeline.setTimeOffset(e);
  }
  setAnimationIsLoop(e) {
    this.is_loop = e;
  }
  /**
   * Get current time offset
   * @returns Current time offset value
   */
  getTimeOffset() {
    return this.timeline.getTimeOffset();
  }
  /**
   * Get current frame time (before offset adjustment)
   * @returns Current frame time
   */
  getFrameTime() {
    return this.timeline.getCurrentTime();
  }
  /**
   * Reset frame time to zero
   */
  resetFrameTime() {
    this.timeline.setTime(0);
  }
  /**
   * Set time update mode
   * @param mode - Time update mode (FIXED_DELTA or VARIABLE_DELTA)
   */
  setTimeUpdateMode(e) {
    this.timeline.setTimeUpdateMode(e);
  }
  /**
   * Get current time update mode
   * @returns Current time update mode
   */
  getTimeUpdateMode() {
    return this.timeline.getTimeUpdateMode() === "fixed_delta" ? g.FIXED_DELTA : g.VARIABLE_DELTA;
  }
  /**
   * Get performance statistics
   */
  getPerformanceStats() {
    return {
      ...this.timeline.getStats(),
      hasOnnxGenerator: !!this.onnxGenerator,
      colorMode: this.colorMode,
      colorChannels: this.colorChannels,
      numPoints: this.numPoints
    };
  }
  /**
   * Dispose of dynamic point cloud resources
   */
  dispose() {
    this.timeline.clearEventListeners(), console.log("🧹 DynamicPointCloud disposed");
  }
}
export {
  B as BUFFER_CONFIG,
  M as DynamicPointCloud,
  G as PointCloud,
  m as getBindGroupLayout,
  b as getRenderBindGroupLayout
};
