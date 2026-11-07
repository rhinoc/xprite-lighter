# Bench

Scores `@xprite/lighter`'s normal-map generation and single-image relighting against
mesh-derived ground truth. Corpus: 64 cases — 8 CC0 KayKit models × 2 views × 4 sizes
(32/48/64/96 px). See `DATASET.zh.md` for the full data card.

## Run

```sh
pnpm run build
node bench/run.mjs                 # -> bench/run/{normals,run.json}
python3 bench/run-relit.py --out bench/run   # -> bench/run/{relit,metrics}
```

Requires Python + NumPy + Pillow for shading/scoring only; the candidate generator
runs in Node from `dist/`.

## Metrics

- `angle_mean_deg` / `angle_p95_deg` / `within_22_5_pct`: predicted vs GT shading
  normals, foreground only.
- `known_albedo_smooth_mae`: GT albedo + predicted normals through the benchmark's
  smooth shader — isolates normal quality.
- `relit_cel_mae`: end-to-end relight. The candidate sees only `input.png` (already
  left-lit, cel shaded); its predicted normals re-shade that same RGB under 4 new
  light directions, compared against `cel-{right,top,bottom,front}` targets.

`baseline/` holds the published reference numbers (Xprite commit `54d8133`,
Object preset). `checks/` has oracle (GT normals, ~0) and naive (all-front
normals / copy input) floors for the scoring pipeline itself.

| Method | angle_mean_deg | within_22_5_pct | known_albedo_smooth_mae | relit_cel_mae |
|---|---:|---:|---:|---:|
| @xprite/lighter object (this repo) | 40.47 | 18.56 | 18.22 | 29.81 |
| @xprite/lighter character | 42.71 | 14.48 | 19.37 | 29.93 |
| Naive front-facing normals | 45.99 | 10.14 | 20.94 | 29.87 |
| GT oracle | 0.00 | 100.00 | 0.00 | 0.00 |

## External reference

The original pack also cross-checked against
[DmytroKhitro/pixel-art-normal-maps](https://huggingface.co/datasets/DmytroKhitro/pixel-art-normal-maps)
(14,497 pairs): Xprite Object/Character 41.13°/40.77° vs author-reported
EDT Bevel 37.00° and U-Net 32.16° on the same 274 validation crops. Those targets
are stylized quantized normals, so scores aren't directly comparable to this
suite's unmodified mesh normals. No public learned model ships an easy
run-locally checkpoint; see DATASET.zh.md for provenance.
