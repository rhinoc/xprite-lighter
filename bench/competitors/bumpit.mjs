// Bump It / NormalSmith-style pipeline reimplemented from the documented engine
// (luminanceHeight -> chamfer distance -> smoothstep bevel -> masked box blur
// -> Sobel/8). The itch demo ships this as a single-file NS.* engine; constants
// follow the published description, not reverse-engineered byte-for-byte.

const C1 = 1;
const C2 = Math.SQRT2;

function chamferDistance(fg, w, h) {
  const INF = 64;
  const d = new Float32Array(w * h).fill(INF);
  for (let i = 0; i < w * h; i++) if (!fg[i]) d[i] = 0;
  const cost = (a, b) => (a === b ? 0 : a % w === b % w ? C1 : C2);
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const p = y * w + x;
      for (const q of [p - w - 1, p - w, p - w + 1, p - 1])
        if (q >= 0 && q < w * h && Math.abs((q % w) - x) <= 1)
          d[p] = Math.min(d[p], d[q] + cost(p, q));
    }
  for (let y = h - 1; y >= 0; y--)
    for (let x = w - 1; x >= 0; x--) {
      const p = y * w + x;
      for (const q of [p + w - 1, p + w, p + w + 1, p + 1])
        if (q >= 0 && q < w * h && Math.abs((q % w) - x) <= 1)
          d[p] = Math.min(d[p], d[q] + cost(p, q));
    }
  return d;
}

const smoothstep = (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t));

// Separable masked box blur: blur(H*mask)/blur(mask) so transparent pixels don't bleed.
function smoothMasked(hf, mask, w, h, radius) {
  const blur = (src, alongX) => {
    const out = new Float32Array(w * h);
    const limit = alongX ? w : h;
    const stride = alongX ? 1 : w;
    for (let line = 0; line < (alongX ? h : w); line++) {
      const base = alongX ? line * w : line;
      let sum = 0;
      const pre = new Float32Array(limit + 1);
      for (let i = 0; i < limit; i++) pre[i + 1] = pre[i] + src[base + i * stride];
      for (let i = 0; i < limit; i++) {
        const lo = Math.max(0, i - radius);
        const hi = Math.min(limit, i + radius + 1);
        out[base + i * stride] = (pre[hi] - pre[lo]) / (hi - lo);
      }
    }
    return out;
  };
  const masked = new Float32Array(w * h);
  for (let i = 0; i < w * h; i++) masked[i] = hf[i] * mask[i];
  const num = blur(blur(masked, true), false);
  const den = blur(blur(mask.slice ? Float32Array.from(mask) : mask, true), false);
  const out = new Float32Array(w * h);
  for (let i = 0; i < w * h; i++) out[i] = den[i] > 1e-6 ? num[i] / den[i] : hf[i];
  return out;
}

export function bumpItNormalMap(source, opts = {}) {
  const { width: w, height: h, data } = source;
  const N = w * h;
  const bevelWidth = opts.bevelWidth ?? 4;
  const bevelAmount = opts.bevelAmount ?? 0.85;
  const strength = opts.strength ?? 1.5;
  const blurRadius = opts.blurRadius ?? 1;

  const fg = new Uint8Array(N);
  const mask = new Float32Array(N);
  const lum = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    const o = i * 4;
    fg[i] = data[o + 3] >= 8 ? 1 : 0;
    mask[i] = fg[i] ? 1 : 0;
    lum[i] = (0.2126 * data[o] + 0.7152 * data[o + 1] + 0.0722 * data[o + 2]) / 255;
  }

  const dist = chamferDistance(fg, w, h);
  let hf = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    if (!fg[i]) continue;
    const t = smoothstep(Math.min(1, dist[i] / bevelWidth));
    hf[i] = lum[i] * (1 - bevelAmount) + t * bevelAmount;
  }
  hf = smoothMasked(hf, mask, w, h, blurRadius);

  const out = new Uint8ClampedArray(N * 4);
  for (let y = 0; y < h; y++) {
    const y0 = y > 0 ? y - 1 : 0;
    const y1 = y < h - 1 ? y + 1 : h - 1;
    for (let x = 0; x < w; x++) {
      const p = y * w + x;
      const o = p * 4;
      if (!fg[p]) {
        out[o] = 128;
        out[o + 1] = 128;
        out[o + 2] = 255;
        out[o + 3] = 0;
        continue;
      }
      const x0 = x > 0 ? x - 1 : 0;
      const x1 = x < w - 1 ? x + 1 : w - 1;
      const gx =
        (hf[y0 * w + x1] + 2 * hf[y * w + x1] + hf[y1 * w + x1] -
          hf[y0 * w + x0] - 2 * hf[y * w + x0] - hf[y1 * w + x0]) / 8;
      const gy =
        (hf[y1 * w + x0] + 2 * hf[y1 * w + x] + hf[y1 * w + x1] -
          hf[y0 * w + x0] - 2 * hf[y0 * w + x] - hf[y0 * w + x1]) / 8;
      const vx0 = -gx * strength;
      const vy0 = -gy * strength;
      const inv = 1 / Math.hypot(vx0, vy0, 1);
      out[o] = Math.round((vx0 * inv * 0.5 + 0.5) * 255);
      out[o + 1] = Math.round((-vy0 * inv * 0.5 + 0.5) * 255);
      out[o + 2] = Math.round((inv * 0.5 + 0.5) * 255);
      out[o + 3] = data[o + 3];
    }
  }
  return { width: w, height: h, data: out };
}
