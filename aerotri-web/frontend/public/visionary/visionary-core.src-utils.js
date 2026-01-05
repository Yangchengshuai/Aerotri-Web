import { vec3 as _, mat4 as $, mat3 as b } from "gl-matrix";
import "three/webgpu";
import "three/examples/jsm/loaders/RGBELoader.js";
function T(t) {
  return t * Math.PI / 180;
}
function I(t, n) {
  return n / (2 * Math.tan(t * 0.5));
}
class H {
  min;
  max;
  constructor(n, o) {
    this.min = _.clone(n), this.max = _.clone(o);
  }
  center() {
    const n = _.create();
    return _.add(n, this.min, this.max), _.scale(n, n, 0.5), n;
  }
  radius() {
    return 0.5 * _.distance(this.min, this.max);
  }
}
const z = $.fromValues(
  1,
  0,
  0,
  0,
  0,
  -1,
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
);
function V(t) {
  const n = Math.sqrt(t);
  return Number.isInteger(n) ? (n | 0) - 1 : void 0;
}
function W(t, n) {
  const o = b.create();
  b.fromQuat(o, t);
  const u = b.fromValues(
    n[0],
    0,
    0,
    0,
    n[1],
    0,
    0,
    0,
    n[2]
  ), e = b.create();
  b.multiply(e, o, u);
  const f = b.create();
  b.transpose(f, e);
  const c = b.create();
  return b.multiply(c, e, f), [c[0], c[1], c[2], c[4], c[5], c[8]];
}
function X(t) {
  if (t >= 0) return 1 / (1 + Math.exp(-t));
  const n = Math.exp(t);
  return n / (1 + n);
}
const B = new Float32Array(1), E = new Uint32Array(B.buffer);
function U(t, n = {}) {
  const {
    round: o = "rne",
    ftz: u = !1,
    saturate: e = !1,
    canonicalNaN: f = !0,
    emulateLegacyExpCutoff: c
  } = n;
  B[0] = t;
  const l = E[0] >>> 0, m = l >>> 31 << 15, P = l >>> 23 & 255, p = l & 8388607;
  if (P === 255)
    return p !== 0 ? m | (f ? 32256 : 31744 | p >>> 13) : m | 31744;
  if (c !== void 0 && P < c)
    return m;
  let N = P - 127 + 15;
  if (N >= 31)
    return m | (e ? 31743 : 31744);
  if (N <= 0) {
    if (N < -10 || u)
      return m;
    let r = p | 8388608;
    const d = 14 - N;
    let x = r >>> d;
    if (o === "rne") {
      const s = (1 << d) - 1, g = r & s, i = 1 << d - 1;
      if ((g > i || g === i && x & 1) && (x++, x === 1024))
        return m | 1024;
    }
    return m | x;
  }
  let a = p >>> 13;
  if (o === "rne") {
    const r = p >>> 12 & 1, d = p & 4095;
    if (r && (d !== 0 || a & 1) && (a++, a === 1024 && (a = 0, N++, N >= 31)))
      return m | (e ? 31743 : 31744);
  }
  return m | N << 10 | a;
}
const F = (t) => (t + 1) * (t + 1);
function q(t) {
  const { props: n, iDC0: o, iDC1: u, iDC2: e, k: f, shU32: c } = t, l = [];
  for (let a = 0; a < n.length; ++a) {
    const r = n[a];
    if (r.startsWith("f_rest_")) {
      const d = Number(r.slice(7));
      l.push({ idx: a, order: Number.isFinite(d) ? d : 1e9 + a });
    }
  }
  l.sort((a, r) => a.order - r.order);
  const m = F(f) - 1, P = m * 3;
  l.length < P && console.warn(`[copySH_f16] f_rest_* too few: have=${l.length}, need=${P}. Will pad zeros.`);
  const p = 3 + P;
  return p !== 48 && console.warn(`[copySH_f16] k=${f} gives ${p} halfs; padding to 48 halfs for fixed 24 u32 stride.`), { copySH: (a, r, d = !1) => {
    const x = m, s = new Uint16Array(48);
    s[0] = U(r[o]), s[1] = U(r[u]), s[2] = U(r[e]);
    let g = 3;
    for (let i = 0; i < x; ++i) {
      {
        const h = l[i]?.idx, y = h !== void 0 ? r[h] : 0;
        s[g++] = U(y);
      }
      {
        const h = l[x + i]?.idx, y = h !== void 0 ? r[h] : 0;
        s[g++] = U(y);
      }
      {
        const h = l[2 * x + i]?.idx, y = h !== void 0 ? r[h] : 0;
        s[g++] = U(y);
      }
    }
    for (; g < 48; ) s[g++] = 0;
    for (let i = 0; i < 48; i += 2)
      c[a + (i >> 1)] = s[i] & 65535 | (s[i + 1] & 65535) << 16;
    d && console.log(`SH[k=${f}] DC (f16):`, s[0], s[1], s[2]);
  }, wordsPerPoint: 24 };
}
function G(t) {
  return Number.isFinite(t[0]) && Number.isFinite(t[1]) && Number.isFinite(t[2]);
}
function L(t, n = !0) {
  if (t.length === 0)
    return { centroid: [0, 0, 0] };
  let o = 0, u = 0, e = 0;
  for (const [g, i, h] of t)
    o += g, u += i, e += h;
  const f = t.length, c = [o / f, u / f, e / f];
  if (t.length < 3)
    return { centroid: c };
  let l = 0, m = 0, P = 0, p = 0, M = 0, N = 0;
  for (const [g, i, h] of t) {
    const y = g - c[0], C = i - c[1], w = h - c[2];
    l += y * y, m += y * C, P += y * w, p += C * C, M += C * w, N += w * w;
  }
  let a = 1, r = 1, d = 1;
  const x = 20;
  for (let g = 0; g < x; g++) {
    const i = l * a + m * r + P * d, h = m * a + p * r + M * d, y = P * a + M * r + N * d, C = Math.hypot(i, h, y);
    if (C < 1e-10) break;
    a = i / C, r = h / C, d = y / C;
  }
  let s = [a, r, d];
  return n && s[1] < 0 && (s = [-s[0], -s[1], -s[2]]), G(s) ? { centroid: c, normal: s } : { centroid: c };
}
async function v(t, n, o = 0, u = 4) {
  const e = t.createBuffer({
    size: u,
    usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST,
    label: "debug-staging-buffer"
  }), f = t.createCommandEncoder();
  f.copyBufferToBuffer(n, o, e, 0, u), t.queue.submit([f.finish()]), await t.queue.onSubmittedWorkDone(), await e.mapAsync(GPUMapMode.READ);
  const c = e.getMappedRange(0, u), l = new ArrayBuffer(u);
  return new Uint8Array(l).set(new Uint8Array(c)), e.unmap(), e.destroy(), l;
}
async function D(t, n, o = 0) {
  const u = await v(t, n, o, 4);
  return new Uint32Array(u)[0];
}
async function O(t, n) {
  return await D(t, n, 0);
}
async function A(t, n) {
  const o = await D(t, n, 68);
  return console.log(`🔍 DEBUG: ModelParams.num_points (offset 68) = ${o}`), o;
}
async function Y(t, n, o, u) {
  if (console.log("🔍 === GPU COUNT DEBUG TRACE ==="), console.log(`📊 Max points allocated: ${u}`), n) {
    const e = await O(t, n);
    console.log(`📊 ONNX inference count: ${e}`);
    const f = await A(t, o);
    console.log(`📊 ModelParams count: ${f}`), e === f ? console.log("✅ Count successfully propagated from ONNX to shader uniforms") : (console.log(`❌ Count mismatch! ONNX=${e}, ModelParams=${f}`), console.log("⚠️ The buffer copy may have failed or timing is wrong")), f === u && console.log("⚠️ WARNING: Using maxPoints instead of dynamic count!");
  } else {
    console.log("ℹ️ No ONNX count buffer (static model)");
    const e = await A(t, o);
    console.log(`📊 ModelParams count: ${e}`);
  }
  console.log("🔍 === END DEBUG TRACE ===");
}
export {
  H as A,
  z as V,
  X as a,
  W as b,
  U as c,
  T as d,
  Y as e,
  I as f,
  q as m,
  L as p,
  O as r,
  V as s
};
