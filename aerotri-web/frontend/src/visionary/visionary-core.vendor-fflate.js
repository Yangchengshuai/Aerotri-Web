var sr = {}, qr = (function(r, e, n, a, f) {
  var t = new Worker(sr[e] || (sr[e] = URL.createObjectURL(new Blob([
    r + ';addEventListener("error",function(e){e=e.error;postMessage({$e$:[e.message,e.code,e.stack]})})'
  ], { type: "text/javascript" }))));
  return t.onmessage = function(v) {
    var o = v.data, u = o.$e$;
    if (u) {
      var s = new Error(u[0]);
      s.code = u[1], s.stack = u[2], f(s, null);
    } else
      f(null, o);
  }, t.postMessage(n, a), t;
}), m = Uint8Array, B = Uint16Array, wr = Int32Array, rr = new m([
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  1,
  1,
  1,
  1,
  2,
  2,
  2,
  2,
  3,
  3,
  3,
  3,
  4,
  4,
  4,
  4,
  5,
  5,
  5,
  5,
  0,
  /* unused */
  0,
  0,
  /* impossible */
  0
]), er = new m([
  0,
  0,
  0,
  0,
  1,
  1,
  2,
  2,
  3,
  3,
  4,
  4,
  5,
  5,
  6,
  6,
  7,
  7,
  8,
  8,
  9,
  9,
  10,
  10,
  11,
  11,
  12,
  12,
  13,
  13,
  /* unused */
  0,
  0
]), pr = new m([16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]), mr = function(r, e) {
  for (var n = new B(31), a = 0; a < 31; ++a)
    n[a] = e += 1 << r[a - 1];
  for (var f = new wr(n[30]), a = 1; a < 30; ++a)
    for (var t = n[a]; t < n[a + 1]; ++t)
      f[t] = t - n[a] << 5 | a;
  return { b: n, r: f };
}, yr = mr(rr, 2), nr = yr.b, Dr = yr.r;
nr[28] = 258, Dr[258] = 28;
var Ir = mr(er, 0), kr = Ir.b, X = new B(32768);
for (var c = 0; c < 32768; ++c) {
  var E = (c & 43690) >> 1 | (c & 21845) << 1;
  E = (E & 52428) >> 2 | (E & 13107) << 2, E = (E & 61680) >> 4 | (E & 3855) << 4, X[c] = ((E & 65280) >> 8 | (E & 255) << 8) >> 1;
}
var W = (function(r, e, n) {
  for (var a = r.length, f = 0, t = new B(e); f < a; ++f)
    r[f] && ++t[r[f] - 1];
  var v = new B(e);
  for (f = 1; f < e; ++f)
    v[f] = v[f - 1] + t[f - 1] << 1;
  var o;
  if (n) {
    o = new B(1 << e);
    var u = 15 - e;
    for (f = 0; f < a; ++f)
      if (r[f])
        for (var s = f << 4 | r[f], g = e - r[f], i = v[r[f] - 1]++ << g, l = i | (1 << g) - 1; i <= l; ++i)
          o[X[i] >> u] = s;
  } else
    for (o = new B(a), f = 0; f < a; ++f)
      r[f] && (o[f] = X[v[r[f] - 1]++] >> 15 - r[f]);
  return o;
}), K = new m(288);
for (var c = 0; c < 144; ++c)
  K[c] = 8;
for (var c = 144; c < 256; ++c)
  K[c] = 9;
for (var c = 256; c < 280; ++c)
  K[c] = 7;
for (var c = 280; c < 288; ++c)
  K[c] = 8;
var xr = new m(32);
for (var c = 0; c < 32; ++c)
  xr[c] = 5;
