import { a as f, A as l, C as M, F as g, M as O, O as x, R as C, U as P, c as h, i as u, l as A } from "./visionary-core.src-app.js";
import { G as N } from "./visionary-core.src-renderer.js";
import { C as R, P as U } from "./visionary-core.src-camera.js";
import "./visionary-core.src-utils.js";
import "gl-matrix";
import "three/webgpu";
import "three/examples/jsm/loaders/RGBELoader.js";
import "three/examples/jsm/loaders/GLTFLoader.js";
import "three/examples/jsm/loaders/OBJLoader.js";
import "three/examples/jsm/loaders/FBXLoader.js";
import "three/examples/jsm/loaders/STLLoader.js";
import "three/examples/jsm/loaders/PLYLoader.js";
import { a as v } from "./visionary-core.src-io.js";
import { a as G } from "./visionary-core.src-ONNX.js";
import { g as X, a as b, i as D, b as E, s as j } from "./visionary-core.src-config.js";
export {
  f as AnimationManager,
  l as App,
  R as CameraAdapter,
  M as CameraManager,
  g as FileLoader,
  N as GaussianRenderer,
  O as ModelManager,
  x as ONNXManager,
  G as ONNXModelTester,
  U as PerspectiveCamera,
  C as RenderLoop,
  P as UnifiedModelLoader,
  h as clamp,
  v as defaultLoader,
  X as getDefaultOrtWasmPaths,
  b as getOrtWasmPaths,
  D as initOrtEnvironment,
  u as initThreeContext,
  E as isOrtConfigured,
  A as loadUnifiedModel,
  j as setOrtWasmPaths
};
