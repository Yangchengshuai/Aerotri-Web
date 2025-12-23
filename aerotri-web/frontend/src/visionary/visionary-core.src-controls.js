import { vec3 as t, quat as l, vec2 as w } from "gl-matrix";
const P = 1, D = 2e-3, S = 0.5, v = 0.85, E = 0.85;
function k(h, e, s) {
  return Math.min(s, Math.max(e, h));
}
class N {
  // Movement settings
  moveSpeed;
  rotateSpeed;
  scrollSpeed;
  moveInertia;
  rotateInertia;
  // Speed multipliers
  capsMultiplier = 10;
  shiftMultiplier = 50;
  ctrlMultiplier = 0.2;
  // Input state
  keycode = {};
  keydown = {};
  // Mouse state
  leftMousePressed = !1;
  rightMousePressed = !1;
  mouseDelta = t.fromValues(0, 0, 0);
  // Scroll state
  scrollDelta = 0;
  // Velocity for inertia
  moveVelocity = t.fromValues(0, 0, 0);
  rotateVelocity = t.fromValues(0, 0, 0);
  // Store yaw and pitch separately to avoid gimbal lock
  yaw = 0;
  pitch = 0;
  // User input flag
  userInput = !1;
  // Enable/disable controller
  enable = !0;
  // Fly mode - true: 6DoF movement along view direction, false: restrict to XZ plane (ground)
  flyMode = !0;
  constructor(e = P, s = D, o = S, c = E, i = v) {
    this.moveSpeed = e, this.rotateSpeed = s, this.scrollSpeed = o, this.moveInertia = c, this.rotateInertia = i, document.addEventListener("keydown", (r) => {
      this.keydown[r.key] = !0, this.keycode[r.code] = !0, this.userInput = !0;
    }), document.addEventListener("keyup", (r) => {
      this.keydown[r.key] = !1, this.keycode[r.code] = !1;
    }), window.addEventListener("blur", () => {
      this.keydown = {}, this.keycode = {}, this.leftMousePressed = !1, this.rightMousePressed = !1;
    });
  }
  processKeyboard(e, s) {
    return this.keycode[e] = s, this.userInput = !0, !0;
  }
  processMouse(e, s) {
    this.leftMousePressed && (this.mouseDelta[0] += e, this.mouseDelta[1] += s, this.userInput = !0), this.rightMousePressed;
  }
  processScroll(e) {
    this.scrollDelta += e, this.userInput = !0;
  }
  update(e, s) {
    if (!this.enable) return;
    let o = 0, c = 0;
    if (this.leftMousePressed && (Math.abs(this.mouseDelta[0]) > 0 || Math.abs(this.mouseDelta[1]) > 0))
      o = this.mouseDelta[0] * this.rotateSpeed, c = -this.mouseDelta[1] * this.rotateSpeed, this.rotateVelocity[0] = o / s, this.rotateVelocity[1] = c / s;
    else {
      o = this.rotateVelocity[0] * s, c = this.rotateVelocity[1] * s;
      const u = Math.exp(-s / (1 - this.rotateInertia + 1e-6));
      this.rotateVelocity[0] *= u, this.rotateVelocity[1] *= u, Math.abs(this.rotateVelocity[0]) < 1e-3 && (this.rotateVelocity[0] = 0), Math.abs(this.rotateVelocity[1]) < 1e-3 && (this.rotateVelocity[1] = 0);
    }
    this.yaw += o, this.pitch += c, this.pitch = k(this.pitch, -Math.PI / 2 + 0.01, Math.PI / 2 - 0.01);
    const i = l.identity(l.create());
    l.rotateY(i, i, this.yaw), l.rotateX(i, i, this.pitch);
    const r = l.invert(l.create(), i);
    l.copy(e.rotationQ, r);
    const a = t.fromValues(0, 0, 0);
    (this.keycode.KeyW || this.keycode.ArrowUp) && (a[2] -= 1), (this.keycode.KeyS || this.keycode.ArrowDown) && (a[2] += 1), (this.keycode.KeyA || this.keycode.ArrowLeft) && (a[0] -= 1), (this.keycode.KeyD || this.keycode.ArrowRight) && (a[0] += 1), (this.keycode.KeyR || this.keycode.PageUp) && (a[1] += 1), (this.keycode.KeyF || this.keycode.PageDown) && (a[1] -= 1), this.keycode.KeyQ && (a[0] -= 1), this.keycode.KeyE && (a[0] += 1), Math.abs(this.scrollDelta) > 0 && (a[2] -= this.scrollDelta * this.scrollSpeed);
    let n = 1;
    if (this.keydown.CapsLock && (n *= this.capsMultiplier), (this.keycode.ShiftLeft || this.keycode.ShiftRight) && (n *= this.shiftMultiplier), (this.keycode.ControlLeft || this.keycode.ControlRight) && (n *= this.ctrlMultiplier), t.length(a) > 0) {
      t.normalize(a, a), t.scale(a, a, this.moveSpeed * n);
      const u = l.invert(l.create(), e.rotationQ), p = t.transformQuat(t.create(), t.fromValues(0, 0, -1), u), y = t.transformQuat(t.create(), t.fromValues(1, 0, 0), u), M = t.transformQuat(t.create(), t.fromValues(0, 1, 0), u), d = t.fromValues(p[0], 0, p[2]), m = t.fromValues(y[0], 0, y[2]), V = t.length(d), A = t.length(m);
      V > 1e-6 && t.scale(d, d, 1 / V), A > 1e-6 && t.scale(m, m, 1 / A);
      const f = t.create();
      t.scaleAndAdd(f, f, this.flyMode ? y : m, a[0]), t.scaleAndAdd(f, f, this.flyMode ? M : t.fromValues(0, 1, 0), a[1]), t.scaleAndAdd(f, f, this.flyMode ? p : V > 1e-6 ? d : p, a[2]), t.copy(this.moveVelocity, f);
    } else {
      const u = Math.exp(-s / (1 - this.moveInertia + 1e-6));
      t.scale(this.moveVelocity, this.moveVelocity, u), t.length(this.moveVelocity) < 1e-3 && t.set(this.moveVelocity, 0, 0, 0);
    }
    if (t.length(this.moveVelocity) > 1e-3) {
      const u = t.clone(this.moveVelocity);
      t.scale(u, u, s), t.add(e.positionV, e.positionV, u);
    }
    t.set(this.mouseDelta, 0, 0, 0), this.scrollDelta = 0, this.userInput = !1;
  }
  // Reset camera orientation
  resetOrientation() {
    this.yaw = 0, this.pitch = 0, this.rotateVelocity = t.fromValues(0, 0, 0), this.moveVelocity = t.fromValues(0, 0, 0);
  }
  // Get current orientation for debugging
  getOrientation() {
    return {
      yaw: this.yaw * 180 / Math.PI,
      pitch: this.pitch * 180 / Math.PI
    };
  }
  // Set orientation (useful for initialization)
  setOrientation(e, s) {
    this.yaw = e, this.pitch = k(s, -Math.PI / 2 + 0.01, Math.PI / 2 - 0.01);
  }
  // Toggle fly mode
  setFlyMode(e) {
    this.flyMode = e, console.log(`FPS Controller: Fly mode ${e ? "enabled" : "disabled (ground movement only)"}`);
  }
  // Implement interface method
  getControllerType() {
    return "fps";
  }
}
function L(h, e, s, o, c) {
  const i = e ? 1 : -1;
  let r = !0;
  switch (h) {
    case "KeyW":
      s[2] += +i;
      break;
    case "KeyS":
      s[2] += -i;
      break;
    case "KeyA":
      s[0] += -i;
      break;
    case "KeyD":
      s[0] += +i;
      break;
    case "KeyQ":
      o[2] += i / c;
      break;
    case "KeyE":
      o[2] += -i / c;
      break;
    case "Space":
      s[1] += i;
      break;
    case "ShiftLeft":
      s[1] += -i;
      break;
    default:
      r = !1;
  }
  return r;
}
function _(h, e, s, o, c, i) {
  let r = !1;
  return s && (c[0] += h, c[1] += -e, r = !0), o && (i[0] += e, i[1] += h, r = !0), r;
}
function x(h) {
  return h * 3;
}
const b = 1e-6, g = t.fromValues(0, 1, 0), R = 5 * Math.PI / 180, K = 0.1, C = 1e3;
function Q(h, e) {
  const s = t.normalize(t.create(), h);
  let o = t.sub(t.create(), e, t.scale(t.create(), s, t.dot(e, s)));
  if (t.sqrLen(o) < b) {
    const d = Math.abs(s[1]) < 0.99 ? g : t.fromValues(1, 0, 0);
    o = t.sub(t.create(), d, t.scale(t.create(), s, t.dot(d, s)));
  }
  t.normalize(o, o);
  const c = l.rotationTo(l.create(), t.fromValues(0, 0, 1), s), i = t.transformQuat(t.create(), t.fromValues(0, 1, 0), c), r = t.sub(t.create(), i, t.scale(t.create(), s, t.dot(i, s)));
  t.normalize(r, r);
  const a = Math.max(-1, Math.min(1, t.dot(r, o)));
  let n = Math.acos(a);
  const u = t.cross(t.create(), r, o), p = t.dot(u, s) >= 0 ? 1 : -1;
  n *= p;
  const y = l.setAxisAngle(l.create(), s, n), M = l.multiply(l.create(), y, c);
  return l.invert(l.create(), M);
}
function I(h, e, s) {
  const o = t.sub(t.create(), h, t.scale(t.create(), e, t.dot(h, e)));
  let c = t.sqrLen(o);
  return c < b ? t.normalize(t.create(), s) : t.scale(o, o, 1 / Math.sqrt(c));
}
function F(h, e, s) {
  const o = t.normalize(
    t.create(),
    t.subtract(t.create(), e, h)
  ), c = I(
    s,
    o,
    Math.abs(o[1]) < 0.99 ? g : t.fromValues(1, 0, 0)
  ), i = t.normalize(t.create(), t.cross(t.create(), o, c)), r = t.normalize(t.create(), t.cross(t.create(), i, o));
  return { forward: o, right: i, yawAxis: r };
}
function T(h, e, s, o, c) {
  const i = Math.max(t.distance(h, e), b), r = Math.exp(Math.log(i) + s * o * 10 * c);
  return Math.max(K, Math.min(r, C));
}
function U(h, e, s, o, c, i, r) {
  const a = c * i * 0.1 * r, n = t.create();
  t.scaleAndAdd(n, n, s, e[1] * a), t.scaleAndAdd(n, n, o, -e[0] * a), t.add(h, h, n);
}
function z(h, e, s, o, c, i) {
  let r = t.clone(h), a = t.clone(e), n = t.clone(s);
  if (Math.abs(o) > 0) {
    const u = l.setAxisAngle(l.create(), n, o);
    r = t.transformQuat(t.create(), r, u), a = t.transformQuat(t.create(), a, u), n = t.normalize(t.create(), t.cross(t.create(), a, r));
  }
  if (Math.abs(c) > 0) {
    const u = Math.cos(R), p = Math.max(-1, Math.min(1, t.dot(r, n))), y = l.setAxisAngle(l.create(), a, c), M = t.transformQuat(t.create(), r, y), d = Math.max(-1, Math.min(1, t.dot(M, n)));
    if (Math.abs(d) > u) {
      const A = (d > 0 ? 1 : -1) * u, f = Math.min(1, Math.abs((A - p) / (d - p + 1e-9)));
      c *= f;
    }
    const m = l.setAxisAngle(l.create(), a, c);
    r = t.transformQuat(t.create(), r, m), n = I(n, r, n), a = t.normalize(t.create(), t.cross(t.create(), r, n));
  }
  if (Math.abs(i) > 0) {
    const u = l.setAxisAngle(l.create(), r, i);
    n = t.transformQuat(t.create(), n, u), a = t.normalize(t.create(), t.cross(t.create(), r, n));
  }
  return { forward: r, right: a, yawAxis: n };
}
function O(h, e, s, o) {
  let c = Math.pow(0.8, o * 60);
  c < 1e-4 && (c = 0);
  const i = t.scale(t.create(), h, c);
  t.len(i) < 1e-4 && t.set(i, 0, 0, 0);
  const r = w.scale(w.create(), e, c);
  w.len(r) < 1e-4 && w.set(r, 0, 0);
  const a = s * c, n = Math.abs(a) < 1e-4 ? 0 : a;
  return { rotation: i, shift: r, scroll: n };
}
class Y {
  center = t.fromValues(0, 0, 0);
  /** If provided, use as "global up reference"; otherwise use internal orbit up state */
  up = null;
  amount = t.fromValues(0, 0, 0);
  // Placeholder (consistent with Rust, not used in this update)
  shift = w.fromValues(0, 0);
  // Right-click pan (x=dy, y=-dx)
  rotation = t.fromValues(0, 0, 0);
  // yaw(x), pitch(y), roll(z)
  scroll = 0;
  speed;
  sensitivity;
  leftMousePressed = !1;
  rightMousePressed = !1;
  altPressed = !1;
  userInput = !1;
  // --- Key: stable orbit up state ---
  orbitUp = t.clone(g);
  // Debug
  debug = !1;
  debugEvery = 1 / 30;
  _acc = 0;
  constructor(e = 0.2, s = 0.1) {
    this.speed = e, this.sensitivity = s;
  }
  // Allow external reset of orbit up (e.g., when switching views)
  resetUp(e) {
    this.orbitUp = t.normalize(t.create(), e ?? g);
  }
  processKeyboard(e, s) {
    const o = L(
      e,
      s,
      this.amount,
      this.rotation,
      this.sensitivity
    );
    return this.userInput = o, o;
  }
  processMouse(e, s) {
    const o = _(
      e,
      s,
      this.leftMousePressed,
      this.rightMousePressed,
      this.rotation,
      this.shift
    );
    this.userInput = o;
  }
  processScroll(e) {
    this.scroll += x(e), this.userInput = !0;
  }
  /** Equivalent to Rust's update_camera, but with stable orbitUp maintenance and pole/twist protection */
  update(e, s) {
    const o = s, c = this.up ? t.normalize(t.create(), this.up) : g;
    let { forward: i, right: r, yawAxis: a } = F(e.positionV, this.center, c);
    const n = T(e.positionV, this.center, this.scroll, o, this.speed), u = Math.max(t.distance(e.positionV, this.center), 1e-6);
    U(this.center, this.shift, r, a, o, this.speed, u);
    const p = t.scale(t.create(), i, -n);
    t.add(e.positionV, this.center, p);
    let y = this.rotation[0] * o * this.sensitivity, M = -this.rotation[1] * o * this.sensitivity, d = 0;
    this.altPressed && (d = -this.rotation[1] * o * this.sensitivity, y = 0, M = 0);
    const m = z(i, r, a, y, M, d);
    i = m.forward, r = m.right, a = m.yawAxis, t.add(e.positionV, this.center, t.scale(t.create(), i, -n)), e.rotationQ = Q(i, c), t.copy(this.orbitUp, a);
    const V = O(this.rotation, this.shift, this.scroll, o);
    if (t.copy(this.rotation, V.rotation), w.copy(this.shift, V.shift), this.scroll = V.scroll, this.userInput = !1, this._acc += o, this.debug && this._acc >= this.debugEvery) {
      this._acc = 0;
      const A = l.invert(l.create(), e.rotationQ), f = t.transformQuat(t.create(), t.fromValues(0, 0, 1), A);
      console.log("[CameraDebug]", {
        pos: [e.positionV[0], e.positionV[1], e.positionV[2]],
        center: [this.center[0], this.center[1], this.center[2]],
        dist: t.distance(e.positionV, this.center),
        forward_to_center: [i[0], i[1], i[2]],
        forward_from_rot: [f[0], f[1], f[2]],
        dot: t.dot(f, i)
      });
    }
  }
  // Implement interface methods
  getControllerType() {
    return "orbit";
  }
  // Optional: Add resetOrientation for compatibility
  resetOrientation() {
    this.center = t.fromValues(0, 0, 0), this.rotation = t.fromValues(0, 0, 0), this.shift = w.fromValues(0, 0), this.scroll = 0, this.orbitUp = t.clone(g);
  }
}
export {
  Y as C,
  N as F
};