var Cr = /* @__PURE__ */ W(K, 9, 1), Fr = /* @__PURE__ */ W(xr, 5, 1), Q = function(r) {
  for (var e = r[0], n = 1; n < r.length; ++n)
    r[n] > e && (e = r[n]);
  return e;
}, C = function(r, e, n) {
  var a = e / 8 | 0;
  return (r[a] | r[a + 1] << 8) >> (e & 7) & n;
}, V = function(r, e) {
  var n = e / 8 | 0;
  return (r[n] | r[n + 1] << 8 | r[n + 2] << 16) >> (e & 7);
}, Mr = function(r) {
  return (r + 7) / 8 | 0;
}, Y = function(r, e, n) {
  return (e == null || e < 0) && (e = 0), (n == null || n > r.length) && (n = r.length), new m(r.subarray(e, n));
}, Ar = [
  "unexpected EOF",
  "invalid block type",
  "invalid length/literal",
  "invalid distance",
  "stream finished",
  "no stream handler",
  ,
  "no callback",
  "invalid UTF-8 data",
  "extra field too long",
  "date not in range 1980-2099",
  "filename too long",
  "stream finishing",
  "invalid zip data"
  // determined by unknown compression method
], p = function(r, e, n) {
  var a = new Error(e || Ar[r]);
  if (a.code = r, Error.captureStackTrace && Error.captureStackTrace(a, p), !n)
    throw a;
  return a;
}, Or = function(r, e, n, a) {
  var f = r.length, t = a ? a.length : 0;
  if (!f || e.f && !e.l)
    return n || new m(0);
  var v = !n, o = v || e.i != 2, u = e.i;
  v && (n = new m(f * 3));
  var s = function(ur) {
    var lr = n.length;
    if (ur > lr) {
      var cr = new m(Math.max(lr * 2, ur));
      cr.set(n), n = cr;
    }
  }, g = e.f || 0, i = e.p || 0, l = e.b || 0, M = e.l, $ = e.d, O = e.m, y = e.n, k = f * 8;
  do {
    if (!M) {
      g = C(r, i, 1);
      var T = C(r, i + 1, 3);
      if (i += 3, T)
        if (T == 1)
          M = Cr, $ = Fr, O = 9, y = 5;
        else if (T == 2) {
          var G = C(r, i, 31) + 257, L = C(r, i + 10, 15) + 4, U = G + C(r, i + 5, 31) + 1;
          i += 14;
          for (var x = new m(U), D = new m(19), h = 0; h < L; ++h)
            D[pr[h]] = C(r, i + h * 3, 7);
          i += L * 3;
          for (var H = Q(D), zr = (1 << H) - 1, Er = W(D, H, 1), h = 0; h < U; ) {
            var fr = Er[C(r, i, zr)];
            i += fr & 15;
            var w = fr >> 4;
            if (w < 16)
              x[h++] = w;
            else {
              var I = 0, N = 0;
              for (w == 16 ? (N = 3 + C(r, i, 3), i += 2, I = x[h - 1]) : w == 17 ? (N = 3 + C(r, i, 7), i += 3) : w == 18 && (N = 11 + C(r, i, 127), i += 7); N--; )
                x[h++] = I;
            }
          }
          var ir = x.subarray(0, G), z = x.subarray(G);
          O = Q(ir), y = Q(z), M = W(ir, O, 1), $ = W(z, y, 1);
        } else
          p(1);
      else {
        var w = Mr(i) + 4, S = r[w - 4] | r[w - 3] << 8, q = w + S;
        if (q > f) {
          u && p(0);
          break;
        }
        o && s(l + S), n.set(r.subarray(w, q), l), e.b = l += S, e.p = i = q * 8, e.f = g;
        continue;
      }
      if (i > k) {
        u && p(0);
        break;
      }
    }
    o && s(l + 131072);
    for (var Ur = (1 << O) - 1, Br = (1 << y) - 1, Z = i; ; Z = i) {
      var I = M[V(r, i) & Ur], R = I >> 4;
      if (i += I & 15, i > k) {
        u && p(0);
        break;
      }
      if (I || p(2), R < 256)
        n[l++] = R;
      else if (R == 256) {
        Z = i, M = null;
        break;
      } else {
        var or = R - 254;
        if (R > 264) {
          var h = R - 257, J = rr[h];
          or = C(r, i, (1 << J) - 1) + nr[h], i += J;
        }
        var j = $[V(r, i) & Br], b = j >> 4;
        j || p(3), i += j & 15;
        var z = kr[b];
        if (b > 3) {
          var J = er[b];
          z += V(r, i) & (1 << J) - 1, i += J;
        }
        if (i > k) {
          u && p(0);
          break;
        }
        o && s(l + 131072);
        var vr = l + or;
        if (l < z) {
          var tr = t - z, $r = Math.min(z, vr);
          for (tr + l < 0 && p(3); l < $r; ++l)
            n[l] = a[tr + l];
        }
        for (; l < vr; ++l)
          n[l] = n[l - z];
      }
    }
    e.l = M, e.p = Z, e.b = l, e.f = g, M && (g = 1, e.m = O, e.d = $, e.n = y);
  } while (!g);
  return l != n.length && v ? Y(n, 0, l) : n.subarray(0, l);
}, Rr = /* @__PURE__ */ new m(0), Wr = function(r, e) {
  var n = {};
  for (var a in r)
    n[a] = r[a];
  for (var a in e)
    n[a] = e[a];
  return n;
}, gr = function(r, e, n) {
  for (var a = r(), f = r.toString(), t = f.slice(f.indexOf("[") + 1, f.lastIndexOf("]")).replace(/\s+/g, "").split(","), v = 0; v < a.length; ++v) {
    var o = a[v], u = t[v];
    if (typeof o == "function") {
      e += ";" + u + "=";
      var s = o.toString();
      if (o.prototype)
        if (s.indexOf("[native code]") != -1) {
          var g = s.indexOf(" ", 8) + 1;
          e += s.slice(g, s.indexOf("(", g));
        } else {
          e += s;
          for (var i in o.prototype)
            e += ";" + u + ".prototype." + i + "=" + o.prototype[i].toString();
        }
      else
        e += s;
    } else
      n[u] = o;
  }
  return e;
}, P = [], Gr = function(r) {
  var e = [];
  for (var n in r)
    r[n].buffer && e.push((r[n] = new r[n].constructor(r[n])).buffer);
  return e;
}, Hr = function(r, e, n, a) {
  if (!P[n]) {
    for (var f = "", t = {}, v = r.length - 1, o = 0; o < v; ++o)
      f = gr(r[o], f, t);
    P[n] = { c: gr(r[v], f, t), e: t };
  }
  var u = Wr({}, P[n].e);
  return qr(P[n].c + ";onmessage=function(e){for(var k in e.data)self[k]=e.data[k];onmessage=" + e.toString() + "}", n, u, Gr(u), a);
}, Jr = function() {
  return [m, B, wr, rr, er, pr, nr, kr, Cr, Fr, X, Ar, W, Q, C, V, Mr, Y, p, Or, ar, Sr, Tr];
}, Sr = function(r) {
  return postMessage(r, [r.buffer]);
}, Tr = function(r) {
  return r && {
    out: r.size && new m(r.size),
    dictionary: r.dictionary
  };
}, Kr = function(r, e, n, a, f, t) {
  var v = Hr(n, a, f, function(o, u) {
    v.terminate(), t(o, u);
  });
  return v.postMessage([r, e], e.consume ? [r.buffer] : []), function() {
    v.terminate();
  };
}, A = function(r, e) {
  return r[e] | r[e + 1] << 8;
}, F = function(r, e) {
  return (r[e] | r[e + 1] << 8 | r[e + 2] << 16 | r[e + 3] << 24) >>> 0;
}, _ = function(r, e) {
  return F(r, e) + F(r, e + 4) * 4294967296;
};
function Lr(r, e, n) {
  return n || (n = e, e = {}), typeof n != "function" && p(7), Kr(r, e, [
    Jr
  ], function(a) {
    return Sr(ar(a.data[0], Tr(a.data[1])));
  }, 1, n);
}
function ar(r, e) {
  return Or(r, { i: 2 }, e && e.out, e && e.dictionary);
}
var d = typeof TextDecoder < "u" && /* @__PURE__ */ new TextDecoder(), Nr = 0;
try {
  d.decode(Rr, { stream: !0 }), Nr = 1;
} catch {
}
var Pr = function(r) {
  for (var e = "", n = 0; ; ) {
    var a = r[n++], f = (a > 127) + (a > 223) + (a > 239);
    if (n + f > r.length)
      return { s: e, r: Y(r, n - 1) };
    f ? f == 3 ? (a = ((a & 15) << 18 | (r[n++] & 63) << 12 | (r[n++] & 63) << 6 | r[n++] & 63) - 65536, e += String.fromCharCode(55296 | a >> 10, 56320 | a & 1023)) : f & 1 ? e += String.fromCharCode((a & 31) << 6 | r[n++] & 63) : e += String.fromCharCode((a & 15) << 12 | (r[n++] & 63) << 6 | r[n++] & 63) : e += String.fromCharCode(a);
  }
};
function Qr(r, e) {
  if (e) {
    for (var n = "", a = 0; a < r.length; a += 16384)
      n += String.fromCharCode.apply(null, r.subarray(a, a + 16384));
    return n;
  } else {
    if (d)
      return d.decode(r);
    var f = Pr(r), t = f.s, n = f.r;
    return n.length && p(8), t;
  }
}
var Vr = function(r, e) {
  return e + 30 + A(r, e + 26) + A(r, e + 28);
}, Xr = function(r, e, n) {
  var a = A(r, e + 28), f = Qr(r.subarray(e + 46, e + 46 + a), !(A(r, e + 8) & 2048)), t = e + 46 + a, v = F(r, e + 20), o = n && v == 4294967295 ? Yr(r, t) : [v, F(r, e + 24), F(r, e + 42)], u = o[0], s = o[1], g = o[2];
  return [A(r, e + 10), u, s, f, t + A(r, e + 30) + A(r, e + 32), g];
}, Yr = function(r, e) {
  for (; A(r, e) != 1; e += 4 + A(r, e + 2))
    ;
  return [_(r, e + 12), _(r, e + 4), _(r, e + 20)];
}, hr = typeof queueMicrotask == "function" ? queueMicrotask : typeof setTimeout == "function" ? setTimeout : function(r) {
  r();
};
function Zr(r, e, n) {
  n || (n = e, e = {}), typeof n != "function" && p(7);
  var a = [], f = function() {
    for (var y = 0; y < a.length; ++y)
      a[y]();
  }, t = {}, v = function(y, k) {
    hr(function() {
      n(y, k);
    });
  };
  hr(function() {
    v = n;
  });
  for (var o = r.length - 22; F(r, o) != 101010256; --o)
    if (!o || r.length - o > 65558)
      return v(p(13, 0, 1), null), f;
  var u = A(r, o + 8);
  if (u) {
    var s = u, g = F(r, o + 16), i = g == 4294967295 || s == 65535;
    if (i) {
      var l = F(r, o - 12);
      i = F(r, l) == 101075792, i && (s = u = F(r, l + 32), g = F(r, l + 48));
    }
    for (var M = e && e.filter, $ = function(y) {
      var k = Xr(r, g, i), T = k[0], w = k[1], S = k[2], q = k[3], G = k[4], L = k[5], U = Vr(r, L);
      g = G;
      var x = function(h, H) {
        h ? (f(), v(h, null)) : (H && (t[q] = H), --u || v(null, t));
      };
      if (!M || M({
        name: q,
        size: w,
        originalSize: S,
        compression: T
      }))
        if (!T)
          x(null, Y(r, U, U + w));
        else if (T == 8) {
          var D = r.subarray(U, U + w);
          if (S < 524288 || w > 0.8 * S)
            try {
              x(null, ar(D, { out: new m(S) }));
            } catch (h) {
              x(h, null);
            }
          else
            a.push(Lr(D, { size: S }, x));
        } else
          x(p(14, "unknown compression type " + T, 1), null);
      else
        x(null, null);
    }, O = 0; O < s; ++O)
      $(O);
  } else
    v(null, {});
  return f;
}
export {
  Zr as u
};
