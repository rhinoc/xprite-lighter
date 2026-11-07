        function applySurfaceHints(output, foreground, hints, kind, gain = 1) {
          if (!hints) return output;
          const N = foreground.length;
          if (kind === "mask") {
            const value = Math.round((255 * (hints.brightness ?? 100)) / 100);
            for (let p = 0; p < N; p++)
              if (foreground[p] && hints.light[p]) {
                const original =
                    0.2126 * output[p * 4] +
                    0.7152 * output[p * 4 + 1] +
                    0.0722 * output[p * 4 + 2],
                  v = hints.relativeBrightness
                    ? Math.round(
                        Math.max(0, Math.min(255, original + (255 * hints.brightness) / 100)),
                      )
                    : value;
                output[p * 4] = output[p * 4 + 1] = output[p * 4 + 2] = v;
              }
            return output;
          }
          for (const group of hints.groups) {
            if (!group.direction || group.direction === "none") continue;
            if (group.direction === "existing") {
              const delta = ((group.tilt - group.baseTilt) * Math.PI) / 180;
              for (let p = 0; p < N; p++)
                if (foreground[p] && hints.surfaces[p] === group.id) {
                  const v = [0, 1, 2].map((c) => (output[p * 4 + c] / 255) * 2 - 1),
                    len = Math.hypot(...v) || 1,
                    angle = Math.atan2(v[1], v[0]),
                    tilt = Math.max(
                      0,
                      Math.min(
                        Math.PI / 2,
                        Math.acos(Math.max(-1, Math.min(1, v[2] / len))) + delta,
                      ),
                    ),
                    normal = [
                      Math.cos(angle) * Math.sin(tilt),
                      Math.sin(angle) * Math.sin(tilt),
                      Math.cos(tilt),
                    ];
                  for (let c = 0; c < 3; c++)
                    output[p * 4 + c] = Math.round((normal[c] + 1) * 127.5);
                }
              continue;
            }
            const sum = [0, 0, 0];
            let count = 0;
            if (group.direction === "auto" || group.direction === "facet") {
              if (group.average) {
                const angle = Math.atan2(group.average[1], group.average[0]),
                  tilt = (group.tilt * Math.PI) / 180;
                sum[0] = Math.cos(angle) * Math.sin(tilt);
                sum[1] = Math.sin(angle) * Math.sin(tilt);
                sum[2] = Math.cos(tilt);
              } else
                for (let p = 0; p < N; p++)
                  if (foreground[p] && hints.surfaces[p] === group.id) {
                    for (let c = 0; c < 3; c++) sum[c] += (output[p * 4 + c] / 255) * 2 - 1;
                    count++;
                  }
            } else {
              const tilt = group.direction === "front" ? 0 : (group.tilt * Math.PI) / 180,
                s = Math.sin(tilt) * gain;
              const direction = group.direction,
                diagonal = direction.includes("-"),
                factor = diagonal ? Math.SQRT1_2 : 1;
              sum[0] =
                (direction.includes("left") ? -s : direction.includes("right") ? s : 0) * factor;
              sum[1] =
                (direction.includes("up") ? s : direction.includes("down") ? -s : 0) * factor;
              sum[2] = Math.cos(tilt);
            }
            const len = Math.hypot(...sum) || 1,
              rgb = sum.map((v) => Math.round((v / len + 1) * 127.5));
            for (let p = 0; p < N; p++)
              if (foreground[p] && hints.surfaces[p] === group.id)
                for (let c = 0; c < 3; c++) output[p * 4 + c] = rgb[c];
          }
          return output;
        }

        function generateTexture(albedo, options) {
          const w = albedo.w,
            h = albedo.h,
            N = w * h,
            a = albedo.data,
            fg = new Uint8Array(N),
            lum = new Float32Array(N),
            labels = new Int32Array(N);
          labels.fill(-1);
          const bg = options.bg,
            hide = options.hide;
          let lo = Infinity,
            hi = -Infinity;
          for (let i = 0; i < N; i++) {
            const k = i * 4;
            fg[i] =
              a[k + 3] > 0 && !(hide && a[k] === bg[0] && a[k + 1] === bg[1] && a[k + 2] === bg[2]);
            lum[i] = (0.2126 * a[k] + 0.7152 * a[k + 1] + 0.0722 * a[k + 2]) / 255;
            if (fg[i]) {
              lo = Math.min(lo, lum[i]);
              hi = Math.max(hi, lum[i]);
            }
          }
          const adjacent = (i) => {
            const x = i % w,
              y = (i / w) | 0,
              out = [];
            if (x) out.push(i - 1);
            if (x < w - 1) out.push(i + 1);
            if (y) out.push(i - w);
            if (y < h - 1) out.push(i + w);
            return out;
          };
          const queue = new Int32Array(N),
            clusters = [];
          for (let i = 0; i < N; i++)
            if (fg[i] && labels[i] < 0) {
              let head = 0,
                tail = 1;
              queue[0] = i;
              const id = clusters.length,
                pixels = [],
                k = i * 4;
              labels[i] = id;
              while (head < tail) {
                const p = queue[head++];
                pixels.push(p);
                for (const n of adjacent(p))
                  if (
                    fg[n] &&
                    labels[n] < 0 &&
                    a[n * 4] === a[k] &&
                    a[n * 4 + 1] === a[k + 1] &&
                    a[n * 4 + 2] === a[k + 2]
                  ) {
                    labels[n] = id;
                    queue[tail++] = n;
                  }
              }
              clusters.push({ pixels, value: lum[i] });
            }
          const distance = new Float32Array(N);
          distance.fill(N);
          let head = 0,
            tail = 0;
          for (let i = 0; i < N; i++)
            if (
              fg[i] &&
              (i % w === 0 ||
                i % w === w - 1 ||
                i < w ||
                i >= N - w ||
                adjacent(i).some((n) => !fg[n]))
            ) {
              distance[i] = 1;
              queue[tail++] = i;
            }
          while (head < tail) {
            const p = queue[head++];
            for (const n of adjacent(p))
              if (fg[n] && distance[n] > distance[p] + 1) {
                distance[n] = distance[p] + 1;
                queue[tail++] = n;
              }
          }
          const range = hi - lo,
            normalized = (i) => (range > 1e-5 ? (lum[i] - lo) / range : 0.75);
          const thin = new Uint8Array(N);
          if (options.merge) {
            for (const cluster of clusters) {
              if (cluster.value > lo + range * 0.24) continue;
              let interior = 0;
              for (const p of cluster.pixels)
                if (adjacent(p).length === 4 && adjacent(p).every((n) => labels[n] === labels[p]))
                  interior++;
              if (interior / cluster.pixels.length < 0.15)
                for (const p of cluster.pixels) thin[p] = 1;
            }
          }
          const output = new Uint8ClampedArray(N * 4);
          if (options.kind === "mask") {
            const strength = options.strength / 100,
              floor = options.floor / 255,
              cavity = options.cavity / 100;
            for (const cluster of clusters) {
              let value = cluster.value;
              const t = range > 1e-5 ? (value - lo) / range : 0.75;
              let receive = floor + (1 - floor) * Math.pow(t, 1.15);
              let surrounded = 0;
              if (cavity && t < 0.35) {
                for (const p of cluster.pixels) {
                  let higher = 0,
                    total = 0;
                  for (const n of adjacent(p))
                    if (fg[n] && labels[n] !== labels[p]) {
                      total++;
                      if (lum[n] > value + range * 0.15) higher++;
                    }
                  if (total && higher / total > 0.5) surrounded++;
                }
                receive *=
                  1 -
                  cavity * Math.min(1, surrounded / Math.max(1, Math.sqrt(cluster.pixels.length)));
              }
              receive = 1 - strength + strength * receive;
              const v = Math.round(255 * Math.max(0, Math.min(options.ceiling / 255, receive)));
              for (const p of cluster.pixels) {
                output[p * 4] = output[p * 4 + 1] = output[p * 4 + 2] = v;
                output[p * 4 + 3] = a[p * 4 + 3];
              }
            }
          } else {
            const preset = options.preset,
              scale = options.strength / 100;
            let field = new Float32Array(N);
            for (let i = 0; i < N; i++)
              if (fg[i]) {
                const convex =
                  Math.sqrt(Math.min(distance[i], preset === "character" ? 8 : 16)) *
                  (preset === "architecture" ? 0 : preset === "terrain" ? 0.12 : 0.65);
                field[i] =
                  convex +
                  normalized(i) *
                    (preset === "architecture"
                      ? 3.5
                      : preset === "terrain"
                        ? 4
                        : preset === "character"
                          ? 1.2
                          : 2.1);
              }
            for (
              let pass = 0;
              pass < (options.edgeWidth ?? (preset === "architecture" ? 1 : 3));
              pass++
            ) {
              const blurred = new Float32Array(N);
              for (let i = 0; i < N; i++)
                if (fg[i]) {
                  let sum = field[i] * 2,
                    count = 2;
                  for (const n of adjacent(i))
                    if (fg[n]) {
                      sum += field[n];
                      count++;
                    }
                  blurred[i] = sum / count;
                }
              field = blurred;
            }
            const dirs = new Float32Array(N * 3);
            const unit = (v) => {
              const len = Math.hypot(...v) || 1;
              return v.map((n) => n / len);
            };
            const normalGain = (options.normalStrength ?? 100) / 100;
            const quantize = (v) => {
              v = unit(v);
              const tilt = Math.hypot(v[0], v[1]);
              if (tilt < 0.12) return [0, 0, 1];
              const angle = (Math.round(Math.atan2(v[1], v[0]) / (Math.PI / 4)) * Math.PI) / 4;
              const elevation =
                preset === "architecture"
                  ? Math.min(0.9, 0.6 * scale)
                  : tilt < 0.3
                    ? 0.24
                    : tilt < 0.6
                      ? 0.48
                      : tilt < 0.85
                        ? 0.72
                        : 0.9;
              return [
                Math.cos(angle) * elevation,
                Math.sin(angle) * elevation,
                Math.sqrt(1 - elevation * elevation),
              ];
            };
            for (let i = 0; i < N; i++)
              if (fg[i]) {
                const x = i % w,
                  y = (i / w) | 0,
                  at = (n) => (n >= 0 && n < N && fg[n] ? field[n] : field[i]);
                const dx = (x < w - 1 ? at(i + 1) : field[i]) - (x ? at(i - 1) : field[i]),
                  dy = (y < h - 1 ? at(i + w) : field[i]) - (y ? at(i - w) : field[i]);
                const normal = unit([-dx * scale, dy * scale, 1]);
                dirs.set(normal, i * 3);
              }
            for (const cluster of clusters) {
              let sum = [0, 0, 0];
              for (const p of cluster.pixels) {
                if (preset === "architecture" && Math.hypot(dirs[p * 3], dirs[p * 3 + 1]) < 0.06)
                  continue;
                for (let c = 0; c < 3; c++) sum[c] += dirs[p * 3 + c];
              }
              if (sum[2] === 0) sum = [0, 0, 1];
              const average = unit(sum),
                groups = new Map();
              const split =
                options.facets > 0 &&
                cluster.pixels.length >= Math.round(180 - options.facets * 1.1);
              if (split) {
                for (const p of cluster.pixels) {
                  const dx = dirs[p * 3],
                    dy = dirs[p * 3 + 1],
                    tilt = Math.hypot(dx, dy);
                  const key = tilt > 0.35 ? Math.round(Math.atan2(dy, dx) / (Math.PI / 2)) : 9;
                  if (!groups.has(key)) groups.set(key, []);
                  groups.get(key).push(p);
                }
              }
              const supported = [...groups.values()].filter(
                (g) => g.length >= Math.max(16, cluster.pixels.length * 0.16),
              );
              let allow = false;
              if (supported.length >= 2) {
                const means = supported.map((g) => {
                  const s = [0, 0, 0];
                  for (const p of g) for (let c = 0; c < 3; c++) s[c] += dirs[p * 3 + c];
                  return unit(s);
                });
                for (let i = 0; i < means.length; i++)
                  for (let j = 0; j < i; j++)
                    if (
                      means[i].reduce((s, v, c) => s + v * means[j][c], 0) <
                      0.8 - options.facets * 0.001
                    )
                      allow = true;
              }
              const base = quantize(average);
              for (const p of cluster.pixels) dirs.set(base, p * 3);
              if (allow)
                for (const g of supported) {
                  const sum = [0, 0, 0];
                  for (const p of g) {
                    const x = p % w,
                      y = (p / w) | 0,
                      at = (n) => (n >= 0 && n < N && fg[n] ? field[n] : field[p]);
                    const dx = (x < w - 1 ? at(p + 1) : field[p]) - (x ? at(p - 1) : field[p]),
                      dy = (y < h - 1 ? at(p + w) : field[p]) - (y ? at(p - w) : field[p]);
                    const v = unit([-dx * scale, dy * scale, 1]);
                    for (let c = 0; c < 3; c++) sum[c] += v[c];
                  }
                  const v = quantize(sum);
                  for (const p of g) dirs.set(v, p * 3);
                }
            }
            if (options.merge) {
              const assigned = new Uint8Array(N);
              head = 0;
              tail = 0;
              for (let i = 0; i < N; i++)
                if (fg[i] && !thin[i]) {
                  assigned[i] = 1;
                  queue[tail++] = i;
                }
              while (head < tail) {
                const p = queue[head++];
                for (const n of adjacent(p))
                  if (fg[n] && !assigned[n]) {
                    assigned[n] = 1;
                    dirs.set(dirs.subarray(p * 3, p * 3 + 3), n * 3);
                    queue[tail++] = n;
                  }
              }
            }
            const seen = new Uint8Array(N);
            for (let i = 0; i < N; i++)
              if (fg[i] && !seen[i]) {
                const group = [];
                head = 0;
                tail = 1;
                queue[0] = i;
                seen[i] = 1;
                while (head < tail) {
                  const p = queue[head++];
                  group.push(p);
                  for (const n of adjacent(p))
                    if (
                      fg[n] &&
                      !seen[n] &&
                      Math.abs(dirs[n * 3] - dirs[i * 3]) < 0.001 &&
                      Math.abs(dirs[n * 3 + 1] - dirs[i * 3 + 1]) < 0.001
                    ) {
                      seen[n] = 1;
                      queue[tail++] = n;
                    }
                }
                if (group.length <= 2) {
                  const neighbors = group
                    .flatMap(adjacent)
                    .filter((n) => fg[n] && !group.includes(n));
                  if (neighbors.length) {
                    const n = neighbors[0];
                    for (const p of group) dirs.set(dirs.subarray(n * 3, n * 3 + 3), p * 3);
                  }
                }
              }
            for (let i = 0; i < N; i++) {
              const normal = fg[i]
                ? unit([dirs[i * 3] * normalGain, dirs[i * 3 + 1] * normalGain, dirs[i * 3 + 2]])
                : [0, 0, 1];
              for (let c = 0; c < 3; c++) output[i * 4 + c] = Math.round((normal[c] + 1) * 127.5);
              output[i * 4 + 3] = a[i * 4 + 3];
            }
          }
          for (let i = 0; i < N; i++) output[i * 4 + 3] = a[i * 4 + 3];
          applySurfaceHints(
            output,
            fg,
            options.hints,
            options.kind,
            (options.normalStrength ?? 100) / 100,
          );
          return { w, h, data: output };
        }


// Bench adapter: Pixel Art Lighter v3.5.24 defaults, no hints.
export function palNormalMap(source, preset = "object") {
  const { w, h, data } = { w: source.width, h: source.height, data: source.data };
  const out = generateTexture({ w, h, data }, {
    kind: "normal",
    preset,
    strength: 100,
    normalStrength: 100,
    edgeWidth: preset === "architecture" ? 1 : preset === "character" ? 2 : 3,
    facets: { architecture: 20, object: 35, terrain: 50, character: 15 }[preset] ?? 35,
    merge: true,
    hide: false,
    bg: [0, 0, 0],
    hints: null,
  });
  return { width: out.w, height: out.h, data: out.data };
}
