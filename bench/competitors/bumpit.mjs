// Bump It / NormalSmith NS.* engine, extracted verbatim from the itch.io demo
// (theluckyduck666.itch.io/bump-it, html-classic.itch.zone/html/19548776).
// Adapter at the bottom maps the frame pipeline onto a PixelBuffer.

const NS = {};

/* ---------- helpers ---------- */
function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
function smoothstep(t) { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); }

/* ---------- 1. luminance -> height (alpha-aware) ---------- */
NS.luminanceHeight = function (rgba, w, h, opts) {
  opts = opts || {};
  const intensity = opts.intensity == null ? 1 : opts.intensity;
  const invert = !!opts.invert;
  const alphaCut = opts.alphaCut == null ? 8 : opts.alphaCut;
  const height = new Float32Array(w * h);
  const mask = new Uint8Array(w * h); // 1 = opaque enough to keep
  for (let i = 0, n = w * h; i < n; i++) {
    const a = rgba[i * 4 + 3];
    if (a < alphaCut) { mask[i] = 0; height[i] = 0; continue; }
    mask[i] = 1;
    let lum = (0.2126 * rgba[i * 4] + 0.7152 * rgba[i * 4 + 1] + 0.0722 * rgba[i * 4 + 2]) / 255;
    if (invert) lum = 1 - lum;
    height[i] = lum * intensity;
  }
  return { height, mask };
};

/* ---------- 2. chamfer distance to nearest transparent pixel ---------- */
NS.distanceToTransparent = function (mask, w, h, maxDist) {
  maxDist = maxDist == null ? 64 : maxDist;
  const INF = 1e9;
  const d = new Float32Array(w * h);
  for (let i = 0; i < w * h; i++) d[i] = mask[i] ? INF : 0;
  const C1 = 1, C2 = 1.41421356;
  // forward pass
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      if (!mask[i]) continue;
      let m = d[i];
      if (x > 0) m = Math.min(m, d[i - 1] + C1);
      if (y > 0) {
        m = Math.min(m, d[i - w] + C1);
        if (x > 0) m = Math.min(m, d[i - w - 1] + C2);
        if (x < w - 1) m = Math.min(m, d[i - w + 1] + C2);
      }
      d[i] = m;
    }
  }
  // backward pass
  for (let y = h - 1; y >= 0; y--) {
    for (let x = w - 1; x >= 0; x--) {
      const i = y * w + x;
      if (!mask[i]) continue;
      let m = d[i];
      if (x < w - 1) m = Math.min(m, d[i + 1] + C1);
      if (y < h - 1) {
        m = Math.min(m, d[i + w] + C1);
        if (x < w - 1) m = Math.min(m, d[i + w + 1] + C2);
        if (x > 0) m = Math.min(m, d[i + w - 1] + C2);
      }
      d[i] = m;
    }
  }
  for (let i = 0; i < w * h; i++) if (d[i] > maxDist) d[i] = maxDist;
  return d;
};

/* ---------- 3. bevel: blend luminance height toward rounded silhouette ---------- */
NS.applyBevel = function (height, mask, dist, w, h, width, amount) {
  width = Math.max(width || 0, 0.0001);
  amount = clamp(amount == null ? 0.6 : amount, 0, 1);
  const out = new Float32Array(height); // copy; transparent stays 0
  for (let i = 0; i < w * h; i++) {
    if (!mask[i] || amount === 0) continue;
    const t = smoothstep(dist[i] / width); // 0 at silhouette -> 1 inside
    out[i] = height[i] * (1 - amount) + t * amount;
  }
  return out;
};

