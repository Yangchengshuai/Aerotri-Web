let e = "/src/ort/";
function s(o) {
  typeof o == "string" ? e = o : e = o.join(",");
}
function t() {
  return e;
}
function r(o) {
  if (o && s(o), typeof window < "u" && window.ort) {
    const n = window.ort;
    n.env.wasm.wasmPaths = t(), console.log(`[VisionaryCore] ONNX Runtime WASM paths configured: ${t()}`);
  } else if (console.warn("[VisionaryCore] ONNX Runtime not available, configuration will be applied when ort is loaded"), typeof window < "u") {
    const n = () => {
      if (window.ort) {
        const i = window.ort;
        i.env.wasm.wasmPaths = t(), console.log(`[VisionaryCore] ONNX Runtime WASM paths configured (delayed): ${t()}`);
      } else
        setTimeout(n, 50);
    };
    setTimeout(n, 50);
  }
}
function a() {
  return "/src/ort/";
}
function w() {
  return typeof window < "u" && window.ort && window.ort.env && window.ort.env.wasm && window.ort.env.wasm.wasmPaths;
}
export {
  t as a,
  w as b,
  a as g,
  r as i,
  s
};
