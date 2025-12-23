import { m as ie, s as ce, a as Wt, b as Ut, c as a, p as Nt } from "./visionary-core.src-utils.js";
import { quat as Q, vec3 as Pt } from "gl-matrix";
import * as Dt from "three/webgpu";
import "three/examples/jsm/loaders/RGBELoader.js";
import { GLTFLoader as le } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OBJLoader as fe } from "three/examples/jsm/loaders/OBJLoader.js";
import { FBXLoader as de } from "three/examples/jsm/loaders/FBXLoader.js";
import { STLLoader as ue } from "three/examples/jsm/loaders/STLLoader.js";
import { PLYLoader as he } from "three/examples/jsm/loaders/PLYLoader.js";
import { u as ge } from "./visionary-core.vendor-fflate.js";
class _t {
  _gaussianBuffer;
  _shCoefsBuffer;
  _numPoints;
  _shDegree;
  _bbox;
  center;
  up;
  kernelSize;
  mipSplatting;
  backgroundColor;
  constructor(t) {
    this._gaussianBuffer = t.gaussianBuffer, this._shCoefsBuffer = t.shCoefsBuffer, this._numPoints = t.numPoints, this._shDegree = t.shDegree, this._bbox = t.bbox, this.center = t.center, this.up = t.up, this.kernelSize = t.kernelSize, this.mipSplatting = t.mipSplatting, this.backgroundColor = t.backgroundColor;
  }
  gaussianBuffer() {
    return this._gaussianBuffer;
  }
  shCoefsBuffer() {
    return this._shCoefsBuffer;
  }
  numPoints() {
    return this._numPoints;
  }
  shDegree() {
    return this._shDegree;
  }
  bbox() {
    return this._bbox;
  }
}
class me {
  async loadFile(t, e) {
    const s = await t.arrayBuffer();
    return this.loadBuffer(s, e);
  }
  async loadUrl(t, e) {
    const s = await fetch(t, { signal: e?.signal });
    if (!s.ok)
      throw new Error(`Failed to fetch PLY file: ${s.status} ${s.statusText}`);
    const o = await s.arrayBuffer();
    return this.loadBuffer(o, e);
  }
  async loadBuffer(t, e) {
    const s = (h, f, d) => {
      e?.onProgress?.({ stage: h, progress: f, message: d });
    };
    s("Parsing PLY header", 0.1);
    const o = this.parseHeader(t);
    s("Parsing vertex data", 0.2);
    const n = this.parseVertices(t, o);
    s("Processing Gaussian data", 0.4);
    const u = this.processGaussianData(o, n, s);
    return s("Complete", 1), u;
  }
  canHandle(t, e) {
    return t.toLowerCase().endsWith(".ply") || e === "application/octet-stream";
  }
  getSupportedExtensions() {
    return [".ply"];
  }
  // ========== Private Implementation ==========
  processGaussianData(t, e, s) {
    const h = (3 + e.props.filter((v) => v.startsWith("f_rest_")).length) / 3, f = ce(h) ?? 0, d = this.getFieldIndices(e.props);
    this.validateRequiredFields(d);
    const c = t.vertices, i = 10, l = new Uint16Array(c * i), x = 24, y = new Uint32Array(c * x), N = [], M = [Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY], F = [Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY], { copySH: g, wordsPerPoint: q } = ie({
      props: e.props,
      iDC0: d.iDC0,
      iDC1: d.iDC1,
      iDC2: d.iDC2,
      k: 3,
      shU32: y
    });
    s?.("Processing Gaussians", 0.5);
    for (let v = 0; v < c; v++) {
      v % 1e4 === 0 && s?.("Processing Gaussians", 0.5 + 0.3 * (v / c), `${v}/${c} points`);
      const A = e.rows(v), E = this.processGaussian(A, d, v, i, l);
      N.push([E.x, E.y, E.z]), g(v * q, A, !1), E.x < M[0] && (M[0] = E.x), E.y < M[1] && (M[1] = E.y), E.z < M[2] && (M[2] = E.z), E.x > F[0] && (F[0] = E.x), E.y > F[1] && (F[1] = E.y), E.z > F[2] && (F[2] = E.z);
    }
    s?.("Computing scene geometry", 0.8);
    const { centroid: I, normal: R } = this.computeSceneGeometry(N), ot = [I[0], I[1], I[2]], k = R ? [R[0], R[1], R[2]] : [1, 0, 0];
    return new _t({
      gaussianBuffer: l.buffer,
      shCoefsBuffer: y.buffer,
      numPoints: c,
      shDegree: f,
      bbox: { min: M, max: F },
      center: ot,
      up: k,
      mipSplatting: void 0,
      kernelSize: void 0,
      backgroundColor: void 0
    });
  }
  getFieldIndices(t) {
    return {
      ix: t.indexOf("x"),
      iy: t.indexOf("y"),
      iz: t.indexOf("z"),
      iOpacity: t.indexOf("opacity"),
      iS0: t.indexOf("scale_0"),
      iS1: t.indexOf("scale_1"),
      iS2: t.indexOf("scale_2"),
      iR0: t.indexOf("rot_0"),
      iR1: t.indexOf("rot_1"),
      iR2: t.indexOf("rot_2"),
      iR3: t.indexOf("rot_3"),
      iDC0: t.indexOf("f_dc_0"),
      iDC1: t.indexOf("f_dc_1"),
      iDC2: t.indexOf("f_dc_2")
    };
  }
  validateRequiredFields(t) {
    const e = ["ix", "iy", "iz", "iOpacity", "iS0", "iS1", "iS2", "iR0", "iR1", "iR2", "iR3", "iDC0", "iDC1", "iDC2"];
    for (const s of e)
      if (t[s] < 0)
        throw new Error(`PLY missing required field: ${s.slice(1)}`);
  }
  processGaussian(t, e, s, o, n) {
    const u = t[e.ix], h = t[e.iy], f = t[e.iz], d = Wt(t[e.iOpacity]), c = [
      Math.exp(t[e.iS0]),
      Math.exp(t[e.iS1]),
      Math.exp(t[e.iS2])
    ], i = Q.fromValues(t[e.iR1], t[e.iR2], t[e.iR3], t[e.iR0]);
    Q.normalize(i, i);
    const [l, x, y, N, M, F] = Ut(i, new Float32Array(c)), g = s * o;
    return n[g + 0] = a(u), n[g + 1] = a(h), n[g + 2] = a(f), n[g + 3] = a(d), n[g + 4] = a(l), n[g + 5] = a(x), n[g + 6] = a(y), n[g + 7] = a(N), n[g + 8] = a(M), n[g + 9] = a(F), { x: u, y: h, z: f };
  }
  computeSceneGeometry(t) {
    return Nt(t);
  }
  parseHeader(t) {
    const e = new TextDecoder().decode(t.slice(0, Math.min(1048576, t.byteLength))), s = e.split(/\r?\n/);
    if (!/^ply\b/.test(s[0])) throw new Error("Not a PLY file");
    let o = null, n = 0;
    const u = [];
    let h = 0, f = !1;
    for (let d = 1; d < s.length; d++) {
      const c = s[d];
      if (c === "end_header") {
        let i = e.indexOf("end_header");
        if (i < 0) throw new Error("Malformed PLY: missing end_header");
        const l = e.indexOf(`
`, i + 10);
        h = l >= 0 ? l + 1 : i + 10 + 1;
        break;
      }
      if (c.startsWith("format ")) {
        const i = c.split(/\s+/)[1];
        if (i === "ascii" || i === "binary_little_endian" || i === "binary_big_endian")
          o = i;
        else
          throw new Error(`Unsupported PLY format: ${i}`);
      } else if (c.startsWith("element "))
        f = c.startsWith("element vertex "), f && (n = parseInt(c.split(/\s+/)[2], 10));
      else if (f && c.startsWith("property ")) {
        const i = c.trim().split(/\s+/);
        if (i[1] === "list") throw new Error("Unexpected list property in vertex");
        const l = i[i.length - 1];
        u.push(l);
      }
    }
    if (!o) throw new Error("PLY header missing format");
    if (n <= 0) throw new Error("PLY has no vertices element");
    return { format: o, vertices: n, props: u, headerByteLength: h };
  }
  parseVertices(t, e) {
    const s = e.props.slice();
    return e.format === "ascii" ? this.parseASCIIVertices(t, e, s) : this.parseBinaryVertices(t, e, s);
  }
  parseASCIIVertices(t, e, s) {
    const n = new TextDecoder().decode(t.slice(e.headerByteLength)).split(/\r?\n/).filter((u) => u.trim().length > 0);
    return {
      props: s,
      rows: (u) => {
        const h = n[u].trim().split(/\s+/);
        if (h.length < s.length) throw new Error("Malformed PLY ASCII row");
        return h.map(parseFloat);
      }
    };
  }
  parseBinaryVertices(t, e, s) {
    const o = e.format === "binary_little_endian", n = new DataView(t, e.headerByteLength), u = s.length * 4;
    return {
      props: s,
      rows: (h) => {
        const f = h * u, d = new Array(s.length);
        for (let c = 0; c < s.length; c++)
          d[c] = n.getFloat32(f + c * 4, o);
        return d;
      }
    };
  }
}
class pe {
  async loadFile(t, e) {
    return this.loadBuffer(await t.arrayBuffer(), e);
  }
  async loadUrl(t, e) {
    const s = await fetch(t, { signal: e?.signal });
    if (!s.ok) throw new Error(`Failed to fetch SPZ: ${s.statusText}`);
    return this.loadBuffer(await s.arrayBuffer(), e);
  }
  async loadBuffer(t, e) {
    const s = (T, b, w) => {
      e?.onProgress?.({ stage: T, progress: b, message: w });
    };
    s("Decompressing SPZ", 0.1);
    const o = new Uint8Array(t), u = new Blob([o]).stream().pipeThrough(new DecompressionStream("gzip")), h = await new Response(u).arrayBuffer();
    s("Parsing Data", 0.2);
    const f = new DataView(h), d = new Uint8Array(h);
    let c = 0;
    const i = f.getUint32(c, !0);
    if (c += 4, i !== 1347635022) throw new Error(`Invalid SPZ magic: 0x${i.toString(16)}`);
    const l = f.getUint32(c, !0);
    c += 4;
    const x = f.getUint32(c, !0);
    c += 4;
    const y = f.getUint8(c++), N = f.getUint8(c++);
    if (f.getUint8(c++), c++, l < 1 || l > 3) throw new Error(`Unsupported SPZ version: ${l}`);
    const M = c;
    l === 1 ? c += x * 6 : c += x * 9;
    const F = c;
    c += x;
    const g = c;
    c += x * 3;
    const q = c;
    c += x * 3;
    const I = c;
    l === 3 ? c += x * 4 : c += x * 3;
    const R = c, k = { 1: 3, 2: 8, 3: 15 }[y] || 0, v = 10, A = new Uint16Array(x * v), E = 24, tt = new Uint32Array(x * E), V = [];
    let W = 1 / 0, Y = 1 / 0, C = 1 / 0, G = -1 / 0, X = -1 / 0, it = -1 / 0;
    const at = 1 << N, st = Q.create(), gt = Pt.create();
    s("Processing Points", 0.3);
    for (let T = 0; T < x; T++) {
      T % 1e4 === 0 && T % 5e4 === 0 && s("Processing Points", 0.3 + 0.6 * (T / x));
      let b, w, r;
      if (l === 1)
        b = this.readHalfFloat(f, M + T * 6 + 0), w = this.readHalfFloat(f, M + T * 6 + 2), r = this.readHalfFloat(f, M + T * 6 + 4);
      else {
        const _ = M + T * 9, P = d[_] | d[_ + 1] << 8 | d[_ + 2] << 16, j = d[_ + 3] | d[_ + 4] << 8 | d[_ + 5] << 16, Z = d[_ + 6] | d[_ + 7] << 8 | d[_ + 8] << 16;
        b = (P << 8 >> 8) / at, w = (j << 8 >> 8) / at, r = (Z << 8 >> 8) / at;
      }
      const p = d[F + T] / 255, S = g + T * 3, m = (d[S] / 255 - 0.5) / 0.15, U = (d[S + 1] / 255 - 0.5) / 0.15, O = (d[S + 2] / 255 - 0.5) / 0.15, L = q + T * 3, H = Math.exp(d[L] / 16 - 10), et = Math.exp(d[L + 1] / 16 - 10), nt = Math.exp(d[L + 2] / 16 - 10);
      if (l === 3) {
        const _ = I + T * 4, P = d[_] | d[_ + 1] << 8 | d[_ + 2] << 16 | d[_ + 3] << 24, j = 0.70710678, Z = 511, K = P >>> 30;
        let J = P;
        const ft = [0, 0, 0, 0];
        let yt = 0;
        for (let D = 3; D >= 0; D--)
          if (D !== K) {
            const pt = J & Z, wt = J >>> 9 & 1;
            J >>>= 10;
            let mt = j * (pt / 511);
            wt && (mt = -mt), ft[D] = mt, yt += mt * mt;
          }
        ft[K] = Math.sqrt(Math.max(1 - yt, 0)), Q.set(st, ft[0], ft[1], ft[2], ft[3]);
      } else {
        const _ = I + T * 3, P = d[_] / 127.5 - 1, j = d[_ + 1] / 127.5 - 1, Z = d[_ + 2] / 127.5 - 1, K = Math.sqrt(Math.max(0, 1 - P * P - j * j - Z * Z));
        Q.set(st, P, j, Z, K);
      }
      Q.normalize(st, st), Pt.set(gt, H, et, nt);
      const [$, B, ut, ht, xt, Bt] = Ut(st, gt), lt = T * v;
      A[lt + 0] = a(b), A[lt + 1] = a(w), A[lt + 2] = a(r), A[lt + 3] = a(p), A[lt + 4] = a($), A[lt + 5] = a(B), A[lt + 6] = a(ut), A[lt + 7] = a(ht), A[lt + 8] = a(xt), A[lt + 9] = a(Bt);
      const bt = T * E;
      if (tt[bt + 0] = a(m) | a(U) << 16, tt[bt + 1] = a(O), k > 0) {
        const _ = R + T * k * 3;
        let P = bt + 1, j = !0;
        for (let Z = 0; Z < k * 3; Z++) {
          const K = (d[_ + Z] - 128) / 128, J = a(K);
          j ? (tt[P] |= J << 16, P++, j = !1) : (tt[P] = J, j = !0);
        }
      }
      b < W && (W = b), b > G && (G = b), w < Y && (Y = w), w > X && (X = w), r < C && (C = r), r > it && (it = r), V.push([b, w, r]);
    }
    s("Finalizing", 0.95);
    const { centroid: rt, normal: ct } = Nt(V);
    return console.log(`[SPZLoader] Loaded ${x} points efficiently.`), new _t({
      gaussianBuffer: A.buffer,
      shCoefsBuffer: tt.buffer,
      numPoints: x,
      shDegree: y,
      bbox: { min: [W, Y, C], max: [G, X, it] },
      center: [rt[0], rt[1], rt[2]],
      up: ct ? [ct[0], ct[1], ct[2]] : [0, 1, 0]
    });
  }
  canHandle(t) {
    return t.toLowerCase().endsWith(".spz");
  }
  getSupportedExtensions() {
    return [".spz"];
  }
  readHalfFloat(t, e) {
    const s = t.getUint16(e, !0), o = (s & 32768) >> 15, n = (s & 31744) >> 10, u = s & 1023;
    return n === 0 ? (o ? -1 : 1) * Math.pow(2, -14) * (u / 1024) : n === 31 ? u ? NaN : o ? -1 / 0 : 1 / 0 : (o ? -1 : 1) * Math.pow(2, n - 15) * (1 + u / 1024);
  }
}
class ye {
  async loadFile(t, e) {
    return this.loadBuffer(await t.arrayBuffer(), e);
  }
  async loadUrl(t, e) {
    const s = await fetch(t, { signal: e?.signal });
    if (!s.ok) throw new Error(`Failed to fetch KSplat: ${s.statusText}`);
    return this.loadBuffer(await s.arrayBuffer(), e);
  }
  async loadBuffer(t, e) {
    const s = (T, b, w) => {
      e?.onProgress?.({ stage: T, progress: b, message: w });
    };
    s("Parsing KSplat Header", 0.1);
    const o = 4096, n = 1024;
    let u = 0;
    const h = new DataView(t, u, o), f = h.getUint8(0), d = h.getUint8(1);
    (f !== 0 || d < 1) && console.warn(`KSplat version ${f}.${d} might not be fully supported.`);
    const c = h.getUint32(4, !0), i = h.getUint32(16, !0), l = h.getUint16(20, !0), x = h.getFloat32(36, !0) || -1.5, y = h.getFloat32(40, !0) || 1.5, N = {
      0: { bytesPerCenter: 12, bytesPerScale: 12, bytesPerRotation: 16, bytesPerColor: 4, bytesPerSphericalHarmonicsComponent: 4, scaleOffsetBytes: 12, rotationOffsetBytes: 24, colorOffsetBytes: 40, sphericalHarmonicsOffsetBytes: 44, scaleRange: 1 },
      1: { bytesPerCenter: 6, bytesPerScale: 6, bytesPerRotation: 8, bytesPerColor: 4, bytesPerSphericalHarmonicsComponent: 2, scaleOffsetBytes: 6, rotationOffsetBytes: 12, colorOffsetBytes: 20, sphericalHarmonicsOffsetBytes: 24, scaleRange: 32767 },
      2: { bytesPerCenter: 6, bytesPerScale: 6, bytesPerRotation: 8, bytesPerColor: 4, bytesPerSphericalHarmonicsComponent: 1, scaleOffsetBytes: 6, rotationOffsetBytes: 12, colorOffsetBytes: 20, sphericalHarmonicsOffsetBytes: 24, scaleRange: 32767 }
    }, M = [0, 9, 24, 45];
    s("Loading Data", 0.2);
    const F = 10, g = new Uint16Array(i * F), q = 24, I = new Uint32Array(i * q);
    let R = 1 / 0, ot = 1 / 0, k = 1 / 0, v = -1 / 0, A = -1 / 0, E = -1 / 0, tt = 0, V = 0, W = 0, Y = o + c * n, C = 0, G = 0;
    const X = Q.create(), it = Pt.create(), at = 0.28209479177387814, st = [
      0,
      3,
      6,
      1,
      4,
      7,
      2,
      5,
      8,
      9,
      14,
      19,
      10,
      15,
      20,
      11,
      16,
      21,
      12,
      17,
      22,
      13,
      18,
      23,
      24,
      31,
      38,
      25,
      32,
      39,
      26,
      33,
      40,
      27,
      34,
      41,
      28,
      35,
      42,
      29,
      36,
      43,
      30,
      37,
      44
    ];
    u = o;
    for (let T = 0; T < c; T++) {
      const b = new DataView(t, u, n);
      u += n;
      const w = b.getUint32(0, !0);
      if (w === 0) continue;
      const r = b.getUint32(4, !0), p = b.getUint32(8, !0), S = b.getUint32(12, !0), m = b.getFloat32(16, !0), U = b.getUint16(20, !0), O = b.getUint32(24, !0) || N[l].scaleRange, L = b.getUint32(32, !0), H = L * p, et = b.getUint32(36, !0), nt = b.getUint16(40, !0);
      G = Math.max(G, nt);
      const $ = M[nt], B = N[l], ut = B.bytesPerCenter + B.bytesPerScale + B.bytesPerRotation + B.bytesPerColor + $ * B.bytesPerSphericalHarmonicsComponent, ht = et * 4, xt = U * S + ht, Bt = ut * r, lt = Y + ht, bt = Y + xt, _ = Bt + xt, P = new DataView(t, bt, Bt), j = new Float32Array(t, lt, S * 3), Z = new Uint32Array(t, Y, et), K = m / 2 / O;
      let J = L, ft = H;
      for (let yt = 0; yt < w; yt++) {
        C % 2e4 === 0 && s("Processing Splats", 0.3 + 0.6 * (C / i));
        const D = yt * ut;
        let pt;
        if (yt < H)
          pt = Math.floor(yt / p);
        else {
          const It = Z[J - L];
          yt >= ft + It && (J += 1, ft += It), pt = J;
        }
        let wt, mt, Lt;
        if (l === 0)
          wt = P.getFloat32(D + 0, !0), mt = P.getFloat32(D + 4, !0), Lt = P.getFloat32(D + 8, !0);
        else {
          const It = j[3 * pt + 0], Mt = j[3 * pt + 1], Ot = j[3 * pt + 2];
          wt = (P.getUint16(D + 0, !0) - O) * K + It, mt = (P.getUint16(D + 2, !0) - O) * K + Mt, Lt = (P.getUint16(D + 4, !0) - O) * K + Ot;
        }
        let Ct, dt, Ft;
        l === 0 ? (Ct = P.getFloat32(D + B.scaleOffsetBytes, !0), dt = P.getFloat32(D + B.scaleOffsetBytes + 4, !0), Ft = P.getFloat32(D + B.scaleOffsetBytes + 8, !0)) : (Ct = this.fromHalf(P.getUint16(D + B.scaleOffsetBytes, !0)), dt = this.fromHalf(P.getUint16(D + B.scaleOffsetBytes + 2, !0)), Ft = this.fromHalf(P.getUint16(D + B.scaleOffsetBytes + 4, !0))), Ct = Math.max(Ct, 1e-6), dt = Math.max(dt, 1e-6), Ft = Math.max(Ft, 1e-6);
        let kt, zt, At, Ht;
        l === 0 ? (kt = P.getFloat32(D + B.rotationOffsetBytes, !0), zt = P.getFloat32(D + B.rotationOffsetBytes + 4, !0), At = P.getFloat32(D + B.rotationOffsetBytes + 8, !0), Ht = P.getFloat32(D + B.rotationOffsetBytes + 12, !0)) : (kt = this.fromHalf(P.getUint16(D + B.rotationOffsetBytes, !0)), zt = this.fromHalf(P.getUint16(D + B.rotationOffsetBytes + 2, !0)), At = this.fromHalf(P.getUint16(D + B.rotationOffsetBytes + 4, !0)), Ht = this.fromHalf(P.getUint16(D + B.rotationOffsetBytes + 6, !0)));
        const Zt = P.getUint8(D + B.colorOffsetBytes) / 255, $t = P.getUint8(D + B.colorOffsetBytes + 1) / 255, Xt = P.getUint8(D + B.colorOffsetBytes + 2) / 255, jt = P.getUint8(D + B.colorOffsetBytes + 3) / 255;
        Q.set(X, zt, At, Ht, kt), Q.normalize(X, X), Pt.set(it, Ct, dt, Ft);
        const [Kt, Jt, Qt, te, ee, se] = Ut(X, it), St = C * F;
        g[St + 0] = a(wt), g[St + 1] = a(mt), g[St + 2] = a(Lt), g[St + 3] = a(jt), g[St + 4] = a(Kt), g[St + 5] = a(Jt), g[St + 6] = a(Qt), g[St + 7] = a(te), g[St + 8] = a(ee), g[St + 9] = a(se);
        const Rt = C * q, ne = (Zt - 0.5) / at, oe = ($t - 0.5) / at, re = (Xt - 0.5) / at;
        if (I[Rt + 0] = a(ne) | a(oe) << 16, I[Rt + 1] = a(re), nt > 0) {
          let It = Rt + 1, Mt = !0;
          for (let Ot = 0; Ot < $; Ot++) {
            const vt = st[Ot];
            let Tt;
            const Gt = D + B.sphericalHarmonicsOffsetBytes;
            if (l === 0)
              Tt = P.getFloat32(Gt + vt * 4, !0);
            else if (l === 1)
              Tt = this.fromHalf(P.getUint16(Gt + vt * 2, !0));
            else {
              const ae = P.getUint8(Gt + vt) / 255;
              Tt = x + ae * (y - x);
            }
            const qt = a(Tt);
            Mt ? (I[It] |= qt << 16, It++, Mt = !1) : (I[It] = qt, Mt = !0);
          }
        }
        R = Math.min(R, wt), v = Math.max(v, wt), ot = Math.min(ot, mt), A = Math.max(A, mt), k = Math.min(k, Lt), E = Math.max(E, Lt), tt += wt, V += mt, W += Lt, C++;
      }
      Y += _;
    }
    s("Finalizing", 0.95);
    const gt = C > 0 ? tt / C : 0, rt = C > 0 ? V / C : 0, ct = C > 0 ? W / C : 0;
    return console.log(`[KSplatLoader] Loaded ${C} splats.`), new _t({
      gaussianBuffer: g.buffer,
      shCoefsBuffer: I.buffer,
      numPoints: i,
      shDegree: G,
      bbox: { min: [R, ot, k], max: [v, A, E] },
      center: [gt, rt, ct],
      up: [0, 1, 0]
    });
  }
  canHandle(t) {
    return t.toLowerCase().endsWith(".ksplat");
  }
  getSupportedExtensions() {
    return [".ksplat"];
  }
  fromHalf(t) {
    const e = (t & 32768) >> 15, s = (t & 31744) >> 10, o = t & 1023;
    return s === 0 ? (e ? -1 : 1) * Math.pow(2, -14) * (o / 1024) : s === 31 ? o ? NaN : e ? -1 / 0 : 1 / 0 : (e ? -1 : 1) * Math.pow(2, s - 15) * (1 + o / 1024);
  }
}
class xe {
  async loadFile(t, e) {
    return this.loadBuffer(await t.arrayBuffer(), e);
  }
  async loadUrl(t, e) {
    const s = await fetch(t, { signal: e?.signal });
    if (!s.ok) throw new Error(`Failed to fetch: ${s.statusText}`);
    return this.loadBuffer(await s.arrayBuffer(), e);
  }
  async loadBuffer(t, e) {
    const s = (F, g, q) => {
      e?.onProgress?.({ stage: F, progress: g, message: q });
    };
    s("Parsing SPLAT", 0.1);
    const o = 32, n = new DataView(t), u = Math.floor(t.byteLength / o);
    t.byteLength % o !== 0 && console.warn("SPLAT file size not aligned to 32 bytes, truncating"), s("Loading SPLAT data", 0.3);
    const h = 10, f = new Uint16Array(u * h), d = 24, c = new Uint32Array(u * d), i = 0.28209479177387814, l = [1 / 0, 1 / 0, 1 / 0], x = [-1 / 0, -1 / 0, -1 / 0], y = [];
    for (let F = 0; F < u; F++) {
      F % 5e3 === 0 && s("Processing SPLAT points", 0.3 + 0.5 * (F / u));
      let g = F * o;
      const q = n.getFloat32(g, !0);
      g += 4;
      const I = n.getFloat32(g, !0);
      g += 4;
      const R = n.getFloat32(g, !0);
      g += 4, y.push([q, I, R]);
      const ot = n.getFloat32(g, !0);
      g += 4;
      const k = n.getFloat32(g, !0);
      g += 4;
      const v = n.getFloat32(g, !0);
      g += 4;
      const A = n.getUint8(g++) / 255, E = n.getUint8(g++) / 255, tt = n.getUint8(g++) / 255, V = n.getUint8(g++) / 255, W = n.getUint8(g++) / 255 * 2 - 1, Y = n.getUint8(g++) / 255 * 2 - 1, C = n.getUint8(g++) / 255 * 2 - 1, G = n.getUint8(g++) / 255 * 2 - 1, X = Q.fromValues(W, Y, C, G);
      Q.normalize(X, X);
      const it = new Float32Array([ot, k, v]), [at, st, gt, rt, ct, T] = Ut(X, it), b = F * h;
      f[b + 0] = a(q), f[b + 1] = a(I), f[b + 2] = a(R), f[b + 3] = a(V), f[b + 4] = a(at), f[b + 5] = a(st), f[b + 6] = a(gt), f[b + 7] = a(rt), f[b + 8] = a(ct), f[b + 9] = a(T);
      const w = F * d, r = (A - 0.5) / i, p = (E - 0.5) / i, S = (tt - 0.5) / i, m = a(r), U = a(p), O = a(S);
      c[w + 0] = m | U << 16, c[w + 1] = O, l[0] = Math.min(l[0], q), l[1] = Math.min(l[1], I), l[2] = Math.min(l[2], R), x[0] = Math.max(x[0], q), x[1] = Math.max(x[1], I), x[2] = Math.max(x[2], R);
    }
    s("Computing geometry", 0.9);
    const { centroid: N, normal: M } = Nt(y);
    return new _t({
      gaussianBuffer: f.buffer,
      shCoefsBuffer: c.buffer,
      numPoints: u,
      shDegree: 0,
      bbox: { min: l, max: x },
      center: [N[0], N[1], N[2]],
      up: M ? [M[0], M[1], M[2]] : [1, 0, 0]
    });
  }
  canHandle(t) {
    return t.toLowerCase().endsWith(".splat");
  }
  getSupportedExtensions() {
    return [".splat"];
  }
}
class we {
  async loadFile(t, e) {
    return this.loadBuffer(await t.arrayBuffer(), e);
  }
  async loadUrl(t, e) {
    const s = await fetch(t, { signal: e?.signal });
    if (!s.ok) throw new Error(`Failed to fetch SOG: ${s.statusText}`);
    return this.loadBuffer(await s.arrayBuffer(), e);
  }
  async loadBuffer(t, e) {
    return new DataView(t).getUint32(0, !0) === 67324752 ? this.loadCompressedSOG(t, e) : this.loadRawSOG(t, e);
  }
  async loadRawSOG(t, e) {
    const s = (V, W, Y) => {
      e?.onProgress?.({ stage: V, progress: W, message: Y });
    };
    s("Parsing SOG header", 0.1);
    const o = new DataView(t);
    let n = 0;
    const u = o.getUint32(n, !0);
    if (n += 4, u !== 1397704448 && u !== 4673363)
      throw new Error("Invalid SOG file");
    const h = o.getUint32(n, !0);
    n += 4;
    const f = o.getUint32(n, !0);
    n += 4;
    const d = o.getUint32(n, !0);
    n += 4, console.log(`[SOGLoader] Ver:${h}, Points:${f}, SH Degree:${d}`), s("Loading SOG data", 0.3);
    const c = 10, i = new Uint16Array(f * c), l = 24, x = new Uint32Array(f * l);
    let y = 1 / 0, N = 1 / 0, M = 1 / 0, F = -1 / 0, g = -1 / 0, q = -1 / 0, I = 0, R = 0, ot = 0;
    const k = Q.create(), v = Pt.create();
    for (let V = 0; V < f; V++) {
      V % 1e4 === 0 && s("Processing SOG points", 0.3 + 0.6 * (V / f));
      const W = o.getFloat32(n, !0);
      n += 4;
      const Y = o.getFloat32(n, !0);
      n += 4;
      const C = o.getFloat32(n, !0);
      n += 4;
      const G = o.getFloat32(n, !0);
      n += 4;
      const X = o.getFloat32(n, !0);
      n += 4;
      const it = o.getFloat32(n, !0);
      n += 4;
      const at = Math.exp(G), st = Math.exp(X), gt = Math.exp(it), rt = o.getFloat32(n, !0);
      n += 4;
      const ct = o.getFloat32(n, !0);
      n += 4;
      const T = o.getFloat32(n, !0);
      n += 4;
      const b = o.getFloat32(n, !0);
      n += 4;
      const w = o.getFloat32(n, !0);
      n += 4;
      const r = Wt(w);
      Q.set(k, ct, T, b, rt), Q.normalize(k, k), Pt.set(v, at, st, gt);
      const [p, S, m, U, O, L] = Ut(k, v), H = V * c;
      i[H + 0] = a(W), i[H + 1] = a(Y), i[H + 2] = a(C), i[H + 3] = a(r), i[H + 4] = a(p), i[H + 5] = a(S), i[H + 6] = a(m), i[H + 7] = a(U), i[H + 8] = a(O), i[H + 9] = a(L);
      const et = 3 * Math.pow(d + 1, 2), nt = V * l;
      for (let $ = 0; $ < et && $ < l * 2; $++) {
        const B = o.getFloat32(n, !0);
        n += 4;
        const ut = a(B), ht = Math.floor($ / 2);
        $ % 2 === 1 ? x[nt + ht] |= ut << 16 : x[nt + ht] = ut;
      }
      if (et > l * 2) {
        const $ = et - l * 2;
        n += $ * 4;
      }
      y = Math.min(y, W), F = Math.max(F, W), N = Math.min(N, Y), g = Math.max(g, Y), M = Math.min(M, C), q = Math.max(q, C), I += W, R += Y, ot += C;
    }
    s("Finalizing", 0.9);
    const A = I / f, E = R / f, tt = ot / f;
    return new _t({
      gaussianBuffer: i.buffer,
      shCoefsBuffer: x.buffer,
      numPoints: f,
      shDegree: d,
      bbox: { min: [y, N, M], max: [F, g, q] },
      center: [A, E, tt],
      up: [0, 1, 0]
    });
  }
  async loadCompressedSOG(t, e) {
    const s = (w, r) => e?.onProgress?.({ stage: "SOG-WebP", progress: w, message: r });
    s(0.1, "Unzipping SOG");
    const o = await new Promise((w, r) => {
      ge(new Uint8Array(t), (p, S) => {
        p ? r(p) : w(S);
      });
    });
    if (!o["meta.json"]) throw new Error("Invalid SOG ZIP: missing meta.json");
    const n = JSON.parse(new TextDecoder().decode(o["meta.json"])), u = n.count;
    console.log(`[SOGLoader] Compressed SOG, Points: ${u}`);
    const h = async (w) => {
      if (!o[w]) throw new Error(`Missing texture: ${w}`);
      const r = new Blob([new Uint8Array(o[w])], { type: "image/webp" }), p = await createImageBitmap(r);
      let S;
      const { width: m, height: U } = p;
      if (typeof OffscreenCanvas < "u") {
        S = new OffscreenCanvas(m, U).getContext("2d"), S?.drawImage(p, 0, 0);
        const L = S?.getImageData(0, 0, m, U);
        return { data: new Uint8Array(L.data.buffer), width: m, height: U };
      } else {
        const O = document.createElement("canvas");
        O.width = m, O.height = U, S = O.getContext("2d"), S?.drawImage(p, 0, 0);
        const L = S?.getImageData(0, 0, m, U);
        return { data: new Uint8Array(L.data.buffer), width: m, height: U };
      }
    };
    s(0.2, "Decoding Base Textures");
    const [f, d, c, i, l] = await Promise.all([
      h(n.means.files[0]),
      h(n.means.files[1]),
      h(n.quats.files[0]),
      h(n.scales.files[0]),
      h(n.sh0.files[0])
    ]);
    let x = 0, y = null, N = null, M = 0, F = [], g = null;
    if (n.shN) {
      const w = n.shN;
      x = w.bands, console.log(`[SOGLoader] Found shN (Vector Quantized). Degree: ${x}`), s(0.4, "Decoding SH Vector Tables");
      let r;
      [N, r] = await Promise.all([
        h(w.files[1]),
        h(w.files[0])
      ]);
      const p = new Float32Array(w.codebook), S = w.count, m = x === 3 ? 15 : x === 2 ? 8 : 3;
      M = m * 3, y = new Float32Array(S * M);
      const U = r.data;
      for (let O = 0; O < S; O++)
        for (let L = 0; L < m; L++) {
          const H = (O * m + L) * 4, et = U[H + 0], nt = U[H + 1], $ = U[H + 2], B = O * M + L * 3;
          y[B + 0] = p[et], y[B + 1] = p[nt], y[B + 2] = p[$];
        }
    } else if (n.sh_rest && n.sh_rest.files.length > 0) {
      console.log("[SOGLoader] Found sh_rest (Scalar Quantized)."), g = new Float32Array(n.sh_rest.codebook), F = await Promise.all(n.sh_rest.files.map((r) => h(r)));
      const w = 3 + F.length * 3;
      x = Math.round(Math.sqrt(w / 3) - 1);
    } else
      console.log("[SOGLoader] No high-order SH data. Degree: 0");
    const q = 10, I = new Uint16Array(u * q), R = 24, ot = new Uint32Array(u * R), k = Q.create(), v = Pt.create(), A = n.means.mins[0], E = n.means.maxs[0] - A || 1, tt = n.means.mins[1], V = n.means.maxs[1] - tt || 1, W = n.means.mins[2], Y = n.means.maxs[2] - W || 1, C = new Float32Array(n.scales.codebook), G = new Float32Array(n.sh0.codebook);
    let X = 1 / 0, it = 1 / 0, at = 1 / 0, st = -1 / 0, gt = -1 / 0, rt = -1 / 0, ct = 0, T = 0, b = 0;
    s(0.6, "Reconstructing Gaussians");
    for (let w = 0; w < u; w++) {
      w % 5e4 === 0 && s(0.6 + 0.3 * (w / u), "Reconstructing...");
      const r = w * 4, p = f.data[r + 0] | d.data[r + 0] << 8, S = f.data[r + 1] | d.data[r + 1] << 8, m = f.data[r + 2] | d.data[r + 2] << 8, U = this.invLogTransform(A + E * (p / 65535)), O = this.invLogTransform(tt + V * (S / 65535)), L = this.invLogTransform(W + Y * (m / 65535)), H = c.data[r + 3];
      this.unpackQuatToRef(c.data[r], c.data[r + 1], c.data[r + 2], H, k);
      const et = Math.exp(C[i.data[r + 0]]), nt = Math.exp(C[i.data[r + 1]]), $ = Math.exp(C[i.data[r + 2]]);
      Pt.set(v, et, nt, $);
      const [B, ut, ht, xt, Bt, lt] = Ut(k, v), bt = l.data[r + 3] / 255, _ = w * q;
      I[_ + 0] = a(U), I[_ + 1] = a(O), I[_ + 2] = a(L), I[_ + 3] = a(bt), I[_ + 4] = a(B), I[_ + 5] = a(ut), I[_ + 6] = a(ht), I[_ + 7] = a(xt), I[_ + 8] = a(Bt), I[_ + 9] = a(lt);
      let P = w * R, j = 0;
      const Z = (K) => {
        const J = a(K), ft = P + (j >> 1);
        (j & 1) === 1 ? ot[ft] |= J << 16 : ot[ft] = J, j++;
      };
      if (Z(G[l.data[r + 0]]), Z(G[l.data[r + 1]]), Z(G[l.data[r + 2]]), y && N) {
        const K = w * 4, J = N.data[K + 0], ft = N.data[K + 1], D = (J | ft << 8) * M;
        for (let pt = 0; pt < M; pt++)
          Z(y[D + pt]);
      } else if (g && F.length > 0)
        for (let K = 0; K < F.length; K++) {
          const J = F[K].data;
          Z(g[J[r + 0]]), Z(g[J[r + 1]]), Z(g[J[r + 2]]);
        }
      X = Math.min(X, U), st = Math.max(st, U), it = Math.min(it, O), gt = Math.max(gt, O), at = Math.min(at, L), rt = Math.max(rt, L), ct += U, T += O, b += L;
    }
    return new _t({
      gaussianBuffer: I.buffer,
      shCoefsBuffer: ot.buffer,
      numPoints: u,
      shDegree: x,
      bbox: { min: [X, it, at], max: [st, gt, rt] },
      center: [ct / u, T / u, b / u],
      up: [0, 1, 0]
    });
  }
  invLogTransform(t) {
    const e = Math.abs(t), s = Math.exp(e) - 1;
    return t < 0 ? -s : s;
  }
  unpackQuatToRef(t, e, s, o, n) {
    const u = o - 252;
    if (u < 0 || u > 3) {
      Q.set(n, 0, 0, 0, 1);
      return;
    }
    const h = t / 255 * 2 - 1, f = e / 255 * 2 - 1, d = s / 255 * 2 - 1, c = 1.41421356;
    let i = 0, l = 0, x = 0, y = 0;
    u === 0 ? (l = h / c, x = f / c, y = d / c, i = Math.sqrt(Math.max(0, 1 - (l * l + x * x + y * y)))) : u === 1 ? (i = h / c, x = f / c, y = d / c, l = Math.sqrt(Math.max(0, 1 - (i * i + x * x + y * y)))) : u === 2 ? (i = h / c, l = f / c, y = d / c, x = Math.sqrt(Math.max(0, 1 - (i * i + l * l + y * y)))) : (i = h / c, l = f / c, x = d / c, y = Math.sqrt(Math.max(0, 1 - (i * i + l * l + x * x)))), Q.set(n, l, x, y, i), Q.normalize(n, n);
  }
  canHandle(t) {
    return t.toLowerCase().endsWith(".sog");
  }
  getSupportedExtensions() {
    return [".sog"];
  }
}
class Yt {
  static CHUNK_SIZE = 256;
  async loadFile(t, e) {
    const s = await t.arrayBuffer();
    return this.loadBuffer(s, e);
  }
  async loadUrl(t, e) {
    const s = await fetch(t, { signal: e?.signal });
    if (!s.ok) throw new Error(`Failed to fetch compressed PLY: ${s.status}`);
    const o = await s.arrayBuffer();
    return this.loadBuffer(o, e);
  }
  canHandle(t) {
    return t.toLowerCase().endsWith(".compressed.ply");
  }
  getSupportedExtensions() {
    return [".compressed.ply"];
  }
  async loadBuffer(t, e) {
    const s = new TextDecoder().decode(t.slice(0, Math.min(1048576, t.byteLength))), o = s.indexOf("end_header") + 10 + 1, n = s.slice(0, o).split(/\r?\n/);
    let u = "binary_little_endian", h = 0, f = 0, d = 0, c = !1;
    for (const r of n)
      r.startsWith("format ") && (r.includes("binary_little_endian") ? u = "binary_little_endian" : r.includes("binary_big_endian") && (u = "binary_big_endian")), r.startsWith("element vertex") && (h = parseInt(r.split(/\s+/)[2])), r.startsWith("element chunk") && (f = parseInt(r.split(/\s+/)[2])), r.startsWith("element sh") ? c = !0 : c && r.startsWith("property") ? d++ : c && r.startsWith("element") && (c = !1);
    const i = u === "binary_little_endian", l = new DataView(t, o), x = 72, y = [];
    for (let r = 0; r < f; r++) {
      const p = r * x;
      y.push({
        minPos: [
          l.getFloat32(p + 0, i),
          l.getFloat32(p + 4, i),
          l.getFloat32(p + 8, i)
        ],
        maxPos: [
          l.getFloat32(p + 12, i),
          l.getFloat32(p + 16, i),
          l.getFloat32(p + 20, i)
        ],
        minScale: [
          l.getFloat32(p + 24, i),
          l.getFloat32(p + 28, i),
          l.getFloat32(p + 32, i)
        ],
        maxScale: [
          l.getFloat32(p + 36, i),
          l.getFloat32(p + 40, i),
          l.getFloat32(p + 44, i)
        ],
        minColor: [
          l.getFloat32(p + 48, i),
          l.getFloat32(p + 52, i),
          l.getFloat32(p + 56, i)
        ],
        maxColor: [
          l.getFloat32(p + 60, i),
          l.getFloat32(p + 64, i),
          l.getFloat32(p + 68, i)
        ]
      });
    }
    const N = f * x, M = 16, F = N + h * M, g = d, q = 10;
    let I, R;
    d === 9 ? (I = 1, R = 12) : d === 24 ? (I = 2, R = 27) : d === 45 ? (I = 3, R = 48) : (I = 0, R = 3);
    const ot = Math.ceil(R / 2), k = new Uint16Array(h * q), v = new Uint32Array(h * ot);
    let A = 1 / 0, E = 1 / 0, tt = 1 / 0, V = -1 / 0, W = -1 / 0, Y = -1 / 0;
    const C = (r, p, S) => r * (1 - S) + p * S, G = (r, p) => {
      const S = (1 << p) - 1;
      return (r & S) / S;
    }, X = (r) => ({
      x: G(r >>> 21, 11),
      y: G(r >>> 11, 10),
      z: G(r, 11)
    }), it = (r) => ({
      r: G(r >>> 24, 8),
      g: G(r >>> 16, 8),
      b: G(r >>> 8, 8),
      a: G(r, 8)
    }), at = (r) => {
      const p = 1 / (Math.sqrt(2) * 0.5), S = (G(r >>> 20, 10) - 0.5) * p, m = (G(r >>> 10, 10) - 0.5) * p, U = (G(r, 10) - 0.5) * p, O = Math.sqrt(Math.max(0, 1 - (S * S + m * m + U * U)));
      switch (r >>> 30) {
        case 0:
          return { w: O, x: S, y: m, z: U };
        case 1:
          return { w: S, x: O, y: m, z: U };
        case 2:
          return { w: S, x: m, y: O, z: U };
        default:
          return { w: S, x: m, y: U, z: O };
      }
    }, st = 0.28209479177387814, gt = (r, p, S) => {
      const m = new Float32Array(R);
      m[0] = (p[0] - 0.5) / st, m[1] = (p[1] - 0.5) / st, m[2] = (p[2] - 0.5) / st;
      const U = S.length / 3;
      for (let L = 0; L < U; L++) {
        const H = 3 + L * 3;
        if (H + 2 >= m.length) break;
        const et = L, nt = L + U, $ = L + U * 2, B = S[et], ut = S[nt], ht = S[$];
        m[H + 0] = (B / 255 - 0.5) * 8, m[H + 1] = (ut / 255 - 0.5) * 8, m[H + 2] = (ht / 255 - 0.5) * 8;
      }
      const O = r * ot;
      for (let L = 0; L < m.length; L += 2) {
        const H = a(m[L]), et = L + 1 < m.length ? a(m[L + 1]) : 0;
        v[O + (L >> 1)] = et << 16 | H;
      }
    }, rt = Q.create(), ct = Pt.create();
    for (let r = 0; r < h; r++) {
      const p = N + r * M, S = F + r * g, m = Math.floor(r / Yt.CHUNK_SIZE), U = l.getUint32(p + 0, i), O = l.getUint32(p + 4, i), L = l.getUint32(p + 8, i), H = l.getUint32(p + 12, i), et = X(U), nt = at(O), $ = X(L), B = it(H), ut = C(y[m].minPos[0], y[m].maxPos[0], et.x), ht = C(y[m].minPos[1], y[m].maxPos[1], et.y), xt = C(y[m].minPos[2], y[m].maxPos[2], et.z), Bt = C(y[m].minScale[0], y[m].maxScale[0], $.x), lt = C(y[m].minScale[1], y[m].maxScale[1], $.y), bt = C(y[m].minScale[2], y[m].maxScale[2], $.z), _ = Math.exp(Bt), P = Math.exp(lt), j = Math.exp(bt), Z = C(y[m].minColor[0], y[m].maxColor[0], B.r), K = C(y[m].minColor[1], y[m].maxColor[1], B.g), J = C(y[m].minColor[2], y[m].maxColor[2], B.b), ft = [Z, K, J], yt = B.a;
      Q.set(rt, nt.x, nt.y, nt.z, nt.w), Pt.set(ct, _, P, j), Q.normalize(rt, rt);
      const [D, pt, wt, mt, Lt, Ct] = Ut(rt, ct), dt = r * q;
      k[dt + 0] = a(ut), k[dt + 1] = a(ht), k[dt + 2] = a(xt), k[dt + 3] = a(yt), k[dt + 4] = a(D), k[dt + 5] = a(pt), k[dt + 6] = a(wt), k[dt + 7] = a(mt), k[dt + 8] = a(Lt), k[dt + 9] = a(Ct);
      const Ft = new Uint8Array(t, o + S, g);
      gt(r, ft, Ft), A = Math.min(A, ut), E = Math.min(E, ht), tt = Math.min(tt, xt), V = Math.max(V, ut), W = Math.max(W, ht), Y = Math.max(Y, xt);
    }
    const T = [A, E, tt], b = [V, W, Y], w = [(A + V) / 2, (E + W) / 2, (tt + Y) / 2];
    return new _t({
      gaussianBuffer: k.buffer,
      shCoefsBuffer: v.buffer,
      numPoints: h,
      shDegree: I,
      bbox: { min: T, max: b },
      center: w,
      up: [0, 1, 0]
    });
  }
}
class Vt {
  _object3D;
  _bbox;
  _modelType;
  constructor(t, e = "unknown") {
    this._object3D = t, this._modelType = e, this._bbox = this.calculateBoundingBox(t);
  }
  // 实现 ThreeJSDataSource 接口
  object3D() {
    return this._object3D;
  }
  modelType() {
    return this._modelType;
  }
  bbox() {
    return this._bbox;
  }
  calculateBoundingBox(t) {
    const e = new Dt.Box3().setFromObject(t);
    return {
      min: [e.min.x, e.min.y, e.min.z],
      max: [e.max.x, e.max.y, e.max.z]
    };
  }
}
class Et {
  loader;
  constructor(t) {
    this.loader = t;
  }
  /**
   * 公共处理：保留自带材质，如无材质则使用回退材质，并开启阴影
   */
  applyShadowsAndMaterial(t, e) {
    t.traverse((s) => {
      s && s.isMesh && (!s.material && e && (s.material = e), "castShadow" in s && (s.castShadow = !0), "receiveShadow" in s && (s.receiveShadow = !0));
    });
  }
  async loadFile(t, e) {
    const s = URL.createObjectURL(t);
    try {
      const o = await this.loadFromUrl(s, e);
      return new Vt(o, this.getModelType());
    } finally {
      URL.revokeObjectURL(s);
    }
  }
  async loadUrl(t, e) {
    const s = await this.loadFromUrl(t, e);
    return new Vt(s, this.getModelType());
  }
  async loadBuffer(t, e) {
    throw new Error("Buffer loading not supported for Three.js models");
  }
  canHandle(t, e) {
    return this.getSupportedExtensions().some(
      (s) => t.toLowerCase().endsWith(s)
    );
  }
}
class Se extends Et {
  constructor() {
    super(new le());
  }
  getSupportedExtensions() {
    return [".gltf", ".glb"];
  }
  getModelType() {
    return "gltf";
  }
  async loadFromUrl(t, e) {
    return new Promise((s, o) => {
      this.loader.load(
        t,
        (n) => {
          this.applyShadowsAndMaterial(n.scene), s(n.scene);
        },
        (n) => {
          e?.onProgress && e.onProgress({
            progress: n.loaded / n.total,
            stage: "Loading GLTF/GLB..."
          });
        },
        o
      );
    });
  }
}
class Pe extends Et {
  constructor() {
    super(new fe());
  }
  getSupportedExtensions() {
    return [".obj"];
  }
  getModelType() {
    return "obj";
  }
  async loadFromUrl(t, e) {
    return new Promise((s, o) => {
      this.loader.load(
        t,
        (n) => {
          this.applyShadowsAndMaterial(n), s(n);
        },
        (n) => {
          e?.onProgress && e.onProgress({
            progress: n.loaded / n.total,
            stage: "Loading OBJ..."
          });
        },
        o
      );
    });
  }
}
class be extends Et {
  constructor() {
    super(new de());
  }
  getSupportedExtensions() {
    return [".fbx"];
  }
  getModelType() {
    return "fbx";
  }
  async loadFromUrl(t, e) {
    return new Promise((s, o) => {
      this.loader.load(
        t,
        (n) => {
          this.applyShadowsAndMaterial(n), s(n);
        },
        (n) => {
          e?.onProgress && e.onProgress({
            progress: n.loaded / n.total,
            stage: "Loading FBX..."
          });
        },
        o
      );
    });
  }
}
class Be extends Et {
  constructor() {
    super(new ue());
  }
  getSupportedExtensions() {
    return [".stl"];
  }
  getModelType() {
    return "stl";
  }
  async loadFromUrl(t, e) {
    return new Promise((s, o) => {
      this.loader.load(
        t,
        (n) => {
          const u = new Dt.MeshStandardMaterial({ color: 8947848 }), h = new Dt.Mesh(n, u);
          this.applyShadowsAndMaterial(h, u), s(h);
        },
        (n) => {
          e?.onProgress && e.onProgress({
            progress: n.loaded / n.total,
            stage: "Loading STL..."
          });
        },
        o
      );
    });
  }
}
class Le extends Et {
  constructor() {
    super(new he());
  }
  getSupportedExtensions() {
    return [".ply"];
  }
  getModelType() {
    return "ply";
  }
  async loadFromUrl(t, e) {
    return new Promise((s, o) => {
      this.loader.load(
        t,
        (n) => {
          const u = new Dt.MeshStandardMaterial({ vertexColors: !0 }), h = new Dt.Mesh(n, u);
          this.applyShadowsAndMaterial(h, u), s(h);
        },
        (n) => {
          e?.onProgress && e.onProgress({
            progress: n.loaded / n.total,
            stage: "Loading PLY..."
          });
        },
        o
      );
    });
  }
}
function Ie() {
  return [
    new Se(),
    new Pe(),
    new be(),
    new Be(),
    new Le()
  ];
}
class Ce {
  gaussianLoaders = /* @__PURE__ */ new Map();
  threeLoaders = /* @__PURE__ */ new Map();
  constructor() {
    this.register(
      new me(),
      [".ply"],
      "gaussian"
      /* GAUSSIAN */
    ), this.register(
      new pe(),
      [".spz"],
      "gaussian"
      /* GAUSSIAN */
    ), this.register(
      new ye(),
      [".ksplat"],
      "gaussian"
      /* GAUSSIAN */
    ), this.register(
      new xe(),
      [".splat"],
      "gaussian"
      /* GAUSSIAN */
    ), this.register(
      new we(),
      [".sog"],
      "gaussian"
      /* GAUSSIAN */
    ), this.register(
      new Yt(),
      [".compressed.ply"],
      "gaussian"
      /* GAUSSIAN */
    ), Ie().forEach((e) => {
      const s = e.getSupportedExtensions();
      this.register(
        e,
        s,
        "three"
        /* THREE */
      );
    });
  }
  /**
   * Register a loader for specific file extensions
   * @param loader - The loader instance
   * @param extensions - Array of file extensions (e.g., ['.ply', '.glb'])
   * @param type - Loader type: GAUSSIAN or THREE
   */
  register(t, e, s = "three") {
    const o = s === "gaussian" ? this.gaussianLoaders : this.threeLoaders;
    for (const n of e)
      o.set(n.toLowerCase(), t);
  }
  /**
   * 核心决策方法：根据文件名和配置获取 Loader
   * 这里是唯一处理 "后缀名 -> Loader" 映射逻辑的地方
   */
  getLoader(t, e, s) {
    const o = t.toLowerCase(), n = this.getFileExtension(o);
    if (o.endsWith(".compressed.ply"))
      return this.gaussianLoaders.get(".compressed.ply") || null;
    s?.isGaussian;
    const u = s?.isGaussian === !1;
    if (u)
      return this.threeLoaders.get(n) || null;
    let h = this.gaussianLoaders.get(n);
    if (h || (h = this.threeLoaders.get(n), h)) return h;
    if (!u) {
      for (const [, f] of this.gaussianLoaders)
        if (f.canHandle(t, e)) return f;
    }
    for (const [, f] of this.threeLoaders)
      if (f.canHandle(t, e)) return f;
    return null;
  }
  /**
   * 辅助方法：对外暴露的异步 Loader 获取 (为了兼容性)
   * 实际上就是 loadFile 逻辑的前半部分
   */
  async getLoaderForFile(t, e) {
    let s;
    return t.name.toLowerCase().endsWith(".ply") && (s = await this.is3dgsPly(t)), this.getLoader(t.name, e, { isGaussian: s });
  }
  /**
   * Get all supported extensions
   */
  getAllSupportedExtensions() {
    const t = /* @__PURE__ */ new Set();
    for (const e of this.gaussianLoaders.keys())
      t.add(e);
    for (const e of this.threeLoaders.keys())
      t.add(e);
    return Array.from(t);
  }
  /**
   * 文件加载入口
   * 负责处理 "文件内容检测" 这一异步步骤，然后委托给 getLoader
   */
  async loadFile(t, e = {}) {
    if (e.isGaussian === void 0 && t.name.toLowerCase().endsWith(".ply")) {
      const o = await this.is3dgsPly(t);
      e.isGaussian = o;
    }
    const s = this.getLoader(t.name, t.type, e);
    if (!s)
      throw new Error(`Unsupported file format: ${t.name}`);
    return s.loadFile(t, e);
  }
  /**
   * URL 加载入口
   */
  async loadUrl(t, e = {}) {
    const s = this.getLoader(t, void 0, e);
    if (!s)
      throw new Error(`Unsupported file format for URL: ${t}`);
    return s.loadUrl(t, e);
  }
  /**
   * Load from buffer - requires explicit format detection
   */
  async loadBuffer(t, e) {
    const s = this.detectFormatFromBuffer(t);
    if (!s)
      throw new Error("Unable to detect file format from buffer");
    return s.loadBuffer(t, e);
  }
  /**
   * Check if any registered loader can handle this file
   */
  canHandle(t, e, s) {
    return this.getLoader(t, e, s) !== null;
  }
  /**
   * Get supported extensions (aggregated from all loaders)
   */
  getSupportedExtensions() {
    return this.getAllSupportedExtensions();
  }
  // ========== Private Helpers ==========
  /**
   * Extract file extension from filename
   */
  getFileExtension(t) {
    const e = t.lastIndexOf(".");
    return e >= 0 ? t.slice(e).toLowerCase() : "";
  }
  /**
   * Attempt to detect file format from buffer content
   * 通过文件头魔数检测格式
   */
  detectFormatFromBuffer(t) {
    const e = new DataView(t), s = new TextDecoder().decode(t.slice(0, 100));
    if (s.startsWith(`ply
`) || s.startsWith(`ply\r
`))
      return this.is3dgsPlyFromHeader(s) ? this.gaussianLoaders.get(".ply") || null : this.threeLoaders.get(".ply") || null;
    if (t.byteLength >= 2) {
      const o = e.getUint8(0), n = e.getUint8(1);
      if (o === 31 && n === 139)
        return this.gaussianLoaders.get(".spz") || null;
    }
    return t.byteLength >= 4 && String.fromCharCode(
      e.getUint8(0),
      e.getUint8(1),
      e.getUint8(2),
      e.getUint8(3)
    ) === "KSPL" ? this.gaussianLoaders.get(".ksplat") || null : t.byteLength >= 4 && e.getUint32(0, !0) === 67324752 ? this.gaussianLoaders.get(".sog") || null : (t.byteLength > 0 && t.byteLength % 32, null);
  }
  /**
   * Read file header to detect format
   */
  async readFileHeader(t, e = 4096) {
    const o = await t.slice(0, e).arrayBuffer();
    return new TextDecoder("utf-8").decode(o || new ArrayBuffer(0));
  }
  /**
   * Check if a PLY file is a 3DGS (3D Gaussian Splatting) file
   * This function checks for required 3DGS properties in the PLY header
   */
  async is3dgsPly(t) {
    try {
      const e = await this.readFileHeader(t), s = this.is3dgsPlyFromHeader(e);
      return console.log(`PLY 文件 ${t.name} 3DGS 检测结果: ${s}`), s;
    } catch (e) {
      return console.warn("读取 PLY 头信息失败，按非 3DGS 处理:", t.name, e), !1;
    }
  }
  /**
   * Check if a PLY header string indicates a 3DGS file
   * This is a synchronous version that works with header strings
   */
  is3dgsPlyFromHeader(t) {
    const e = t.toLowerCase();
    return e.startsWith("ply") ? [
      "property float opacity",
      "property float scale_0",
      "property float scale_1",
      "property float scale_2",
      "property float rot_0",
      "property float rot_1",
      "property float rot_2",
      "property float rot_3"
    ].every((n) => e.includes(n)) : !1;
  }
}
function Fe() {
  return new Ce();
}
const Re = Fe();
var Ue = /* @__PURE__ */ ((z) => (z.PLY = "ply", z.SPZ = "spz", z.KSPLAT = "ksplat", z.SPLAT = "splat", z.SOG = "sog", z.COMPRESSED_PLY = "compressed.ply", z))(Ue || {});
function _e() {
  return [".ply", ".spz", ".ksplat", ".splat", ".sog", ".compressed.ply"];
}
function ve(z) {
  const t = z.toLowerCase();
  return _e().some((e) => t.endsWith(e));
}
function Ge(z) {
  const t = z.toLowerCase();
  return t.endsWith(".compressed.ply") ? "compressed.ply" : t.endsWith(".ksplat") ? "ksplat" : t.endsWith(".splat") ? "splat" : t.endsWith(".spz") ? "spz" : t.endsWith(".sog") ? "sog" : t.endsWith(".ply") ? "ply" : null;
}
function Ne(z) {
  return "gaussianBuffer" in z && "shCoefsBuffer" in z && "numPoints" in z && "shDegree" in z;
}
export {
  Ue as G,
  Vt as T,
  Re as a,
  Ne as b,
  Ge as d,
  ve as i
};
