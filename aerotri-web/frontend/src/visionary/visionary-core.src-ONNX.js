import * as u from "onnxruntime-web/webgpu";
import { r as B } from "./visionary-core.src-utils.js";
import * as g from "onnxruntime-web";
import { mat4 as w } from "gl-matrix";
function O(m) {
  return Math.ceil(m / 16) * 16;
}
function U(m, t) {
  const e = m.reduce((i, s) => i * Math.max(1, s), 1);
  return O(e * t.bytesPerElement);
}
function b(m) {
  return m.dataType;
}
class N {
  // 新逻辑：仅基于输出名称后缀判断精度
  static detectOutputPrecisionFromName(t) {
    const e = (t || "").toLowerCase();
    return e.includes("_f32") || e.includes("_float32") ? { dataType: "float32", bytesPerElement: 4 } : e.includes("_f16") || e.includes("_float16") ? { dataType: "float16", bytesPerElement: 2 } : e.includes("_i8") || e.includes("_int8") ? { dataType: "int8", bytesPerElement: 1 } : e.includes("_u8") || e.includes("_uint8") ? { dataType: "uint8", bytesPerElement: 1 } : { dataType: "float16", bytesPerElement: 2 };
  }
  // 从 outputMetadata 获取对应条目，优先使用 meta type 判断；只有没有 meta 信息时才回退到名称
  static detectFromMetadataPreferringNameSuffix(t, e) {
    try {
      const i = t.outputMetadata;
      if (i && typeof i == "object") {
        const s = (o) => i instanceof Map ? i.get(o) ?? i.get(String(o)) : Array.isArray(i) && typeof o == "number" ? i[o] : i[o] ?? i[String(o)], a = i instanceof Map ? Array.from(i.values()) : Object.keys(i).map((o) => i[o]);
        let n = e ? s(e) : void 0;
        if (!n && a.length && (n = a.find((o) => o?.name === e)), !n && e) {
          const o = t.outputNames, r = Array.isArray(o) ? o.findIndex((l) => l === e) : -1;
          r >= 0 && (n = s(r));
        }
        if (n) {
          const o = n?.type ?? n?.dataType;
          if (o) {
            const r = this.mapOrtTypeToPrecision(o);
            if (r) return r;
          }
        }
      }
    } catch {
    }
    return this.detectOutputPrecisionFromName(e);
  }
  static mapOrtTypeToPrecision(t) {
    const e = String(t).toLowerCase();
    if (e.includes("float16") || e === "float16" || e === "tensor(float16)") return { dataType: "float16", bytesPerElement: 2 };
    if (e.includes("float32") || e === "float32" || e === "float" || e === "tensor(float)") return { dataType: "float32", bytesPerElement: 4 };
    if (e.includes("int8") || e === "int8" || e === "tensor(int8)") return { dataType: "int8", bytesPerElement: 1 };
    if (e.includes("uint8") || e === "uint8" || e === "tensor(uint8)") return { dataType: "uint8", bytesPerElement: 1 };
  }
  static extractQuantizationParams(t, e) {
    try {
      const s = t.model?.graph?.initializer ?? [];
      let a, n;
      for (const o of s) {
        const r = o?.name;
        if (!r) continue;
        const l = r.toLowerCase();
        if (l.includes("scale") && l.includes(e.toLowerCase())) {
          const d = o?.floatData?.[0] ?? o?.doubleData?.[0];
          typeof d == "number" && (a = d);
        }
        if ((l.includes("zero") || l.includes("zeropoint")) && l.includes(e.toLowerCase())) {
          const d = o?.int32Data?.[0] ?? o?.int64Data?.[0];
          typeof d == "number" && (n = d);
        }
      }
      return { scale: a, zeroPoint: n };
    } catch {
      return {};
    }
  }
  static calculateBufferSize(t, e) {
    return U(t, e);
  }
}
let C = !1;
class P {
  device;
  session;
  verbose = !1;
  // 全局推理串行化协调器，避免 ORT WebGPU IOBinding 并发导致的 Session 冲突
  static _runChain = Promise.resolve();
  static async runExclusive(t) {
    const e = P._runChain;
    let i;
    P._runChain = new Promise((s) => i = s);
    try {
      await e;
    } catch {
    }
    try {
      const s = await t();
      return i(), s;
    } catch (s) {
      throw i(), s;
    }
  }
  // Color detection fields
  colorMode = "sh";
  colorDim = 48;
  // 48 for SH, 3 for RGB
  colorOutputName = null;
  // Capacity detection fields
  capacity;
  // Detected maxPoints from metadata
  gaussOutputName = null;
  gaussFields = 10;
  // Usually 10 for gaussian attributes
  // 直接暴露给渲染阶段使用的 GPUBuffer
  gaussBuf;
  // (maxPoints, 10) f16 → 20B/pt
  shBuf;
  // (maxPoints, colorDim) f16 → variable size
  countBuf;
  // i32[1]：本次推理实际点数（不回读 CPU）
  // Input GPU buffers for enableGraphCapture compatibility
  cameraMatrixBuf;
  // 4x4 float32 → 64B
  projMatrixBuf;
  // 4x4 float32 → 64B
  timeBuf;
  // 1 float32 → 4B
  maxPoints;
  get detectedCapacity() {
    return this.capacity;
  }
  get detectedGaussOutputName() {
    return this.gaussOutputName;
  }
  get detectedGaussFields() {
    return this.gaussFields;
  }
  actualPoints;
  // Actual points returned by the model
  inputNames;
  // Model's expected input names
  // Precision information (detected or overridden)
  gaussianPrecision;
  // data type for gaussian output
  colorPrecision;
  // data type for color output
  // Public getters for color detection results
  get detectedColorMode() {
    return this.colorMode;
  }
  get detectedColorDim() {
    return this.colorDim;
  }
  get detectedColorOutputName() {
    return this.colorOutputName;
  }
  // Conditional logging helpers
  log(...t) {
    this.verbose && console.log(...t);
  }
  warn(...t) {
    this.verbose && console.warn(...t);
  }
  table(t) {
    this.verbose && console.table(t);
  }
  async init(t) {
    this.device = t.device, this.verbose = t.verbose ?? !1, this.log("Initializing ONNX Runtime environment...");
    try {
      u.env.wasm.numThreads = 1, u.env.logLevel = "verbose", this.log("isGPUDevice?", t.device && typeof t.device.createBuffer == "function" && !!t.device.queue), this.log("ONNX Runtime environment configured with provided WebGPU device");
    } catch (c) {
      this.warn("ONNX Runtime environment configuration failed:", c);
    }
    this.log(`Attempting to create ONNX session with model: ${t.modelUrl}`), this.log(`Model URL type: ${typeof t.modelUrl}`), t.modelUrl && t.modelUrl.constructor && this.log(`Model URL constructor: ${t.modelUrl.constructor.name}`), t.modelUrl && typeof t.modelUrl.toString == "function" && this.log(`Model URL toString: ${t.modelUrl.toString()}`);
    let e;
    if (t.modelUrl)
      if (typeof t.modelUrl == "string")
        e = t.modelUrl;
      else if (typeof t.modelUrl == "object" && t.modelUrl && "toString" in t.modelUrl && typeof t.modelUrl.toString == "function")
        e = t.modelUrl.toString();
      else
        throw new Error(`Invalid modelUrl type: ${typeof t.modelUrl}. Expected string path.`);
    else throw new Error(`modelUrl is required but was ${t.modelUrl}`);
    if (!e || e.trim() === "")
      throw new Error(`modelUrl cannot be empty. Got: "${e}"`);
    const i = (c) => ({
      executionProviders: [{
        name: "webgpu",
        deviceId: 0,
        powerPreference: "high-performance"
      }],
      graphOptimizationLevel: "extended",
      preferredOutputLocation: "gpu-buffer",
      enableGraphCapture: c && !C,
      enableProfiling: C
    });
    let s = null;
    const a = async () => {
      if (s) return s;
      this.log(` Fetching model as ArrayBuffer from: ${e}`);
      const c = await fetch(e);
      if (!c.ok)
        throw new Error(`Failed to fetch model: ${c.status} ${c.statusText}`);
      const f = await c.arrayBuffer();
      return this.log(` Model buffer size: ${f.byteLength} bytes`), s = new Uint8Array(f), s;
    }, n = async (c) => {
      const f = i(c);
      this.log(`Creating WebGPU-only ONNX session (graphCapture=${c})...`), this.log(`Using model path: "${e}"`), this.log("Session options:", f);
      try {
        this.session = await u.InferenceSession.create(e, f), this.log(" ONNX session created successfully with WebGPU provider");
        return;
      } catch (p) {
        this.warn(" WebGPU session creation failed, trying ArrayBuffer approach:", p);
        try {
          const y = await a();
          this.session = await u.InferenceSession.create(y, f), this.log(" ONNX session created successfully with WebGPU provider (ArrayBuffer)");
          return;
        } catch (y) {
          console.error(" WebGPU session creation failed with both path and buffer approaches"), console.error("Path error:", p), console.error("Buffer error:", y);
          const $ = new Error(`WebGPU execution provider required but failed to initialize (graphCapture=${c}). Ensure WebGPU is supported and enabled.`);
          throw $.pathError = p, $.bufferError = y, $;
        }
      }
    };
    try {
      await n(!0);
    } catch (c) {
      const p = `Onnx can not enable WebGPU Graph Capture, system will automatically close this feature and re-initialize.
Error details: ${c instanceof Error ? c.message : String(c)}`, y = globalThis?.alert;
      typeof y == "function" ? y(p) : console.error(p), this.warn(" Graph Capture initialization failed, retrying without it", c), await n(!1);
    }
    this.log(" Using provided WebGPU device to avoid device mismatch"), this.log("📋 Model Input Names:", this.session.inputNames), this.log("📋 Model Output Names:", this.session.outputNames), this.inputNames = this.session.inputNames, await this.detectFromMetadata(), this.maxPoints = this.capacity || t.maxPoints || 2e6, this.log(`📏 Using maxPoints: ${this.maxPoints} (detected: ${this.capacity}, config: ${t.maxPoints})`), await this.detectPrecisions(t.precisionConfig), console.log("gaussianPrecision", this.gaussianPrecision), console.log("gaussianPrecision", this.colorPrecision);
    const o = U([this.maxPoints, 10], this.gaussianPrecision), r = U([this.maxPoints, this.colorDim], this.colorPrecision);
    this.log(` Allocating buffers (gauss ${this.gaussianPrecision.dataType}): ${o}B, (color ${this.colorPrecision.dataType}): ${r}B, channels=${this.colorDim}`), this.log(` Color mode: ${this.colorMode}, output name: '${this.colorOutputName}'`);
    const l = GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC | GPUBufferUsage.COPY_DST | GPUBufferUsage.VERTEX;
    this.gaussBuf = this.device.createBuffer({ size: o, usage: l, label: `gaussian_${this.gaussianPrecision.dataType}` }), this.shBuf = this.device.createBuffer({ size: r, usage: l, label: `color_${this.colorPrecision.dataType}` }), this.countBuf = this.device.createBuffer({
      size: Math.ceil(4 / 16) * 16,
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC | GPUBufferUsage.COPY_DST,
      label: "num_points"
    });
    const d = GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST, h = (c) => Math.ceil(c / 16) * 16;
    this.cameraMatrixBuf = this.device.createBuffer({
      size: h(64),
      // 4x4 float32
      usage: d,
      label: "camera_matrix"
    }), this.projMatrixBuf = this.device.createBuffer({
      size: h(64),
      // 4x4 float32  
      usage: d,
      label: "projection_matrix"
    }), this.timeBuf = this.device.createBuffer({
      size: h(4),
      // 1 float32
      usage: d,
      label: "time_input"
    });
  }
  /**
   * Detect capacity and color output from ONNX model metadata
   */
  async detectFromMetadata() {
    this.log(" Detecting capacity and color output from model metadata...");
    try {
      await this.pickCapacityFromMetadataOrProbe() ? this.log(` Capacity detected from metadata: ${this.capacity}`) : this.log(" Could not detect capacity from metadata"), this.pickColorOutputFromMetadata() ? this.log(` Color mode detected from metadata: ${this.colorMode} (${this.colorDim} channels)`) : (this.log(" Could not detect color type from metadata, using defaults"), this.colorMode = "sh", this.colorDim = 48, this.colorOutputName = "sh_f16");
    } catch (t) {
      console.error(" Metadata detection failed:", t), this.warn(" Falling back to defaults"), this.colorMode = "sh", this.colorDim = 48, this.colorOutputName = "sh_f16", this.log(` Detection completed with defaults: capacity=${this.capacity || "none"}, color=${this.colorMode} (${this.colorDim} channels)`);
    }
  }
  async detectPrecisions(t) {
    try {
      const s = this.session.outputNames || [], a = this.session.outputMetadata;
      if (this.verbose && (console.log("[ONNX][Debug] outputNames =", s), a))
        for (const n in a) {
          const o = a[n], r = o?.shape ? `[${o.shape.join(", ")}]` : "unknown";
          console.log(`[ONNX][Meta] idx=${n} name='${o?.name}' type='${o?.type ?? o?.dataType}' shape=${r}`);
        }
    } catch {
    }
    const e = this.gaussOutputName || (this.session.outputNames?.find((s) => /gauss|gaussian/i.test(s)) ?? "gaussian_f16"), i = N.detectFromMetadataPreferringNameSuffix(this.session, e);
    if (this.gaussianPrecision = i, this.colorPrecision = { ...i }, i.dataType === "int8" || i.dataType === "uint8") {
      const s = N.extractQuantizationParams(this.session, e);
      this.gaussianPrecision.scale = s.scale ?? 1, this.gaussianPrecision.zeroPoint = s.zeroPoint ?? 0;
      const a = this.colorOutputName || "sh_f16", n = N.extractQuantizationParams(this.session, a);
      this.colorPrecision.scale = n.scale ?? 1, this.colorPrecision.zeroPoint = n.zeroPoint ?? 0;
    }
    this.log(`Precision detected: gaussian=${this.gaussianPrecision.dataType} (${this.gaussianPrecision.bytesPerElement}B), color=${this.colorPrecision.dataType}`), this.detectedPrecisionLabel = this.gaussianPrecision?.dataType || "float16";
  }
  /**
   * Detect capacity from metadata using the approach provided by user
   */
  async pickCapacityFromMetadataOrProbe() {
    this.log("🧭 Detecting capacity from gaussian output metadata...");
    try {
      const t = this.session;
      this.log(" DEBUG: session object keys:", Object.keys(t));
      const e = t.outputMetadata;
      this.log(" DEBUG: outputMetadata:", e);
      for (const i of Object.keys(e))
        if (console.log(` Found gaussian candidate in outputMetadata: '${i}' dims=${e[i]?.shape ? `[${e[i]?.shape.join(", ")}]` : "undefined"}`), e[i].name.startsWith("gauss") || e[i].name.startsWith("gaussian")) {
          const s = e[i]?.shape;
          return console.log(` Found gaussian candidate in outputMetadata: '${i}' dims=${s ? `[${s.join(", ")}]` : "undefined"}`), this.gaussOutputName = e[i].name, this.gaussFields = s[-1], this.capacity = s[0], this.log(`🦭 Capacity from metadata: ${e[i].name} -> N=${this.capacity}, fields=${this.gaussFields}`), !0;
        }
      return console.log("🔬 Fallback: Running minimal CPU inference to detect shapes..."), await this.detectCapacityFromCPUInference();
    } catch (t) {
      return console.warn(" Error accessing output metadata:", t), await this.detectCapacityFromCPUInference();
    }
  }
  /**
   * Fallback: Use minimal CPU inference to detect capacity and color dimensions
   */
  async detectCapacityFromCPUInference() {
    this.log("🔬 Running minimal CPU inference to detect model dimensions...");
    try {
      const t = {};
      for (const s of this.inputNames)
        s.toLowerCase().includes("camera") || s.toLowerCase().includes("view") || s.toLowerCase().includes("matrix") ? t[s] = new u.Tensor("float32", new Float32Array(16).fill(0), [4, 4]) : s.toLowerCase().includes("time") || s === "t" ? t[s] = new u.Tensor("float32", new Float32Array([0]), [1]) : (s.toLowerCase().includes("projection") || s.toLowerCase().includes("proj")) && (t[s] = new u.Tensor("float32", new Float32Array(16).fill(0), [4, 4]));
      this.log(` Running CPU inference with inputs: ${Object.keys(t).join(", ")}`);
      const e = await this.session.run(t), i = this.session.outputNames.filter((s) => /gauss|gaussian|means|cov|gaussian_f16/i.test(s));
      for (const s of i) {
        const a = e[s];
        if (a && a.dims.length >= 2) {
          const n = a.dims, o = n[n.length - 1], r = n[0];
          if (this.log(` Found gaussian output '${s}': shape [${n.join(", ")}]`), (o === 10 || o === 9) && Number.isFinite(r) && r > 0)
            return this.gaussOutputName = s, this.gaussFields = o, this.capacity = r, this.log(` Capacity detected from CPU inference: ${s} -> N=${this.capacity}, fields=${this.gaussFields}`), this.detectColorFromCPUResult(e), !0;
        }
      }
      return this.log(" No gaussian output found with expected dimensions"), !1;
    } catch (t) {
      return this.warn(" CPU inference detection failed:", t), !1;
    }
  }
  /**
   * Detect color output from CPU inference result
   */
  detectColorFromCPUResult(t) {
    for (const [e, i] of Object.entries(t)) {
      const s = i.dims, a = e.toLowerCase();
      if ((a.includes("color") || a.includes("sh") || a.includes("rgb")) && s.length >= 2) {
        const n = s[s.length - 1];
        if (n === 48) {
          this.colorMode = "sh", this.colorDim = 48, this.colorOutputName = e, this.log(` Color mode detected from CPU inference: SH (${n} channels) - ${e}`);
          return;
        } else if (n === 3 || n === 4) {
          this.colorMode = "rgb", this.colorDim = n === 3 ? 4 : n, this.colorOutputName = e, this.log(` Color mode detected from CPU inference: RGB (${n} channels) - ${e}`);
          return;
        } else if (n === 12 || n === 27) {
          this.colorMode = "sh", this.colorDim = n, this.colorOutputName = e, this.log(` Color mode detected from CPU inference: SH (${n} channels) - ${e}`);
          return;
        }
      }
    }
  }
  /**
   * Try to detect color output type from session metadata using dimensions
   */
  pickColorOutputFromMetadata() {
    this.log(" Detecting color output type from metadata dimensions...");
    try {
      const e = this.session.outputMetadata ?? {};
      for (const i of this.session.outputNames) {
        const s = i.toLowerCase();
        if (s.includes("color") || s.includes("sh") || s.includes("rgb")) {
          let a = -1;
          for (const r in e)
            if (e[r]?.name === i) {
              a = Number(r);
              break;
            }
          if (a === -1) continue;
          const o = e[a]?.shape;
          if (this.log(` Found potential color output: '${i}' dims=${o ? `[${o.join(", ")}]` : "undefined"}`), o && o.length >= 2) {
            const r = o[o.length - 1];
            if (r === 48)
              return this.colorMode = "sh", this.colorDim = 48, this.colorOutputName = i, this.log(` Detected SH from dimensions: '${i}' → ${r} channels`), !0;
            if (r === 3 || r === 4)
              return this.colorMode = "rgb", this.colorDim = r, this.colorOutputName = i, this.log(` Detected RGB from dimensions: '${i}' → ${r} channels`), !0;
            if (r === 12 || r === 27)
              return this.colorMode = "sh", this.colorDim = r, this.colorOutputName = i, this.log(` Detected SH from dimensions: '${i}' → ${r} channels`), !0;
            this.warn(` Found color output '${i}' with unexpected ${r} channels`);
          }
        }
      }
    } catch (e) {
      this.warn(" Error accessing color output metadata:", e);
    }
    const t = ["sh_f16", "spherical_harmonics", "color_sh"];
    for (const e of t)
      if (this.session.outputNames.includes(e))
        return this.colorMode = "sh", this.colorDim = 48, this.colorOutputName = e, this.log(`📝 Found standard SH output: '${e}' → 48 channels (name-based fallback)`), !0;
    return this.log(" No color output detected from metadata"), !1;
  }
  /**
   * Update input GPU buffers from CPU data
   * Required for enableGraphCapture compatibility
   */
  updateInputBuffers(t, e, i) {
    if (t && (this.log(" DEBUG: Camera Matrix passed to ONNX:"), this.log(t), this.table([
      t.slice(0, 4),
      t.slice(4, 8),
      t.slice(8, 12),
      t.slice(12, 16)
    ]), this.device.queue.writeBuffer(this.cameraMatrixBuf, 0, t.buffer)), e && (this.log(" DEBUG: Projection Matrix passed to ONNX:"), this.log(e), this.table([
      e.slice(0, 4),
      e.slice(4, 8),
      e.slice(8, 12),
      e.slice(12, 16)
    ]), this.device.queue.writeBuffer(this.projMatrixBuf, 0, e.buffer)), i !== void 0) {
      this.log(` DEBUG: Time passed to ONNX: ${i}`);
      const s = new Float32Array([i]);
      this.device.queue.writeBuffer(this.timeBuf, 0, s.buffer);
    }
  }
  // 执行推理，将结果直接写入 GPUBuffer
  async runInference(t = {}) {
    return P.runExclusive(async () => {
      this.log(" GPU DIRECT: Running WebGPU inference with IOBinding..."), this.log(`📏 Using pre-allocated buffers for ${this.maxPoints} points`), this.updateInputBuffers(t.cameraMatrix, t.projectionMatrix, t.time);
      const e = this.maxPoints, i = {};
      for (const o of this.inputNames)
        o.toLowerCase().includes("camera") || o.toLowerCase().includes("view") || o.toLowerCase().includes("matrix") ? (i[o] = u.Tensor.fromGpuBuffer(
          this.cameraMatrixBuf,
          { dataType: "float32", dims: [4, 4] }
        ), this.log(`  📷 Created GPU camera matrix for '${o}'`)) : o.toLowerCase().includes("time") || o === "t" ? (i[o] = u.Tensor.fromGpuBuffer(
          this.timeBuf,
          { dataType: "float32", dims: [1] }
        ), this.log(`  ⏰ Created GPU time input for '${o}'`)) : (o.toLowerCase().includes("projection") || o.toLowerCase().includes("proj")) && (i[o] = u.Tensor.fromGpuBuffer(
          this.projMatrixBuf,
          { dataType: "float32", dims: [4, 4] }
        ), this.log(`  📐 Created GPU projection matrix for '${o}'`));
      const s = this.gaussOutputName || "gaussian_f16", a = {};
      a[s] = u.Tensor.fromGpuBuffer(
        this.gaussBuf,
        { dataType: b(this.gaussianPrecision), dims: [e, 10] }
      ), a.num_points = u.Tensor.fromGpuBuffer(
        this.countBuf,
        { dataType: "int32", dims: [1] }
      );
      const n = this.colorOutputName || "sh_f16";
      if (this.log("----- real needed color channels " + this.colorDim), this.session.outputNames.includes(n))
        a[n] = u.Tensor.fromGpuBuffer(
          this.shBuf,
          { dataType: b(this.colorPrecision), dims: [e, this.colorDim] }
        );
      else {
        this.warn(` Color output '${n}' not found in model outputs`), this.warn(`Available outputs: ${this.session.outputNames.join(", ")}`);
        const o = this.session.outputNames.find(
          (r) => r.toLowerCase().includes("color") || r.toLowerCase().includes("sh") || r.toLowerCase().includes("rgb")
        );
        if (o)
          this.warn(` Using possible color output: '${o}'`), a[o] = u.Tensor.fromGpuBuffer(
            this.shBuf,
            { dataType: b(this.colorPrecision), dims: [e, this.colorDim] }
          );
        else
          throw new Error(`No suitable color output found in model. Available outputs: ${this.session.outputNames.join(", ")}`);
      }
      this.log(` IOBinding configured: gaussian[${e}x10], ${this.colorMode}[${e}x${this.colorDim}]`), this.log(` Input feeds: ${Object.keys(i).join(", ")}`), this.log(` Output fetches: ${Object.keys(a).join(", ")}`);
      try {
        await this.session.run(i, a), this.log(" GPU DIRECT SUCCESS: Inference completed with full GPU pipeline");
        try {
          const o = await B(this.device, this.countBuf);
          this.log(` DEBUG: ONNX wrote count=${o} to GPU buffer`), this.actualPoints = o;
        } catch (o) {
          this.warn(" Could not read count buffer for debugging:", o);
        }
      } catch (o) {
        console.error(" WebGPU IOBinding failed:", o);
        const r = o instanceof Error ? o.message : String(o);
        throw console.error("name:", o?.name, "message:", o?.message, "stack:", o?.stack), new Error(`WebGPU inference required but failed: ${r}`);
      }
    });
  }
  destroy() {
    this.gaussBuf?.destroy?.(), this.shBuf?.destroy?.(), this.countBuf?.destroy?.(), this.cameraMatrixBuf?.destroy?.(), this.projMatrixBuf?.destroy?.(), this.timeBuf?.destroy?.();
  }
}
class T {
  constructor(t) {
    this.cfg = t;
  }
  io;
  inited = !1;
  async initialize(t) {
    const e = t || this.cfg.device;
    if (!e)
      throw new Error("WebGPU device is required. Pass device to initialize() or provide it in config.");
    this.io = new P(), await this.io.init({
      modelUrl: this.cfg.modelUrl,
      maxPoints: this.cfg.maxPoints,
      device: e,
      verbose: !1,
      //this.cfg.debugLogging
      precisionConfig: this.cfg.precisionConfig
    }), this.inited = !0;
  }
  // 仅在需要时调用；通常初始化时 run 一次后全程复用显存数据
  async generate(t = {}) {
    if (!this.inited) throw new Error("ONNXGenerator not initialized");
    await this.io.runInference(t);
  }
  // 提供渲染阶段取用 GPUBuffer 的方法
  getGaussianBuffer() {
    return this.io.gaussBuf;
  }
  getSHBuffer() {
    return this.io.shBuf;
  }
  getCountBuffer() {
    return this.io.countBuf;
  }
  getDevice() {
    return this.io.device;
  }
  getInputNames() {
    return this.io.inputNames || [];
  }
  // 获取检测到的模型参数
  getDetectedCapacity() {
    return this.io.detectedCapacity;
  }
  getDetectedColorMode() {
    return this.io.detectedColorMode;
  }
  getDetectedColorDim() {
    return this.io.detectedColorDim;
  }
  getActualMaxPoints() {
    return this.io.maxPoints;
  }
  // 精度信息
  getGaussianPrecision() {
    return this.io.gaussianPrecisionInfo ?? this.io.gaussianPrecision;
  }
  getColorPrecision() {
    return this.io.colorPrecisionInfo ?? this.io.colorPrecision;
  }
  dispose() {
    this.io?.destroy();
  }
}
class x {
  session = null;
  /**
   * Initialize ONNX Runtime and set WebAssembly paths
   */
  static async initialize() {
    g.env.logLevel = "verbose", console.log("ONNX Runtime initialized with WASM paths");
  }
  /**
   * Load the test ONNX model
   */
  async loadModel(t = "./models/gaussians3d.onnx") {
    try {
      console.log(`Loading ONNX model from: ${t}`), this.session = await g.InferenceSession.create(t, {
        executionProviders: ["wasm"]
        // Start with WASM provider
      }), console.log("✅ ONNX model loaded successfully"), this.logModelInfo();
    } catch (e) {
      throw console.error("❌ Failed to load ONNX model:", e), e;
    }
  }
  /**
   * Log detailed model information
   */
  logModelInfo() {
    if (!this.session) return;
    console.log(`
📊 Model Information:`), console.log(`
🔵 Inputs:`);
    const t = this.session.inputNames;
    for (const i of t)
      try {
        const s = this.session.inputMetadata[i];
        console.log(`  - ${i}:`, {
          type: s?.type || "unknown",
          dims: s?.dims || []
        });
      } catch {
        console.log(`  - ${i}: metadata unavailable`);
      }
    console.log(`
🟢 Outputs:`);
    const e = this.session.outputNames;
    for (const i of e)
      try {
        const s = this.session.outputMetadata[i];
        console.log(`  - ${i}:`, {
          type: s?.type || "unknown",
          dims: s?.dims || []
        });
      } catch {
        console.log(`  - ${i}: metadata unavailable`);
      }
  }
  /**
   * Test inference with sample data
   */
  async testInference() {
    if (!this.session)
      throw new Error("Model not loaded. Call loadModel() first.");
    console.log(`
🧪 Testing inference with sample data...`);
    try {
      const t = this.createTestInputs();
      console.log("Input tensors prepared:");
      for (const [a, n] of Object.entries(t))
        console.log(`  - ${a}: shape=${n.dims}, type=${n.type}`);
      const e = performance.now(), i = await this.session.run(t), s = performance.now() - e;
      console.log(`✅ Inference completed in ${s.toFixed(2)}ms`), console.log(`
📤 Output tensors:`);
      for (const [a, n] of Object.entries(i))
        if (console.log(`  - ${a}: shape=${n.dims}, type=${n.type}, size=${n.size}`), n.data.length > 0) {
          const o = n.data instanceof Float32Array ? n.data : new Float32Array(n.data), r = Array.from(o.slice(0, 10));
          console.log(`    First 10 values: [${r.join(", ")}${n.data.length > 10 ? ", ..." : ""}]`);
        }
      return i;
    } catch (t) {
      throw console.error("❌ Inference failed:", t), t;
    }
  }
  /**
   * Create test input tensors based on expected model inputs
   */
  createTestInputs() {
    const t = {};
    if (!this.session) throw new Error("Session not initialized");
    for (const e of this.session.inputNames) {
      const i = this.session.inputMetadata[e];
      if (e.toLowerCase().includes("camera") || e.toLowerCase().includes("view") || e.toLowerCase().includes("matrix")) {
        const s = w.create();
        w.identity(s), t[e] = new g.Tensor("float32", s, [4, 4]), console.log(`  📷 Created camera matrix for '${e}'`);
      } else if (e.toLowerCase().includes("time") || e.toLowerCase().includes("t")) {
        const s = new Float32Array([0.5]);
        t[e] = new g.Tensor("float32", s, [1]), console.log(`  ⏰ Created time input for '${e}': ${s[0]}`);
      } else if (e.toLowerCase().includes("projection") || e.toLowerCase().includes("proj")) {
        const s = w.create();
        w.perspective(s, Math.PI / 4, 16 / 9, 0.1, 1e3), t[e] = new g.Tensor("float32", s, [4, 4]), console.log(`  📐 Created projection matrix for '${e}'`);
      } else {
        const s = i.dims, a = s.reduce((o, r) => o * r, 1), n = new Float32Array(a).fill(0.5);
        t[e] = new g.Tensor("float32", n, s), console.log(`  🔢 Created generic input for '${e}': shape=${s}, filled with 0.5`);
      }
    }
    return t;
  }
  /**
   * Run comprehensive model analysis
   */
  async analyzeModel() {
    console.log(`
🔍 Starting comprehensive model analysis...
`), console.log("Testing temporal variation:");
    for (const e of [0, 0.25, 0.5, 0.75, 1])
      console.log(`
⏰ Testing with time = ${e}`), await this.testInferenceWithTime(e);
    console.log(`
📷 Testing camera position variation:`);
    const t = [
      [0, 0, 5],
      // Front
      [5, 0, 0],
      // Right  
      [0, 5, 0],
      // Top
      [-5, 0, 0]
      // Left
    ];
    for (const [e, i, s] of t)
      console.log(`
📍 Testing with camera at [${e}, ${i}, ${s}]`), await this.testInferenceWithCamera([e, i, s]);
  }
  /**
   * Test inference with specific time value
   */
  async testInferenceWithTime(t) {
    if (!this.session) return;
    const e = this.createTestInputs(), i = this.session.inputNames.find(
      (a) => a.toLowerCase().includes("time") || a.toLowerCase().includes("t")
    );
    i && (e[i] = new g.Tensor("float32", new Float32Array([t]), [1]));
    const s = await this.session.run(e);
    for (const [a, n] of Object.entries(s)) {
      const o = n.data, r = o.reduce((h, c) => h + c, 0) / o.length, l = Math.min(...o), d = Math.max(...o);
      console.log(`    ${a}: mean=${r.toFixed(4)}, range=[${l.toFixed(4)}, ${d.toFixed(4)}]`);
    }
    return s;
  }
  /**
   * Test inference with specific camera position
   */
  async testInferenceWithCamera(t) {
    if (!this.session) return;
    const e = this.createTestInputs(), i = w.create(), s = new Float32Array(t), a = new Float32Array([0, 0, 0]), n = new Float32Array([0, 1, 0]);
    w.lookAt(i, s, a, n);
    const o = this.session.inputNames.find(
      (l) => l.toLowerCase().includes("camera") || l.toLowerCase().includes("view") || l.toLowerCase().includes("matrix")
    );
    o && (e[o] = new g.Tensor("float32", i, [4, 4]));
    const r = await this.session.run(e);
    for (const [l, d] of Object.entries(r)) {
      const h = d.data, c = h.reduce((f, p) => f + p, 0) / h.length;
      console.log(`    ${l}: mean=${c.toFixed(4)}, size=${h.length}`);
    }
    return r;
  }
  /**
   * Clean up resources
   */
  async dispose() {
    this.session && (this.session = null, console.log("🧹 ONNX session disposed"));
  }
}
export {
  T as O,
  x as a
};