/* ---------- 4. masked separable box blur (transparent pixels stay 0) ---------- */
NS.smoothMasked = function (height, mask, w, h, radius) {
  radius = Math.round(radius || 0);
  if (radius <= 0) return new Float32Array(height);
  // masked separable box blur via prefix sums: out = blur(H*mask)/blur(mask),
  // transparent pixels stay 0, no dark halos bleed in from holes.
  function blurRows(src, wgt) {
    const P = new Float64Array(w + 1), W = new Float64Array(w + 1);
    const o = new Float32Array(w * h), ow = new Float32Array(w * h);
    for (let y = 0; y < h; y++) {
      P[0] = 0; W[0] = 0;
      for (let x = 0; x < w; x++) { P[x + 1] = P[x] + src[y * w + x]; W[x + 1] = W[x] + wgt[y * w + x]; }
      for (let x = 0; x < w; x++) {
        const x0 = Math.max(x - radius, 0), x1 = Math.min(x + radius, w - 1);
        o[y * w + x] = P[x1 + 1] - P[x0]; ow[y * w + x] = W[x1 + 1] - W[x0];
      }
    }
    return { o, ow };
  }
  const v = new Float32Array(w * h);
  for (let i = 0; i < w * h; i++) v[i] = height[i] * mask[i];
  const hp = blurRows(v, mask);
  // vertical pass on the horizontal results
  const P = new Float64Array(h + 1), W = new Float64Array(h + 1);
  const out = new Float32Array(w * h);
  for (let x = 0; x < w; x++) {
    P[0] = 0; W[0] = 0;
    for (let y = 0; y < h; y++) { P[y + 1] = P[y] + hp.o[y * w + x]; W[y + 1] = W[y] + hp.ow[y * w + x]; }
    for (let y = 0; y < h; y++) {
      const y0 = Math.max(y - radius, 0), y1 = Math.min(y + radius, h - 1);
      const s = P[y1 + 1] - P[y0], sw = W[y1 + 1] - W[y0];
      const i = y * w + x;
      out[i] = (!mask[i] || sw < 1e-6) ? 0 : s / sw;
    }
  }
  return out;
};

/* ---------- 5. Sobel height -> tangent-space normals ---------- */
NS.computeNormals = function (height, mask, w, h, strength, wrap, yFlip) {
  strength = strength == null ? 2 : strength;
  const out = new Uint8Array(w * h * 3);
  const nrm = new Float32Array(w * h * 3); // decoded float normals, for preview/QA
  const H = function (x, y) {
    if (wrap) { x = ((x % w) + w) % w; y = ((y % h) + h) % h; }
    else { x = clamp(x, 0, w - 1); y = clamp(y, 0, h - 1); }
    return height[y * w + x];
  };
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      let nx = 0, ny = 0, nz = 1;
      if (mask[i]) {
        const gx = (H(x + 1, y - 1) + 2 * H(x + 1, y) + H(x + 1, y + 1))
                 - (H(x - 1, y - 1) + 2 * H(x - 1, y) + H(x - 1, y + 1));
        const gy = (H(x - 1, y + 1) + 2 * H(x, y + 1) + H(x + 1, y + 1))
                 - (H(x - 1, y - 1) + 2 * H(x, y - 1) + H(x + 1, y - 1));
        // Sobel sums to 8x the per-pixel slope for linear ramps
        nx = -(gx / 8) * strength;
        ny = (yFlip ? -1 : 1) * (gy / 8) * strength; // false = OpenGL (+Y up)
        const inv = 1 / Math.sqrt(nx * nx + ny * ny + 1);
        nx *= inv; ny *= inv; nz = inv;
      }
      nrm[i * 3] = nx; nrm[i * 3 + 1] = ny; nrm[i * 3 + 2] = nz;
      out[i * 3] = Math.round(clamp(nx * 0.5 + 0.5, 0, 1) * 255);
      out[i * 3 + 1] = Math.round(clamp(ny * 0.5 + 0.5, 0, 1) * 255);
      out[i * 3 + 2] = Math.round(clamp(nz * 0.5 + 0.5, 0, 1) * 255);
    }
  }
  return { rgb: out, nrm };
};

