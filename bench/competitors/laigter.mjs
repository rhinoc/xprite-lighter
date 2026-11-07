// Laigter's normal pipeline (azagaya/laigter, GPL-3) reimplemented headlessly:
// alpha distance transform -> bevel curve -> emboss normal + distance normal.
// No GUI deps. Parameters match ImageProcessor's constructor defaults:
// normal_depth=250, normal_blur_radius=6, normal_bisel_depth=100,
// normal_bisel_distance=60, normal_bisel_blur_radius=10, normal_bisel_soft=true.

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);

// Gaussian-ish blur used by CImg's img.blur(sigma) — separable, zero-flux edges.
function gaussianBlur(src, w, h, sigma) {
  if (sigma <= 0) return Float32Array.from(src);
  const radius = Math.max(1, Math.ceil(sigma * 3));
  const kernel = new Float32Array(radius * 2 + 1);
  let sum = 0;
  for (let i = -radius; i <= radius; i++) {
    const v = Math.exp(-(i * i) / (2 * sigma * sigma));
    kernel[i + radius] = v;
    sum += v;
  }
  for (let i = 0; i < kernel.length; i++) kernel[i] /= sum;
  const tmp = new Float32Array(w * h);
  const out = new Float32Array(w * h);
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      let s = 0;
      for (let k = -radius; k <= radius; k++)
        s += src[y * w + clamp(x + k, 0, w - 1)] * kernel[k + radius];
      tmp[y * w + x] = s;
    }
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      let s = 0;
      for (let k = -radius; k <= radius; k++)
        s += tmp[clamp(y + k, 0, h - 1) * w + x] * kernel[k + radius];
      out[y * w + x] = s;
    }
  return out;
}

// CImg::distance(0) — exact Euclidean EDT (Felzenszwalb-Huttenlocher).
function euclideanDistance(mask, w, h) {
  const INF = 1e9;
  const d1 = new Float32Array(w * h);
  const oneD = (f, d, n) => {
    const v = new Int32Array(n);
    const z = new Float32Array(n + 1);
    let k = 0;
    v[0] = 0;
    z[0] = -INF;
    z[1] = INF;
    for (let q = 1; q < n; q++) {
      let s = ((f[q] + q * q) - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]);
      while (s <= z[k]) {
        k--;
        s = ((f[q] + q * q) - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]);
      }
      k++;
      v[k] = q;
      z[k] = s;
      z[k + 1] = INF;
    }
    k = 0;
    for (let q = 0; q < n; q++) {
      while (z[k + 1] < q) k++;
      const r = v[k];
      d[q] = (q - r) * (q - r) + f[r];
    }
  };
  const f = new Float32Array(Math.max(w, h));
  const d = new Float32Array(Math.max(w, h));
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) f[x] = mask[y * w + x] ? 0 : INF;
    oneD(f, d, w);
    for (let x = 0; x < w; x++) d1[y * w + x] = d[x];
  }
  for (let x = 0; x < w; x++) {
    for (let y = 0; y < h; y++) f[y] = d1[y * w + x];
    oneD(f, d, h);
    for (let y = 0; y < h; y++) d1[y * w + x] = Math.sqrt(d[y]);
  }
  return d1;
}

// Central-difference normals with one-sided second-order edges; img in [0,1].
function calculateNormal(img, w, h, alpha, depth, blurSigma) {
  const blurred = gaussianBlur(img, w, h, blurSigma / 3);
  const src = Float32Array.from(blurred, (v) => v / 255);
  const normals = new Float32Array(w * h * 3);
  const scale = depth / 100;
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      if (alpha[i] === 0) {
        normals[i * 3 + 2] = 1;
        continue;
      }
      const at = (xx, yy) => src[clamp(yy, 0, h - 1) * w + clamp(xx, 0, w - 1)];
      const dx =
        x === 0
          ? -3 * at(x, y) + 4 * at(x + 1, y) - at(x + 2, y)
          : x === w - 1
            ? 3 * at(x, y) - 4 * at(x - 1, y) + at(x - 2, y)
            : -at(x - 1, y) + at(x + 1, y);
      const dy =
        y === 0
          ? -3 * at(x, y) + 4 * at(x, y + 1) - at(x, y + 2)
          : y === h - 1
            ? 3 * at(x, y) - 4 * at(x, y - 1) + at(x, y - 2)
            : -at(x, y - 1) + at(x, y + 1);
      normals[i * 3] = dx * scale;
      normals[i * 3 + 1] = -dy * scale;
      normals[i * 3 + 2] = 1;
    }
  return normals;
}

export function laigterNormalMap(source, opts = {}) {
  const { width: w, height: h, data } = source;
  const N = w * h;
  const normalDepth = opts.normalDepth ?? 250;
  const normalBlur = opts.normalBlur ?? 6;
  const biselDepth = opts.biselDepth ?? 100;
  const biselDistance = opts.biselDistance ?? 60;
  const biselBlur = opts.biselBlur ?? 10;
  const biselSoft = opts.biselSoft ?? true;

  // m_gray = input grayscale; alpha mask = alpha > 0.1
  const gray = new Float32Array(N);
  const mask = new Uint8Array(N);
  for (let i = 0; i < N; i++) {
    const o = i * 4;
    mask[i] = data[o + 3] / 255 > 0.1 ? 1 : 0;
    gray[i] = (0.2126 * data[o] + 0.7152 * data[o + 1] + 0.0722 * data[o + 2]);
  }

  // distance transform of the alpha channel, then scaled + clipped + soft curve
  const dist = euclideanDistance(mask, w, h);
  const shaped = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    let d = dist[i] * (255 / biselDistance);
    d = clamp(d, 0, 255);
    if (biselSoft) d = Math.sqrt(1 - (d / 255 - 1) ** 2) * 255;
    shaped[i] = d;
  }

  const emboss = calculateNormal(
    Float32Array.from(gray, (v) => v * 10),
    w, h, mask, normalDepth, normalBlur,
  );
  const distance = calculateNormal(shaped, w, h, mask, biselDepth * biselDistance, biselBlur);

  const out = new Uint8ClampedArray(N * 4);
  for (let i = 0; i < N; i++) {
    const o = i * 4;
    if (!mask[i]) {
      out[o] = 128;
      out[o + 1] = 128;
      out[o + 2] = 255;
      out[o + 3] = data[o + 3];
      continue;
    }
    const nr = emboss[i * 3] * 1.5 + distance[i * 3] * 1.5;
    const ng = emboss[i * 3 + 1] * 1.5 + distance[i * 3 + 1] * 1.5;
    const nb = emboss[i * 3 + 2] * 1.5 + distance[i * 3 + 2] * 1.5;
    const norm = Math.hypot(nr, ng, nb) || 1;
    out[o] = Math.round(255 * (nr / norm / 2 + 0.5));
    out[o + 1] = Math.round(255 * (ng / norm / 2 + 0.5));
    out[o + 2] = Math.round(255 * (nb / norm / 2 + 0.5));
    out[o + 3] = data[o + 3];
  }
  return { width: w, height: h, data: out };
}
