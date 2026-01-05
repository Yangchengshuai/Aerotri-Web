import { PointCloud as c, BUFFER_CONFIG as m } from "./visionary-core.src-point-cloud.js";
import "gl-matrix";
import { G as u } from "./visionary-core.src-sort.js";
import { G as d } from "./visionary-core.src-preprocess.js";
import { g as f } from "./visionary-core.src-shaders.js";
import "./visionary-core.src-utils.js";
import "three/webgpu";
import "three/examples/jsm/loaders/RGBELoader.js";
const b = 0.3;
class v {
  device;
  format;
  shDegree;
  compressed;
  debug;
  // Core GPU resources (static, cached)
  pipeline;
  pipelineDepth;
  useDepth = !1;
  depthFormat = "depth24plus";
  // Configurable depth format
  pipelineLayout;
  drawIndirectBuffer;
  // Subsystem instances
  sorter;
  preprocessorSH;
  // For spherical harmonics models
  preprocessorRGB;
  // For direct RGB models
  // Per-point-cloud resources (cached by point count)
  sortResourcesCache = /* @__PURE__ */ new WeakMap();
  // Global-sorting scaffolding
  globalCapacity = 0;
  // total allocated splats capacity
  globalBuffers = null;
  // Implementation
  constructor(e, t, i, s = !1) {
    "device" in e ? (this.device = e.device, this.format = e.format, this.shDegree = e.shDegree, this.compressed = e.compressed ?? !1, this.debug = e.debug ?? !1) : (this.device = e, this.format = t, this.shDegree = i, this.compressed = s, this.debug = !1);
  }
  /**
   * Ensure sorter is initialized (legacy method name for compatibility)
   */
  async ensureSorter() {
    await this.initialize();
  }
  /**
   * Initialize all GPU resources asynchronously
   * Called once during renderer setup
   */
  async initialize() {
    await this.initializeSorter(), await this.initializePreprocessor(), this.createPipelineLayout(), this.createRenderPipeline(), this.createIndirectDrawBuffer(), this.ensureGlobalCapacity(1e6);
    try {
      globalThis.gaussianRenderer = this;
    } catch {
    }
    this.debug && console.log(`GaussianRenderer initialized: ${this.format}, SH degree ${this.shDegree}, global capacity ${this.globalCapacity}`);
  }
  /**
   * Record render commands to the provided render pass
   */
  render(e, t) {
    const i = this.getSortResources(t);
    e.setBindGroup(0, t.renderBindGroup()), e.setBindGroup(1, i.sorter_render_bg), e.setPipeline(this.useDepth && this.pipelineDepth ? this.pipelineDepth : this.pipeline), e.drawIndirect(this.drawIndirectBuffer, 0);
  }
  /**
   * Get pipeline information for external integrations
   */
  /** Enable or disable depth testing for GS render pipeline */
  setDepthEnabled(e) {
    this.useDepth = !!e;
  }
  /**
   * Set depth format and recreate depth pipeline if format changed
   * @param format - WebGPU depth texture format (e.g., 'depth24plus', 'depth32float')
   */
  setDepthFormat(e) {
    this.depthFormat !== e && (this.depthFormat = e, this.createDepthPipeline(), globalThis.GS_DEPTH_DEBUG && (console.log("[GaussianRenderer] Depth format changed to:", e), console.log("[GaussianRenderer] Depth pipeline recreated")));
  }
  /**
   * Create depth-enabled pipeline variant
   */
  createDepthPipeline() {
    const e = this.device.createShaderModule({
      label: "Gaussian Shader Module",
      code: f
    });
    this.pipelineDepth = this.device.createRenderPipeline({
      label: `Gaussian Render Pipeline (Depth-${this.depthFormat})`,
      layout: this.pipelineLayout,
      vertex: {
        module: e,
        entryPoint: "vs_main",
        buffers: []
      },
      fragment: {
        module: e,
        entryPoint: "fs_main",
        targets: [{
          format: this.format,
          blend: {
            color: { srcFactor: "one", dstFactor: "one-minus-src-alpha", operation: "add" },
            alpha: { srcFactor: "one", dstFactor: "one-minus-src-alpha", operation: "add" }
          }
        }]
      },
      primitive: {
        topology: "triangle-strip",
        frontFace: "ccw"
      },
      depthStencil: {
        format: this.depthFormat,
        depthWriteEnabled: !1,
        depthCompare: "less"
      },
      multisample: {}
    });
  }
  getPipelineInfo() {
    return {
      format: this.format,
      bindGroupLayouts: [
        c.renderBindGroupLayout(this.device),
        u.createRenderBindGroupLayout(this.device)
      ]
    };
  }
  /**
   * Get rendering statistics for profiling
   */
  getRenderStats(e) {
    const t = this.sortResourcesCache.get(e);
    return {
      gaussianCount: e.numPoints,
      visibleSplats: t?.num_points ?? 0,
      memoryUsage: this.estimateMemoryUsage(e)
    };
  }
  /**
   * prepare multiple point clouds.
   * Current turn: falls back to per-model prepare to keep behavior unchanged.
   */
  prepareMulti(e, t, i, s) {
    if (i.length === 0) return;
    const r = [];
    let a = 0;
    for (const o of i)
      r.push(a), a += o.numPoints;
    if (this._dlog("[prepareMulti] total points =", a, "offsets =", r), this.ensureGlobalCapacity(a), !!this.globalBuffers) {
      this._dlog("[prepareMulti] using global capacity =", this.globalCapacity), this.sorter.recordResetIndirectBuffer(this.globalBuffers.sortStuff.sorter_dis, this.globalBuffers.sortStuff.sorter_uni, t);
      for (let o = 0; o < i.length; o++) {
        const n = i[o], p = r[o];
        this._dlog(`[prepareMulti] dispatch model #${o} baseOffset=${p} count=${n.numPoints}`);
        let l;
        "countBuffer" in n && typeof n.countBuffer == "function" && (l = n.countBuffer(), l && this._dlog(`[prepareMulti] Model #${o} has ONNX count buffer`));
        const h = this.getColorMode(n) === "rgb" ? this.preprocessorRGB : this.preprocessorSH, g = this.buildRenderSettings(n, s);
        h.dispatchModel({
          camera: s.camera,
          viewport: s.viewport,
          pointCloud: n,
          sortStuff: this.globalBuffers.sortStuff,
          settings: g,
          modelMatrix: n.transform,
          // Use the point cloud's transform matrix
          baseOffset: p,
          global: { splat2D: this.globalBuffers.splat2D },
          countBuffer: l
          // Pass the count buffer if available
        }, e);
      }
      this.sorter.recordSortIndirect(this.globalBuffers.sortStuff, this.globalBuffers.sortStuff.sorter_dis, e), e.copyBufferToBuffer(this.globalBuffers.sortStuff.sorter_uni, 0, this.drawIndirectBuffer, 4, 4), this._dlog("[prepareMulti] recorded global sort & updated instanceCount from sorter_uni");
    }
  }
  /**
   * Phase B API (M1 scaffolding): record render for multiple point clouds.
   * Current turn: falls back to per-model render to keep behavior unchanged.
   */
  renderMulti(e, t) {
    this.globalBuffers && (e.setBindGroup(0, this.globalBuffers.renderBG), e.setBindGroup(1, this.globalBuffers.sortStuff.sorter_render_bg), e.setPipeline(this.useDepth && this.pipelineDepth ? this.pipelineDepth : this.pipeline), e.drawIndirect(this.drawIndirectBuffer, 0));
  }
  // ========== Private Implementation ==========
  /**
   * Initialize the radix sorter
   */
  async initializeSorter() {
    this.sorter = await u.create(this.device, this.device.queue);
  }
  /**
   * Initialize the preprocessing pipeline
   */
  async initializePreprocessor() {
    this.preprocessorSH = new d(), await this.preprocessorSH.initialize(this.device, this.shDegree, !1), this.preprocessorRGB = new d(), await this.preprocessorRGB.initialize(this.device, 0, !0), console.log("Initialized dual preprocessors: SH and RGB modes");
  }
  /**
   * Detect color mode from point cloud to select appropriate preprocessor
   */
  getColorMode(e) {
    return e.colorMode;
  }
  /**
   * Create the pipeline layout (static resource)
   */
  createPipelineLayout() {
    this.pipelineLayout = this.device.createPipelineLayout({
      label: "Gaussian Renderer Pipeline Layout",
      bindGroupLayouts: [
        c.renderBindGroupLayout(this.device),
        // @group(0)
        u.createRenderBindGroupLayout(this.device)
        // @group(1)
      ]
    });
  }
  /**
   * Create the render pipeline (static resource)
   */
  createRenderPipeline() {
    const e = this.device.createShaderModule({
      label: "Gaussian Shader Module",
      code: f
    });
    this.pipeline = this.device.createRenderPipeline({
      label: "Gaussian Render Pipeline",
      layout: this.pipelineLayout,
      vertex: {
        module: e,
        entryPoint: "vs_main",
        buffers: []
        // No vertex buffers - everything comes from storage
      },
      fragment: {
        module: e,
        entryPoint: "fs_main",
        targets: [{
          format: this.format,
          blend: {
            color: { srcFactor: "one", dstFactor: "one-minus-src-alpha", operation: "add" },
            alpha: { srcFactor: "one", dstFactor: "one-minus-src-alpha", operation: "add" }
          }
        }]
      },
      primitive: {
        topology: "triangle-strip",
        frontFace: "ccw"
      },
      multisample: {}
    }), this.createDepthPipeline();
  }
  /**
   * Create indirect draw buffer (static resource)
   */
  createIndirectDrawBuffer() {
    this.drawIndirectBuffer = this.device.createBuffer({
      label: "Gaussian Indirect Draw Buffer",
      size: 16,
      // DrawIndirect struct: 4 × u32
      usage: GPUBufferUsage.INDIRECT | GPUBufferUsage.COPY_DST | GPUBufferUsage.COPY_SRC
    }), this.device.queue.writeBuffer(this.drawIndirectBuffer, 0, new Uint32Array([4, 0, 0, 0]));
  }
  /**
   * Get sort resources for a point cloud (cached to avoid per-frame allocation)
   */
  getSortResources(e) {
    let t = this.sortResourcesCache.get(e);
    return (!t || t.num_points !== e.numPoints) && (t = this.sorter.createSortStuff(this.device, e.numPoints), this.sortResourcesCache.set(e, t), this.debug && console.log(`Created sort resources for ${e.numPoints} points`)), t;
  }
  /**
   * Build render settings from args and point cloud properties
   */
  buildRenderSettings(e, t) {
    const i = e.bbox, s = e.center, r = i.min, a = i.max, o = Math.max(
      Math.abs(a[0] - r[0]),
      Math.abs(a[1] - r[1]),
      Math.abs(a[2] - r[2])
    );
    return {
      maxSHDegree: Math.min(t.maxSHDegree ?? e.shDeg, this.shDegree),
      showEnvMap: t.showEnvMap ?? !0,
      mipSplatting: t.mipSplatting ?? e.mipSplatting ?? !1,
      kernelSize: t.kernelSize ?? e.kernelSize ?? b,
      walltime: t.walltime ?? 1,
      sceneExtend: t.sceneExtend ?? o,
      center: new Float32Array([
        t.sceneCenter?.[0] ?? s[0],
        t.sceneCenter?.[1] ?? s[1],
        t.sceneCenter?.[2] ?? s[2]
      ]),
      clippingBoxMin: new Float32Array([
        t.clippingBox?.min[0] ?? r[0],
        t.clippingBox?.min[1] ?? r[1],
        t.clippingBox?.min[2] ?? r[2]
      ]),
      clippingBoxMax: new Float32Array([
        t.clippingBox?.max[0] ?? a[0],
        t.clippingBox?.max[1] ?? a[1],
        t.clippingBox?.max[2] ?? a[2]
      ])
    };
  }
  /**
   * Estimate memory usage for debugging
   */
  estimateMemoryUsage(e) {
    const t = e.numPoints * 128, i = e.numPoints * 8 * 2;
    return t + i;
  }
  /**
   * Ensure global buffers capacity (placeholder for upcoming M1 implementation)
   */
  async ensureGlobalCapacity(e) {
    const t = Math.max(1, e);
    if (this.globalBuffers && t <= this.globalCapacity) return;
    this._dlog("[ensureGlobalCapacity] grow needed. needed=", t, "oldCap=", this.globalCapacity);
    const i = Math.ceil(t * 1.25);
    if (this.globalBuffers) {
      try {
        this.globalBuffers.splat2D.destroy();
      } catch {
      }
      this.globalBuffers = null;
    }
    for (; !this.sorter; )
      await new Promise((n) => setTimeout(n, 100));
    const s = this.sorter.createSortStuff(this.device, i), r = this.device.createBuffer({
      label: `global/splat2d(cap=${i})`,
      size: i * m.SPLAT_STRIDE,
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST | GPUBufferUsage.COPY_SRC
    }), a = c.renderBindGroupLayout(this.device), o = this.device.createBindGroup({
      label: "global/render/bg",
      layout: a,
      entries: [{ binding: 2, resource: { buffer: r } }]
    });
    this.globalBuffers = { splat2D: r, renderBG: o, sortStuff: s }, this.globalCapacity = i, this._dlog("[ensureGlobalCapacity] new capacity =", this.globalCapacity);
  }
  /**
   * Debug helper: read current instanceCount from drawIndirectBuffer.
   * Usage in Console: await gaussianRenderer.readInstanceCountDebug()
   */
  async readInstanceCountDebug() {
    const e = this.device.createBuffer({
      label: "debug/instanceCount",
      size: 4,
      usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST
    }), t = this.device.createCommandEncoder({ label: "debug/enc" });
    t.copyBufferToBuffer(this.drawIndirectBuffer, 4, e, 0, 4), this.device.queue.submit([t.finish()]), await this.device.queue.onSubmittedWorkDone(), await e.mapAsync(GPUMapMode.READ);
    const i = new Uint32Array(e.getMappedRange())[0];
    return e.unmap(), e.destroy(), console.log("[debug] instanceCount =", i), i;
  }
  /**
   * Debug ONNX count values through the pipeline
   */
  async debugONNXCount() {
    if (console.log("=== RENDERER DEBUG: ONNX Count Pipeline ==="), this._debugCountBuffer) {
      const e = this.preprocessorSH;
      "debugCountValues" in e && typeof e.debugCountValues == "function" && await e.debugCountValues();
      const t = this._debugPointCloud;
      t && console.log(`PointCloud.numPoints = ${t.numPoints}`);
    } else
      console.log("No ONNX count buffer to debug");
  }
  /**
   * Debug: read a small sample of payload indices (global) to inspect ranges.
   * Usage: await gaussianRenderer.readPayloadSampleDebug(8)
   */
  async readPayloadSampleDebug(e = 8) {
    if (!this.globalBuffers) throw new Error("globalBuffers not ready");
    const t = this.globalBuffers.sortStuff.payload_a, i = Math.min(t.size, e * 4), s = this.device.createBuffer({ label: "debug/payloadSample", size: i, usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST }), r = this.device.createCommandEncoder({ label: "debug/payloadEnc" });
    r.copyBufferToBuffer(t, 0, s, 0, i), this.device.queue.submit([r.finish()]), await this.device.queue.onSubmittedWorkDone(), await s.mapAsync(GPUMapMode.READ);
    const a = new Uint32Array(s.getMappedRange().slice(0));
    return s.unmap(), s.destroy(), console.log("[debug] payload[0..", e, ")=", Array.from(a)), a;
  }
  // Dev-only debug logger (disabled by default). Enable via: window.GS_DEBUG_LOGS = true
  _dlog(...e) {
    try {
      globalThis.GS_DEBUG_LOGS && console.log(...e);
    } catch {
    }
  }
}
export {
  v as G
};