NS.decodeNormal = function (r, g, b) {
  const v = [r / 255 * 2 - 1, g / 255 * 2 - 1, b / 255 * 2 - 1];
  const l = Math.hypot(v[0], v[1], v[2]) || 1;
  return [v[0] / l, v[1] / l, v[2] / l];
};

/* ---------- 6. specular approximation from curvature ---------- */
NS.specularApprox = function (height, mask, w, h, gain) {
  gain = gain == null ? 6 : gain;
  const out = new Uint8Array(w * h);
  const H = function (x, y) {
    x = clamp(x, 0, w - 1); y = clamp(y, 0, h - 1);
    return height[y * w + x];
  };
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      if (!mask[i]) { out[i] = 0; continue; }
      const c = H(x, y);
      const lap = H(x - 1, y) + H(x + 1, y) + H(x, y - 1) + H(x, y + 1) - 4 * c;
      out[i] = Math.round(clamp(1 - Math.abs(lap) * gain, 0, 1) * 255);
    }
  }
  return out;
};

/* ---------- 7. sprite-sheet batch ---------- */
NS.splitSheet = function (rgba, w, h, frameW, frameH) {
  const cols = Math.floor(w / frameW), rows = Math.floor(h / frameH);
  const frames = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const f = new Uint8ClampedArray(frameW * frameH * 4);
      for (let y = 0; y < frameH; y++) {
        for (let x = 0; x < frameW; x++) {
          const s = ((r * frameH + y) * w + (c * frameW + x)) * 4;
          const d = (y * frameW + x) * 4;
          f[d] = rgba[s]; f[d + 1] = rgba[s + 1]; f[d + 2] = rgba[s + 2]; f[d + 3] = rgba[s + 3];
        }
      }
      frames.push({ rgba: f, w: frameW, h: frameH, col: c, row: r });
    }
  }
  return { frames, cols, rows };
};

// processFrame: full pipeline for one RGBA frame; returns {normalRgb, heightGray, specGray, w, h}
NS.processFrame = function (rgba, w, h, s) {
  s = s || {};
  const lh = NS.luminanceHeight(rgba, w, h, s);
  const bevelW = s.bevelWidth || 0, bevelA = s.bevelAmount == null ? 0.6 : s.bevelAmount;
  let hasTransparent = false;
  for (let i = 0; i < w * h; i++) if (!lh.mask[i]) { hasTransparent = true; break; }
  let height = lh.height;
  if (hasTransparent && bevelW > 0 && bevelA > 0) {
    const dist = NS.distanceToTransparent(lh.mask, w, h, bevelW);
    height = NS.applyBevel(lh.height, lh.mask, dist, w, h, bevelW, bevelA);
  }
  height = NS.smoothMasked(height, lh.mask, w, h, s.smooth || 0);
  const nm = NS.computeNormals(height, lh.mask, w, h, s.strength == null ? 2 : s.strength, !!s.wrap, !!s.yFlip);
  const spec = NS.specularApprox(height, lh.mask, w, h, 6);
  const heightGray = new Uint8Array(w * h);
  let hmax = 1e-6;
  for (let i = 0; i < w * h; i++) if (lh.mask[i] && height[i] > hmax) hmax = height[i];
  for (let i = 0; i < w * h; i++) heightGray[i] = lh.mask[i] ? Math.round(clamp(height[i] / hmax, 0, 1) * 255) : 0;
  return { normalRgb: nm.rgb, normalF: nm.nrm, heightGray, specGray: spec, mask: lh.mask, w, h };
};

