import { vec3 as u, quat as m, mat3 as x, mat4 as M } from "gl-matrix";
import { d as w, f as d } from "./visionary-core.src-utils.js";
import * as V from "three/webgpu";
import "three/examples/jsm/loaders/RGBELoader.js";
class y {
  fovx;
  // radians
  fovy;
  // radians
  znear;
  zfar;
  /** fov ratio to viewport ratio (used to preserve FOV on resize) */
  fov2viewRatio;
  constructor(t, o, s, v) {
    const a = (typeof t[0] == "number", t[0]), n = (typeof t[1] == "number", t[1]), f = (typeof o[0] == "number", o[0]), h = (typeof o[1] == "number", o[1]), l = a / n, i = f / h;
    this.fovx = f, this.fovy = h, this.znear = s, this.zfar = v, this.fov2viewRatio = l / i;
  }
  clone() {
    const t = new y([1, 1], [this.fovx, this.fovy], this.znear, this.zfar);
    return t.fov2viewRatio = this.fov2viewRatio, t;
  }
  /** Maintain FOV consistency when viewport changes. */
  resize(t) {
    const o = (typeof t[0] == "number", t[0]), s = (typeof t[1] == "number", t[1]), a = o / s / this.fov2viewRatio, n = 2 * Math.atan(Math.tan(this.fovy * 0.5) * (a / (this.fovx / this.fovy)));
    Math.abs(this.fovx / this.fovy - a) < 1e-6 || (this.fovy = n, this.fovx = this.fovy * a);
  }
  projectionMatrix() {
    return A(this.znear, this.zfar, this.fovx, this.fovy);
  }
  focal(t) {
    const o = (typeof t[0] == "number", t[0]), s = (typeof t[1] == "number", t[1]);
    return [d(this.fovx, o), d(this.fovy, s)];
  }
  lerp(t, o) {
    const s = this.clone();
    return s.fovx = this.fovx * (1 - o) + t.fovx * o, s.fovy = this.fovy * (1 - o) + t.fovy * o, s.znear = this.znear * (1 - o) + t.znear * o, s.zfar = this.zfar * (1 - o) + t.zfar * o, s.fov2viewRatio = this.fov2viewRatio * (1 - o) + t.fov2viewRatio * o, s;
  }
}
class j {
  positionV;
  rotationQ;
  projection;
  constructor(t, o, s) {
    this.positionV = u.clone(t), this.rotationQ = m.clone(o), this.projection = s;
  }
  static default() {
    return new j(
      u.fromValues(0, 0, -1),
      m.fromValues(0, 0, 0, 1),
      new y([1, 1], [w(45), w(45)], 0.1, 100)
    );
  }
  fitNearFar(t) {
    const o = t.center(), s = t.radius(), v = u.distance(this.positionV, o), a = v + s, n = Math.max(v - s, a / 1e3);
    this.projection.zfar = a * 1.5, this.projection.znear = n;
  }
  viewMatrix() {
    const t = x.create();
    return x.fromQuat(t, this.rotationQ), z(t, this.positionV);
  }
  projMatrix() {
    return this.projection.projectionMatrix();
  }
  position() {
    return u.clone(this.positionV);
  }
  frustumPlanes() {
    const t = this.projMatrix(), o = this.viewMatrix(), s = M.create();
    M.multiply(s, t, o);
    const v = [s[0], s[4], s[8], s[12]], a = [s[1], s[5], s[9], s[13]], n = [s[2], s[6], s[10], s[14]], f = [s[3], s[7], s[11], s[15]], h = (e, c) => new Float32Array([e[0] + c[0], e[1] + c[1], e[2] + c[2], e[3] + c[3]]), l = (e, c) => new Float32Array([e[0] - c[0], e[1] - c[1], e[2] - c[2], e[3] - c[3]]), i = (e) => {
      const c = Math.hypot(e[0], e[1], e[2]);
      return c > 0 ? new Float32Array([e[0] / c, e[1] / c, e[2] / c, e[3] / c]) : e;
    };
    return {
      left: i(h(f, v)),
      right: i(l(f, v)),
      bottom: i(h(f, a)),
      top: i(l(f, a)),
      near: i(h(f, n)),
      far: i(l(f, n))
    };
  }
}
function z(r, t) {
  const o = M.create();
  o[0] = r[0], o[1] = r[1], o[2] = r[2], o[3] = 0, o[4] = r[3], o[5] = r[4], o[6] = r[5], o[7] = 0, o[8] = r[6], o[9] = r[7], o[10] = r[8], o[11] = 0;
  const s = u.create();
  return u.transformMat3(s, t, r), o[12] = -s[0], o[13] = -s[1], o[14] = -s[2], o[15] = 1, o;
}
function A(r, t, o, s) {
  const v = Math.tan(s * 0.5), a = Math.tan(o * 0.5), n = v * r, f = -n, h = a * r, l = -h, i = M.create();
  return i[0] = 2 * r / (h - l), i[5] = 2 * r / (n - f), i[8] = (h + l) / (h - l), i[9] = (n + f) / (n - f), i[11] = 1, i[10] = t / (t - r), i[14] = -(t * r) / (t - r), i[15] = 0, i;
}
class Y {
  viewMat = M.create();
  projMat = M.create();
  _position = new Float32Array(3);
  _focal = [0, 0];
  _viewport = [1, 1];
  // Flags kept for compatibility; current update() follows DirectCameraAdapter
  transposeRotation = !0;
  flipProjY = !1;
  flipProjX = !1;
  compensatePreprocessYFlip = !0;
  // counter the single Y-flip in preprocess packing
  // Minimal projection object with focal() method as expected by preprocess
  projection = {
    focal: (t) => this._focal
  };
  /** Update from a Three.js PerspectiveCamera and viewport in pixels */
  update(t, o) {
    t.updateMatrixWorld(), t.updateProjectionMatrix();
    const s = t.matrixWorldInverse.elements;
    for (let i = 0; i < 16; i++) this.viewMat[i] = s[i];
    this.viewMat[0] = -this.viewMat[0], this.viewMat[4] = -this.viewMat[4], this.viewMat[8] = -this.viewMat[8], this.viewMat[12] = -this.viewMat[12], this.viewMat[2] = -this.viewMat[2], this.viewMat[6] = -this.viewMat[6], this.viewMat[10] = -this.viewMat[10], this.viewMat[14] = -this.viewMat[14];
    const v = t.projectionMatrix.elements, a = new Float32Array(16);
    a[0] = -1, a[5] = 1, a[10] = -1, a[15] = 1;
    const n = new Float32Array(16);
    for (let i = 0; i < 4; i++)
      for (let e = 0; e < 4; e++) {
        let c = 0;
        for (let p = 0; p < 4; p++) {
          const P = v[p * 4 + e], F = a[i * 4 + p];
          c += P * F;
        }
        n[i * 4 + e] = c;
      }
    this.compensatePreprocessYFlip && (n[1] = -n[1], n[5] = -n[5], n[9] = -n[9], n[13] = -n[13]);
    for (let i = 0; i < 16; i++) this.projMat[i] = n[i];
    t.getWorldPosition(new V.Vector3()).toArray(this._position);
    const f = (t.fov ?? 60) * Math.PI / 180, h = t.aspect && isFinite(t.aspect) && t.aspect > 0 ? t.aspect : o[0] / Math.max(1, o[1]), l = 2 * Math.atan(Math.tan(f * 0.5) * h);
    this._viewport = o, this._focal[0] = o[0] / (2 * Math.tan(l * 0.5)), this._focal[1] = o[1] / (2 * Math.tan(f * 0.5));
  }
  viewMatrix() {
    return this.viewMat;
  }
  projMatrix() {
    return this.projMat;
  }
  position() {
    return this._position;
  }
  frustumPlanes() {
    const t = new Float32Array(24);
    for (let o = 0; o < 24; o++)
      t[o] = o < 12 ? 1e3 : -1e3;
    return t;
  }
}
export {
  Y as C,
  j as P,
  y as a
};
