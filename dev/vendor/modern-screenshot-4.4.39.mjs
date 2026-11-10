var Pe = Object.defineProperty, _e = Object.defineProperties;
var Ue = Object.getOwnPropertyDescriptors;
var L = Object.getOwnPropertySymbols;
var Z = Object.prototype.hasOwnProperty, ee = Object.prototype.propertyIsEnumerable;
var te = Math.pow, Q = (e, t, r) => t in e ? Pe(e, t, { enumerable: !0, configurable: !0, writable: !0, value: r }) : e[t] = r, T = (e, t) => {
  for (var r in t || (t = {}))
    Z.call(t, r) && Q(e, r, t[r]);
  if (L)
    for (var r of L(t))
      ee.call(t, r) && Q(e, r, t[r]);
  return e;
}, R = (e, t) => _e(e, Ue(t));
var re = (e, t) => {
  var r = {};
  for (var n in e)
    Z.call(e, n) && t.indexOf(n) < 0 && (r[n] = e[n]);
  if (e != null && L)
    for (var n of L(e))
      t.indexOf(n) < 0 && ee.call(e, n) && (r[n] = e[n]);
  return r;
};
var S = (e, t, r) => new Promise((n, a) => {
  var s = (l) => {
    try {
      i(r.next(l));
    } catch (u) {
      a(u);
    }
  }, o = (l) => {
    try {
      i(r.throw(l));
    } catch (u) {
      a(u);
    }
  }, i = (l) => l.done ? n(l.value) : Promise.resolve(l.value).then(s, o);
  i((r = r.apply(e, t)).next());
});
function ue(e, t) {
  return e[13] = 1, e[14] = t >> 8, e[15] = t & 255, e[16] = t >> 8, e[17] = t & 255, e;
}
const fe = "p".charCodeAt(0), de = "H".charCodeAt(0), me = "Y".charCodeAt(0), ge = "s".charCodeAt(0);
let q;
function $e() {
  const e = new Int32Array(256);
  for (let t = 0; t < 256; t++) {
    let r = t;
    for (let n = 0; n < 8; n++)
      r = r & 1 ? 3988292384 ^ r >>> 1 : r >>> 1;
    e[t] = r;
  }
  return e;
}
function Be(e) {
  let t = -1;
  q || (q = $e());
  for (let r = 0; r < e.length; r++)
    t = q[(t ^ e[r]) & 255] ^ t >>> 8;
  return t ^ -1;
}
function Le(e) {
  const t = e.length - 1;
  for (let r = t; r >= 4; r--)
    if (e[r - 4] === 9 && e[r - 3] === fe && e[r - 2] === de && e[r - 1] === me && e[r] === ge)
      return r - 3;
  return 0;
}
function he(e, t, r = !1) {
  const n = new Uint8Array(13);
  t *= 39.3701, n[0] = fe, n[1] = de, n[2] = me, n[3] = ge, n[4] = t >>> 24, n[5] = t >>> 16, n[6] = t >>> 8, n[7] = t & 255, n[8] = n[4], n[9] = n[5], n[10] = n[6], n[11] = n[7], n[12] = 1;
  const a = Be(n), s = new Uint8Array(4);
  if (s[0] = a >>> 24, s[1] = a >>> 16, s[2] = a >>> 8, s[3] = a & 255, r) {
    const o = Le(e);
    return e.set(n, o), e.set(s, o + 13), e;
  } else {
    const o = new Uint8Array(4);
    o[0] = 0, o[1] = 0, o[2] = 0, o[3] = 9;
    const i = new Uint8Array(54);
    return i.set(e, 0), i.set(o, 33), i.set(n, 37), i.set(s, 50), i;
  }
}
const Me = "AAlwSFlz", Oe = "AAAJcEhZ", We = "AAAACXBI";
function je(e) {
  let t = e.indexOf(Me);
  return t === -1 && (t = e.indexOf(Oe)), t === -1 && (t = e.indexOf(We)), t;
}
const H = "[modern-screenshot]", x = typeof window != "undefined", qe = x && "Worker" in window, we = x && "atob" in window, Ve = x && "btoa" in window;
var le;
const z = x ? (le = window.navigator) == null ? void 0 : le.userAgent : "", pe = z.includes("Chrome"), M = z.includes("AppleWebKit") && !pe, X = z.includes("Firefox"), He = (e) => e && "__CONTEXT__" in e, ze = (e) => e.constructor.name === "CSSFontFaceRule", Xe = (e) => e.constructor.name === "CSSImportRule", A = (e) => e.nodeType === 1, U = (e) => typeof e.className == "object", ye = (e) => e.tagName === "image", Ge = (e) => e.tagName === "use", F = (e) => A(e) && typeof e.style != "undefined" && !U(e), Ye = (e) => e.nodeType === 8, Je = (e) => e.nodeType === 3, D = (e) => e.tagName === "IMG", O = (e) => e.tagName === "VIDEO", Ke = (e) => e.tagName === "CANVAS", ne = (e) => e.tagName === "TEXTAREA", Qe = (e) => e.tagName === "INPUT", Ze = (e) => e.tagName === "STYLE", et = (e) => e.tagName === "SCRIPT", tt = (e) => e.tagName === "SELECT", rt = (e) => e.tagName === "SLOT", nt = (e) => e.tagName === "IFRAME", C = (...e) => console.warn(H, ...e), ot = (e) => console.time(`${H} ${e}`), at = (e) => console.timeEnd(`${H} ${e}`), st = (e) => {
  var r;
  const t = (r = e == null ? void 0 : e.createElement) == null ? void 0 : r.call(e, "canvas");
  return t && (t.height = t.width = 1), t && "toDataURL" in t && Boolean(t.toDataURL("image/webp").includes("image/webp"));
}, V = (e) => e.startsWith("data:");
function be(e, t) {
  if (e.match(/^[a-z]+:\/\//i))
    return e;
  if (x && e.match(/^\/\//))
    return window.location.protocol + e;
  if (e.match(/^[a-z]+:/i) || !x)
    return e;
  const r = W().implementation.createHTMLDocument(), n = r.createElement("base"), a = r.createElement("a");
  return r.head.appendChild(n), r.body.appendChild(a), t && (n.href = t), a.href = e, a.href;
}
function W(e) {
  var t;
  return (t = e && A(e) ? e == null ? void 0 : e.ownerDocument : e) != null ? t : window.document;
}
const j = "http://www.w3.org/2000/svg";
function Se(e, t, r) {
  const n = W(r).createElementNS(j, "svg");
  return n.setAttributeNS(null, "width", e.toString()), n.setAttributeNS(null, "height", t.toString()), n.setAttributeNS(null, "viewBox", `0 0 ${e} ${t}`), n;
}
function Ee(e, t) {
  let r = new XMLSerializer().serializeToString(e);
  return t && (r = r.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\uD800-\uDFFF\uFFFE\uFFFF]/ug, "")), `data:image/svg+xml;charset=utf-8,${encodeURIComponent(r)}`;
}
function it(e, t = "image/png", r = 1) {
  return S(this, null, function* () {
    try {
      return yield new Promise((n, a) => {
        e.toBlob((s) => {
          s ? n(s) : a(new Error("Blob is null"));
        }, t, r);
      });
    } catch (n) {
      if (we)
        return C("Failed canvas to blob", { type: t, quality: r }, n), ct(e.toDataURL(t, r));
      throw n;
    }
  });
}
function ct(e) {
  var i, l;
  const [t, r] = e.split(","), n = (l = (i = t.match(/data:(.+);/)) == null ? void 0 : i[1]) != null ? l : void 0, a = window.atob(r), s = a.length, o = new Uint8Array(s);
  for (let u = 0; u < s; u += 1)
    o[u] = a.charCodeAt(u);
  return new Blob([o], { type: n });
}
function Ce(e, t) {
  return new Promise((r, n) => {
    const a = new FileReader();
    a.onload = () => r(a.result), a.onerror = () => n(a.error), a.onabort = () => n(new Error(`Failed read blob to ${t}`)), t === "dataUrl" ? a.readAsDataURL(e) : t === "arrayBuffer" && a.readAsArrayBuffer(e);
  });
}
const lt = (e) => Ce(e, "dataUrl"), ut = (e) => Ce(e, "arrayBuffer");
function k(e, t) {
  const r = W(t).createElement("img");
  return r.decoding = "sync", r.loading = "eager", r.src = e, r;
}
function P(e, t) {
  return new Promise((r) => {
    const { timeout: n, ownerDocument: a, onError: s } = t != null ? t : {}, o = typeof e == "string" ? k(e, W(a)) : e;
    let i = null, l = null;
    function u() {
      r(o), i && clearTimeout(i), l == null || l();
    }
    if (n && (i = setTimeout(u, n)), O(o)) {
      const c = o.currentSrc || o.src;
      if (!c)
        return o.poster ? P(o.poster, t).then(r) : u();
      if (o.readyState >= 2)
        return u();
      const f = u, d = (m) => {
        C(
          "Failed video load",
          c,
          m
        ), s == null || s(m), u();
      };
      l = () => {
        o.removeEventListener("loadeddata", f), o.removeEventListener("error", d);
      }, o.addEventListener("loadeddata", f, { once: !0 }), o.addEventListener("error", d, { once: !0 });
    } else {
      const c = ye(o) ? o.href.baseVal : o.currentSrc || o.src;
      if (!c)
        return u();
      const f = () => S(this, null, function* () {
        if (D(o) && "decode" in o)
          try {
            yield o.decode();
          } catch (m) {
            C(
              "Failed to decode image, trying to render anyway",
              o.dataset.originalSrc || c,
              m
            );
          }
        u();
      }), d = (m) => {
        C(
          "Failed image load",
          o.dataset.originalSrc || c,
          m
        ), u();
      };
      if (D(o) && o.complete)
        return f();
      l = () => {
        o.removeEventListener("load", f), o.removeEventListener("error", d);
      }, o.addEventListener("load", f, { once: !0 }), o.addEventListener("error", d, { once: !0 });
    }
  });
}
function ft(e, t) {
  return S(this, null, function* () {
    F(e) && (D(e) || O(e) ? yield P(e, { timeout: t }) : yield Promise.all(
      ["img", "video"].flatMap((r) => Array.from(e.querySelectorAll(r)).map((n) => P(n, { timeout: t })))
    ));
  });
}
const ve = function() {
  let t = 0;
  const r = () => (
    // eslint-disable-next-line no-bitwise
    `0000${(Math.random() * te(36, 4) << 0).toString(36)}`.slice(-4)
  );
  return () => (t += 1, `u${r()}${t}`);
}();
function Te(e) {
  return e == null ? void 0 : e.split(",").map((t) => t.trim().replace(/"|'/g, "").toLowerCase()).filter(Boolean);
}
function dt(e) {
  return {
    time: (t) => e && ot(t),
    timeEnd: (t) => e && at(t),
    warn: (...t) => e && C(...t)
  };
}
function mt(e) {
  return {
    cache: e ? "no-cache" : "force-cache"
  };
}
function N(e, t) {
  return S(this, null, function* () {
    return He(e) ? e : gt(e, R(T({}, t), { autoDestruct: !0 }));
  });
}
function gt(e, t) {
  return S(this, null, function* () {
    var m, h, w, y, g;
    const { scale: r = 1, workerUrl: n, workerNumber: a = 1 } = t || {}, s = Boolean(t == null ? void 0 : t.debug), o = (m = t == null ? void 0 : t.features) != null ? m : !0, i = (h = e.ownerDocument) != null ? h : x ? window.document : void 0, l = (y = (w = e.ownerDocument) == null ? void 0 : w.defaultView) != null ? y : x ? window : void 0, u = /* @__PURE__ */ new Map(), c = R(T({
      // Options
      width: 0,
      height: 0,
      quality: 1,
      type: "image/png",
      scale: r,
      backgroundColor: null,
      style: null,
      filter: null,
      maximumCanvasSize: 0,
      timeout: 3e4,
      progress: null,
      debug: s,
      fetch: T({
        requestInit: mt((g = t == null ? void 0 : t.fetch) == null ? void 0 : g.bypassingCache),
        placeholderImage: "data:image/png;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7",
        bypassingCache: !1
      }, t == null ? void 0 : t.fetch),
      fetchFn: null,
      font: {},
      drawImageInterval: 100,
      workerUrl: null,
      workerNumber: a,
      onCloneNode: null,
      onEmbedNode: null,
      onCreateForeignObjectSvg: null,
      includeStyleProperties: null,
      autoDestruct: !1
    }, t), {
      // InternalContext
      __CONTEXT__: !0,
      log: dt(s),
      node: e,
      ownerDocument: i,
      ownerWindow: l,
      dpi: r === 1 ? null : 96 * r,
      svgStyleElement: Ae(i),
      svgDefsElement: i == null ? void 0 : i.createElementNS(j, "defs"),
      svgStyles: /* @__PURE__ */ new Map(),
      defaultComputedStyles: /* @__PURE__ */ new Map(),
      workers: [
        ...new Array(
          qe && n && a ? a : 0
        )
      ].map(() => {
        try {
          const b = new Worker(n);
          return b.onmessage = (p) => S(this, null, function* () {
            var I, J, B, K;
            const { url: E, result: v } = p.data;
            v ? (J = (I = u.get(E)) == null ? void 0 : I.resolve) == null || J.call(I, v) : (K = (B = u.get(E)) == null ? void 0 : B.reject) == null || K.call(B, new Error(`Error receiving message from worker: ${E}`));
          }), b.onmessageerror = (p) => {
            var v, I;
            const { url: E } = p.data;
            (I = (v = u.get(E)) == null ? void 0 : v.reject) == null || I.call(v, new Error(`Error receiving message from worker: ${E}`));
          }, b;
        } catch (b) {
          return C("Failed to new Worker", b), null;
        }
      }).filter(Boolean),
      fontFamilies: /* @__PURE__ */ new Set(),
      fontCssTexts: /* @__PURE__ */ new Map(),
      acceptOfImage: `${[
        st(i) && "image/webp",
        "image/svg+xml",
        "image/*",
        "*/*"
      ].filter(Boolean).join(",")};q=0.8`,
      requests: u,
      drawImageCount: 0,
      tasks: [],
      features: o,
      isEnable: (b) => {
        var p, E;
        return b === "restoreScrollPosition" ? typeof o == "boolean" ? !1 : (p = o[b]) != null ? p : !1 : typeof o == "boolean" ? o : (E = o[b]) != null ? E : !0;
      }
    });
    c.log.time("wait until load"), yield ft(e, c.timeout), c.log.timeEnd("wait until load");
    const { width: f, height: d } = ht(e, c);
    return c.width = f, c.height = d, c;
  });
}
function Ae(e) {
  if (!e)
    return;
  const t = e.createElement("style"), r = t.ownerDocument.createTextNode(`
.______background-clip--text {
  background-clip: text;
  -webkit-background-clip: text;
}
`);
  return t.appendChild(r), t;
}
function ht(e, t) {
  let { width: r, height: n } = t;
  if (A(e) && (!r || !n)) {
    const a = e.getBoundingClientRect();
    r = r || a.width || Number(e.getAttribute("width")) || 0, n = n || a.height || Number(e.getAttribute("height")) || 0;
  }
  return { width: r, height: n };
}
function wt(e, t) {
  return S(this, null, function* () {
    const {
      log: r,
      timeout: n,
      drawImageCount: a,
      drawImageInterval: s
    } = t;
    r.time("image to canvas");
    const o = yield P(e, { timeout: n }), { canvas: i, context2d: l } = pt(e.ownerDocument, t), u = () => {
      try {
        l == null || l.drawImage(o, 0, 0, i.width, i.height);
      } catch (c) {
        C("Failed to drawImage", c);
      }
    };
    if (u(), t.isEnable("fixSvgXmlDecode"))
      for (let c = 0; c < a; c++)
        yield new Promise((f) => {
          setTimeout(() => {
            u(), f();
          }, c + s);
        });
    return t.drawImageCount = 0, r.timeEnd("image to canvas"), i;
  });
}
function pt(e, t) {
  const { width: r, height: n, scale: a, backgroundColor: s, maximumCanvasSize: o } = t, i = e.createElement("canvas");
  i.width = Math.floor(r * a), i.height = Math.floor(n * a), i.style.width = `${r}px`, i.style.height = `${n}px`, o && (i.width > o || i.height > o) && (i.width > o && i.height > o ? i.width > i.height ? (i.height *= o / i.width, i.width = o) : (i.width *= o / i.height, i.height = o) : i.width > o ? (i.height *= o / i.width, i.width = o) : (i.width *= o / i.height, i.height = o));
  const l = i.getContext("2d");
  return l && s && (l.fillStyle = s, l.fillRect(0, 0, i.width, i.height)), { canvas: i, context2d: l };
}
const yt = [
  "width",
  "height",
  "-webkit-text-fill-color"
], bt = [
  "stroke",
  "fill"
];
function Ne(e, t, r) {
  var y;
  const { defaultComputedStyles: n, ownerDocument: a } = r, s = e.nodeName.toLowerCase(), o = U(e) && s !== "svg", i = o ? bt.map((g) => [g, e.getAttribute(g)]).filter(([, g]) => g !== null) : [], l = [
    o && "svg",
    s,
    i.map((g, b) => `${g}=${b}`).join(","),
    t
  ].filter(Boolean).join(":");
  if (n.has(l))
    return n.get(l);
  let u = r.sandbox;
  if (!u)
    try {
      a && (u = a.createElement("iframe"), u.id = `__SANDBOX__-${ve()}`, u.width = "0", u.height = "0", u.style.visibility = "hidden", u.style.position = "fixed", a.body.appendChild(u), (y = u.contentWindow) == null || y.document.write('<!DOCTYPE html><meta charset="UTF-8"><title></title><body>'), r.sandbox = u);
    } catch (g) {
      C("Failed to create iframe sandbox", g);
    }
  if (!u)
    return /* @__PURE__ */ new Map();
  const c = u.contentWindow;
  if (!c)
    return /* @__PURE__ */ new Map();
  const f = c.document;
  let d, m;
  o ? (d = f.createElementNS(j, "svg"), m = d.ownerDocument.createElementNS(d.namespaceURI, s), i.forEach(([g, b]) => {
    m.setAttributeNS(null, g, b);
  }), d.appendChild(m)) : d = m = f.createElement(s), m.textContent = " ", f.body.appendChild(d);
  const h = c.getComputedStyle(m, t), w = /* @__PURE__ */ new Map();
  for (let g = h.length, b = 0; b < g; b++) {
    const p = h.item(b);
    yt.includes(p) || w.set(p, h.getPropertyValue(p));
  }
  return f.body.removeChild(d), n.set(l, w), w;
}
function Ie(e, t, r) {
  var i;
  const n = /* @__PURE__ */ new Map(), a = [], s = /* @__PURE__ */ new Map();
  if (r)
    for (const l of r)
      o(l);
  else
    for (let l = e.length, u = 0; u < l; u++) {
      const c = e.item(u);
      o(c);
    }
  for (let l = a.length, u = 0; u < l; u++)
    (i = s.get(a[u])) == null || i.forEach((c, f) => n.set(f, c));
  function o(l) {
    const u = e.getPropertyValue(l), c = e.getPropertyPriority(l), f = l.lastIndexOf("-"), d = f > -1 ? l.substring(0, f) : void 0;
    if (d) {
      let m = s.get(d);
      m || (m = /* @__PURE__ */ new Map(), s.set(d, m)), m.set(l, [u, c]);
    }
    t.get(l) === u && !c || (d ? a.push(d) : n.set(l, [u, c]));
  }
  return n;
}
const St = [
  ":before",
  ":after"
  // ':placeholder', TODO
], Et = [
  ":-webkit-scrollbar",
  ":-webkit-scrollbar-button",
  // ':-webkit-scrollbar:horizontal', TODO
  ":-webkit-scrollbar-thumb",
  ":-webkit-scrollbar-track",
  ":-webkit-scrollbar-track-piece",
  // ':-webkit-scrollbar:vertical', TODO
  ":-webkit-scrollbar-corner",
  ":-webkit-resizer"
];
function Ct(e, t, r, n) {
  const { ownerWindow: a, svgStyleElement: s, svgStyles: o, currentNodeStyle: i } = n;
  if (!s || !a)
    return;
  function l(u) {
    var b;
    const c = a.getComputedStyle(e, u);
    let f = c.getPropertyValue("content");
    if (!f || f === "none")
      return;
    f = f.replace(/(')|(")|(counter\(.+\))/g, "");
    const d = [ve()], m = Ne(e, u, n);
    i == null || i.forEach((p, E) => {
      m.delete(E);
    });
    const h = Ie(c, m, n.includeStyleProperties);
    h.delete("content"), h.delete("-webkit-locale"), ((b = h.get("background-clip")) == null ? void 0 : b[0]) === "text" && t.classList.add("______background-clip--text");
    const w = [
      `content: '${f}';`
    ];
    if (h.forEach(([p, E], v) => {
      w.push(`${v}: ${p}${E ? " !important" : ""};`);
    }), w.length === 1)
      return;
    try {
      t.className = [t.className, ...d].join(" ");
    } catch (p) {
      return;
    }
    const y = w.join(`
  `);
    let g = o.get(y);
    g || (g = [], o.set(y, g)), g.push(`.${d[0]}:${u}`);
  }
  St.forEach(l), r && Et.forEach(l);
}
function vt(e, t) {
  ne(e) && (t.innerHTML = e.value), (ne(e) || Qe(e) || tt(e)) && t.setAttribute("value", e.value);
}
function Tt(e, t, r, n) {
  var f, d, m, h;
  const { ownerWindow: a, includeStyleProperties: s, currentParentNodeStyle: o } = n, i = t.style, l = a.getComputedStyle(e), u = Ne(e, null, n);
  o == null || o.forEach((w, y) => {
    u.delete(y);
  });
  const c = Ie(l, u, s);
  return c.delete("transition-property"), c.delete("all"), c.delete("d"), c.delete("content"), r && (c.delete("margin-top"), c.delete("margin-right"), c.delete("margin-bottom"), c.delete("margin-left"), c.delete("margin-block-start"), c.delete("margin-block-end"), c.delete("margin-inline-start"), c.delete("margin-inline-end"), c.set("box-sizing", ["border-box", ""])), ((f = c.get("background-clip")) == null ? void 0 : f[0]) === "text" && t.classList.add("______background-clip--text"), pe && (c.has("font-kerning") || c.set("font-kerning", ["normal", ""]), (((d = c.get("overflow-x")) == null ? void 0 : d[0]) === "hidden" || ((m = c.get("overflow-y")) == null ? void 0 : m[0]) === "hidden") && ((h = c.get("text-overflow")) == null ? void 0 : h[0]) === "ellipsis" && e.scrollWidth === e.clientWidth && c.set("text-overflow", ["clip", ""])), c.forEach(([w, y], g) => {
    i.setProperty(g, w, y);
  }), c;
}
function At(e, t) {
  var r;
  try {
    if ((r = e == null ? void 0 : e.contentDocument) != null && r.body)
      return G(e.contentDocument.body, t);
  } catch (n) {
    C("Failed to clone iframe", n);
  }
  return e.cloneNode(!1);
}
function xe(e) {
  if (e.ownerDocument)
    try {
      const a = e.toDataURL();
      if (a !== "data:,")
        return k(a, e.ownerDocument);
    } catch (a) {
    }
  const t = e.cloneNode(!1), r = e.getContext("2d"), n = t.getContext("2d");
  try {
    return r && n && n.putImageData(
      r.getImageData(0, 0, e.width, e.height),
      0,
      0
    ), t;
  } catch (a) {
    C("Failed to clone canvas", a);
  }
  return t;
}
function Nt(e) {
  return S(this, null, function* () {
    if (e.ownerDocument && !e.currentSrc && e.poster)
      return k(e.poster, e.ownerDocument);
    const t = e.cloneNode(!1);
    t.crossOrigin = "anonymous", e.currentSrc && e.currentSrc !== e.src && (t.src = e.currentSrc);
    const r = t.ownerDocument;
    if (r) {
      let n = !0;
      if (yield P(t, {
        onError: () => n = !1
      }), !n)
        return e.poster ? k(e.poster, e.ownerDocument) : t;
      t.currentTime = e.currentTime, yield new Promise((s) => {
        t.addEventListener("seeked", s, { once: !0 });
      });
      const a = r.createElement("canvas");
      a.width = e.offsetWidth, a.height = e.offsetHeight;
      try {
        const s = a.getContext("2d");
        s && s.drawImage(t, 0, 0, a.width, a.height);
      } catch (s) {
        return C("Failed to clone video", s), e.poster ? k(e.poster, e.ownerDocument) : t;
      }
      return xe(a);
    }
    return t;
  });
}
function It(e) {
  const t = e.cloneNode(!1);
  return e.currentSrc && e.currentSrc !== e.src && (t.src = e.currentSrc, t.srcset = ""), t.loading === "lazy" && (t.loading = "eager"), t;
}
function xt(e, t) {
  return Ke(e) ? xe(e) : nt(e) ? At(e, t) : D(e) ? It(e) : O(e) ? Nt(e) : e.cloneNode(!1);
}
const oe = /* @__PURE__ */ new Set([
  "symbol"
  // test/fixtures/svg.symbol.html
]);
function ae(e, t, r, n) {
  return S(this, null, function* () {
    if (A(r) && (Ze(r) || et(r)) || n.filter && !n.filter(r))
      return;
    oe.has(t.nodeName) || oe.has(r.nodeName) ? n.currentParentNodeStyle = void 0 : n.currentParentNodeStyle = n.currentNodeStyle;
    const a = yield G(r, n);
    n.isEnable("restoreScrollPosition") && kt(e, a), t.appendChild(a);
  });
}
function se(e, t, r) {
  return S(this, null, function* () {
    var a, s;
    const n = (s = A(e) ? (a = e.shadowRoot) == null ? void 0 : a.firstChild : void 0) != null ? s : e.firstChild;
    for (let o = n; o; o = o.nextSibling)
      if (!Ye(o))
        if (A(o) && rt(o) && typeof o.assignedNodes == "function") {
          const i = o.assignedNodes();
          for (let l = 0; l < i.length; l++)
            yield ae(e, t, i[l], r);
        } else
          yield ae(e, t, o, r);
  });
}
function kt(e, t) {
  if (!F(e) || !F(t))
    return;
  const { scrollTop: r, scrollLeft: n } = e;
  if (!r && !n)
    return;
  const { transform: a } = t.style, s = new DOMMatrix(a), { a: o, b: i, c: l, d: u } = s;
  s.a = 1, s.b = 0, s.c = 0, s.d = 1, s.translateSelf(-n, -r), s.a = o, s.b = i, s.c = l, s.d = u, t.style.transform = s.toString();
}
function Rt(e, t) {
  const { backgroundColor: r, width: n, height: a, style: s } = t, o = e.style;
  if (r && o.setProperty("background-color", r, "important"), n && o.setProperty("width", `${n}px`, "important"), a && o.setProperty("height", `${a}px`, "important"), s)
    for (const i in s)
      o[i] = s[i];
}
const Dt = /^[\w-:]+$/;
function G(e, t, r = !1) {
  return S(this, null, function* () {
    var i, l, u, c;
    const { ownerDocument: n, ownerWindow: a, fontFamilies: s } = t;
    if (n && Je(e))
      return n.createTextNode(e.data);
    if (n && a && A(e) && (F(e) || U(e))) {
      const f = yield xt(e, t);
      if (t.isEnable("removeAbnormalAttributes")) {
        const h = f.getAttributeNames();
        for (let w = h.length, y = 0; y < w; y++) {
          const g = h[y];
          Dt.test(g) || f.removeAttribute(g);
        }
      }
      const d = t.currentNodeStyle = Tt(e, f, r, t);
      r && Rt(f, t);
      let m = !1;
      if (t.isEnable("copyScrollbar")) {
        const h = [
          (i = d.get("overflow-x")) == null ? void 0 : i[0],
          (l = d.get("overflow-y")) == null ? void 0 : l[1]
        ];
        m = h.includes("scroll") || (h.includes("auto") || h.includes("overlay")) && (e.scrollHeight > e.clientHeight || e.scrollWidth > e.clientWidth);
      }
      return Ct(e, f, m, t), vt(e, f), (c = Te((u = d.get("font-family")) == null ? void 0 : u[0])) == null || c.forEach((h) => s.add(h)), O(e) || (yield se(e, f, t)), f;
    }
    const o = e.cloneNode(!1);
    return yield se(e, o, t), o;
  });
}
function Ft(e) {
  if (e.ownerDocument = void 0, e.ownerWindow = void 0, e.svgStyleElement = void 0, e.svgDefsElement = void 0, e.svgStyles.clear(), e.defaultComputedStyles.clear(), e.sandbox) {
    try {
      e.sandbox.remove();
    } catch (t) {
    }
    e.sandbox = void 0;
  }
  e.workers = [], e.fontFamilies.clear(), e.fontCssTexts.clear(), e.requests.clear(), e.tasks = [];
}
function Pt(e) {
  const i = e, { url: t, timeout: r, responseType: n } = i, a = re(i, ["url", "timeout", "responseType"]), s = new AbortController(), o = r ? setTimeout(() => s.abort(), r) : void 0;
  return fetch(t, T({ signal: s.signal }, a)).then((l) => {
    if (!l.ok)
      throw new Error("Failed fetch, not 2xx response", { cause: l });
    switch (n) {
      case "dataUrl":
        return l.blob().then(lt);
      case "text":
      default:
        return l.text();
    }
  }).finally(() => clearTimeout(o));
}
function _(e, t) {
  const { url: r, requestType: n = "text", responseType: a = "text", imageDom: s } = t;
  let o = r;
  const {
    timeout: i,
    acceptOfImage: l,
    requests: u,
    fetchFn: c,
    fetch: {
      requestInit: f,
      bypassingCache: d,
      placeholderImage: m
    },
    workers: h
  } = e;
  n === "image" && (M || X) && e.drawImageCount++;
  let w = u.get(r);
  if (!w) {
    d && d instanceof RegExp && d.test(o) && (o += (/\?/.test(o) ? "&" : "?") + new Date().getTime());
    const y = T({
      url: o,
      timeout: i,
      responseType: a,
      headers: n === "image" ? { accept: l } : void 0
    }, f);
    w = {
      type: n,
      resolve: void 0,
      reject: void 0,
      response: null
    }, w.response = (() => S(this, null, function* () {
      if (c && n === "image") {
        const g = yield c(r);
        if (g)
          return g;
      }
      return !M && r.startsWith("http") && h.length ? new Promise((g, b) => {
        h[u.size & h.length - 1].postMessage(T({ rawUrl: r }, y)), w.resolve = g, w.reject = b;
      }) : Pt(y);
    }))().catch((g) => {
      if (u.delete(r), n === "image" && m)
        return C("Failed to fetch image base64, trying to use placeholder image", o), typeof m == "string" ? m : m(s);
      throw g;
    }), u.set(r, w);
  }
  return w.response;
}
function ke(e, t, r, n) {
  return S(this, null, function* () {
    if (!Re(e))
      return e;
    for (const [a, s] of _t(e, t))
      try {
        const o = yield _(
          r,
          {
            url: s,
            requestType: n ? "image" : "text",
            responseType: "dataUrl"
          }
        );
        e = e.replace(Ut(a), `$1${o}$3`);
      } catch (o) {
        C("Failed to fetch css data url", a, o);
      }
    return e;
  });
}
function Re(e) {
  return /url\((['"]?)([^'"]+?)\1\)/.test(e);
}
const De = /url\((['"]?)([^'"]+?)\1\)/g;
function _t(e, t) {
  const r = [];
  return e.replace(De, (n, a, s) => (r.push([s, be(s, t)]), n)), r.filter(([n]) => !V(n));
}
function Ut(e) {
  const t = e.replace(/([.*+?^${}()|\[\]\/\\])/g, "\\$1");
  return new RegExp(`(url\\(['"]?)(${t})(['"]?\\))`, "g");
}
function $t(e, t) {
  return S(this, null, function* () {
    const {
      ownerDocument: r,
      svgStyleElement: n,
      fontFamilies: a,
      fontCssTexts: s,
      tasks: o,
      font: i
    } = t;
    if (!(!r || !n || !a.size))
      if (i && i.cssText) {
        const l = ce(i.cssText, t);
        n.appendChild(r.createTextNode(`${l}
`));
      } else {
        const l = Array.from(r.styleSheets).filter((c) => {
          try {
            return "cssRules" in c && Boolean(c.cssRules.length);
          } catch (f) {
            return C(`Error while reading CSS rules from ${c.href}`, f), !1;
          }
        });
        yield Promise.all(
          l.flatMap((c) => Array.from(c.cssRules).map((f, d) => S(this, null, function* () {
            if (Xe(f)) {
              let m = d + 1;
              const h = f.href;
              let w = "";
              try {
                w = yield _(t, {
                  url: h,
                  requestType: "text",
                  responseType: "text"
                });
              } catch (g) {
                C(`Error fetch remote css import from ${h}`, g);
              }
              const y = w.replace(
                De,
                (g, b, p) => g.replace(p, be(p, h))
              );
              for (const g of Lt(y))
                try {
                  c.insertRule(
                    g,
                    g.startsWith("@import") ? m += 1 : c.cssRules.length
                  );
                } catch (b) {
                  C("Error inserting rule from remote css import", { rule: g, error: b });
                }
            }
          })))
        ), l.flatMap((c) => Array.from(c.cssRules)).filter((c) => {
          var f;
          return ze(c) && Re(c.style.getPropertyValue("src")) && ((f = Te(c.style.getPropertyValue("font-family"))) == null ? void 0 : f.some((d) => a.has(d)));
        }).forEach((c) => {
          const f = c, d = s.get(f.cssText);
          d ? n.appendChild(r.createTextNode(`${d}
`)) : o.push(
            ke(
              f.cssText,
              f.parentStyleSheet ? f.parentStyleSheet.href : null,
              t
            ).then((m) => {
              m = ce(m, t), s.set(f.cssText, m), n.appendChild(r.createTextNode(`${m}
`));
            })
          );
        });
      }
  });
}
const Bt = /(\/\*[\s\S]*?\*\/)/gi, ie = /((@.*?keyframes [\s\S]*?){([\s\S]*?}\s*?)})/gi;
function Lt(e) {
  if (e == null)
    return [];
  const t = [];
  let r = e.replace(Bt, "");
  for (; ; ) {
    const s = ie.exec(r);
    if (!s)
      break;
    t.push(s[0]);
  }
  r = r.replace(ie, "");
  const n = /@import[\s\S]*?url\([^)]*\)[\s\S]*?;/gi, a = new RegExp(
    "((\\s*?(?:\\/\\*[\\s\\S]*?\\*\\/)?\\s*?@media[\\s\\S]*?){([\\s\\S]*?)}\\s*?})|(([\\s\\S]*?){([\\s\\S]*?)})",
    "gi"
  );
  for (; ; ) {
    let s = n.exec(r);
    if (s)
      a.lastIndex = n.lastIndex;
    else if (s = a.exec(r), s)
      n.lastIndex = a.lastIndex;
    else
      break;
    t.push(s[0]);
  }
  return t;
}
const Mt = /url\([^)]+\)\s*format\((["']?)([^"']+)\1\)/g, Ot = /src:\s*(?:url\([^)]+\)\s*format\([^)]+\)[,;]\s*)+/g;
function ce(e, t) {
  const { font: r } = t, n = r ? r == null ? void 0 : r.preferredFormat : void 0;
  return n ? e.replace(Ot, (a) => {
    for (; ; ) {
      const [s, , o] = Mt.exec(a) || [];
      if (!o)
        return "";
      if (o === n)
        return `src: ${s};`;
    }
  }) : e;
}
function Wt(e, t) {
  if (D(e)) {
    const r = e.currentSrc || e.src;
    if (!V(r))
      return [
        _(t, {
          url: r,
          imageDom: e,
          requestType: "image",
          responseType: "dataUrl"
        }).then((n) => {
          n && (e.srcset = "", e.dataset.originalSrc = r, e.src = n || "");
        })
      ];
    (M || X) && t.drawImageCount++;
  } else if (U(e) && !V(e.href.baseVal)) {
    const r = e.href.baseVal;
    return [
      _(t, {
        url: r,
        imageDom: e,
        requestType: "image",
        responseType: "dataUrl"
      }).then((n) => {
        n && (e.dataset.originalSrc = r, e.href.baseVal = n || "");
      })
    ];
  }
  return [];
}
const jt = [
  "background-image",
  "border-image-source",
  "-webkit-border-image",
  "-webkit-mask-image",
  "list-style-image"
];
function qt(e, t) {
  return jt.map((r) => {
    const n = e.getPropertyValue(r);
    return !n || n === "none" ? null : ((M || X) && t.drawImageCount++, ke(n, null, t, !0).then((a) => {
      !a || n === a || e.setProperty(
        r,
        a,
        e.getPropertyPriority(r)
      );
    }));
  }).filter(Boolean);
}
function Vt(e, t) {
  var i;
  const { ownerDocument: r, svgDefsElement: n } = t, a = (i = e.getAttribute("href")) != null ? i : e.getAttribute("xlink:href");
  if (!a)
    return [];
  const [s, o] = a.split("#");
  if (o) {
    const l = `#${o}`, u = r == null ? void 0 : r.querySelector(`svg ${l}`);
    if (s && e.setAttribute("href", l), n != null && n.querySelector(l))
      return [];
    if (u)
      return n == null || n.appendChild(u.cloneNode(!0)), [];
    if (s)
      return [
        _(t, {
          url: s,
          responseType: "text"
        }).then((c) => {
          n == null || n.insertAdjacentHTML("beforeend", c);
        })
      ];
  }
  return [];
}
function Fe(e, t) {
  const { tasks: r } = t;
  A(e) && ((D(e) || ye(e)) && r.push(...Wt(e, t)), Ge(e) && r.push(...Vt(e, t))), F(e) && r.push(...qt(e.style, t)), e.childNodes.forEach((n) => {
    Fe(n, t);
  });
}
function Ht(e, t) {
  return S(this, null, function* () {
    const r = yield N(e, t);
    if (A(r.node) && U(r.node))
      return r.node;
    const {
      ownerDocument: n,
      log: a,
      tasks: s,
      svgStyleElement: o,
      svgDefsElement: i,
      svgStyles: l,
      font: u,
      progress: c,
      autoDestruct: f,
      onCloneNode: d,
      onEmbedNode: m,
      onCreateForeignObjectSvg: h
    } = r;
    a.time("clone node");
    const w = yield G(r.node, r, !0);
    if (o && n) {
      let E = "";
      l.forEach((v, I) => {
        E += `${v.join(`,
`)} {
  ${I}
}
`;
      }), o.appendChild(n.createTextNode(E));
    }
    a.timeEnd("clone node"), d == null || d(w), u !== !1 && A(w) && (a.time("embed web font"), yield $t(w, r), a.timeEnd("embed web font")), a.time("embed node"), Fe(w, r);
    const y = s.length;
    let g = 0;
    const b = () => S(this, null, function* () {
      for (; ; ) {
        const E = s.pop();
        if (!E)
          break;
        try {
          yield E;
        } catch (v) {
          C("Failed to run task", v);
        }
        c == null || c(++g, y);
      }
    });
    c == null || c(g, y), yield Promise.all([...Array(4)].map(b)), a.timeEnd("embed node"), m == null || m(w);
    const p = zt(w, r);
    return i && p.insertBefore(i, p.children[0]), o && p.insertBefore(o, p.children[0]), f && Ft(r), h == null || h(p), p;
  });
}
function zt(e, t) {
  const { width: r, height: n } = t, a = Se(r, n, e.ownerDocument), s = a.ownerDocument.createElementNS(a.namespaceURI, "foreignObject");
  return s.setAttributeNS(null, "x", "0%"), s.setAttributeNS(null, "y", "0%"), s.setAttributeNS(null, "width", "100%"), s.setAttributeNS(null, "height", "100%"), s.append(e), a.appendChild(s), a;
}
function Y(e, t) {
  return S(this, null, function* () {
    var o;
    const r = yield N(e, t), n = yield Ht(r), a = Ee(n, r.isEnable("removeControlCharacter"));
    r.autoDestruct || (r.svgStyleElement = Ae(r.ownerDocument), r.svgDefsElement = (o = r.ownerDocument) == null ? void 0 : o.createElementNS(j, "defs"), r.svgStyles.clear());
    const s = k(a, n.ownerDocument);
    return yield wt(s, r);
  });
}
function Yt(e, t) {
  return S(this, null, function* () {
    const r = yield N(e, t), { log: n, type: a, quality: s, dpi: o } = r, i = yield Y(r);
    n.time("canvas to blob");
    const l = yield it(i, a, s);
    if (["image/png", "image/jpeg"].includes(a) && o) {
      const u = yield ut(l.slice(0, 33));
      let c = new Uint8Array(u);
      return a === "image/png" ? c = he(c, o) : a === "image/jpeg" && (c = ue(c, o)), n.timeEnd("canvas to blob"), new Blob([c, l.slice(33)], { type: a });
    }
    return n.timeEnd("canvas to blob"), l;
  });
}
function $(e, t) {
  return S(this, null, function* () {
    const r = yield N(e, t), { log: n, quality: a, type: s, dpi: o } = r, i = yield Y(r);
    n.time("canvas to data url");
    let l = i.toDataURL(s, a);
    if (["image/png", "image/jpeg"].includes(s) && o && we && Ve) {
      const [u, c] = l.split(",");
      let f = 0, d = !1;
      if (s === "image/png") {
        const p = je(c);
        p >= 0 ? (f = Math.ceil((p + 28) / 3) * 4, d = !0) : f = 33 / 3 * 4;
      } else
        s === "image/jpeg" && (f = 18 / 3 * 4);
      const m = c.substring(0, f), h = c.substring(f), w = window.atob(m), y = new Uint8Array(w.length);
      for (let p = 0; p < y.length; p++)
        y[p] = w.charCodeAt(p);
      const g = s === "image/png" ? he(y, o, d) : ue(y, o), b = window.btoa(String.fromCharCode(...g));
      l = [u, ",", b, h].join("");
    }
    return n.timeEnd("canvas to data url"), l;
  });
}
function Xt(e, t) {
  return S(this, null, function* () {
    const r = yield N(e, t), { width: n, height: a, ownerDocument: s } = r, o = yield $(r), i = Se(n, a, s), l = i.ownerDocument.createElementNS(i.namespaceURI, "image");
    return l.setAttributeNS(null, "href", o), l.setAttributeNS(null, "height", "100%"), l.setAttributeNS(null, "width", "100%"), i.appendChild(l), Ee(i, r.isEnable("removeControlCharacter"));
  });
}
function Jt(e, t) {
  return S(this, null, function* () {
    const r = yield N(e, t), { ownerDocument: n, width: a, height: s, scale: o, type: i } = r, l = i === "image/svg+xml" ? yield Xt(r) : yield $(r), u = k(l, n);
    return u.width = Math.floor(a * o), u.height = Math.floor(s * o), u.style.width = `${a}px`, u.style.height = `${s}px`, u;
  });
}
function Kt(e, t) {
  return S(this, null, function* () {
    return $(
      yield N(e, R(T({}, t), { type: "image/jpeg" }))
    );
  });
}
function Qt(e, t) {
  return S(this, null, function* () {
    const r = yield N(e, t), n = yield Y(r);
    return n.getContext("2d").getImageData(0, 0, n.width, n.height).data;
  });
}
function Zt(e, t) {
  return S(this, null, function* () {
    return $(
      yield N(e, R(T({}, t), { type: "image/png" }))
    );
  });
}
function er(e, t) {
  return S(this, null, function* () {
    return $(
      yield N(e, R(T({}, t), { type: "image/webp" }))
    );
  });
}
export {
  gt as createContext,
  Ft as destroyContext,
  Yt as domToBlob,
  Y as domToCanvas,
  $ as domToDataUrl,
  Ht as domToForeignObjectSvg,
  Jt as domToImage,
  Kt as domToJpeg,
  Qt as domToPixel,
  Zt as domToPng,
  Xt as domToSvg,
  er as domToWebp,
  P as loadMedia,
  ft as waitUntilLoad
};
