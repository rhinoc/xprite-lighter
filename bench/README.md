# Bench

Scores `@xprite/lighter`'s normal-map generation and single-image relighting against
mesh-derived ground truth. Corpus: 64 cases — 8 CC0 KayKit models × 2 views × 4 sizes
(32/48/64/96 px). See `DATASET.zh.md` for the full data card.

## Run

```sh
pnpm run build
pnpm run bench                                # -> bench/run/{normals,relit,metrics}
node bench/run.mjs bench bench/run-X METHOD   # one method
python3 bench/run-relit.py --out bench/run-X  # score it
```

Methods: `object` (default), `character`, `terrain`, `architecture`,
`spritelab` (JS port of the spritelab.dev tool, defaults), `spritefusion`
(Sprite Fusion sprite-normals release CLI, default settings), `naive`
(all-front normals).

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

| Method | angle_mean_deg | angle_p95_deg | within_22_5_pct | known_albedo_smooth_mae | relit_cel_mae |
|---|---:|---:|---:|---:|---:|
| GT oracle | 0.00 | 0.00 | 100.00 | 0.00 | 0.00 |
| Sprite Fusion sprite-normals | 37.57 | 82.02 | 29.34 | 15.57 | 30.37 |
| SpriteLab (defaults) | 38.74 | 70.54 | 20.87 | 17.08 | 29.71 |
| @xprite/lighter object | 40.47 | 73.67 | 18.56 | 18.22 | **29.81** |
| @xprite/lighter character | 42.71 | 71.95 | 14.48 | 19.37 | 29.93 |
| @xprite/lighter terrain | 45.58 | 80.72 | 13.43 | 20.31 | 31.27 |
| @xprite/lighter architecture | 48.15 | 90.77 | 15.30 | 20.61 | 33.08 |
| Naive front-facing normals | 45.98 | 73.46 | 10.11 | 20.94 | 30.55 |

Takeaways on this corpus: the two continuous pipelines edge out our cluster-and-
quantify generator on raw angle accuracy (their unquantized normals track smooth
mesh normals better), while our Object preset is best-or-tied on the end-to-end
cel relight task — quantizing into facets costs angular precision but stays
closer to the 5-band shading style the suite uses for its targets. SpriteLab's
score benefits from its color-boundary groove; SpriteFusion's island-split +
EDT pipeline leads on angular error.

## External reference

The original pack also cross-checked against
[DmytroKhitro/pixel-art-normal-maps](https://huggingface.co/datasets/DmytroKhitro/pixel-art-normal-maps)
(14,497 pairs): Xprite Object/Character 41.13°/40.77° vs author-reported
EDT Bevel 37.00° and U-Net 32.16° on the same 274 validation crops. Those targets
are stylized quantized normals, so scores aren't directly comparable to this
suite's unmodified mesh normals. No public learned model ships an easy
run-locally checkpoint; see DATASET.zh.md for provenance.
