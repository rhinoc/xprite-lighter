// Port of SpriteLab's in-page normal-map generator (spritelab.dev/tools/normal-map-generator).
// Default slider values, OpenGL Y. Reference only — not our code.

function chamfer(seed, w, h) {
  const INF = 1e9;
  const d = new Float32Array(w * h);
  for (let p = 0; p < w * h; p++) d[p] = seed[p] ? 0 : INF;
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const p = y * w + x;
      let v = d[p];
      if (v === 0) continue;
      if (x > 0) v = Math.min(v, d[p - 1] + 3);
      if (y > 0) {
        v = Math.min(v, d[p - w] + 3);
        if (x > 0) v = Math.min(v, d[p - w - 1] + 4);
        if (x < w - 1) v = Math.min(v, d[p - w + 1] + 4);
      }
      d[p] = v;
    }
  for (let y = h - 1; y >= 0; y--)
    for (let x = w - 1; x >= 0; x--) {
      const p = y * w + x;
      let v = d[p];
      if (v === 0) continue;
      if (x < w - 1) v = Math.min(v, d[p + 1] + 3);
      if (y < h - 1) {
        v = Math.min(v, d[p + w] + 3);
        if (x < w - 1) v = Math.min(v, d[p + w + 1] + 4);
        if (x > 0) v = Math.min(v, d[p + w - 1] + 4);
      }
      d[p] = v;
    }
  for (let p = 0; p < w * h; p++) if (d[p] < INF) d[p] /= 3;
  return d;
}

function boxBlur(src, w, h) {
  const out = new Float32Array(w * h);
  for (let y = 0; y < h; y++) {
    const y0 = y > 0 ? y - 1 : 0;
    const y1 = y < h - 1 ? y + 1 : h - 1;
    for (let x = 0; x < w; x++) {
      const x0 = x > 0 ? x - 1 : 0;
      const x1 = x < w - 1 ? x + 1 : w - 1;
      out[y * w + x] =
        (src[y0 * w + x0] + src[y0 * w + x] + src[y0 * w + x1] +
          src[y * w + x0] + src[y * w + x] + src[y * w + x1] +
          src[y1 * w + x0] + src[y1 * w + x] + src[y1 * w + x1]) / 9;
    }
  }
  return out;
}

export function spriteLabNormalMap(source, opts = {}) {
  const { width: W, height: H, data: d } = source;
  const N = W * H;
  const radius = opts.radius ?? 4;
  const curve = opts.curve ?? 1.5;
  const shadeW = (opts.shade ?? 30) / 100;
  const detailW = (opts.detail ?? 40) / 100;
  const blurN = opts.blur ?? 1;
  const strength = opts.strength ?? 3;

  const mask = new Uint8Array(N);
  const bgSeed = new Uint8Array(N);
  const lum = new Float32Array(N);
  let nMask = 0;
  for (let p = 0; p < N; p++) {
    if (d[p * 4 + 3] < 128) {
      bgSeed[p] = 1;
      continue;
    }
    mask[p] = 1;
    nMask++;
    lum[p] = (0.299 * d[p * 4] + 0.587 * d[p * 4 + 1] + 0.114 * d[p * 4 + 2]) / 255;
  }
  const distBg = chamfer(bgSeed, W, H);

  const edgeSeed = new Uint8Array(N);
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      const p = y * W + x;
      if (!mask[p]) continue;
      const i = p * 4;
      if (x < W - 1 && mask[p + 1]) {
        const j = i + 4;
        if (d[i] !== d[j] || d[i + 1] !== d[j + 1] || d[i + 2] !== d[j + 2]) {
          edgeSeed[p] = 1;
          edgeSeed[p + 1] = 1;
        }
      }
      if (y < H - 1 && mask[p + W]) {
        const j = i + W * 4;
        if (d[i] !== d[j] || d[i + 1] !== d[j + 1] || d[i + 2] !== d[j + 2]) {
          edgeSeed[p] = 1;
          edgeSeed[p + W] = 1;
        }
      }
    }
  const distEdge = chamfer(edgeSeed, W, H);

  let hf = new Float32Array(N);
  for (let p = 0; p < N; p++) {
    if (!mask[p]) continue;
    const bevel = Math.pow(Math.min(1, distBg[p] / radius), curve);
    hf[p] = bevel + lum[p] * shadeW + detailW * Math.min(1, distEdge[p] / 2);
  }
  for (let b = 0; b < blurN; b++) hf = boxBlur(hf, W, H);

  const data = new Uint8ClampedArray(N * 4);
  for (let y = 0; y < H; y++) {
    const y0 = y > 0 ? y - 1 : 0;
    const y1 = y < H - 1 ? y + 1 : H - 1;
    for (let x = 0; x < W; x++) {
      const p = y * W + x;
      const o = p * 4;
      if (!mask[p]) {
        data[o] = 128;
        data[o + 1] = 128;
        data[o + 2] = 255;
        data[o + 3] = 0;
        continue;
      }
      const x0 = x > 0 ? x - 1 : 0;
      const x1 = x < W - 1 ? x + 1 : W - 1;
      const gx =
        (hf[y0 * W + x1] + 2 * hf[y * W + x1] + hf[y1 * W + x1] -
          hf[y0 * W + x0] - 2 * hf[y * W + x0] - hf[y1 * W + x0]) / 8;
      const gy =
        (hf[y1 * W + x0] + 2 * hf[y1 * W + x] + hf[y1 * W + x1] -
          hf[y0 * W + x0] - 2 * hf[y0 * W + x] - hf[y0 * W + x1]) / 8;
      const vx0 = -gx * strength;
      const vy0 = -gy * strength;
      const inv = 1 / Math.sqrt(vx0 * vx0 + vy0 * vy0 + 1);
      const vx = vx0 * inv;
      const vy = vy0 * inv;
      const vz = inv;
      data[o] = Math.round((vx * 0.5 + 0.5) * 255);
      data[o + 1] = Math.round((-vy * 0.5 + 0.5) * 255);
      data[o + 2] = Math.round((vz * 0.5 + 0.5) * 255);
      data[o + 3] = 255;
    }
  }
  return { width: W, height: H, data };
}
