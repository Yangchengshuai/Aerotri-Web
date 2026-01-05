import { vec3 as c, mat4 as p, quat as f, vec2 as z } from "gl-matrix";
import { A, d as x } from "./visionary-core.src-utils.js";
import * as h from "three/webgpu";
import "three/examples/jsm/loaders/RGBELoader.js";
import "three/examples/jsm/loaders/GLTFLoader.js";
import "three/examples/jsm/loaders/OBJLoader.js";
import { FBXLoader as Z } from "three/examples/jsm/loaders/FBXLoader.js";
import "three/examples/jsm/loaders/STLLoader.js";
import "three/examples/jsm/loaders/PLYLoader.js";
import { i as R, d as C, a as T, b as Q, G as $, T as ee } from "./visionary-core.src-io.js";
import { O as te } from "./visionary-core.src-ONNX.js";
import { F as I, C as G } from "./visionary-core.src-controls.js";
import { G as X } from "./visionary-core.src-renderer.js";
import { i as oe, g as se } from "./visionary-core.src-config.js";
import { P as U, a as W, C as k } from "./visionary-core.src-camera.js";
import { DynamicPointCloud as v, PointCloud as V } from "./visionary-core.src-point-cloud.js";
import "onnxruntime-web/webgpu";
import { F as _ } from "./visionary-core.src-models.js";
const M = (d) => document.querySelector(d);
class ne {
  // Canvas
  canvas = M("#canvas");
  // Loading UI
  loadingOverlay = M("#loadingOverlay");
  progressFill = document.querySelector("#loadingOverlay .progress-fill");
  progressText = document.querySelector("#loadingOverlay .progress-text");
  // Error handling UI
  errorModal = M("#errorModal");
  errorMessage = M("#errorMessage");
  closeError = M("#closeError");
  noWebGPU = M("#noWebGPU");
  // File handling UI
  dropZone = M("#dropZone");
  browseBtn = M("#browseButton");
  fileInput = M("#fileInput");
  // Toggle panel (still available)
  togglePanelBtn = M("#togglePanel");
  // Stats display
  fpsEl = M("#fps");
  pointCountEl = M("#pointCount");
}
function D(d, e) {
  d?.classList.toggle("hidden", e);
}
function ae(d, e, t) {
  return Math.max(e, Math.min(t, d));
}
class re {
  dom;
  callbacks;
  controller;
  // Mouse state
  lastX = 0;
  lastY = 0;
  draggingL = !1;
  draggingR = !1;
  constructor(e, t, o) {
    this.dom = e, this.callbacks = o, this.controller = t;
  }
  /**
   * Initialize all UI event listeners
   */
  bindEvents(e) {
    this.bindFileHandling(), this.bindCameraControls(e), this.bindModalControls();
  }
  /**
   * File handling events (drag & drop, browse, samples)
   */
  bindFileHandling() {
    this.dom.dropZone.addEventListener("dragover", (e) => {
      e.preventDefault(), this.dom.dropZone.classList.add("dragover");
    }), this.dom.dropZone.addEventListener("dragleave", () => {
      this.dom.dropZone.classList.remove("dragover");
    }), this.dom.dropZone.addEventListener("drop", async (e) => {
      e.preventDefault(), this.dom.dropZone.classList.remove("dragover");
      const t = e.dataTransfer?.files?.[0];
      t && await this.callbacks.onFileLoad(t);
    }), this.dom.browseBtn.addEventListener("click", () => {
      this.dom.fileInput.click();
    }), this.dom.fileInput.addEventListener("change", async () => {
      const e = this.dom.fileInput.files?.[0];
      e && (await this.callbacks.onFileLoad(e), this.dom.fileInput.value = "");
    }), this.dom.togglePanelBtn?.addEventListener("click", () => {
      document.querySelector(".side-panel")?.classList.toggle("collapsed");
    });
  }
  /**
   * Camera control events (mouse, keyboard, wheel)
   */
  bindCameraControls(e) {
    e.addEventListener("mousedown", (t) => {
      t.button === 0 && (this.draggingL = !0, this.controller.leftMousePressed = !0), t.button === 2 && (this.draggingR = !0, this.controller.rightMousePressed = !0), this.lastX = t.clientX, this.lastY = t.clientY;
    }), window.addEventListener("mouseup", (t) => {
      t.button === 0 && (this.draggingL = !1, this.controller.leftMousePressed = !1), t.button === 2 && (this.draggingR = !1, this.controller.rightMousePressed = !1);
    }), window.addEventListener("mousemove", (t) => {
      const o = t.clientX - this.lastX, s = t.clientY - this.lastY;
      this.lastX = t.clientX, this.lastY = t.clientY, (this.draggingL || this.draggingR) && this.controller.processMouse(o, s);
    }), e.addEventListener("wheel", (t) => {
      t.preventDefault(), this.controller.processScroll(t.deltaY > 0 ? 0.05 : -0.05);
    }, { passive: !1 }), window.addEventListener("keydown", (t) => {
      this.controller.processKeyboard(t.code, !0);
    }), window.addEventListener("keyup", (t) => {
      this.controller.processKeyboard(t.code, !1);
    }), e.addEventListener("contextmenu", (t) => t.preventDefault());
  }
  /**
   * Modal control events
   */
  bindModalControls() {
    this.dom.closeError.addEventListener("click", () => {
      D(this.dom.errorModal, !0);
    });
  }
}
const J = new URL("data:application/octet-stream;base64,CAgSB3B5dG9yY2gaBTIuNS4wOlgKNRIFZHVtbXkaCkNvbnN0YW50XzEiCENvbnN0YW50KhYKBXZhbHVlKgoIARAGSgQBAAAAoAEEEgptYWluX2dyYXBoYhMKBWR1bW15EgoKCAgGEgQKAggBQgIQEQ==", import.meta.url).toString();
async function O() {
  const d = globalThis;
  if (d.__ORT_WEBGPU_SINGLETON__) return d.__ORT_WEBGPU_SINGLETON__;
  try {
    const e = await import("onnxruntime-web/webgpu");
    return d.__ORT_WEBGPU_SINGLETON__ = e, e;
  } catch {
    return null;
  }
}
async function ie(d) {
  const e = await O();
  if (!e) return;
  e.env.wasm.numThreads = 1, e.env.logLevel = "warning", e.env.wasm.wasmPaths ? console.log("[WebGPU] Using existing WASM paths:", e.env.wasm.wasmPaths) : (e.env.wasm.wasmPaths = "/src/ort/", console.log("[WebGPU] Setting default WASM paths:", e.env.wasm.wasmPaths));
  const t = await fetch(d);
  if (!t.ok) throw new Error(`[ORT] Failed to fetch dummy model: ${d}`);
  const o = await t.arrayBuffer();
  await e.InferenceSession.create(o, { executionProviders: ["webgpu"] });
}
async function le(d) {
  const e = await O();
  if (!e) return null;
  try {
    const t = e.env.webgpu;
    if (t) {
      const o = t.device;
      if (o) {
        const s = o instanceof Promise ? await o : o;
        if (s)
          return console.log("[WebGPU] Reusing existing ORT device from obtainOrtDevice"), s;
      }
    }
  } catch (t) {
    console.warn("[WebGPU] Could not check existing ORT device:", t);
  }
  if (d.adapter)
    try {
      const t = e.env.webgpu || {};
      e.env.webgpu = t;
      const o = t.adapter;
      if (o) {
        if (o !== d.adapter)
          try {
            const s = Object.getOwnPropertyDescriptor(t, "adapter");
            s && s.writable !== !1 ? t.adapter = d.adapter : console.warn("[WebGPU] Adapter is read-only, keeping existing adapter");
          } catch (s) {
            console.warn("[WebGPU] Could not update adapter (may be read-only, which is OK):", s);
          }
      } else try {
        t.adapter = d.adapter;
      } catch (s) {
        console.warn("[WebGPU] Could not set adapter (may be read-only):", s);
      }
    } catch (t) {
      console.warn("[WebGPU] Could not access ORT webgpu environment:", t);
    }
  try {
    const t = e.env.webgpu;
    if (t) {
      const o = t.device;
      if (o) {
        const s = o instanceof Promise ? await o : o;
        if (s) return s;
      }
    }
  } catch (t) {
    console.warn("[WebGPU] Could not get device from ORT env:", t);
  }
  if (d.dummyModelUrl)
    try {
      await ie(d.dummyModelUrl);
      const t = await O();
      if (t)
        try {
          const o = t.env.webgpu?.device;
          if (o) {
            const s = o instanceof Promise ? await o : o;
            if (s) return s;
          }
        } catch {
        }
    } catch (t) {
      console.warn("[WebGPU] Failed to create dummy session:", t);
    }
  return null;
}
async function de(d) {
  const e = [];
  d.features.has("shader-f16") && e.push("shader-f16"), d.features.has("timestamp-query") && e.push("timestamp-query"), d.features.has("chromium-experimental-timestamp-query-inside-passes") && e.push("chromium-experimental-timestamp-query-inside-passes");
  const t = d.limits, o = {
    maxStorageBufferBindingSize: t.maxStorageBufferBindingSize,
    maxBufferSize: t.maxBufferSize ?? t.maxStorageBufferBindingSize,
    maxComputeWorkgroupStorageSize: Math.min(32768, t.maxComputeWorkgroupStorageSize),
    maxComputeInvocationsPerWorkgroup: t.maxComputeInvocationsPerWorkgroup,
    maxComputeWorkgroupSizeX: t.maxComputeWorkgroupSizeX,
    maxComputeWorkgroupSizeY: t.maxComputeWorkgroupSizeY,
    maxComputeWorkgroupSizeZ: t.maxComputeWorkgroupSizeZ
  }, s = await d.requestDevice({
    requiredFeatures: e,
    requiredLimits: o
  });
  return s.label || (s.label = "app-device"), s;
}
async function B(d, e = {}) {
  if (!navigator.gpu)
    return console.error("WebGPU not supported in this environment."), null;
  const t = await O();
  let o = null, s = null;
  if (e.preferShareWithOrt !== !1 && t)
    try {
      const r = t.env.webgpu;
      if (r) {
        const i = r.device;
        i && (o = i instanceof Promise ? await i : i, o && (console.log("[WebGPU] Reusing existing ORT device for new canvas"), s = r.adapter));
      }
    } catch (r) {
      console.warn("[WebGPU] Could not get existing ORT device:", r);
    }
  if (o) {
    if (!s) {
      try {
        s = t?.env?.webgpu?.adapter;
      } catch {
      }
      s || (s = await navigator.gpu.requestAdapter({
        powerPreference: e.adapterPowerPreference
      }));
    }
  } else {
    if (s = await navigator.gpu.requestAdapter({
      powerPreference: e.adapterPowerPreference
    }), !s) throw new Error("No WebGPU adapter found");
    if (e.preferShareWithOrt !== !1 && t)
      if (o = await le({ adapter: s, dummyModelUrl: e.dummyModelUrl ?? null }), o) {
        if (o && !s)
          try {
            s = t.env?.webgpu?.adapter;
          } catch {
          }
      } else {
        const r = !!e.allowOwnDeviceWhenOrtPresent, i = "[WebGPU init] ORT detected but failed to obtain its device. " + (r ? "Proceeding with app-owned device (do NOT use ORT later)." : "Refusing to create a separate device to avoid future mismatch.- Provide a valid dummyModelUrl, ORdisable preferShareWithOrt, ORensure a single ORT import.");
        if (console.warn(i), !r) throw new Error("ORT present but cannot acquire ORT device (strict mode)");
      }
    if (!o) {
      if (!s && (s = await navigator.gpu.requestAdapter({
        powerPreference: e.adapterPowerPreference
      }), !s))
        throw new Error("No WebGPU adapter found");
      o = await de(s);
    }
  }
  o.pushErrorScope("out-of-memory"), o.pushErrorScope("validation"), await o.popErrorScope().then((r) => console.warn("validation:", r)), await o.popErrorScope().then((r) => console.warn("oom:", r)), o.lost.then((r) => console.error("device lost:", r.message, r.reason));
  const n = d.getContext("webgpu");
  if (!n) throw new Error("Failed to get WebGPU canvas context");
  const a = navigator.gpu.getPreferredCanvasFormat();
  return n.configure({ device: o, format: a, alphaMode: "premultiplied" }), console.log(`[WebGPU] initialized. format=${a}, sharedWithORT=${!!(t && e.preferShareWithOrt !== !1)}`), { device: o, context: n, format: a };
}
class j {
  models = [];
  maxModels;
  constructor(e = 1e4) {
    this.maxModels = e;
  }
  /**
   * Add a new model to the collection
   */
  addModel(e) {
    if (this.models.length >= this.maxModels)
      throw new Error(`Reached model limit (${this.maxModels}). Remove models before adding more.`);
    const o = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
      ...e
    };
    return this.models.push(o), console.log(`Model added: ${o.name} (${o.pointCount.toLocaleString()} points, ${o.modelType})`), o;
  }
  /**
   * Remove a model by ID
   */
  removeModel(e) {
    const t = this.models.findIndex((o) => o.id === e);
    if (t >= 0) {
      const o = this.models[t];
      return this.models.splice(t, 1), console.log(`Model removed: ${o.name}`), !0;
    }
    return !1;
  }
  /**
   * Get all models as simplified info (public API)
   */
  getModels() {
    return this.models.map((e) => ({
      id: e.id,
      name: e.name,
      visible: e.visible,
      pointCount: e.pointCount || 0,
      isDynamic: e.isDynamic,
      modelType: e.modelType,
      colorMode: e.colorMode,
      colorChannels: e.colorChannels
    }));
  }
  /**
   * Get a model with full pointCloud reference for debugging/testing
   */
  getModelWithPointCloud(e, t) {
    return t ? this.models.find((o) => o.id === t) || null : this.models.find((o) => o.modelType === e) || null;
  }
  /**
   * Get all model entries with full pointCloud references (for debugging/testing)
   */
  getFullModels() {
    return [...this.models];
  }
  /**
   * Get models by type
   */
  getModelsByType(e) {
    return this.models.filter((t) => t.modelType === e);
  }
  /**
   * Get visible models only
   */
  getVisibleModels() {
    return this.models.filter((e) => e.visible);
  }
  /**
   * Get dynamic models only
   */
  getDynamicModels() {
    return this.models.filter((e) => e.isDynamic);
  }
  /**
   * Update model visibility
   */
  setModelVisibility(e, t) {
    const o = this.models.find((s) => s.id === e);
    return o ? (o.visible = t, console.log(`Model ${o.name}: ${t ? "shown" : "hidden"}`), !0) : !1;
  }
  /**
   * Get total point count for visible models
   */
  getTotalVisiblePoints() {
    return this.models.filter((e) => e.visible).reduce((e, t) => e + t.pointCount, 0);
  }
  /**
   * Get total point count for all models
   */
  getTotalPoints() {
    return this.models.reduce((e, t) => e + t.pointCount, 0);
  }
  /**
   * Check if at model limit
   */
  isAtCapacity() {
    return this.models.length >= this.maxModels;
  }
  /**
   * Get model count
   */
  getModelCount() {
    return this.models.length;
  }
  /**
   * Get remaining capacity
   */
  getRemainingCapacity() {
    return Math.max(0, this.maxModels - this.models.length);
  }
  /**
   * Clear all models
   */
  clearAllModels() {
    const e = this.models.length;
    this.models = [], console.log(`Cleared ${e} models`);
  }
  /**
   * Find model by name (first match)
   */
  findModelByName(e) {
    return this.models.find((t) => t.name === e) || null;
  }
  /**
   * Set model position (legacy method - creates transform matrix from TRS)
   */
  setModelPosition(e, t, o, s) {
    return this.updateModelTransform(e, { translation: c.fromValues(t, o, s) });
  }
  /**
   * Set model rotation (radians, XYZ)
   */
  setModelRotation(e, t, o, s) {
    return this.updateModelTransform(e, { rotationEuler: c.fromValues(t, o, s) });
  }
  /**
   * Set model scale (uniform or non-uniform). Clamp each axis to epsilon to avoid collapse.
   */
  setModelScale(e, t) {
    const s = Array.isArray(t) ? c.fromValues(Math.max(1e-4, t[0]), Math.max(1e-4, t[1]), Math.max(1e-4, t[2])) : c.fromValues(Math.max(1e-4, t), Math.max(1e-4, t), Math.max(1e-4, t));
    return this.updateModelTransform(e, { scale: s });
  }
  /**
   * Set model transform matrix directly
   */
  setModelTransform(e, t) {
    const o = this.models.find((s) => s.id === e);
    return o ? (o.pointCloud.setTransform(t), console.log(`Model ${o.name} transform updated`), !0) : !1;
  }
  /**
   * Get model position
   */
  getModelPosition(e) {
    const t = this.models.find((o) => o.id === e);
    if (t) {
      const o = t.pointCloud.transform;
      return [o[12], o[13], o[14]];
    }
    return null;
  }
  /**
   * Get model rotation (in radians) - legacy method, limited functionality
   */
  getModelRotation(e) {
    const t = this.models.find((w) => w.id === e);
    if (!t) return null;
    const o = p.clone(t.pointCloud.transform), s = f.create();
    if (!p.getRotation) return [0, 0, 0];
    p.getRotation(s, o);
    const n = 2 * (s[3] * s[0] + s[1] * s[2]), a = 1 - 2 * (s[0] * s[0] + s[1] * s[1]), r = Math.atan2(n, a), i = 2 * (s[3] * s[1] - s[2] * s[0]), l = Math.abs(i) >= 1 ? Math.sign(i) * Math.PI / 2 : Math.asin(i), u = 2 * (s[3] * s[2] + s[0] * s[1]), m = 1 - 2 * (s[1] * s[1] + s[2] * s[2]), b = Math.atan2(u, m);
    return [r, l, b];
  }
  /**
   * Get model scale - legacy method, limited functionality
   */
  getModelScale(e) {
    const t = this.models.find((n) => n.id === e);
    if (!t) return null;
    const o = p.clone(t.pointCloud.transform), s = c.create();
    return p.getScaling ? (p.getScaling(s, o), [s[0], s[1], s[2]]) : [1, 1, 1];
  }
  /**
   * Get model transform matrix
   */
  getModelTransform(e) {
    const t = this.models.find((o) => o.id === e);
    return t ? t.pointCloud.transform : null;
  }
  /**
   * Internal helper: compose TRS and write back to point cloud
   */
  updateModelTransform(e, t) {
    const o = this.models.find((l) => l.id === e);
    if (!o)
      return console.log(`Model with ID ${e} not found for transform update`), !1;
    const s = p.clone(o.pointCloud.transform), n = c.create();
    p.getTranslation?.(n, s);
    const a = c.create();
    p.getScaling ? p.getScaling(a, s) : c.set(a, 1, 1, 1);
    const r = f.create();
    if (p.getRotation ? p.getRotation(r, s) : f.identity(r), t.translation && c.copy(n, t.translation), t.scale && c.copy(a, t.scale), t.rotationEuler) {
      const l = c.fromValues(
        t.rotationEuler[0] * 180 / Math.PI,
        t.rotationEuler[1] * 180 / Math.PI,
        t.rotationEuler[2] * 180 / Math.PI
      );
      f.fromEuler(r, l[0], l[1], l[2]);
    }
    const i = p.create();
    return p.fromRotationTranslationScale(i, r, n, a), o.pointCloud.setTransform(i), console.log(`Model ${o.name} transform updated (pos=${n.join(",")}, scale=${a.join(",")})`), !0;
  }
  /**
   * Check if model name exists
   */
  hasModelWithName(e) {
    return this.models.some((t) => t.name === e);
  }
  /**
   * Generate unique name based on base name
   */
  generateUniqueName(e) {
    if (!this.hasModelWithName(e))
      return e;
    let t = 1, o;
    do
      o = `${e} (${t})`, t++;
    while (this.hasModelWithName(o));
    return o;
  }
}
class q {
  loader;
  modelManager;
  callbacks;
  constructor(e, t = {}) {
    this.modelManager = e, this.callbacks = t, this.loader = new Z(), console.warn("⚠️ FBXLoader 与 WebGPU 渲染器可能存在兼容性问题。如果加载失败，建议："), console.warn("1. 将 FBX 模型转换为 GLTF/GLB 格式"), console.warn("2. 使用 GLTFLoader 替代 FBXLoader"), console.warn("3. 或暂时切换到 WebGLRenderer");
  }
  /**
   * 从文件加载 FBX 模型
   */
  async loadFromFile(e, t = {}) {
    try {
      if (this.showProgress(!0, "Loading FBX file...", 10), this.modelManager.isAtCapacity())
        throw this.showProgress(!1), this.showError(`Reached model limit (${this.modelManager.getRemainingCapacity()}). Remove models before adding more.`), new Error("Model limit reached");
      const o = await this.loadFBXFromFile(e);
      this.showProgress(!0, "Processing animations...", 30);
      const s = this.extractAnimationClips(o);
      this.showProgress(!0, "Creating model wrapper...", 60);
      const n = new _(o, s, t);
      this.showProgress(!0, "Registering model...", 80);
      const a = e.name.replace(/\.[^/.]+$/, ""), r = this.modelManager.generateUniqueName(a), i = this.modelManager.addModel({
        name: r,
        visible: !0,
        pointCloud: n,
        pointCount: n.getVertexCount(),
        isDynamic: s.length > 0,
        modelType: "fbx"
      });
      return this.showProgress(!1), this.callbacks.onSuccess?.(i), console.log(`FBX model loaded: ${i.name} (${i.pointCount} vertices, ${s.length} animations)`), i;
    } catch (o) {
      this.showProgress(!1);
      const s = `Failed to load FBX file: ${o.message}`;
      throw this.showError(s), o;
    }
  }
  /**
   * 从 URL 加载 FBX 模型
   */
  async loadFromURL(e, t = {}) {
    try {
      if (this.showProgress(!0, "Loading FBX from URL...", 10), this.modelManager.isAtCapacity())
        throw this.showProgress(!1), this.showError(`Reached model limit (${this.modelManager.getRemainingCapacity()}). Remove models before adding more.`), new Error("Model limit reached");
      const o = await this.loadFBXFromURL(e);
      this.showProgress(!0, "Processing animations...", 30);
      const s = this.extractAnimationClips(o);
      this.showProgress(!0, "Creating model wrapper...", 60);
      const n = new _(o, s, t);
      this.showProgress(!0, "Registering model...", 80);
      const a = e.split("/").pop()?.replace(/\.[^/.]+$/, "") || "FBX Model", r = this.modelManager.generateUniqueName(a), i = this.modelManager.addModel({
        name: r,
        visible: !0,
        pointCloud: n,
        pointCount: n.getVertexCount(),
        isDynamic: s.length > 0,
        modelType: "fbx"
      });
      return this.showProgress(!1), this.callbacks.onSuccess?.(i), console.log(`FBX model loaded from URL: ${i.name} (${i.pointCount} vertices, ${s.length} animations)`), i;
    } catch (o) {
      this.showProgress(!1);
      const s = `Failed to load FBX from URL: ${o.message}`;
      throw this.showError(s), o;
    }
  }
  /**
   * 从文件加载 FBX
   */
  async loadFBXFromFile(e) {
    return new Promise((t, o) => {
      const s = setTimeout(() => {
        o(new Error("FBX loading timeout after 30 seconds. This might be due to WebGPU compatibility issues with FBXLoader."));
      }, 3e4), n = new FileReader();
      n.onload = (a) => {
        try {
          const r = a.target?.result;
          if (!r)
            throw new Error("Failed to read file");
          console.log(`FBX file read successfully, size: ${r.byteLength} bytes`), console.log("Starting FBX parsing...");
          try {
            const i = this.loader.parse(r, "");
            clearTimeout(s), console.log("FBX parsing completed successfully"), t(i);
          } catch (i) {
            clearTimeout(s), console.error("FBX parsing failed:", i), o(new Error(`FBX parsing error: ${i.message || i}`));
          }
        } catch (r) {
          clearTimeout(s), console.error("Error in file read handler:", r), o(r);
        }
      }, n.onerror = () => {
        clearTimeout(s);
        const a = new Error("Failed to read file");
        console.error(a), o(a);
      }, console.log(`Reading FBX file: ${e.name}, size: ${e.size} bytes`), n.readAsArrayBuffer(e);
    });
  }
  /**
   * 从 URL 加载 FBX
   */
  async loadFBXFromURL(e) {
    return new Promise((t, o) => {
      this.loader.load(
        e,
        (s) => t(s),
        (s) => {
          const n = s.loaded / s.total * 100;
          this.showProgress(!0, `Loading... ${n.toFixed(1)}%`, n);
        },
        (s) => o(s)
      );
    });
  }
  /**
   * 从对象中提取动画剪辑
   */
  extractAnimationClips(e) {
    const t = [];
    return e.traverse((s) => {
      s.animations && s.animations.length > 0 && t.push(...s.animations);
    }), t.filter(
      (s, n, a) => n === a.findIndex((r) => r.name === s.name)
    );
  }
  /**
   * 显示进度
   */
  showProgress(e, t, o) {
    e && t && o !== void 0 ? this.callbacks.onProgress?.(o, t) : e || this.callbacks.onProgress?.(0, "");
  }
  /**
   * 显示错误
   */
  showError(e) {
    console.error(e), this.callbacks.onError?.(e);
  }
}
class Y {
  modelManager;
  callbacks;
  constructor(e, t = {}) {
    this.modelManager = e, this.callbacks = t;
  }
  /**
   * Load a file from a File object (drag & drop or file picker)
   * Now supports all Gaussian formats via defaultLoader
   */
  async loadFile(e, t) {
    try {
      if (this.showProgress(!0, "Reading file...", 10), e.arrayBuffer().then((s) => {
        console.log("[FileLoader] First 16 bytes:", new Uint8Array(s).slice(0, 16));
      }), this.modelManager.isAtCapacity())
        return this.showProgress(!1), this.showError(`Reached model limit (${this.modelManager.getRemainingCapacity()}). Remove models before adding more.`), null;
      const o = e.name.toLowerCase();
      if (R(o)) {
        const s = C(o);
        return console.log(`[FileLoader] Loading Gaussian format: ${s}`), await this.loadGaussianFile(e, t);
      } else return o.endsWith(".onnx") ? (this.showError("ONNX files should be loaded through ONNXManager, not FileLoader"), null) : o.endsWith(".fbx") ? await this.loadFBXFile(e) : (this.showProgress(!1), this.showError(`Unsupported file type: ${o}
Supported formats: ${this.getSupportedExtensions().join(", ")}`), null);
    } catch (o) {
      return this.showProgress(!1), this.showError(o.message), null;
    }
  }
  /**
   * Load a sample file from URL
   * Now supports all Gaussian formats
   */
  async loadSample(e, t, o) {
    try {
      if (this.modelManager.isAtCapacity())
        return this.showError("Reached model limit. Remove models before adding more."), null;
      console.log("[FileLoader] Loading sample:", e, o ? `(expected: ${o})` : "");
      let s = o;
      return s || (s = this.detectTypeFromFilename(e)), s && ["ply", "gaussian", "sog", "splat", "ksplat", "spz", "compressed.ply"].includes(s) ? await this.loadGaussianUrl(e, t, s) : s === "onnx" ? (this.showError("ONNX files should be loaded through ONNXManager, not FileLoader"), null) : (this.showError(`Unsupported file type: ${e}`), null);
    } catch (s) {
      return console.error(`[FileLoader] Failed to load sample ${e}:`, s), this.showProgress(!1), this.showError(s.message), null;
    }
  }
  /**
   * Detect file type from filename
   */
  detectTypeFromFilename(e) {
    const t = e.toLowerCase();
    if (R(t)) return "gaussian";
    if (t.endsWith(".onnx")) return "onnx";
  }
  /**
   * Load Gaussian format file from File object
   * Supports: PLY, SPZ, KSplat, SPLAT, SOG, Compressed PLY
   */
  async loadGaussianFile(e, t) {
    const o = C(e.name) || "unknown";
    console.log(`[FileLoader] Loading ${o.toUpperCase()} file:`, e.name);
    const s = await T.loadFile(e, {
      onProgress: (n) => {
        this.showProgress(!0, n.stage, n.progress * 100);
      },
      isGaussian: !0
    });
    if (!this.isGaussianDataSource(s))
      throw new Error(`Loaded data is not a valid Gaussian format: ${e.name}`);
    return await this.createGaussianModel(s, e.name, t);
  }
  /**
   * Load Gaussian format file from URL
   * Supports: PLY, SPZ, KSplat, SPLAT, SOG, Compressed PLY
   */
  async loadGaussianUrl(e, t, o) {
    if (e.startsWith("blob:"))
      return console.log("[FileLoader] Detected blob URL, using blob-to-file loading path"), await this.loadGaussianFromBlob(e, t, o);
    const s = C(e) || "unknown";
    console.log(`[FileLoader] Loading ${s.toUpperCase()} from URL:`, e);
    const n = await T.loadUrl(e, {
      onProgress: (r) => {
        this.showProgress(!0, r.stage, r.progress * 100);
      }
    });
    if (!this.isGaussianDataSource(n))
      throw new Error(`Loaded data is not a valid Gaussian format: ${e}`);
    const a = e.split("/").pop() || e;
    return await this.createGaussianModel(n, a, t);
  }
  /**
   * Load Gaussian file from blob URL by converting to File object
   */
  async loadGaussianFromBlob(e, t, o) {
    console.log(`[FileLoader] Converting blob URL to File object. Hint: ${o}`);
    try {
      const s = await fetch(e);
      if (!s.ok)
        throw new Error(`Failed to fetch blob: ${s.status} ${s.statusText}`);
      const n = await s.blob();
      let a = "ply";
      o && o !== "gaussian" && (a = o, console.log("type:", a));
      const r = `scene-model.${a}`, i = new File([n], r, { type: "application/octet-stream" });
      return console.log(`[FileLoader] Created File object '${r}' from blob, delegating to loadGaussianFile`), await this.loadGaussianFile(i, t);
    } catch (s) {
      throw console.error("[FileLoader] Failed to load from blob URL:", s), s;
    }
  }
  /**
   * Create a model from Gaussian data (unified for all formats)
   * This is the key method that converts GaussianDataSource to ModelEntry
   */
  async createGaussianModel(e, t, o) {
    this.showProgress(!0, "Creating GPU buffers...", 60);
    const { PointCloud: s } = await import("./visionary-core.src-point-cloud.js"), n = new s(o, e), a = this.modelManager.generateUniqueName(t), r = C(t) || "ply", i = this.modelManager.addModel({
      name: a,
      visible: !0,
      pointCloud: n,
      pointCount: n.numPoints,
      isDynamic: !1,
      modelType: r
      // Store the actual format (ply, spz, ksplat, etc.)
    });
    return this.showProgress(!0, "Initializing renderer...", 90), this.showProgress(!1), console.log(`[FileLoader] Successfully created ${r.toUpperCase()} model:`, a), i;
  }
  /**
   * Load FBX file
   */
  async loadFBXFile(e) {
    try {
      return await new q(this.modelManager, {
        onProgress: (o, s) => this.showProgress(!0, s, o),
        onError: (o) => this.showError(o),
        onSuccess: (o) => console.log("[FileLoader] FBX loaded successfully:", o.name)
      }).loadFromFile(e);
    } catch (t) {
      return this.showError(`Failed to load FBX file: ${t.message}`), null;
    }
  }
  /**
   * Check if file type is supported (updated to include all Gaussian formats)
   */
  isFileTypeSupported(e) {
    const t = e.toLowerCase();
    return R(t) || t.endsWith(".onnx") || t.endsWith(".fbx");
  }
  /**
   * Get supported file extensions (updated to include all Gaussian formats)
   */
  getSupportedExtensions() {
    return [
      ".ply",
      ".spz",
      ".ksplat",
      ".splat",
      ".sog",
      ".compressed.ply",
      // Gaussian formats
      ".onnx",
      // ONNX
      ".fbx"
      // FBX
    ];
  }
  /**
   * Get file type from filename (updated)
   */
  getFileType(e) {
    const t = e.toLowerCase();
    return R(t) ? "gaussian" : t.endsWith(".onnx") ? "onnx" : t.endsWith(".fbx") ? "fbx" : "unknown";
  }
  /**
   * Get specific Gaussian format
   */
  getGaussianFormat(e) {
    return C(e);
  }
  /**
   * Update loading callbacks
   */
  setCallbacks(e) {
    this.callbacks = { ...this.callbacks, ...e };
  }
  /**
   * Show loading progress
   */
  showProgress(e, t, o) {
    this.callbacks.onProgress && this.callbacks.onProgress(e, t, o);
  }
  /**
   * Show error message
   */
  showError(e) {
    this.callbacks.onError ? this.callbacks.onError(e) : console.error("[FileLoader] Error:", e);
  }
  /**
   * Validate file before loading
   */
  validateFile(e) {
    return e.size > 1073741824 ? { valid: !1, error: "File too large (max 1GB)" } : this.isFileTypeSupported(e.name) ? this.modelManager.isAtCapacity() ? {
      valid: !1,
      error: "Model limit reached. Remove models before adding more."
    } : { valid: !0 } : {
      valid: !1,
      error: `Unsupported file type. Supported: ${this.getSupportedExtensions().join(", ")}`
    };
  }
  /**
   * Type guard to check if data is GaussianDataSource
   * Uses the helper from io module
   */
  isGaussianDataSource(e) {
    return Q(e);
  }
}
class H {
  constructor(e) {
    this.modelManager = e;
  }
  generators = /* @__PURE__ */ new Map();
  pointClouds = /* @__PURE__ */ new Map();
  async loadONNXModel(e, t, o, s, n, a = {}) {
    console.log(a), console.log(`Loading ONNX model from: ${t}`);
    const { staticInference: r = !0, maxPoints: i, debugLogging: l = !1 } = a, u = new te({
      modelUrl: t,
      maxPoints: i,
      // undefined if not provided, will be auto-detected
      debugLogging: l,
      precisionConfig: a.precisionConfig
    });
    await u.initialize(e);
    const m = u.getInputNames();
    if (!r && m.length > 0) {
      const K = {
        cameraMatrix: o,
        projectionMatrix: s,
        time: 0
      };
      console.log(`Initial data for dynamic model - inputs: ${m.join(", ")}`), await u.generate(K);
    } else
      await u.generate({}), console.log(r, m.length, m), console.log("Static model - ran single inference with no inputs");
    const b = u.io?.actualPoints || i || 0, w = u.io?.detectedColorMode || "sh", g = u.io?.detectedColorDim || 48, S = u.io?.detectedColorOutputName || null, y = new v(
      e,
      u.getGaussianBuffer(),
      // gaussianBuffer
      u.getSHBuffer(),
      // shBuffer  
      i || u.getActualMaxPoints(),
      // maxPoints (use detected if not provided)
      u.getCountBuffer(),
      // countBuffer (旁路句柄，仅保存引用)
      g,
      // colorChannels for dynamic SH degree calculation
      {
        gaussian: u.getGaussianPrecision?.(),
        color: u.getColorPrecision?.()
      }
    ), F = u.io?.detectedPrecisionLabel || "float16", P = n || `ONNX Model (${F})`, N = this.modelManager.generateUniqueName(P);
    l && (console.log("ONNX Color Detection Results:"), console.log(`  Color Mode: ${w}`), console.log(`  Color Channels: ${g}`), console.log(`  Color Output Name: ${S || "default"}`), console.log(`  Actual Points: ${b}`), console.log(`  Max Points: ${i}`)), r || (y.setOnnxGenerator(u), l && console.log("🎬 Dynamic mode enabled - will update per frame"));
    const E = this.modelManager.addModel({
      name: N,
      visible: !0,
      pointCloud: y,
      pointCount: b,
      isDynamic: !r,
      modelType: "onnx",
      colorMode: w,
      colorChannels: g
    });
    return this.generators.set(E.id, u), this.pointClouds.set(E.id, y), l && console.log(`ONNX Model '${N}' (ID: ${E.id}) registered with isolated resources - color mode: ${w} (${g} channels)`), E;
  }
  async loadONNXFromFile(e, t, o, s) {
    const n = URL.createObjectURL(t);
    try {
      const a = new Float32Array(16), r = new Float32Array(16), i = [0, 0, 5], l = [0, 0, 0], u = [0, 1, 0];
      return p.lookAt(a, i, l, u), p.perspective(r, Math.PI / 4, 16 / 9, 0.01, 1e3), await this.loadONNXModel(
        e,
        n,
        o || a,
        s || r,
        t.name.replace(".onnx", ""),
        { staticInference: !0, maxPoints: 4e6, debugLogging: !0 }
      );
    } finally {
      URL.revokeObjectURL(n);
    }
  }
  async updateCameraMatrices(e, t, o) {
    console.log(`Updating camera matrices for model: ${e}`);
  }
  /**
   * Dispose a specific ONNX model by ID
   */
  disposeModel(e) {
    const t = this.generators.get(e), o = this.pointClouds.get(e);
    t?.dispose(), o?.dispose?.(), this.generators.delete(e), this.pointClouds.delete(e), console.log(`ONNXManager: Disposed model ${e}`);
  }
  /**
   * Dispose all ONNX resources
   */
  dispose() {
    for (const [e, t] of this.generators.entries())
      t?.dispose(), console.log(`ONNXManager: Disposed generator ${e}`);
    for (const [e, t] of this.pointClouds.entries())
      t?.dispose?.(), console.log(`ONNXManager: Disposed point cloud ${e}`);
    this.generators.clear(), this.pointClouds.clear(), console.log("ONNXManager: All resources disposed");
  }
  /**
   * Get generator for a specific model (for debugging/advanced use)
   */
  getGenerator(e) {
    return this.generators.get(e);
  }
  /**
   * Get point cloud for a specific model (for debugging/advanced use)
   */
  getPointCloud(e) {
    return this.pointClouds.get(e);
  }
  /**
   * Check if there are any ONNX models loaded
   */
  hasONNXModels() {
    return this.generators.size > 0;
  }
  /**
   * Get list of all loaded ONNX models
   */
  getONNXModels() {
    return Array.from(this.generators.keys());
  }
  /**
   * Get performance stats for ONNX models
   */
  getONNXPerformanceStats() {
    return {
      modelCount: this.generators.size,
      totalGenerators: this.generators.size,
      totalPointClouds: this.pointClouds.size
    };
  }
}
class L extends h.Object3D {
  mEntry;
  autoSyncEnabled = !0;
  _overrideLocalAabb = null;
  // 手动覆盖的局部 AABB（优先级最高）
  _cachedWorldAabb = null;
  // 缓存的世界 AABB
  _worldAabbDirty = !0;
  // 变换或覆盖变化后置脏
  // 高斯点缩放参数（独立于Three.js的scale属性）
  _gaussianScale = 1;
  /**
   * Create a GaussianModel from a ModelEntry
   * @param entry - Model data entry containing PointCloud
   */
  constructor(e) {
    super(), this.mEntry = e, this.name = e.name, this.setupAutoSync();
  }
  /**
   * Setup automatic synchronization of Object3D transform to GPU
   * This works by monitoring matrix updates and common transform operations
   * @private
   */
  setupAutoSync() {
    let e = !1, t = Date.now();
    const o = () => {
      this.autoSyncEnabled && !e && (e = !0, requestAnimationFrame(() => {
        this.syncTransformToGPU(), this._worldAabbDirty = !0, e = !1;
      }));
    }, s = this.updateMatrix.bind(this);
    this.updateMatrix = () => {
      s();
      const n = Date.now();
      n - t > 8 && (t = n, o());
    }, this.matrixAutoUpdate = !0, this.interceptTransformMethods(o), console.log(`✅ Auto-sync setup for model: ${this.name}`);
  }
  /**
   * Intercept common transform methods to trigger immediate sync
   * @private
   */
  interceptTransformMethods(e) {
    const t = this.position.set.bind(this.position), o = this.scale.set.bind(this.scale), s = this.rotation.set.bind(this.rotation);
    this.position.set = (n, a, r) => {
      const i = t(n, a, r);
      return e(), i;
    }, this.scale.set = (n, a, r) => {
      const i = o(n, a, r);
      return e(), i;
    }, this.rotation.set = (n, a, r, i) => {
      const l = s(n, a, r, i);
      return e(), l;
    };
  }
  // ============ Getters ============
  /**
   * Get model ID (note: different from Object3D.id which is a number)
   */
  getModelId() {
    return this.mEntry.id;
  }
  get modelName() {
    return this.mEntry.name;
  }
  get pointCount() {
    return this.mEntry.pointCount;
  }
  get isDynamic() {
    return this.mEntry.isDynamic;
  }
  get modelType() {
    return this.mEntry.modelType;
  }
  /**
   * Get the underlying ModelEntry (data layer access)
   */
  getEntry() {
    return this.mEntry;
  }
  /**
   * Get the PointCloud instance
   */
  getPointCloud() {
    if (!this.mEntry?.pointCloud)
      throw new Error("PointCloud is not initialized");
    return this.mEntry.pointCloud;
  }
  /**
   * Check if the model is a Gaussian model (PointCloud or DynamicPointCloud)
   * @returns True if model is PointCloud or DynamicPointCloud, false if FBX
   */
  isGaussianModel() {
    const e = this.mEntry.pointCloud;
    return e instanceof V || e instanceof v;
  }
  // ============ Transform Management ============
  /**
   * Get current transform matrix from Object3D TRS
   * @returns 4x4 column-major transform matrix
   */
  getTransformMatrix() {
    const e = new h.Matrix4();
    e.compose(this.position, this.quaternion, this.scale);
    const t = new h.Matrix4().makeScale(1, -1, -1);
    return t.premultiply(e), new Float32Array(t.elements);
  }
  /**
   * Sync Object3D transform to PointCloud GPU buffer
   * Call this after modifying position/rotation/scale
   * @param baseOffset - Base offset in global buffer (for multi-model rendering)
   */
  syncTransformToGPU(e = 0) {
    if (!this.mEntry?.pointCloud) return;
    const t = this.getTransformMatrix();
    this.mEntry.pointCloud.setTransform(t), this.isGaussianModel() && this.mEntry.pointCloud.updateModelParamsBuffer(t, e), globalThis.GS_DEBUG_FLAG && console.log(`[GaussianModel] Synced transform for ${this.name}:`, {
      position: [this.position.x.toFixed(3), this.position.y.toFixed(3), this.position.z.toFixed(3)],
      rotation: [this.rotation.x.toFixed(3), this.rotation.y.toFixed(3), this.rotation.z.toFixed(3)],
      scale: [this.scale.x.toFixed(3), this.scale.y.toFixed(3), this.scale.z.toFixed(3)]
    });
  }
  // ============ AABB（包围盒） ============
  /**
   * 设置（或清除）局部空间 AABB 覆盖值。
   * 传入 null 可清除覆盖（恢复为自动/估计）。
   */
  setOverrideAABB(e) {
    if (e === null)
      this._overrideLocalAabb = null;
    else if (e instanceof A)
      this._overrideLocalAabb = e;
    else {
      const t = c.fromValues(e.min[0], e.min[1], e.min[2]), o = c.fromValues(e.max[0], e.max[1], e.max[2]);
      this._overrideLocalAabb = new A(t, o);
    }
    this._worldAabbDirty = !0;
  }
  /**
   * 获取局部空间 AABB。
   * 优先使用覆盖值；否则读取底层 PointCloud 的 bbox（静态 PLY 准确，动态 ONNX 为保守/默认）。
   */
  getLocalAABB() {
    if (this._overrideLocalAabb) return this._overrideLocalAabb;
    const e = this.mEntry?.pointCloud;
    return e && e.bbox instanceof A ? e.bbox : null;
  }
  /**
   * 计算并返回世界空间 AABB（一次性缓存，变换或覆盖更新后置脏重算）。
   */
  getWorldAABB() {
    const e = this.getLocalAABB();
    if (!e) return null;
    if (this._cachedWorldAabb && !this._worldAabbDirty) return this._cachedWorldAabb;
    const t = e.min, o = e.max, s = [
      [t[0], t[1], t[2]],
      [t[0], t[1], o[2]],
      [t[0], o[1], t[2]],
      [t[0], o[1], o[2]],
      [o[0], t[1], t[2]],
      [o[0], t[1], o[2]],
      [o[0], o[1], t[2]],
      [o[0], o[1], o[2]]
    ], n = new h.Matrix4();
    n.compose(this.position, this.quaternion, this.scale);
    const a = new h.Vector3(), r = c.fromValues(1 / 0, 1 / 0, 1 / 0), i = c.fromValues(-1 / 0, -1 / 0, -1 / 0);
    for (const l of s)
      a.set(l[0], l[1], l[2]).applyMatrix4(n), a.x < r[0] && (r[0] = a.x), a.y < r[1] && (r[1] = a.y), a.z < r[2] && (r[2] = a.z), a.x > i[0] && (i[0] = a.x), a.y > i[1] && (i[1] = a.y), a.z > i[2] && (i[2] = a.z);
    return this._cachedWorldAabb = new A(r, i), this._worldAabbDirty = !1, this._cachedWorldAabb;
  }
  // ============ Dynamic Update ============
  /**
   * Update dynamic model (ONNX) with camera matrices
   * Transform is dynamically obtained from Object3D and passed to PointCloud
   * @param cameraMatrix - Camera view matrix
   * @param time - Optional time parameter for animation
   * @param projectionMatrix - Optional projection matrix
   */
  async update(e, t, o) {
    if (!(this.mEntry?.pointCloud instanceof v))
      return;
    const s = this.getTransformMatrix();
    await this.mEntry.pointCloud.update(e, s, t || 0, o);
  }
  // ============ Visibility ============
  /**
   * Set model visibility (syncs both Object3D.visible and ModelEntry.visible)
   */
  setModelVisible(e) {
    this.visible = e, this.mEntry.visible = e;
  }
  /**
   * Get model visibility (checks both Object3D and ModelEntry)
   */
  getModelVisible() {
    return this.mEntry.visible && this.visible;
  }
  /**
   * Check if model is visible from camera (for frustum culling)
   * Currently always returns true - can be enhanced with proper frustum culling
   */
  isVisible(e) {
    return this.getModelVisible();
  }
  // ============ Auto-Sync Control ============
  /**
   * Enable or disable automatic GPU synchronization
   * When enabled, changes to position/rotation/scale automatically sync to GPU
   * @param enabled - Whether to enable auto-sync
   */
  setAutoSync(e) {
    this.autoSyncEnabled = e, console.log(`Auto-sync ${e ? "enabled" : "disabled"} for model: ${this.modelName}`);
  }
  /**
   * Check if auto-sync is enabled
   */
  getAutoSync() {
    return this.autoSyncEnabled;
  }
  /**
   * Force immediate synchronization to GPU (regardless of auto-sync setting)
   */
  forceSyncToGPU() {
    this.syncTransformToGPU();
  }
  /**
   * Dispose resources and cleanup
   * Call this when the model is no longer needed
   * Note: Proxy interceptions will be cleaned up when object is garbage collected
   */
  dispose() {
    this.autoSyncEnabled = !1, console.log(`🧹 GaussianModel disposed: ${this.modelName}`);
  }
  // ============ Deprecated Methods ============
  /**
   * @deprecated Use setTransform from external PointCloud methods
   * This method is kept for backward compatibility
   */
  setTransform(e, t = 0) {
    console.warn("GaussianModel.setTransform() is deprecated. Modify position/rotation/scale instead."), this.mEntry.pointCloud.setTransform(e), this.isGaussianModel() && this.mEntry.pointCloud.updateModelParamsBuffer(e, t);
  }
  // ============ Gaussian Scaling ============
  /**
   * Set Gaussian scaling parameter (independent of Three.js scale)
   * @param scale - Scaling factor for Gaussian points
   */
  setGaussianScale(e) {
    this._gaussianScale = e, this.isGaussianModel() && (this.mEntry.pointCloud.setGaussianScaling(e), console.log(`[GaussianModel] ${this.name} Gaussian scale set to: ${e}`));
  }
  /**
   * Get current Gaussian scaling parameter
   * @returns Current Gaussian scale value
   */
  getGaussianScale() {
    return this.isGaussianModel() ? this.mEntry.pointCloud.getGaussianScaling() : this._gaussianScale;
  }
  /**
   * Set maximum spherical harmonics degree
   * @param deg - Maximum SH degree (0-3)
   */
  setMaxShDeg(e) {
    this.isGaussianModel() && (this.mEntry.pointCloud.setMaxShDeg(e), console.log(`[GaussianModel] ${this.name} Max SH degree set to: ${e}`));
  }
  /**
   * Get current maximum spherical harmonics degree
   * @returns Current max SH degree
   */
  getMaxShDeg() {
    return this.isGaussianModel() ? this.mEntry.pointCloud.getMaxShDeg() : 0;
  }
  /**
   * Set kernel size for 2D splatting
   * @param size - Kernel size
   */
  setKernelSize(e) {
    this.isGaussianModel() && (this.mEntry.pointCloud.setKernelSize(e), console.log(`[GaussianModel] ${this.name} Kernel size set to: ${e}`));
  }
  /**
   * Get current kernel size
   * @returns Current kernel size
   */
  getKernelSize() {
    return this.isGaussianModel() ? this.mEntry.pointCloud.getKernelSize() : 0;
  }
  /**
   * Set opacity scale factor
   * @param scale - Opacity scale factor
   */
  setOpacityScale(e) {
    this.isGaussianModel() && (this.mEntry.pointCloud.setOpacityScale(e), console.log(`[GaussianModel] ${this.name} Opacity scale set to: ${e}`));
  }
  /**
   * Get current opacity scale factor
   * @returns Current opacity scale factor
   */
  getOpacityScale() {
    return this.isGaussianModel() ? this.mEntry.pointCloud.getOpacityScale() : 1;
  }
  /**
   * Set cutoff scale factor for pixel ratio
   * @param scale - Cutoff scale factor
   */
  setCutoffScale(e) {
    this.isGaussianModel() && (this.mEntry.pointCloud.setCutoffScale(e), console.log(`[GaussianModel] ${this.name} Cutoff scale set to: ${e}`));
  }
  /**
   * Get current cutoff scale factor
   * @returns Current cutoff scale factor
   */
  getCutoffScale() {
    return this.isGaussianModel() ? this.mEntry.pointCloud.getCutoffScale() : 1;
  }
  /**
   * Set time scale factor for dynamic models
   * @param scale - Time scale factor
   */
  setTimeScale(e) {
    this.mEntry.pointCloud && "setTimeScale" in this.mEntry.pointCloud ? (this.mEntry.pointCloud.setTimeScale(e), console.log(`[GaussianModel] ${this.name} Time scale set to: ${e}`)) : console.warn(`[GaussianModel] ${this.name} does not support time scale (not a dynamic model)`);
  }
  /**
   * Get current time scale factor
   * @returns Current time scale factor
   */
  getTimeScale() {
    return this.mEntry.pointCloud && "getTimeScale" in this.mEntry.pointCloud ? this.mEntry.pointCloud.getTimeScale() : 1;
  }
  /**
   * Set time offset for dynamic models
   * @param offset - Time offset in seconds
   */
  setTimeOffset(e) {
    this.mEntry.pointCloud && "setTimeOffset" in this.mEntry.pointCloud ? (this.mEntry.pointCloud.setTimeOffset(e), console.log(`[GaussianModel] ${this.name} Time offset set to: ${e}`)) : console.warn(`[GaussianModel] ${this.name} does not support time offset (not a dynamic model)`);
  }
  /**
   * Set time offset for dynamic models
   * @param offset - Time offset in seconds
   */
  setAnimationIsLoop(e) {
    this.mEntry.pointCloud && "setAnimationIsLoop" in this.mEntry.pointCloud ? (this.mEntry.pointCloud.setAnimationIsLoop(e), console.log(`[GaussianModel] ${this.name} Is Loop set to: ${e}`)) : console.warn(`[GaussianModel] ${this.name} does not support animation is loop (not a dynamic model)`);
  }
  /**
   * Get current time offset
   * @returns Current time offset
   */
  getTimeOffset() {
    return this.mEntry.pointCloud && "getTimeOffset" in this.mEntry.pointCloud ? this.mEntry.pointCloud.getTimeOffset() : 0;
  }
  /**
   * Set time update mode for dynamic models
   * @param mode - Time update mode
   */
  setTimeUpdateMode(e) {
    this.mEntry.pointCloud && "setTimeUpdateMode" in this.mEntry.pointCloud ? (this.mEntry.pointCloud.setTimeUpdateMode(e), console.log(`[GaussianModel] ${this.name} Time update mode set to: ${e}`)) : console.warn(`[GaussianModel] ${this.name} does not support time update mode (not a dynamic model)`);
  }
  /**
   * Set render mode for the model
   * @param mode - Render mode (0=color, 1=normal, 2=depth)
   */
  setRenderMode(e) {
    this.isGaussianModel() && (this.mEntry.pointCloud.setRenderMode(e), console.log(`[GaussianModel] ${this.name} Render mode set to: ${e}`));
  }
  /** Get current render mode */
  getRenderMode() {
    if (this.isGaussianModel()) {
      const e = this.mEntry.pointCloud;
      if (typeof e.getRenderMode == "function")
        return e.getRenderMode();
    }
    return 0;
  }
  /**
   * Get current time update mode
   * @returns Current time update mode
   */
  getTimeUpdateMode() {
    return this.mEntry.pointCloud && "getTimeUpdateMode" in this.mEntry.pointCloud ? this.mEntry.pointCloud.getTimeUpdateMode() : "fixed_delta";
  }
  /**
   * Start animation for dynamic models
   * @param speed - Animation speed multiplier
   */
  startAnimation(e = 1) {
    this.mEntry.pointCloud && "startAnimation" in this.mEntry.pointCloud ? (this.mEntry.pointCloud.startAnimation(e), console.log(`[GaussianModel] ${this.name} Animation started at ${e}x speed`)) : console.warn(`[GaussianModel] ${this.name} does not support animation (not a dynamic model)`);
  }
  /**
   * Pause animation for dynamic models
   */
  pauseAnimation() {
    this.mEntry.pointCloud && "pauseAnimation" in this.mEntry.pointCloud ? (this.mEntry.pointCloud.pauseAnimation(), console.log(`[GaussianModel] ${this.name} Animation paused`)) : console.warn(`[GaussianModel] ${this.name} does not support animation (not a dynamic model)`);
  }
  /**
   * Resume animation for dynamic models
   */
  resumeAnimation() {
    this.mEntry.pointCloud && "resumeAnimation" in this.mEntry.pointCloud ? (this.mEntry.pointCloud.resumeAnimation(), console.log(`[GaussianModel] ${this.name} Animation resumed`)) : console.warn(`[GaussianModel] ${this.name} does not support animation (not a dynamic model)`);
  }
  /**
   * Stop animation for dynamic models
   */
  stopAnimation() {
    this.mEntry.pointCloud && "stopAnimation" in this.mEntry.pointCloud ? (this.mEntry.pointCloud.stopAnimation(), console.log(`[GaussianModel] ${this.name} Animation stopped`)) : console.warn(`[GaussianModel] ${this.name} does not support animation (not a dynamic model)`);
  }
  /**
   * Set animation time for dynamic models
   * @param time - Animation time in seconds
   */
  setAnimationTime(e) {
    this.mEntry.pointCloud && "setAnimationTime" in this.mEntry.pointCloud ? (this.mEntry.pointCloud.setAnimationTime(e), console.log(`[GaussianModel] ${this.name} Animation time set to ${e.toFixed(3)}s`)) : console.warn(`[GaussianModel] ${this.name} does not support animation (not a dynamic model)`);
  }
  /**
   * Set animation speed for dynamic models
   * @param speed - Animation speed multiplier
   */
  setAnimationSpeed(e) {
    this.mEntry.pointCloud && "setAnimationSpeed" in this.mEntry.pointCloud ? (this.mEntry.pointCloud.setAnimationSpeed(e), console.log(`[GaussianModel] ${this.name} Animation speed set to ${e}x`)) : console.warn(`[GaussianModel] ${this.name} does not support animation (not a dynamic model)`);
  }
  /**
   * Get animation speed for dynamic models
   * @returns Current animation speed
   */
  getAnimationSpeed() {
    return this.mEntry.pointCloud && "getAnimationSpeed" in this.mEntry.pointCloud ? this.mEntry.pointCloud.getAnimationSpeed() : 1;
  }
  /**
   * Check if animation is running for dynamic models
   * @returns True if animation is running
   */
  isAnimationRunning() {
    return this.mEntry.pointCloud && "isAnimationRunning" in this.mEntry.pointCloud ? this.mEntry.pointCloud.isAnimationRunning : !1;
  }
  /**
   * Check if animation is paused for dynamic models
   * @returns True if animation is paused
   */
  isAnimationPaused() {
    return this.mEntry.pointCloud && "isAnimationPaused" in this.mEntry.pointCloud ? this.mEntry.pointCloud.isAnimationPaused : !1;
  }
}
class ce {
  constructor(e, t) {
    this.fileLoader = e, this.onnxManager = t;
  }
  /**
   * Create GaussianModel from Gaussian format file (PLY, SPZ, KSplat, SPLAT, SOG, etc.)
   * @param renderer - Three.js WebGPU renderer
   * @param modelPath - Path to Gaussian format file
   * @param options - Optional loading options
   * @returns GaussianModel instance
   */
  async createFromGaussian(e, t, o, s) {
    const n = e.backend.device, a = C(t);
    console.log(`[GaussianLoader] Loading ${a?.toUpperCase() || "GAUSSIAN"} file:`, t);
    const r = await this.fileLoader.loadSample(
      t,
      n,
      s || "gaussian"
    );
    if (!r)
      throw new Error(`Failed to load Gaussian file: ${t}`);
    return o?.name && (r.name = o.name), new L(r);
  }
  /**
   * Create GaussianModel from PLY file
   * @param renderer - Three.js WebGPU renderer
   * @param modelPath - Path to PLY file
   * @param options - Optional loading options
   * @returns GaussianModel instance
   */
  async createFromPLY(e, t, o) {
    const s = e.backend.device, n = await this.fileLoader.loadSample(t, s, "ply");
    if (!n)
      throw new Error(`Failed to load PLY file: ${t}`);
    return o?.name && (n.name = o.name), new L(n);
  }
  /**
   * Create GaussianModel from SPZ file
   */
  async createFromSPZ(e, t, o) {
    return this.createFromGaussian(e, t, o);
  }
  /**
   * Create GaussianModel from KSplat file
   */
  async createFromKSplat(e, t, o) {
    return this.createFromGaussian(e, t, o);
  }
  /**
   * Create GaussianModel from SPLAT file
   */
  async createFromSplat(e, t, o) {
    return this.createFromGaussian(e, t, o);
  }
  /**
   * Create GaussianModel from SOG file
   */
  async createFromSOG(e, t, o) {
    return this.createFromGaussian(e, t, o);
  }
  /**
   * Create GaussianModel from ONNX file
   * @param renderer - Three.js WebGPU renderer
   * @param modelPath - Path to ONNX file
   * @param cameraMatrix - Initial camera view matrix
   * @param projectionMatrix - Initial projection matrix
   * @param options - Optional loading options
   * @returns GaussianModel instance
   */
  async createFromONNX(e, t, o, s, n) {
    const a = e.backend.device, r = {
      staticInference: !1,
      // Default to dynamic mode
      debugLogging: !0,
      ...n?.onnxOptions
    }, i = await this.onnxManager.loadONNXModel(
      a,
      t,
      o,
      s,
      n?.name,
      r
    );
    return new L(i);
  }
  /**
   * Auto-detect file type and create GaussianModel
   * Uses FileLoader's detection logic
   * @param renderer - Three.js WebGPU renderer
   * @param modelPath - Path to model file
   * @param cameraMatrices - Camera matrices (required for ONNX)
   * @param options - Optional loading options
   * @param fileType - Optional explicit file type
   * @returns GaussianModel instance
   */
  async createFromFile(e, t, o, s, n) {
    const a = n || this.fileLoader.getFileType(t);
    if (a === "ply")
      return this.createFromPLY(e, t, s);
    if (a === "onnx") {
      if (!o)
        throw new Error(`ONNX file ${t} requires camera matrices`);
      return this.createFromONNX(
        e,
        t,
        o.camMat,
        o.projMat,
        s
      );
    }
    if (["gaussian", "sog", "splat", "ksplat", "spz", "compressed.ply"].includes(a))
      return this.createFromGaussian(e, t, s, a);
    throw new Error(`Unsupported file type: ${a}`);
  }
  /**
   * Create GaussianModel from existing ModelEntry
   * Useful when you already have a ModelEntry from other sources
   */
  createFromEntry(e) {
    return new L(e);
  }
  /**
   * Check if a file format is supported
   */
  isFormatSupported(e) {
    return this.fileLoader.isFileTypeSupported(e);
  }
  /**
   * Get supported file formats
   */
  getSupportedFormats() {
    return this.fileLoader.getSupportedExtensions();
  }
  /**
   * Detect the Gaussian format of a file
   */
  detectFormat(e) {
    return this.fileLoader.getGaussianFormat(e);
  }
}
class ue {
  camera = null;
  controller;
  controllerType = "fps";
  canvasElement = null;
  constructor(e = "orbit") {
    this.controllerType = e, this.controller = this.createController(e);
  }
  createController(e) {
    return e === "orbit" ? new G() : new I();
  }
  /**
   * Initialize camera with default settings
   */
  initCamera(e) {
    this.canvasElement = e;
    const t = 45, o = x(t), s = e.width || 1, n = e.height || 1, a = s / n, r = x(t / a);
    this.camera = new U(
      c.fromValues(0, 0, 3),
      f.fromValues(0, 0, 0, 1),
      new W(
        [s, n],
        [o, r],
        // Use aspect-corrected Y FOV
        0.01,
        2e3
      )
    ), console.log(`📷 Camera initialized: ${s}x${n}, aspect: ${a.toFixed(2)}, FOV: [${(o * 180 / Math.PI).toFixed(1)}°, ${(r * 180 / Math.PI).toFixed(1)}°]`);
  }
  /**
   * Reset camera to default position
   */
  resetCamera() {
    if (!this.camera || !this.canvasElement) {
      console.warn("⚠️ Camera or canvas not available for reset");
      return;
    }
    this.camera = new U(
      c.fromValues(0, 0, 3),
      f.fromValues(0, 0, 0, 1),
      this.camera.projection.clone()
    ), this.controller = this.createController(this.controllerType), this.controller.resetOrientation && this.controller.resetOrientation(), console.log("📷 Camera reset to default position");
  }
  /**
   * Position camera based on point cloud bounds
   */
  setupCameraForPointCloud(e) {
    if (!this.camera || !this.canvasElement) {
      console.warn("⚠️ Camera or canvas not available for point cloud setup");
      return;
    }
    const t = e.bbox, o = t.center(), s = t.radius(), n = c.fromValues(
      o[0] - s * 0.5,
      o[1] - s * 0.5,
      o[2] - s * 0.5
    ), a = f.fromValues(0, 0, 0, 1), r = this.canvasElement.width / this.canvasElement.height, i = new W(
      [this.canvasElement.width, this.canvasElement.height],
      [x(45), x(45 / r)],
      0.01,
      1e3
    );
    this.camera = new U(n, a, i), this.controllerType === "orbit" && this.controller instanceof G && (c.copy(this.controller.center, o), c.set(this.controller.rotation, 0, 0, 0), z.set(this.controller.shift, 0, 0), this.controller.scroll = 0), console.log(`📷 Camera positioned for point cloud: radius=${s.toFixed(2)}, center=[${o[0].toFixed(2)}, ${o[1].toFixed(2)}, ${o[2].toFixed(2)}]`);
  }
  /**
   * Handle canvas resize
   */
  resize(e) {
    const t = window.devicePixelRatio || 1, o = e.getBoundingClientRect(), s = Math.max(1, Math.floor(o.width * t)), n = Math.max(1, Math.floor(o.height * t));
    let a = !1;
    (e.width !== s || e.height !== n) && (e.width = s, e.height = n, a = !0), this.camera && a && (this.camera.projection.resize([s, n]), console.log(`📷 Camera resized: ${s}x${n} (dpr: ${t.toFixed(2)})`)), this.canvasElement = e;
  }
  /**
   * Update camera with controller input
   */
  update(e) {
    this.camera && this.controller.update(this.camera, e);
  }
  /**
   * Get current camera matrix for ONNX input
   */
  getCameraMatrix() {
    return this.camera ? this.camera.viewMatrix() : (console.warn("⚠️ Camera not available, returning identity matrix"), p.create());
  }
  /**
   * Get current projection matrix for ONNX input
   */
  getProjectionMatrix() {
    if (!this.camera) {
      console.warn("⚠️ Camera not available, returning default projection matrix");
      const e = p.create();
      return p.perspective(e, Math.PI / 4, 16 / 9, 0.1, 1e3), e;
    }
    return this.camera.projMatrix();
  }
  /**
   * Get the camera instance
   */
  getCamera() {
    return this.camera;
  }
  /**
   * Get the camera controller
   */
  getController() {
    return this.controller;
  }
  /**
   * Switch between controller types
   */
  switchController(e) {
    if (e === this.controllerType) return;
    console.log(`🎮 Switching from ${this.controllerType} to ${e} controller`);
    const t = this.camera ? c.clone(this.camera.positionV) : c.fromValues(0, 0, 3), o = this.camera ? f.clone(this.camera.rotationQ) : f.fromValues(0, 0, 0, 1), s = this.controllerType;
    if (this.controllerType = e, this.controller = this.createController(e), this.camera)
      if (s === "fps" && e === "orbit") {
        const n = f.invert(f.create(), o), a = c.transformQuat(c.create(), c.fromValues(0, 0, -1), n);
        let r = 5;
        const i = c.length(t);
        i > 10 && (r = i * 0.5);
        const l = c.create();
        c.scaleAndAdd(l, t, a, r), this.controller instanceof G && (c.copy(this.controller.center, l), c.set(this.controller.rotation, 0, 0, 0), z.set(this.controller.shift, 0, 0), this.controller.scroll = 0), c.copy(this.camera.positionV, t), f.copy(this.camera.rotationQ, o);
      } else if (s === "orbit" && e === "fps") {
        const n = f.invert(f.create(), o), a = c.transformQuat(c.create(), c.fromValues(0, 0, -1), n), r = Math.atan2(a[0], a[2]), i = Math.sqrt(a[0] * a[0] + a[2] * a[2]), l = Math.atan2(-a[1], i);
        this.controller instanceof I && (this.controller.setOrientation(r, l), this.controller.leftMousePressed = !1, this.controller.rightMousePressed = !1), c.copy(this.camera.positionV, t), f.copy(this.camera.rotationQ, o);
      } else
        c.copy(this.camera.positionV, t), f.copy(this.camera.rotationQ, o);
    console.log(`✅ Controller switched to ${e}`);
  }
  /**
   * Get current controller type
   */
  getControllerType() {
    return this.controllerType;
  }
  /**
   * Check if camera is initialized
   */
  isInitialized() {
    return this.camera !== null;
  }
  /**
   * Get camera position
   */
  getCameraPosition() {
    return this.camera ? c.clone(this.camera.positionV) : null;
  }
  /**
   * Get camera rotation
   */
  getCameraRotation() {
    return this.camera ? f.clone(this.camera.rotationQ) : null;
  }
  /**
   * Set camera position
   */
  setCameraPosition(e) {
    this.camera && (c.copy(this.camera.positionV, e), console.log(`📷 Camera position set: [${e[0].toFixed(2)}, ${e[1].toFixed(2)}, ${e[2].toFixed(2)}]`));
  }
  /**
   * Set camera rotation
   */
  setCameraRotation(e) {
    this.camera && (f.copy(this.camera.rotationQ, e), console.log("📷 Camera rotation set"));
  }
  /**
   * Get camera viewport information
   */
  getViewportInfo() {
    if (!this.canvasElement)
      return null;
    const e = this.canvasElement.width, t = this.canvasElement.height, o = e / t;
    return { width: e, height: t, aspect: o };
  }
  /**
   * Get camera frustum information
   */
  getFrustumInfo() {
    return this.camera ? { fov: this.camera.projection.fovy || x(45), near: 0.01, far: 2e3 } : null;
  }
  /**
   * Set orbit controller center point
   */
  setOrbitCenter(e) {
    this.controllerType === "orbit" && this.controller instanceof G && (c.copy(this.controller.center, e), console.log(`📷 Orbit center set to: [${e[0].toFixed(2)}, ${e[1].toFixed(2)}, ${e[2].toFixed(2)}]`));
  }
  /**
   * Get orbit controller center point
   */
  getOrbitCenter() {
    return this.controllerType === "orbit" && this.controller instanceof G ? c.clone(this.controller.center) : null;
  }
  /**
   * Get camera debug info
   */
  getDebugInfo() {
    if (!this.camera) return null;
    const e = this.getCameraPosition(), t = this.getCameraRotation(), o = this.getViewportInfo(), s = this.getFrustumInfo();
    return {
      position: e ? [e[0], e[1], e[2]] : null,
      rotation: t ? [t[0], t[1], t[2], t[3]] : null,
      viewport: o,
      frustum: s,
      initialized: this.isInitialized(),
      controllerType: this.controllerType,
      orbitCenter: this.getOrbitCenter()
    };
  }
}
class he {
  modelManager;
  // Update tracking
  lastUpdateTime = 0;
  minUpdateInterval = 16;
  // ~60 FPS max
  forceNextUpdate = !1;
  // Performance metrics
  updateCount = 0;
  totalUpdateTime = 0;
  debugLogging = !1;
  constructor(e) {
    this.modelManager = e;
  }
  /**
   * Update all dynamic point clouds with current camera and time
   */
  // 在 AnimationManager 里加一个字段
  _frameUpdating = !1;
  updateDynamicPointClouds(e, t, o) {
    this._frameUpdating = !0;
    const s = this.modelManager.getDynamicModels().filter((i) => i.visible);
    if (s.length === 0)
      return this._frameUpdating = !1, Promise.resolve();
    const n = performance.now(), a = (i) => {
      if (!(i.pointCloud instanceof v))
        return Promise.resolve();
      const l = i.pointCloud, u = l.transform || new Float32Array([
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
      return l.update(e, u, o, t).catch((m) => {
        console.warn(`⚠️ Failed to update dynamic model '${i.name}':`, m);
      });
    };
    return s.reduce(
      (i, l) => i.then(() => a(l)),
      Promise.resolve()
    ).then(() => {
      this.lastUpdateTime = performance.now(), this.updateCount++;
      const i = this.lastUpdateTime - n;
      if (this.totalUpdateTime += i, this.debugLogging && this.updateCount % 60 === 0) {
        const l = this.totalUpdateTime / this.updateCount;
        console.log(`📊 Animation update #${this.updateCount}: ${s.length} models, avg: ${l.toFixed(2)}ms`);
      }
    }).finally(() => {
      this._frameUpdating = !1;
    });
  }
  /**
   * Control animation for all dynamic models
   */
  controlDynamicAnimation(e, t) {
    const o = this.modelManager.getDynamicModels();
    let s = 0;
    o.forEach((a) => {
      if (!(a.pointCloud instanceof v)) return;
      const r = a.pointCloud;
      switch (e) {
        case "start":
          r.startAnimation(t || 1), s++;
          break;
        case "pause":
          r.pauseAnimation(), s++;
          break;
        case "resume":
          r.resumeAnimation(), s++;
          break;
        case "stop":
          r.stopAnimation(), s++;
          break;
      }
    });
    const n = t ? ` at ${t}x speed` : "";
    console.log(`🎬 Animation ${e}${n} for ${s} dynamic models`);
  }
  /**
   * Set animation time for all dynamic models
   */
  setDynamicAnimationTime(e) {
    const t = this.modelManager.getDynamicModels();
    let o = 0;
    t.forEach((s) => {
      if (!(s.pointCloud instanceof v)) return;
      s.pointCloud.setAnimationTime(e), o++;
    }), console.log(`⏰ Set animation time to ${e.toFixed(3)} for ${o} dynamic models`);
  }
  /**
   * Get performance statistics for all dynamic models
   */
  getDynamicPerformanceStats() {
    return this.modelManager.getDynamicModels().filter((e) => e.pointCloud instanceof v).map((e) => ({
      modelName: e.name,
      stats: e.pointCloud.getPerformanceStats()
    }));
  }
  /**
   * Get overall animation statistics
   */
  getAnimationStats() {
    const e = this.modelManager.getDynamicModels(), t = e.filter((o) => o.visible);
    return {
      updateCount: this.updateCount,
      averageUpdateTime: this.updateCount > 0 ? this.totalUpdateTime / this.updateCount : 0,
      lastUpdateTime: this.lastUpdateTime,
      totalDynamicModels: e.length,
      activeDynamicModels: t.length
    };
  }
  /**
   * Reset performance statistics
   */
  resetPerformanceStats() {
    this.updateCount = 0, this.totalUpdateTime = 0, this.lastUpdateTime = 0, console.log("📊 Animation performance stats reset");
  }
  /**
   * Force next update regardless of interval
   */
  forceUpdate() {
    this.forceNextUpdate = !0;
  }
  /**
   * Set minimum update interval (in milliseconds)
   */
  setUpdateInterval(e) {
    this.minUpdateInterval = Math.max(1, e), console.log(`⏱️ Animation update interval set to ${this.minUpdateInterval}ms`);
  }
  /**
   * Get minimum update interval
   */
  getUpdateInterval() {
    return this.minUpdateInterval;
  }
  /**
   * Enable/disable debug logging
   */
  setDebugLogging(e) {
    this.debugLogging = e, console.log(`🐛 Animation debug logging ${e ? "enabled" : "disabled"}`);
  }
  /**
   * Check if updates are needed (throttling)
   */
  shouldUpdate() {
    return this.forceNextUpdate ? !0 : performance.now() - this.lastUpdateTime >= this.minUpdateInterval;
  }
  /**
   * Get all dynamic models (convenience method)
   */
  getDynamicModels() {
    return this.modelManager.getDynamicModels();
  }
  /**
   * Check if any dynamic models are active
   */
  hasDynamicModels() {
    return this.getDynamicModels().length > 0;
  }
  /**
   * Get count of active dynamic models
   */
  getActiveDynamicModelCount() {
    return this.modelManager.getDynamicModels().filter((e) => e.visible).length;
  }
  /**
   * Pause all animations
   */
  pauseAll() {
    this.controlDynamicAnimation("pause");
  }
  /**
   * Resume all animations
   */
  resumeAll() {
    this.controlDynamicAnimation("resume");
  }
  /**
   * Stop all animations
   */
  stopAll() {
    this.controlDynamicAnimation("stop");
  }
  /**
   * Start all animations
   */
  startAll(e = 1) {
    this.controlDynamicAnimation("start", e);
  }
  /**
   * Get animation debug info
   */
  getDebugInfo() {
    const e = this.getAnimationStats(), t = this.getDynamicPerformanceStats();
    return {
      stats: e,
      performanceStats: t,
      settings: {
        minUpdateInterval: this.minUpdateInterval,
        debugLogging: this.debugLogging,
        forceNextUpdate: this.forceNextUpdate
      },
      dynamicModels: this.getDynamicModels().map((o) => ({
        name: o.name,
        visible: o.visible,
        pointCount: o.pointCount,
        isAnimating: o.pointCloud instanceof v ? o.pointCloud.isAnimationRunning : !1
      }))
    };
  }
}
class me {
  modelManager;
  animationManager;
  cameraManager;
  renderer = null;
  gpu = null;
  canvas = null;
  startTime = performance.now();
  // Render state
  state = {
    background: [0, 0, 0, 1],
    gaussianScale: 1,
    animationId: 0,
    lastTime: performance.now(),
    frames: 0,
    fpsAccumStart: performance.now()
  };
  // Callbacks
  callbacks = {};
  isRunning = !1;
  constructor(e, t, o) {
    this.modelManager = e, this.animationManager = t, this.cameraManager = o;
  }
  /**
   * Initialize the render loop with GPU context and renderer
   */
  init(e, t, o) {
    this.gpu = e, this.renderer = t, this.canvas = o, console.log("🎬 RenderLoop initialized");
  }
  /**
   * Start the render loop
   */
  start() {
    if (this.isRunning) {
      console.warn("RenderLoop already running");
      return;
    }
    this.isRunning = !0, this.state.lastTime = performance.now(), this.state.fpsAccumStart = performance.now(), this.state.frames = 0, this.state.animationId = requestAnimationFrame(() => this.frame()), console.log("RenderLoop started");
  }
  /**
   * Stop the render loop
   */
  stop() {
    if (!this.isRunning) {
      console.warn("RenderLoop not running");
      return;
    }
    this.isRunning = !1, this.state.animationId && (cancelAnimationFrame(this.state.animationId), this.state.animationId = 0), console.log("RenderLoop stopped");
  }
  /**
   * Main render loop frame
   */
  async frame() {
    if (!this.isRunning) return;
    if (!this.gpu || !this.renderer || !this.cameraManager.isInitialized()) {
      this.state.animationId = requestAnimationFrame(() => this.frame());
      return;
    }
    const e = performance.now(), t = Math.min(0.05, (e - this.state.lastTime) / 1e3);
    this.state.lastTime = e;
    const o = e - this.startTime;
    this.cameraManager.update(t), await this.animationManager.updateDynamicPointClouds(
      this.cameraManager.getCameraMatrix(),
      this.cameraManager.getProjectionMatrix(),
      o / 500
    ), this.updateFPS(e), this.renderFrame(), this.isRunning && (this.state.animationId = requestAnimationFrame(() => this.frame()));
  }
  /**
   * Render a single frame
   */
  renderFrame() {
    if (!this.gpu || !this.renderer || !this.canvas) return;
    const e = this.cameraManager.getCamera();
    if (!e) return;
    const t = this.modelManager.getVisibleModels();
    if (t.length === 0) return;
    const o = this.gpu.device.createCommandEncoder({ label: "frame" }), s = this.gpu.context.getCurrentTexture().createView(), n = t.map((r) => r.pointCloud);
    this.renderer.prepareMulti(o, this.gpu.device.queue, n, {
      camera: e,
      viewport: [this.canvas.width, this.canvas.height],
      gaussianScaling: this.state.gaussianScale
    });
    const a = o.beginRenderPass({
      colorAttachments: [{
        view: s,
        clearValue: {
          r: this.state.background[0],
          g: this.state.background[1],
          b: this.state.background[2],
          a: this.state.background[3]
        },
        loadOp: "clear",
        storeOp: "store"
      }]
    });
    this.renderer.renderMulti(a, n), a.end(), this.gpu.device.queue.submit([o.finish()]);
  }
  /**
   * Update FPS counter and point count
   */
  updateFPS(e) {
    if (this.state.frames++, e - this.state.fpsAccumStart >= 1e3) {
      const t = Math.round(this.state.frames * 1e3 / (e - this.state.fpsAccumStart));
      this.callbacks.onFPSUpdate && this.callbacks.onFPSUpdate(t), this.updatePointStats(), this.state.frames = 0, this.state.fpsAccumStart = e;
    }
  }
  /**
   * Update point count display
   */
  updatePointStats() {
    const e = this.modelManager.getTotalVisiblePoints();
    this.callbacks.onPointCountUpdate && this.callbacks.onPointCountUpdate(e);
  }
  /**
   * Set render state
   */
  setBackgroundColor(e) {
    this.state.background = [...e];
  }
  /**
   * Set Gaussian scaling factor
   */
  setGaussianScale(e) {
    this.state.gaussianScale = e;
  }
  /**
   * Get render state
   */
  getState() {
    return { ...this.state };
  }
  /**
   * Set FPS and point count callbacks
   */
  setCallbacks(e) {
    this.callbacks = { ...this.callbacks, ...e };
  }
  /**
   * Force render of current frame (without animation loop)
   */
  renderOnce() {
    if (this.isRunning) {
      console.warn("Cannot render once while render loop is running");
      return;
    }
    console.warn("⚠️ Cannot render once while render loop is running"), this.renderFrame();
  }
  /**
   * Check if render loop is running
   */
  isActive() {
    return this.isRunning;
  }
  /**
   * Get current FPS (approximate)
   */
  getCurrentFPS() {
    const t = performance.now() - this.state.fpsAccumStart;
    return t === 0 ? 0 : Math.round(this.state.frames * 1e3 / t);
  }
  /**
   * Get frame count since start
   */
  getFrameCount() {
    return this.state.frames;
  }
  /**
   * Reset FPS counter
   */
  resetFPSCounter() {
    this.state.frames = 0, this.state.fpsAccumStart = performance.now();
  }
  /**
   * Get performance info
   */
  getPerformanceInfo() {
    const t = performance.now() - this.state.fpsAccumStart, o = this.getCurrentFPS(), s = this.state.frames > 0 ? t / this.state.frames : 0;
    return {
      fps: o,
      frameCount: this.state.frames,
      elapsedTime: t,
      averageFrameTime: s,
      isRunning: this.isRunning
    };
  }
  /**
   * Get render debug info
   */
  getDebugInfo() {
    const e = this.getPerformanceInfo(), t = this.modelManager.getVisibleModels();
    return {
      performance: e,
      state: this.getState(),
      models: {
        total: this.modelManager.getModelCount(),
        visible: t.length,
        dynamic: this.animationManager.getActiveDynamicModelCount(),
        totalPoints: this.modelManager.getTotalVisiblePoints()
      },
      renderer: {
        initialized: !!this.renderer,
        // @kangan 此接口无人实现，打包错误
        globalSorting: !1
        // this.renderer?.isGlobalSortingEnabled() || false
      },
      gpu: {
        initialized: !!this.gpu,
        device: !!this.gpu?.device
      }
    };
  }
}
const ge = 1e4;
class De {
  // Core components
  dom;
  gpu = null;
  renderer = null;
  uiController;
  // Managers
  modelManager;
  fileLoader;
  onnxManager;
  cameraManager;
  animationManager;
  renderLoop;
  constructor() {
    this.dom = new ne(), this.modelManager = new j(ge), this.cameraManager = new ue("orbit"), this.animationManager = new he(this.modelManager), this.renderLoop = new me(this.modelManager, this.animationManager, this.cameraManager);
    const e = {
      onProgress: (o, s, n) => this.showLoading(o, s, n),
      onError: (o) => this.showError(o)
    };
    this.fileLoader = new Y(this.modelManager, e), this.onnxManager = new H(this.modelManager);
    const t = {
      onFileLoad: (o) => this.loadFile(o)
    };
    this.uiController = new re(this.dom, this.cameraManager.getController(), t);
  }
  /**
   * Initialize the application
   */
  async init() {
    const e = se();
    if (oe(e), console.log(`[App] Initialized ORT environment with paths: ${e}`), !this.dom.canvas)
      throw new Error("Canvas element not found");
    try {
      const t = J;
      this.gpu = await B(this.dom.canvas, {
        dummyModelUrl: t,
        adapterPowerPreference: "high-performance",
        allowOwnDeviceWhenOrtPresent: !1
      }), console.log("[App] WebGPU initialized with ORT integration");
    } catch (t) {
      console.warn("[App] ORT integration failed, falling back to standalone WebGPU:", t), this.gpu = await B(this.dom.canvas, {
        preferShareWithOrt: !1,
        // Disable ORT sharing
        adapterPowerPreference: "high-performance"
      }), console.log("[App] WebGPU initialized in standalone mode");
    }
    if (!this.gpu) {
      D(this.dom.noWebGPU, !1);
      return;
    }
    this.renderer = new X(this.gpu.device, this.gpu.format, 3), await this.renderer.ensureSorter(), this.cameraManager.initCamera(this.dom.canvas), this.switchController("orbit"), this.uiController.bindEvents(this.dom.canvas), window.addEventListener("resize", () => this.resize()), this.resize(), this.renderLoop.init(this.gpu, this.renderer, this.dom.canvas), this.renderLoop.setCallbacks({
      onFPSUpdate: (t) => {
        this.dom.fpsEl && (this.dom.fpsEl.textContent = String(t));
      },
      onPointCountUpdate: (t) => {
        this.dom.pointCountEl && (this.dom.pointCountEl.textContent = String(t));
      }
    }), this.renderLoop.start(), console.log("[App] Initialized with multi-format support:", T.getAllSupportedExtensions());
  }
  /**
   * Unified model loading method (private implementation)
   * Now supports: PLY, SPZ, KSplat, SPLAT, SOG, compressed PLY, ONNX, and 3D models
   */
  async loadModel(e, t = {}) {
    if (!this.gpu) {
      this.showError("WebGPU not initialized");
      return;
    }
    try {
      const o = (e instanceof File ? e.name : e).toLowerCase(), s = t.expectedType ?? this.detectFileType(o);
      console.log(`[App] Loading ${s} file:`, o), s === "gaussian" ? await this.loadGaussianModel(e, t) : s === "onnx" ? await this.loadONNXModelInternal(e, t) : s === "model" ? await this.load3DModel(e, t) : this.showError(`Unsupported file type: ${o}
Supported formats: ${T.getAllSupportedExtensions().join(", ")}`);
    } catch (o) {
      const s = o;
      console.error("[App] Load error:", s), this.showError(`Failed to load file: ${s.message}`);
    }
  }
  /**
   * Load Gaussian Splatting models (PLY, SPZ, KSplat, SPLAT, SOG, etc.)
   * 
   * 注意：这个方法目前使用 defaultLoader 加载数据，然后委托给 FileLoader
   * 如果你的 FileLoader 还不支持 GaussianDataSource，
   * 这里会回退到使用原有的 FileLoader.loadFile/loadSample 方法
   */
  async loadGaussianModel(e, t = {}) {
    if (!this.gpu)
      throw new Error("WebGPU not initialized");
    const o = e instanceof File ? e.name : e;
    console.log(`[App] Loading Gaussian model: ${o}`), this.showLoading(!0, `Loading ${o}...`, 0);
    try {
      let s = null;
      if (e instanceof File ? s = await this.fileLoader.loadFile(e, this.gpu.device) : s = await this.fileLoader.loadSample(e, this.gpu.device, "ply"), s)
        this.setupCameraForFirstModel(s), this.resize(), this.showLoading(!1), console.log(`[App] Successfully loaded Gaussian model: ${o}`);
      else
        throw new Error("Failed to create model entry");
    } catch (s) {
      this.showLoading(!1);
      const n = s.message;
      if (n.includes("Unsupported") || n.includes("unknown")) {
        const a = C(o);
        if (a && a !== "ply") {
          console.warn(`[App] ${a.toUpperCase()} format detected but FileLoader may not support it yet`), this.showError(
            `The file appears to be a ${a.toUpperCase()} format.
Your FileLoader may need to be updated to support this format.
Currently only PLY format is fully supported in FileLoader.`
          );
          return;
        }
      }
      throw s;
    }
  }
  /**
   * Load ONNX models
   */
  async loadONNXModelInternal(e, t = {}) {
    if (!this.gpu)
      throw new Error("WebGPU not initialized");
    const { staticInference: o = !1, debugLogging: s = !1 } = t, n = {
      staticInference: o,
      debugLogging: s
    }, a = e instanceof File ? URL.createObjectURL(e) : e, r = e instanceof File ? e.name : "onnx model";
    console.log(`[App] Loading ONNX model: ${r}`);
    const i = await this.onnxManager.loadONNXModel(
      this.gpu.device,
      a,
      this.cameraManager.getCameraMatrix(),
      this.cameraManager.getProjectionMatrix(),
      r,
      n
    );
    i && (this.setupCameraForFirstModel(i), this.resize(), console.log(`[App] Successfully loaded ONNX model: ${r}`));
  }
  /**
   * Load 3D models (GLTF, OBJ, FBX, STL)
   */
  async load3DModel(e, t = {}) {
    throw new Error("3D model loading not yet implemented in this architecture");
  }
  /**
   * Detect file type from filename
   */
  detectFileType(e) {
    const t = e.toLowerCase();
    if (R(t))
      return "gaussian";
    if (t.endsWith(".onnx"))
      return "onnx";
    if ([".gltf", ".glb", ".obj", ".fbx", ".stl"].some((s) => t.endsWith(s)))
      return "model";
    if (t.endsWith(".ply"))
      return "gaussian";
    throw new Error(`Unable to detect file type for: ${e}`);
  }
  /**
   * Get format-specific information
   */
  getFormatInfo(e) {
    const t = this.detectFileType(e), o = t === "gaussian" ? C(e) : void 0;
    return { type: t, format: o ?? void 0 };
  }
  /**
   * Load a file using universal loader
   */
  async loadFile(e) {
    const { type: t, format: o } = this.getFormatInfo(e.name);
    console.log(`[App] Detected file type: ${t}${o ? ` (${o})` : ""}`), await this.loadModel(e, { expectedType: t, gaussianFormat: o });
  }
  /**
   * Load a sample file
   */
  async loadSample(e) {
    const { type: t, format: o } = this.getFormatInfo(e);
    console.log(`[App] Loading sample: ${e} (${t}${o ? `, ${o}` : ""})`), await this.loadModel(e, { expectedType: t, gaussianFormat: o });
  }
  /**
   * Load a Gaussian model (any supported format) - public API
   */
  async loadGaussian(e, t = {}) {
    await this.loadModel(e, { ...t, expectedType: "gaussian" });
  }
  /**
   * Load a PLY model specifically (backward compatibility)
   */
  async loadPLY(e, t = {}) {
    console.warn("[App] loadPLY is deprecated, use loadGaussian instead"), await this.loadGaussian(e, t);
  }
  /**
   * Load SPZ format specifically
   */
  async loadSPZ(e, t = {}) {
    await this.loadModel(e, { ...t, expectedType: "gaussian", gaussianFormat: $.SPZ });
  }
  /**
   * Load KSplat format specifically
   */
  async loadKSplat(e, t = {}) {
    await this.loadModel(e, { ...t, expectedType: "gaussian", gaussianFormat: $.KSPLAT });
  }
  /**
   * Load SPLAT format specifically
   */
  async loadSplat(e, t = {}) {
    await this.loadModel(e, { ...t, expectedType: "gaussian", gaussianFormat: $.SPLAT });
  }
  /**
   * Load SOG format specifically
   */
  async loadSOG(e, t = {}) {
    await this.loadModel(e, { ...t, expectedType: "gaussian", gaussianFormat: $.SOG });
  }
  /**
   * Setup camera for the first model if needed
   */
  setupCameraForFirstModel(e) {
    this.modelManager.getModelCount() === 1 && import("./visionary-core.src-point-cloud.js").then(({ PointCloud: t }) => {
      e.pointCloud instanceof t && this.cameraManager.setupCameraForPointCloud(e.pointCloud);
    });
  }
  /**
   * Handle canvas resize
   */
  resize() {
    this.dom.canvas && this.cameraManager.resize(this.dom.canvas);
  }
  /**
   * Load ONNX model (public API)
   */
  async loadONNXModel(e = "./models/gaussians3d.onnx", t, o = !0) {
    if (!this.gpu)
      throw new Error("App not initialized. Call init() first.");
    const s = {
      staticInference: o,
      debugLogging: !1
    }, n = await this.onnxManager.loadONNXModel(
      this.gpu.device,
      e,
      this.cameraManager.getCameraMatrix(),
      this.cameraManager.getProjectionMatrix(),
      t,
      s
    );
    n && (this.setupCameraForFirstModel(n), this.resize());
  }
  /**
   * Show loading overlay
   */
  showLoading(e, t, o) {
    this.dom.loadingOverlay && (D(this.dom.loadingOverlay, !e), t && this.dom.progressText && (this.dom.progressText.textContent = t), typeof o == "number" && this.dom.progressFill && (this.dom.progressFill.style.width = `${ae(o, 0, 100)}%`));
  }
  /**
   * Show error modal
   */
  showError(e) {
    console.error("[App] Error:", e), this.dom.errorMessage && (this.dom.errorMessage.textContent = e), this.dom.errorModal && D(this.dom.errorModal, !1);
  }
  // ==================== Public API (Delegated to Managers) ====================
  /**
   * Get information about supported formats
   */
  getSupportedFormats() {
    const e = T.getAllSupportedExtensions();
    return {
      gaussian: e.filter(
        (t) => [".ply", ".spz", ".ksplat", ".splat", ".sog", ".compressed.ply"].includes(t)
      ),
      onnx: [".onnx"],
      models: e.filter(
        (t) => [".gltf", ".glb", ".obj", ".fbx", ".stl"].includes(t)
      ),
      all: e
    };
  }
  /**
   * Check if a file is supported
   */
  isFileSupported(e) {
    try {
      return this.detectFileType(e), !0;
    } catch {
      return !1;
    }
  }
  /**
   * Get all loaded models information
   */
  getModels() {
    return this.modelManager.getModels();
  }
  /**
   * Get a model entry with full pointCloud reference for debugging/testing
   */
  getModelWithPointCloud(e, t) {
    return this.modelManager.getModelWithPointCloud(e, t);
  }
  /**
   * Get all model entries with full pointCloud references (for debugging/testing)
   */
  getFullModels() {
    return this.modelManager.getFullModels();
  }
  /**
   * Public API to load ONNX model (accessible from global scope)
   */
  async loadONNXModelPublic(e, t) {
    return this.loadONNXModel(e, t);
  }
  /**
   * Get current camera matrix for ONNX input
   */
  getCameraMatrix() {
    return this.cameraManager.getCameraMatrix();
  }
  /**
   * Get current projection matrix for ONNX input
   */
  getProjectionMatrix() {
    return this.cameraManager.getProjectionMatrix();
  }
  /**
   * Control animation for dynamic models
   */
  controlDynamicAnimation(e, t) {
    this.animationManager.controlDynamicAnimation(e, t);
  }
  /**
   * Set animation time for dynamic models
   */
  setDynamicAnimationTime(e) {
    this.animationManager.setDynamicAnimationTime(e);
  }
  /**
   * Get performance stats for dynamic models
   */
  getDynamicPerformanceStats() {
    return this.animationManager.getDynamicPerformanceStats();
  }
  /**
   * Reset camera to default position (public API for testing)
   */
  resetCamera() {
    this.cameraManager.resetCamera();
  }
  /**
   * Switch camera controller type
   */
  switchController(e) {
    if (e === "orbit" && this.modelManager.getModelCount() > 0) {
      const t = this.modelManager.getModels();
      let o = c.create(), s = 0;
      for (const n of t)
        if (n.visible) {
          const a = this.modelManager.getModelPosition(n.id);
          a && (c.add(o, o, a), s++);
        }
      if (s > 0) {
        const n = c.scale(c.create(), o, 1 / s);
        this.cameraManager.switchController(e), this.cameraManager.setOrbitCenter(n);
      } else
        this.cameraManager.switchController(e);
    } else
      this.cameraManager.switchController(e);
    this.uiController.controller = this.cameraManager.getController();
  }
  /**
   * Set Gaussian scaling factor (public API for testing)
   */
  setGaussianScale(e) {
    this.renderLoop.setGaussianScale(e);
  }
  /**
   * Set background color (public API for testing)
   */
  setBackgroundColor(e) {
    this.renderLoop.setBackgroundColor(e);
  }
  /**
   * Get current gaussian scale
   */
  getGaussianScale() {
    return this.renderLoop.getState().gaussianScale;
  }
  /**
   * Get current background color
   */
  getBackgroundColor() {
    return [...this.renderLoop.getState().background];
  }
  // ==================== Manager Access (for debugging/advanced usage) ====================
  /**
   * Get the model manager instance
   */
  getModelManager() {
    return this.modelManager;
  }
  /**
   * Get the ONNX manager instance
   */
  getONNXManager() {
    return this.onnxManager;
  }
  /**
   * Get the camera manager instance
   */
  getCameraManager() {
    return this.cameraManager;
  }
  /**
   * Get the animation manager instance
   */
  getAnimationManager() {
    return this.animationManager;
  }
  /**
   * Get the render loop instance
   */
  getRenderLoop() {
    return this.renderLoop;
  }
  /**
   * Get comprehensive debug information
   */
  getDebugInfo() {
    return {
      app: {
        initialized: !!this.gpu && !!this.renderer,
        canvas: {
          width: this.dom.canvas?.width || 0,
          height: this.dom.canvas?.height || 0
        },
        supportedFormats: this.getSupportedFormats()
      },
      models: {
        count: this.modelManager.getModelCount(),
        capacity: this.modelManager.getRemainingCapacity(),
        totalPoints: this.modelManager.getTotalPoints(),
        visiblePoints: this.modelManager.getTotalVisiblePoints()
      },
      camera: this.cameraManager.getDebugInfo(),
      animation: this.animationManager.getDebugInfo(),
      renderLoop: this.renderLoop.getDebugInfo(),
      onnx: {
        hasModels: this.onnxManager.hasONNXModels(),
        modelCount: this.onnxManager.getONNXModels().length,
        performanceStats: this.onnxManager.getONNXPerformanceStats()
      }
    };
  }
}
async function Oe(d) {
  const e = await B(d, {
    dummyModelUrl: J,
    // 关键：用 dummy 拉起 ORT 的 device
    adapterPowerPreference: "high-performance",
    // 可选
    allowOwnDeviceWhenOrtPresent: !1
  });
  if (!e)
    return Promise.reject("initWebGPU_onnx failed!");
  const t = new h.WebGPURenderer({
    canvas: d,
    antialias: !0,
    forceWebGL: !1,
    context: e.context,
    device: e.device
  });
  return await t.init(), t.setClearColor(new h.Color("#808080"), 1), t.setPixelRatio(Math.min(window.devicePixelRatio, 2)), t.setSize(d.clientWidth, d.clientHeight, !1), console.log("Init ThreeJS Successfully!", "Width:", d.clientWidth, "Height", d.clientHeight), t;
}
class pe extends h.Mesh {
  renderer;
  gaussianModels;
  pcs = null;
  // Three.js integration
  threeRenderer;
  threeScene;
  device;
  canvasFormat;
  // Depth capture from full scene (new architecture)
  sceneDepthRT = null;
  // Three.js scene renders here for depth
  sceneDepthTexture = null;
  autoDepthMode = !0;
  // Auto capture depth from full scene
  // Legacy occluder support (kept for compatibility)
  occluderMeshes = [];
  occluderScene = new h.Scene();
  // Gizmo overlay support
  gizmoOverlayRT = null;
  overlaySampler = null;
  overlayBindGroupLayout = null;
  overlayPipeline = null;
  overlayRenderedThisFrame = !1;
  constructor(e, t, o) {
    super(), this.frustumCulled = !1, this.threeRenderer = e, this.threeScene = t, this.device = e.backend.device;
    const s = navigator.gpu.getPreferredCanvasFormat();
    this.renderer = new X(this.device, s, 3), this.gaussianModels = o, this.canvasFormat = s;
  }
  onResize(e, t, o) {
  }
  /**
   * Render Three.js scene internally to capture depth
   * This replaces the manual renderer.render(scene, camera) in demo
   */
  renderThreeScene(e) {
    if (!this.autoDepthMode) return;
    const t = new h.Vector2();
    this.threeRenderer.getDrawingBufferSize?.(t);
    const o = t.x || this.threeRenderer.domElement.width || 1, s = t.y || this.threeRenderer.domElement.height || 1;
    (!this.sceneDepthRT || this.sceneDepthRT.width !== o || this.sceneDepthRT.height !== s) && (this.sceneDepthRT && this.sceneDepthRT.dispose(), this.sceneDepthRT = new h.RenderTarget(o, s, {
      format: h.RGBAFormat,
      type: h.HalfFloatType,
      // 16位浮点，支持可过滤采样，精度通常足够
      samples: 1,
      depthBuffer: !0
    }), this.sceneDepthRT.texture.colorSpace = h.LinearSRGBColorSpace, this.sceneDepthTexture = new h.DepthTexture(o, s, h.FloatType), this.sceneDepthRT.depthTexture = this.sceneDepthTexture), this.threeRenderer.setRenderTarget(this.sceneDepthRT), this.threeRenderer.clear(!0, !0, !1), this.threeRenderer.render(this.threeScene, e), this.threeRenderer.setRenderTarget(null), this.blitRenderTargetToCanvas(e);
  }
  /**
   * Blit RenderTarget color buffer to canvas using render pass
   * Uses a fullscreen quad shader to handle format conversion
   */
  blitRenderTargetToCanvas(e) {
    if (this.sceneDepthRT)
      try {
        const t = this.threeRenderer.backend?.device;
        if (!t) {
          console.warn("[Depth] No GPU device available for blit"), this.threeRenderer.render(this.threeScene, e);
          return;
        }
        const s = this.threeRenderer.domElement.getContext("webgpu");
        if (!s) {
          console.warn("[Depth] No WebGPU context available for blit"), this.threeRenderer.render(this.threeScene, e);
          return;
        }
        const n = s.getCurrentTexture(), a = n.createView(), i = this.threeRenderer.backend?.get?.(this.sceneDepthRT.texture), l = i?.texture;
        if (!l) {
          console.warn("[Depth] Could not access RT color texture for blit"), this.threeRenderer.render(this.threeScene, e);
          return;
        }
        const u = i?.format, m = n.format;
        globalThis.GS_DEPTH_DEBUG, this.blitWithRenderPass(t, l, a, this.sceneDepthRT.width, this.sceneDepthRT.height), globalThis.GS_DEPTH_DEBUG;
      } catch (t) {
        console.warn("[Depth] Blit with render pass failed, falling back to re-render:", t), this.threeRenderer.render(this.threeScene, e);
      }
  }
  /**
   * Blit using render pass with fullscreen quad shader
   * This handles format conversion reliably
   */
  blitWithRenderPass(e, t, o, s, n) {
    const a = e.createSampler({
      magFilter: "linear",
      minFilter: "linear",
      mipmapFilter: "linear"
      // 如果纹理有mipmap，使用线性过滤
      // 不使用anisotropic filtering，因为这是全屏blit，不需要
    }), r = e.createBindGroupLayout({
      entries: [{
        binding: 0,
        visibility: GPUShaderStage.FRAGMENT,
        texture: { viewDimension: "2d" }
      }, {
        binding: 1,
        visibility: GPUShaderStage.FRAGMENT,
        sampler: {}
      }]
    }), i = e.createBindGroup({
      layout: r,
      entries: [{
        binding: 0,
        resource: t.createView()
        // FloatType格式，提供高精度
      }, {
        binding: 1,
        resource: a
      }]
    }), l = e.createRenderPipeline({
      layout: e.createPipelineLayout({ bindGroupLayouts: [r] }),
      vertex: {
        module: e.createShaderModule({
          code: `
                        @vertex
                        fn vs_main(@builtin(vertex_index) vertexIndex: u32) -> @builtin(position) vec4f {
                            var pos = array<vec2f, 6>(
                                vec2f(-1.0, -1.0), vec2f(1.0, -1.0), vec2f(-1.0, 1.0),
                                vec2f(-1.0, 1.0),  vec2f(1.0, -1.0), vec2f(1.0, 1.0)
                            );
                            return vec4f(pos[vertexIndex], 0.0, 1.0);
                        }
                    `
        }),
        entryPoint: "vs_main"
      },
      fragment: {
        module: e.createShaderModule({
          code: `
                        @group(0) @binding(0) var sourceTexture: texture_2d<f32>;
                        @group(0) @binding(1) var sourceSampler: sampler;

                        // 线性空间到sRGB空间的转换函数（标准sRGB gamma校正）
                        fn linearToSRGB(linear: vec3<f32>) -> vec3<f32> {
                            return select(
                                linear * 12.92,
                                pow(max(linear, vec3<f32>(0.0)), vec3<f32>(1.0 / 2.4)) * 1.055 - 0.055,
                                linear > vec3<f32>(0.0031308)
                            );
                        }

                        @fragment
                        fn fs_main(@builtin(position) fragCoord: vec4f) -> @location(0) vec4f {
                            let texCoord = fragCoord.xy / vec2f(${s}.0, ${n}.0);
                            // RT使用HalfFloatType（16位浮点），存储的是线性空间的值
                            // HalfFloatType支持可过滤采样，精度通常足够保持高动态范围内容
                            let linearColor = textureSample(sourceTexture, sourceSampler, texCoord);
                            
                            // 关键修复：将线性空间的值转换为sRGB空间输出到canvas
                            // 使用HalfFloatType（16位浮点）支持WebGPU的过滤采样，避免验证错误
                            // 在输出时进行线性到sRGB的转换，确保颜色正确显示
                            let srgbColor = linearToSRGB(linearColor.rgb);
                            
                            return vec4<f32>(srgbColor, linearColor.a);
                        }
                    `
        }),
        entryPoint: "fs_main",
        targets: [{
          format: "bgra8unorm"
          // Canvas format (sRGB显示)
        }]
      },
      primitive: {
        topology: "triangle-list"
      }
    }), u = e.createCommandEncoder({ label: "RT-to-Canvas render pass" }), m = u.beginRenderPass({
      colorAttachments: [{
        view: o,
        loadOp: "clear",
        storeOp: "store",
        clearValue: { r: 0, g: 0, b: 0, a: 1 }
      }]
    });
    m.setPipeline(l), m.setBindGroup(0, i), m.draw(6, 1, 0, 0), m.end(), e.queue.submit([u.finish()]);
  }
  onBeforeRender(e, t, o, s, n, a) {
    if (!(o instanceof h.PerspectiveCamera) && o.type !== "PerspectiveCamera") {
      console.log("Only THREE.PerspectiveCamera is supported!", o);
      return;
    }
    const r = this.convertCamera(o, e), i = this.gaussianModels.filter((g) => g.isVisible(o));
    if (this.pcs = i.map((g) => g.getPointCloud()).filter(
      (g) => g && typeof g == "object" && ("numPoints" in g || "countBuffer" in g) && !("skeletalAnimation" in g || "fbxMesh" in g)
    ), !this.pcs || this.pcs.length === 0) {
      globalThis.GS_VIDEO_EXPORT_DEBUG && (console.warn("[GaussianThreeJSRenderer] onBeforeRender: 没有可见的高斯点云"), console.log("[GaussianThreeJSRenderer] - gaussianModels数量:", this.gaussianModels.length), console.log("[GaussianThreeJSRenderer] - visibleModels数量:", i.length), i.forEach((g, S) => {
        const y = g.getPointCloud();
        console.log(
          `[GaussianThreeJSRenderer] - 模型${S} getPointCloud返回类型:`,
          y.constructor.name,
          "is PointCloud:",
          y instanceof V,
          "is DynamicPointCloud:",
          y instanceof v,
          "is FBXModelWrapper:",
          y instanceof _
        );
      }));
      return;
    }
    i.forEach((g, S) => {
      g.syncTransformToGPU();
    });
    const l = e.backend.device, u = l.createCommandEncoder({ label: "frame" }), m = new h.Vector2();
    e.getDrawingBufferSize?.(m);
    const b = m.x || e.getSize(new h.Vector2()).x, w = m.y || e.getSize(new h.Vector2()).y;
    this.renderer.prepareMulti(u, l.queue, this.pcs, {
      camera: r,
      viewport: [b, w]
      // 不再需要全局 gaussianScaling，每个模型使用自己的参数
    }), l.queue.submit([u.finish()]), this.autoDepthMode && globalThis.GS_DEPTH_DEBUG;
  }
  drawSplats(e, t, o, s, n, a) {
    if (this.pcs == null || this.pcs.length === 0)
      return globalThis.GS_VIDEO_EXPORT_DEBUG && console.warn("[GaussianThreeJSRenderer] drawSplats: pcs为空或长度为0"), !1;
    if (!(o instanceof h.PerspectiveCamera) && o.type !== "PerspectiveCamera")
      return console.warn("drawSplats: Only THREE.PerspectiveCamera is supported!", o), !1;
    const r = e.backend.device, l = e.backend.context.getCurrentTexture().createView(), u = r.createCommandEncoder({ label: "GS-render" });
    let m;
    if (this.sceneDepthTexture) {
      const g = new h.Vector2();
      e.getDrawingBufferSize?.(g), g.x || e.getSize(new h.Vector2()).x, g.y || e.getSize(new h.Vector2()).y;
      try {
        const y = this.threeRenderer.backend?.get?.(this.sceneDepthTexture);
        globalThis.GS_DEPTH_DEBUG;
        const F = y?.texture, P = y?.format;
        F && P ? (this.renderer.setDepthFormat(P), m = F.createView(), globalThis.GS_DEPTH_DEBUG) : globalThis.GS_DEPTH_DEBUG && console.warn("[Depth] ⚠️ Could not access depth GPU texture from Three.js backend"), m && (this.renderer.setDepthEnabled(!0), globalThis.GS_DEPTH_DEBUG);
      } catch (S) {
        globalThis.GS_DEPTH_DEBUG && console.error("[Depth] ❌ Error accessing depth texture:", S);
      }
    } else
      this.renderer.setDepthEnabled(!1);
    const b = {
      colorAttachments: [{
        view: l,
        clearValue: { r: 0, g: 0, b: 0, a: 1 },
        loadOp: "load",
        storeOp: "store"
      }]
    };
    m ? b.depthStencilAttachment = {
      view: m,
      depthLoadOp: "load",
      // Always load depth from RT
      depthStoreOp: "store",
      depthClearValue: 1
    } : globalThis.GS_DEPTH_DEBUG && console.warn("[Depth] ⚠️ No depth view available - render pass has no depth attachment");
    const w = u.beginRenderPass(b);
    return this.renderer.renderMulti(w, this.pcs), w.end(), this.compositeOverlayToCanvas(r, u, l), r.queue.submit([u.finish()]), !0;
  }
  renderOverlayScene(e, t) {
    const [o, s] = this.getViewport();
    if (this.ensureGizmoOverlayRenderTarget(o, s), !this.gizmoOverlayRT) return;
    const n = this.threeRenderer.getRenderTarget(), a = new h.Color();
    this.threeRenderer.getClearColor?.(a);
    const r = this.threeRenderer.getClearAlpha?.() ?? 1;
    this.threeRenderer.setRenderTarget(this.gizmoOverlayRT), this.threeRenderer.setClearColor?.(new h.Color(0), 0), this.threeRenderer.clear(!0, !1, !1), this.threeRenderer.render(e, t), this.threeRenderer.setClearColor?.(a, r), this.threeRenderer.setRenderTarget(n), this.overlayRenderedThisFrame = !0;
  }
  ensureGizmoOverlayRenderTarget(e, t) {
    const o = Math.max(1, Math.floor(e)), s = Math.max(1, Math.floor(t));
    if (this.gizmoOverlayRT && this.gizmoOverlayRT.width === o && this.gizmoOverlayRT.height === s)
      return;
    this.gizmoOverlayRT && this.gizmoOverlayRT.dispose();
    const n = h.WebGPURenderTarget ?? h.WebGLRenderTarget ?? h.RenderTarget;
    this.gizmoOverlayRT = new n(o, s), this.gizmoOverlayRT && this.gizmoOverlayRT.texture && (this.gizmoOverlayRT.texture.colorSpace = h.SRGBColorSpace);
  }
  compositeOverlayToCanvas(e, t, o) {
    if (!this.overlayRenderedThisFrame || !this.gizmoOverlayRT)
      return;
    const a = this.threeRenderer.backend?.get?.(this.gizmoOverlayRT.texture)?.texture;
    if (!a) {
      this.overlayRenderedThisFrame = !1;
      return;
    }
    this.overlaySampler || (this.overlaySampler = e.createSampler({
      magFilter: "linear",
      minFilter: "linear"
    })), this.overlayBindGroupLayout || (this.overlayBindGroupLayout = e.createBindGroupLayout({
      entries: [
        {
          binding: 0,
          visibility: GPUShaderStage.FRAGMENT,
          texture: { viewDimension: "2d" }
        },
        {
          binding: 1,
          visibility: GPUShaderStage.FRAGMENT,
          sampler: {}
        }
      ]
    }));
    const r = e.createBindGroup({
      layout: this.overlayBindGroupLayout,
      entries: [
        { binding: 0, resource: a.createView() },
        { binding: 1, resource: this.overlaySampler }
      ]
    });
    if (!this.overlayPipeline) {
      const l = e.createShaderModule({
        code: `
                    struct VertexOutput {
                        @builtin(position) position : vec4f,
                        @location(0) uv : vec2f,
                    };

                    @vertex
                    fn vs_main(@builtin(vertex_index) vertexIndex : u32) -> VertexOutput {
                        var positions = array<vec2f, 6>(
                            vec2f(-1.0, -1.0), vec2f(1.0, -1.0), vec2f(-1.0, 1.0),
                            vec2f(-1.0, 1.0),  vec2f(1.0, -1.0), vec2f(1.0, 1.0)
                        );
                        var uvs = array<vec2f, 6>(
                            vec2f(0.0, 1.0), vec2f(1.0, 1.0), vec2f(0.0, 0.0),
                            vec2f(0.0, 0.0), vec2f(1.0, 1.0), vec2f(1.0, 0.0)
                        );

                        var output : VertexOutput;
                        output.position = vec4f(positions[vertexIndex], 0.0, 1.0);
                        output.uv = uvs[vertexIndex];
                        return output;
                    }

                    @group(0) @binding(0) var overlayTexture : texture_2d<f32>;
                    @group(0) @binding(1) var overlaySampler : sampler;

                    @fragment
                    fn fs_main(@location(0) uv : vec2f) -> @location(0) vec4f {
                        return textureSample(overlayTexture, overlaySampler, uv);
                    }
                `
      }), u = e.createPipelineLayout({ bindGroupLayouts: [this.overlayBindGroupLayout] });
      this.overlayPipeline = e.createRenderPipeline({
        layout: u,
        vertex: {
          module: l,
          entryPoint: "vs_main"
        },
        fragment: {
          module: l,
          entryPoint: "fs_main",
          targets: [
            {
              format: this.canvasFormat,
              blend: {
                color: {
                  srcFactor: "one",
                  dstFactor: "one-minus-src-alpha",
                  operation: "add"
                },
                alpha: {
                  srcFactor: "one",
                  dstFactor: "one-minus-src-alpha",
                  operation: "add"
                }
              }
            }
          ]
        },
        primitive: {
          topology: "triangle-list"
        }
      });
    }
    const i = t.beginRenderPass({
      colorAttachments: [
        {
          view: o,
          loadOp: "load",
          storeOp: "store"
        }
      ]
    });
    i.setPipeline(this.overlayPipeline), i.setBindGroup(0, r), i.draw(6, 1, 0, 0), i.end(), this.overlayRenderedThisFrame = !1;
  }
  async init() {
    await this.renderer.ensureSorter(), console.log("GaussianThreeJSRenderer.init() Done!");
  }
  /**
   * Set occluder meshes for depth rendering (DEPRECATED - use auto depth mode instead)
   * Calling this will disable auto depth mode
   */
  setOccluderMeshes(e) {
    console.warn("[GaussianThreeJSRenderer] setOccluderMeshes is deprecated. Auto depth mode captures the full scene automatically."), console.warn("[GaussianThreeJSRenderer] To use manual occluders, set autoDepthMode = false"), this.autoDepthMode = !1, this.occluderMeshes = e, this.occluderScene.clear(), e.forEach((t) => this.occluderScene.add(t));
  }
  /**
   * Enable or disable auto depth mode
   * Auto mode: Captures depth from full scene automatically
   * Manual mode: Requires setOccluderMeshes()
   */
  setAutoDepthMode(e) {
    this.autoDepthMode = e;
  }
  /**
   * Diagnostic: Check if depth is properly configured
   */
  diagnoseDepth() {
    console.group("[Depth Diagnostic]"), console.log("Auto depth mode:", this.autoDepthMode), console.log("Scene depth RT exists:", !!this.sceneDepthRT), console.log("Scene depth texture exists:", !!this.sceneDepthTexture), this.sceneDepthRT && (console.log("Scene depth RT size:", this.sceneDepthRT.width, "x", this.sceneDepthRT.height), console.log("Scene depth RT format:", this.sceneDepthRT.texture.format)), this.renderer && (console.log("GaussianRenderer depth enabled:", this.renderer.useDepth), console.log("GaussianRenderer depth format:", this.renderer.depthFormat)), console.groupEnd();
  }
  /**
   * Clean up depth resources
   */
  disposeDepthResources() {
    this.sceneDepthRT && (this.sceneDepthRT.dispose(), this.sceneDepthRT = null), this.sceneDepthTexture = null, globalThis.GS_DEPTH_DEBUG && console.log("[Depth] Cleaned up depth resources"), this.gizmoOverlayRT && (this.gizmoOverlayRT.dispose(), this.gizmoOverlayRT = null), this.overlayPipeline = null, this.overlayBindGroupLayout = null, this.overlaySampler = null, this.overlayRenderedThisFrame = !1;
  }
  getViewport() {
    const e = new h.Vector2();
    this.threeRenderer.getDrawingBufferSize?.(e);
    const t = e.x || (this.threeRenderer.domElement?.width ?? 0) || this.threeRenderer.getSize(new h.Vector2()).x, o = e.y || (this.threeRenderer.domElement?.height ?? 0) || this.threeRenderer.getSize(new h.Vector2()).y;
    return [t, o];
  }
  convertCamera(e, t) {
    const o = this.getViewport(), s = new k();
    return s.update(e, o), s;
  }
  /** 
  * Update all dynamic models with current camera and time
  */
  async updateDynamicModels(e, t) {
    const o = new k(), s = this.getViewport();
    o.update(e, s);
    const n = o.viewMatrix(), a = o.projMatrix();
    for (const r of this.gaussianModels)
      try {
        await r.update(n, t, a);
      } catch (i) {
        console.warn("Failed to update model:", i);
      }
  }
  // ==================== 3DGS Parameters Management ====================
  /**
   * Set Gaussian scaling for a specific model
   */
  setModelGaussianScale(e, t) {
    const o = parseInt(e.replace("model_", ""));
    o >= 0 && o < this.gaussianModels.length ? (this.gaussianModels[o].setGaussianScale(t), console.log(`[GaussianThreeJSRenderer] Model ${e} Gaussian scale set to: ${t}`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /**
   * Get Gaussian scale for a specific model
   */
  getModelGaussianScale(e) {
    const t = parseInt(e.replace("model_", ""));
    return t >= 0 && t < this.gaussianModels.length ? this.gaussianModels[t].getGaussianScale() : 1;
  }
  /** Get model visibility */
  getModelVisible(e) {
    const t = parseInt(e.replace("model_", ""));
    return t >= 0 && t < this.gaussianModels.length ? this.gaussianModels[t].getModelVisible() : !1;
  }
  /**
   * Set maximum spherical harmonics degree for a specific model
   */
  setModelMaxShDeg(e, t) {
    const o = parseInt(e.replace("model_", ""));
    o >= 0 && o < this.gaussianModels.length ? (this.gaussianModels[o].setMaxShDeg(t), console.log(`[GaussianThreeJSRenderer] Model ${e} Max SH degree set to: ${t}`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /** Get max SH degree for a specific model */
  getModelMaxShDeg(e) {
    const t = parseInt(e.replace("model_", ""));
    return t >= 0 && t < this.gaussianModels.length ? this.gaussianModels[t].getMaxShDeg() : 0;
  }
  /**
   * Set kernel size for a specific model
   */
  setModelKernelSize(e, t) {
    const o = parseInt(e.replace("model_", ""));
    o >= 0 && o < this.gaussianModels.length ? (this.gaussianModels[o].setKernelSize(t), console.log(`[GaussianThreeJSRenderer] Model ${e} Kernel size set to: ${t}`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /** Get kernel size for a specific model */
  getModelKernelSize(e) {
    const t = parseInt(e.replace("model_", ""));
    return t >= 0 && t < this.gaussianModels.length ? this.gaussianModels[t].getKernelSize() : 0;
  }
  /**
   * Set opacity scale for a specific model
   */
  setModelOpacityScale(e, t) {
    const o = parseInt(e.replace("model_", ""));
    o >= 0 && o < this.gaussianModels.length ? (this.gaussianModels[o].setOpacityScale(t), console.log(`[GaussianThreeJSRenderer] Model ${e} Opacity scale set to: ${t}`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /** Get opacity scale for a specific model */
  getModelOpacityScale(e) {
    const t = parseInt(e.replace("model_", ""));
    return t >= 0 && t < this.gaussianModels.length ? this.gaussianModels[t].getOpacityScale() : 1;
  }
  /**
   * Set cutoff scale for a specific model
   */
  setModelCutoffScale(e, t) {
    const o = parseInt(e.replace("model_", ""));
    o >= 0 && o < this.gaussianModels.length ? (this.gaussianModels[o].setCutoffScale(t), console.log(`[GaussianThreeJSRenderer] Model ${e} Cutoff scale set to: ${t}`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /** Get cutoff scale for a specific model */
  getModelCutoffScale(e) {
    const t = parseInt(e.replace("model_", ""));
    return t >= 0 && t < this.gaussianModels.length ? this.gaussianModels[t].getCutoffScale() : 1;
  }
  /**
   * Set time scale for a specific model
   */
  setModelTimeScale(e, t) {
    const o = parseInt(e.replace("model_", ""));
    o >= 0 && o < this.gaussianModels.length ? (this.gaussianModels[o].setTimeScale(t), console.log(`[GaussianThreeJSRenderer] Model ${e} Time scale set to: ${t}`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /**
   * Set time offset for a specific model
   */
  setModelTimeOffset(e, t) {
    const o = parseInt(e.replace("model_", ""));
    o >= 0 && o < this.gaussianModels.length ? (this.gaussianModels[o].setTimeOffset(t), console.log(`[GaussianThreeJSRenderer] Model ${e} Time offset set to: ${t}`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /**
   * Set time offset for a specific model
   */
  setModelAnimationIsLoop(e, t) {
    const o = parseInt(e.replace("model_", ""));
    o >= 0 && o < this.gaussianModels.length ? (this.gaussianModels[o].setAnimationIsLoop(t), console.log(`[GaussianThreeJSRenderer] Model ${e} Animation is loop set to: ${t}`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /**
   * Set time update mode for a specific model
   */
  setModelTimeUpdateMode(e, t) {
    const o = parseInt(e.replace("model_", ""));
    o >= 0 && o < this.gaussianModels.length ? (this.gaussianModels[o].setTimeUpdateMode(t), console.log(`[GaussianThreeJSRenderer] Model ${e} Time update mode set to: ${t}`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /**
   * Set render mode for a specific model
   */
  setModelRenderMode(e, t) {
    const o = parseInt(e.replace("model_", ""));
    o >= 0 && o < this.gaussianModels.length ? (this.gaussianModels[o].setRenderMode(t), console.log(`[GaussianThreeJSRenderer] Model ${e} Render mode set to: ${t}`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /** Get render mode for a specific model */
  getModelRenderMode(e) {
    const t = parseInt(e.replace("model_", ""));
    return t >= 0 && t < this.gaussianModels.length ? this.gaussianModels[t].getRenderMode() : 0;
  }
  /**
   * Start animation for a specific model
   */
  startModelAnimation(e, t = 1) {
    const o = parseInt(e.replace("model_", ""));
    o >= 0 && o < this.gaussianModels.length ? (this.gaussianModels[o].startAnimation(t), console.log(`[GaussianThreeJSRenderer] Model ${e} Animation started at ${t}x speed`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /**
   * Pause animation for a specific model
   */
  pauseModelAnimation(e) {
    const t = parseInt(e.replace("model_", ""));
    t >= 0 && t < this.gaussianModels.length ? (this.gaussianModels[t].pauseAnimation(), console.log(`[GaussianThreeJSRenderer] Model ${e} Animation paused`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /**
   * Resume animation for a specific model
   */
  resumeModelAnimation(e) {
    const t = parseInt(e.replace("model_", ""));
    t >= 0 && t < this.gaussianModels.length ? (this.gaussianModels[t].resumeAnimation(), console.log(`[GaussianThreeJSRenderer] Model ${e} Animation resumed`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /**
   * Stop animation for a specific model
   */
  stopModelAnimation(e) {
    const t = parseInt(e.replace("model_", ""));
    t >= 0 && t < this.gaussianModels.length ? (this.gaussianModels[t].stopAnimation(), console.log(`[GaussianThreeJSRenderer] Model ${e} Animation stopped`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /**
   * Set animation time for a specific model
   */
  setModelAnimationTime(e, t) {
    const o = parseInt(e.replace("model_", ""));
    o >= 0 && o < this.gaussianModels.length ? (this.gaussianModels[o].setAnimationTime(t), console.log(`[GaussianThreeJSRenderer] Model ${e} Animation time set to: ${t.toFixed(3)}s`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /**
   * Set animation speed for a specific model
   */
  setModelAnimationSpeed(e, t) {
    const o = parseInt(e.replace("model_", ""));
    o >= 0 && o < this.gaussianModels.length ? (this.gaussianModels[o].setAnimationSpeed(t), console.log(`[GaussianThreeJSRenderer] Model ${e} Animation speed set to: ${t}x`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /**
   * Get all model parameters
   */
  getModelParams() {
    const e = {
      models: {}
    };
    return this.gaussianModels.forEach((t, o) => {
      const s = `model_${o}`;
      e.models[s] = {
        id: s,
        name: t.name,
        visible: t.getModelVisible(),
        gaussianScale: t.getGaussianScale(),
        maxShDeg: t.getMaxShDeg(),
        kernelSize: t.getKernelSize(),
        opacityScale: t.getOpacityScale(),
        cutoffScale: t.getCutoffScale(),
        timeScale: t.getTimeScale(),
        timeOffset: t.getTimeOffset(),
        timeUpdateMode: t.getTimeUpdateMode(),
        animationSpeed: t.getAnimationSpeed(),
        isAnimationRunning: t.isAnimationRunning(),
        isAnimationPaused: t.isAnimationPaused()
      };
    }), e;
  }
  /**
   * 获取所有高斯模型
   * @returns 高斯模型数组的副本
   */
  getGaussianModels() {
    return [...this.gaussianModels];
  }
  /**
   * Append a GaussianModel at runtime
   */
  appendGaussianModel(e) {
    this.gaussianModels.push(e);
  }
  /**
   * Remove a GaussianModel by id (e.g., 'model_2')
   * Returns true if removed
   */
  removeModelById(e) {
    const t = parseInt(e.replace("model_", ""));
    if (isNaN(t) || t < 0 || t >= this.gaussianModels.length)
      return console.warn(`[GaussianThreeJSRenderer] removeModelById: invalid id ${e}`), !1;
    const o = this.gaussianModels[t];
    try {
      this.threeScene.remove(o), o.dispose?.();
    } catch (s) {
      console.warn("[GaussianThreeJSRenderer] Error removing model from scene:", s);
    }
    return this.gaussianModels.splice(t, 1), console.log(`[GaussianThreeJSRenderer] Removed ${e} (${o.name})`), !0;
  }
  /**
   * Set visibility for a specific model
   */
  setModelVisible(e, t) {
    const o = parseInt(e.replace("model_", ""));
    o >= 0 && o < this.gaussianModels.length ? (this.gaussianModels[o].setModelVisible(t), console.log(`[GaussianThreeJSRenderer] Model ${e} visible: ${t}`)) : console.warn(`[GaussianThreeJSRenderer] Model ${e} not found`);
  }
  /**
   * Reset all parameters to defaults
   */
  resetParameters() {
    this.gaussianModels.forEach((e) => {
      e.setGaussianScale(1), e.setMaxShDeg(3), e.setKernelSize(0.1), e.setOpacityScale(1), e.setCutoffScale(1), e.setTimeScale(1), e.setTimeOffset(0), e.setTimeUpdateMode("fixed_delta");
    }), console.log("[GaussianThreeJSRenderer] All parameters reset to defaults");
  }
  // ==================== Global Animation Controls ====================
  /** Set time scale for all models */
  setGlobalTimeScale(e) {
    this.gaussianModels.forEach((t) => t.setTimeScale(e)), console.log(`[GaussianThreeJSRenderer] Global time scale set: ${e}`);
  }
  /** Set time offset for all models */
  setGlobalTimeOffset(e) {
    this.gaussianModels.forEach((t) => t.setTimeOffset(e)), console.log(`[GaussianThreeJSRenderer] Global time offset set: ${e}`);
  }
  /** Set time update mode for all models */
  setGlobalTimeUpdateMode(e) {
    this.gaussianModels.forEach((t) => t.setTimeUpdateMode(e)), console.log(`[GaussianThreeJSRenderer] Global time update mode: ${e}`);
  }
  /** Start animation on all models */
  startAllAnimations(e = 1) {
    this.gaussianModels.forEach((t) => t.startAnimation(e)), console.log(`[GaussianThreeJSRenderer] All animations started at ${e}x`);
  }
  /** Pause animation on all models */
  pauseAllAnimations() {
    this.gaussianModels.forEach((e) => e.pauseAnimation()), console.log("[GaussianThreeJSRenderer] All animations paused");
  }
  /** Resume animation on all models */
  resumeAllAnimations() {
    this.gaussianModels.forEach((e) => e.resumeAnimation()), console.log("[GaussianThreeJSRenderer] All animations resumed");
  }
  /** Stop animation on all models */
  stopAllAnimations() {
    this.gaussianModels.forEach((e) => e.stopAnimation()), console.log("[GaussianThreeJSRenderer] All animations stopped");
  }
  /** Set animation time for all models */
  setAllAnimationTime(e) {
    this.gaussianModels.forEach((t) => t.setAnimationTime(e)), console.log(`[GaussianThreeJSRenderer] Global animation time set: ${e.toFixed(3)}s`);
  }
  /** Set animation speed for all models */
  setAllAnimationSpeed(e) {
    this.gaussianModels.forEach((t) => t.setAnimationSpeed(e)), console.log(`[GaussianThreeJSRenderer] Global animation speed set: ${e}x`);
  }
}
class fe {
  renderer;
  scene;
  gaussianLoader;
  fbxLoader;
  modelManager;
  constructor(e, t) {
    this.renderer = e, this.scene = t, this.modelManager = new j();
    const o = new Y(this.modelManager), s = new H(this.modelManager);
    this.gaussianLoader = new ce(o, s), this.fbxLoader = new q(this.modelManager);
  }
  detectFileType(e) {
    const t = e.toLowerCase();
    if (t.endsWith(".compressed.ply"))
      return "gaussian";
    const o = t.split(".").pop();
    return ["onnx", "sog", "ksplat", "splat", "spz"].includes(o || "") ? "gaussian" : o === "ply" ? "ply" : o === "fbx" ? "fbx" : o || "unknown";
  }
  async loadModel(e, t = {}) {
    try {
      const o = e instanceof File ? e.name : e, s = t.type || this.detectFileType(o);
      console.log(`开始加载模型: ${o}, 类型: ${s}`);
      let n = o.toLowerCase().split(".").pop(), a = n === "onnx";
      n === "ply" && (e instanceof File ? a = await this.is3dgsPly(e) : a = await this.isGaussianPlyUrl(e)), t.isGaussian = a;
      const r = await this.loadModelByType(e, s, t);
      return console.log(`模型加载完成: ${r.info.name}, 数量: ${r.info.count}`), r;
    } catch (o) {
      const s = o;
      throw console.error(`模型加载失败: ${s.message}`), t.onError && t.onError(s), s;
    }
  }
  /**
   * 根据类型加载模型
   */
  async loadModelByType(e, t, o) {
    if (console.log("fileType:", t, "is Gaussian?", o.isGaussian), t === "gaussian" || t === "onnx")
      return await this.loadGaussianModel(e, o);
    if (t === "ply") {
      if (o.isGaussian)
        return await this.loadGaussianModel(e, o);
      console.log("UnifiedModelLoader: 检测到普通 Mesh PLY");
    } else if (o.isGaussian)
      return await this.loadGaussianModel(e, o);
    if (t === "fbx")
      return await this.loadFBXModel(e, o);
    const s = await this.loadWithUniversalLoader(e, o);
    return await this.processLoadedData(s, t, o);
  }
  /**
   * 使用 UniversalLoader 统一加载
   */
  async loadWithUniversalLoader(e, t) {
    const o = {
      onProgress: (s) => {
        t.onProgress && t.onProgress(s.progress);
      },
      isGaussian: t.isGaussian
    };
    return e instanceof File ? await T.loadFile(e, o) : await T.loadUrl(e, o);
  }
  /**
   * 处理加载的数据
   */
  async processLoadedData(e, t, o) {
    const s = o.sourceFile?.name || "model", n = o.name || s.split("/").pop()?.split(".")[0] || "model";
    return e instanceof ee ? (console.log("处理 Three.js 模型"), this.processThreeJSModel(e, t, n, o)) : (console.log("处理 高斯模型"), this.processGaussianModel(e, t, n, o));
  }
  /**
   * 处理 Three.js 模型
   */
  processThreeJSModel(e, t, o, s) {
    const n = e.object3D(), a = [];
    return n instanceof h.Group ? a.push(...n.children) : a.push(n), a.forEach((r) => {
      this.scene.add(r);
    }), console.log("=== Three.js 模型加载完成 ==="), console.log("模型名称:", o), console.log("模型数量:", a.length), a.forEach((r, i) => {
      console.log(`模型 ${i + 1}:`), console.log("  Object3D UUID:", r.uuid), console.log("  Object3D 类型:", r.constructor.name), console.log("  Object3D 名称:", r.name || "未命名");
    }), s.sourceFile ? (console.log("原始文件路径:", s.sourceFile.name), console.log("文件大小:", s.sourceFile.size, "bytes"), console.log("文件类型:", s.sourceFile.type)) : console.log("原始文件: URL 加载，无 File 对象"), {
      models: a,
      sourceFile: s.sourceFile,
      info: {
        type: t,
        name: o,
        count: a.length,
        isGaussian: !1
      }
    };
  }
  /**
   * 处理高斯模型
   */
  async processGaussianModel(e, t, o, s) {
    throw new Error("高斯模型处理需要特殊实现，请使用 loadGaussianModel 方法");
  }
  /**
   * 加载高斯模型
   * 简化版本 - 直接使用 Core 的 GaussianLoader
   */
  async loadGaussianModel(e, t) {
    const o = e instanceof File ? e.name : e, s = t.name || o.split("/").pop()?.split(".")[0] || "gaussian_model";
    console.log("=== 进入 loadGaussianModel ==="), console.log("文件名:", o);
    let n = "ply";
    const a = o.toLowerCase();
    a.endsWith(".compressed.ply") ? n = "compressed.ply" : a.endsWith(".sog") ? n = "sog" : a.endsWith(".ksplat") ? n = "ksplat" : a.endsWith(".splat") ? n = "splat" : a.endsWith(".spz") ? n = "spz" : a.endsWith(".onnx") && (n = "onnx"), console.log("传递给加载器的具体格式:", n);
    const r = t.sourceFile || (e instanceof File ? e : void 0), i = await this.gaussianLoader.createFromFile(
      this.renderer,
      e instanceof File ? URL.createObjectURL(e) : e,
      {
        camMat: t.cameraMatrix || new Float32Array(16),
        projMat: t.projectionMatrix || new Float32Array(16),
        ...t.gaussianOptions
      },
      t.gaussianOptions,
      n
    );
    e instanceof File && URL.revokeObjectURL(URL.createObjectURL(e)), this.scene.add(i);
    const l = new pe(
      this.renderer,
      this.scene,
      [i]
    );
    return await l.init(), this.scene.add(l), console.log("=== 高斯模型加载完成 ==="), console.log("模型名称:", s), console.log("Object3D UUID:", i.uuid), console.log("Object3D 类型:", i.constructor.name), r ? (console.log("原始文件路径:", r.name), console.log("文件大小:", r.size, "bytes"), console.log("文件类型:", r.type)) : console.log("原始文件: URL 加载，无 File 对象"), console.log("高斯渲染器 UUID:", l.uuid), {
      models: [i],
      gaussianRenderer: l,
      sourceFile: r,
      info: {
        type: "gaussian",
        name: s,
        count: 1,
        isGaussian: !0
      }
    };
  }
  async readFileHeader(e, t = 4096) {
    const s = await e.slice(0, t).arrayBuffer();
    return new TextDecoder("utf-8").decode(s || new ArrayBuffer(0));
  }
  async is3dgsPly(e) {
    try {
      const t = (await this.readFileHeader(e)).toLowerCase();
      if (!t.startsWith("ply"))
        return console.log("不是 PLY 文件:", e.name), !1;
      const s = [
        "property float opacity",
        "property float scale_0",
        "property float scale_1",
        "property float scale_2",
        "property float rot_0",
        "property float rot_1",
        "property float rot_2",
        "property float rot_3"
      ].every((a) => t.includes(a)), n = /property\s+float\s+sh_\d+/.test(t);
      return console.log(`PLY 文件 ${e.name} 3DGS 检测结果: 基础属性=${s}, SH 系数=${n}`), s;
    } catch (t) {
      return console.warn("读取 PLY 头信息失败，按非 3DGS 处理:", e.name, t), !1;
    }
  }
  /**
   * 通过读取 URL 的文件头判断是否为 3DGS 高斯模型
   * 只下载前 4KB 数据，检查是否包含高斯特有的属性字段
   */
  async isGaussianPlyUrl(e) {
    try {
      const t = e.includes("?") ? "&" : "?", o = `${e}${t}temp=${(/* @__PURE__ */ new Date()).getTime()}`, s = await fetch(o, {
        method: "GET",
        mode: "cors",
        // 必须支持跨域
        headers: {
          Range: "bytes=0-4095"
        }
      });
      !s.ok && s.status !== 206 && console.warn(`[UnifiedModelLoader] Range 请求未按预期返回 206，状态码: ${s.status}。尝试继续解析...`);
      const a = (await s.text()).slice(0, 4096).toLowerCase();
      if (!a.startsWith("ply"))
        return console.log(`[UnifiedModelLoader] URL 资源不是 PLY 格式: ${o}`), !1;
      const i = [
        "property float opacity",
        "property float scale_0",
        "property float scale_1",
        "property float scale_2",
        "property float rot_0",
        "property float rot_1",
        "property float rot_2",
        "property float rot_3"
      ].every((u) => a.includes(u)), l = /property\s+float\s+sh_\d+/.test(a) || /property\s+float\s+f_dc_0/.test(a);
      return console.log(`[UnifiedModelLoader] 线上 PLY 检测结果: 基础属性=${i}, SH系数=${l}, URL=${o}`), i;
    } catch (t) {
      return console.warn("[UnifiedModelLoader] 无法检测线上 PLY 类型 (可能是跨域或网络问题)，默认按 False 处理:", t), !1;
    }
  }
  /**
   * 批量加载模型
   */
  async loadModels(e, t = {}) {
    const o = [];
    for (let s = 0; s < e.length; s++) {
      const n = e[s], a = {
        ...t,
        onProgress: (r) => {
          if (t.onProgress) {
            const i = (s + r) / e.length;
            t.onProgress(i);
          }
        }
      };
      try {
        const r = await this.loadModel(n, a);
        o.push(r);
      } catch (r) {
        console.error(`加载模型失败: ${n}`, r), t.onError && t.onError(r);
      }
    }
    return o;
  }
  /**
   * 加载 FBX 模型
   */
  async loadFBXModel(e, t) {
    const o = e instanceof File ? e.name : e, s = t.name || o.split("/").pop()?.split(".")[0] || "fbx_model";
    console.log("=== 进入 loadFBXModel ==="), console.log("文件名:", o);
    try {
      let n;
      e instanceof File ? n = await this.fbxLoader.loadFromFile(e, t.fbxOptions) : n = await this.fbxLoader.loadFromURL(e, t.fbxOptions);
      const a = n.pointCloud, r = a.object3D;
      return this.scene.add(r), console.log("=== FBX 模型加载完成 ==="), console.log("模型名称:", s), console.log("Object3D UUID:", r.uuid), console.log("Object3D 类型:", r.constructor.name), console.log("动画数量:", a.clips.length), console.log("顶点数量:", n.pointCount), {
        models: [r],
        sourceFile: e instanceof File ? e : void 0,
        info: {
          type: "fbx",
          name: s,
          count: 1,
          isGaussian: !1
        }
      };
    } catch (n) {
      throw console.error("FBX 模型加载失败:", n), n;
    }
  }
  /**
   * 清理资源
   */
  dispose() {
  }
}
async function Ue(d, e, t, o = {}) {
  const s = new fe(d, e);
  try {
    return Array.isArray(t) ? await s.loadModels(t, o) : await s.loadModel(t, o);
  } finally {
    s.dispose();
  }
}
export {
  De as A,
  ue as C,
  Y as F,
  j as M,
  H as O,
  me as R,
  fe as U,
  he as a,
  ae as c,
  Oe as i,
  Ue as l
};