NS.assembleSheet = function (framesRgb, frameW, frameH, cols, rows, channels) {
  const W = cols * frameW, H = rows * frameH;
  const out = channels === 1 ? new Uint8Array(W * H) : new Uint8Array(W * H * 3);
  framesRgb.forEach(function (fr, k) {
    const c = k % cols, r = Math.floor(k / cols);
    for (let y = 0; y < frameH; y++) {
      for (let x = 0; x < frameW; x++) {
        const dx = (r * frameH + y) * W + (c * frameW + x);
        const sx = y * frameW + x;
        if (channels === 1) out[dx] = fr[sx];
        else { out[dx * 3] = fr[sx * 3]; out[dx * 3 + 1] = fr[sx * 3 + 1]; out[dx * 3 + 2] = fr[sx * 3 + 2]; }
      }
    }
  });
  return { data: out, w: W, h: H };
};

/* ---------- 8. demo gating helper (pure) ---------- */
NS.clampDemo = function (w, h, maxDim) {
  maxDim = maxDim || 64;
  const m = Math.max(w, h);
  if (m <= maxDim) return { w, h, scale: 1, clamped: false };
  const scale = maxDim / m;
  return { w: Math.max(1, Math.round(w * scale)), h: Math.max(1, Math.round(h * scale)), scale, clamped: true };
};

/* ---------- 9. ground-truth shapes for QA ---------- */
NS.sphereHeightFn = function (w, h, r) {
  const cx = (w - 1) / 2, cy = (h - 1) / 2;
  return function (x, y) {
    const X = x - cx, Y = -(y - cy); // world Y up
    const q = r * r - X * X - Y * Y;
    return q <= 0 ? 0 : Math.sqrt(q) / r;
  };
};
NS.rampHeightFn = function (w, h, slope) {
  return function (x) { return (x / (w - 1)) * (slope == null ? 1 : slope); };
};
// analytic normals via central differences on the height FUNCTION (independent of Sobel)
NS.analyticNormals = function (heightFn, w, h, yFlip) {
  const e = 0.01, out = new Float32Array(w * h * 3);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const dhdx = (heightFn(x + e, y) - heightFn(x - e, y)) / (2 * e);
    const dhdy = (heightFn(x, y + e) - heightFn(x, y - e)) / (2 * e); // image y down
    let nx = -dhdx, ny = (yFlip ? -1 : 1) * dhdy, nz = 1;
    const l = Math.hypot(nx, ny, nz); nx /= l; ny /= l; nz /= l;
    const i = y * w + x;
    out[i * 3] = nx; out[i * 3 + 1] = ny; out[i * 3 + 2] = nz;
  }
  return out;
};
NS.angularError = function (a, b, w, h, maskFn) {
  let sum = 0, max = 0, n = 0;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    if (maskFn && !maskFn(x, y)) continue;
    const i = (y * w + x) * 3;
    const dot = clamp(a[i] * b[i] + a[i + 1] * b[i + 1] + a[i + 2] * b[i + 2], -1, 1);
    const deg = Math.acos(dot) * 180 / Math.PI;
    sum += deg; if (deg > max) max = deg; n++;
  }
  return { mean: n ? sum / n : 0, max, n };
};

export function bumpItNormalMap(source, opts = {}) {
  const rgba = source.data instanceof Uint8ClampedArray ? source.data : new Uint8ClampedArray(source.data);
  const settings = {
    bevelWidth: opts.bevelWidth ?? 4,
    bevelAmount: opts.bevelAmount ?? 0.6,
    smooth: opts.smooth ?? 1,
    strength: opts.strength ?? 2,
    wrap: false,
    yFlip: false,
    alphaCut: 8,
  };
  const r = NS.processFrame(rgba, source.width, source.height, settings);
  const { w, h, normalRgb, mask } = r;
  const data = new Uint8ClampedArray(w * h * 4);
  for (let i = 0; i < w * h; i++) {
    data[i * 4] = normalRgb[i * 3];
    data[i * 4 + 1] = normalRgb[i * 3 + 1];
    data[i * 4 + 2] = normalRgb[i * 3 + 2];
    data[i * 4 + 3] = mask[i] ? rgba[i * 4 + 3] : 0;
  }
  return { width: w, height: h, data };
}
