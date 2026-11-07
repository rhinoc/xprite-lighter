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
(Sprite Fusion sprite-normals release CLI, default settings),
`pal-upstream` (verbatim `generateTexture` from Pixel Art Lighter v3.5.24,
MIT, extracted from the single-file HTML), `bumpit` (verbatim `NS.*` engine
from the Bump It / NormalSmith itch.io demo), `naive` (all-front normals).

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

| Method | acc@11.25° | median ° | edge mean ° | mean ° | p95 ° | within_22_5° | smooth MAE | relit MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GT oracle | 100.0 | 0.00 | 0.00 | 0.00 | 0.00 | 100.0 | 0.00 | 0.00 |
| Sprite Fusion sprite-normals | **8.90** | **33.03** | 47.40 | **37.57** | 82.02 | **29.34** | **15.57** | 30.37 |
| SpriteLab (defaults) | 6.14 | 36.91 | **46.19** | 38.74 | 70.54 | 20.87 | 17.08 | 29.71 |
| Pixel Art Lighter v3.5.24 (upstream) | 5.59 | 37.81 | 47.75 | 40.03 | 75.65 | 21.13 | 17.60 | 29.95 |
| @xprite/lighter object | 4.93 | 39.01 | 47.37 | 40.47 | 73.67 | 18.56 | 18.22 | 29.81 |
| Bump It / NormalSmith (verbatim NS engine) | 3.39 | 40.48 | 47.05 | 41.38 | 68.50 | 14.11 | 18.66 | **29.68** |
| Laigter (headless port, GUI defaults) | 4.70 | 43.02 | 53.99 | 47.10 | 93.41 | 17.22 | 20.57 | 33.24 |
| @xprite/lighter character | 4.10 | 41.36 | 49.13 | 42.71 | 71.95 | 14.48 | 19.37 | 29.93 |
| @xprite/lighter terrain | 3.62 | 44.24 | 51.10 | 45.58 | 80.72 | 13.43 | 20.31 | 31.27 |
| @xprite/lighter architecture | 3.60 | 45.57 | 53.10 | 48.15 | 90.77 | 15.30 | 20.61 | 33.08 |
| @xprite/lighter object + light mask | 4.93 | 39.01 | 47.37 | 40.47 | 73.67 | 18.56 | 18.22 | 38.01 |
| PAL upstream + light mask | 5.59 | 37.81 | 47.75 | 40.03 | 75.65 | 21.13 | 17.60 | 38.10 |
| Naive front-facing normals | 2.45 | 44.97 | 51.02 | 45.98 | 73.46 | 10.11 | 20.94 | 30.55 |

Columns, left to right in roughly decreasing signal-to-pixel-art-detail:
- `acc@11.25°`: % of foreground pixels whose normal lands within 11.25° of GT —
  the bucket that separates "kept the helmet ridge" from "one soft pillow".
- `angle_median_deg`: median angular error; resists the symmetric-errors-
  cancel-out that makes flat pillows look fine on the mean.
- `edge_angle_mean_deg`: mean error on the 20% of foreground pixels with the
  largest GT normal gradient (facet edges, occluding contours, facial detail).
- `angle_mean_deg` / `angle_p95_deg` / `within_22_5°`: the standard suite.
- `known_albedo_smooth_mae` / `relit_cel_mae`: downstream render error.

Takeaways on this corpus: the continuous pipelines (SpriteFusion's EDT + Oklab,
SpriteLab's chamfer + color-boundary groove) lead on raw normal accuracy.
Upstream PAL v3.5.24 edges our fork slightly — their exact-RGB clustering is
closer to the GT mesh normals than our Lab-perceptual grouping here. On the
end-to-end cel relight task every real method sits within ~0.7/255 of each
other, with Bump It narrowly ahead.

## Detail / boundary metrics (score_detail.py)

`tools/score_detail.py` scores internal fold edges as pixel-pair events rather
than per-pixel orientation: for every horizontal/vertical foreground bond it
measures the angle between the two endpoint normals, on both GT and prediction,
at thresholds 20/30/45°. It reports:

- `ap` — average precision of predicted bond strength ranking the GT-positive
  bonds (location-agnostic confidence quality)
- `recall_pct` — GT-positive bonds also predicted at the same position
- `aligned_recall_pct` — additionally requiring the predicted *direction* of
  the normal change (Δn) to agree with GT's
- `false_edge_on_flat_albedo_change_pct` — predicted edges where GT is flat but
  the albedo changes (texture/print mistaken for geometry)
- `input_rgb_ap` — same ranking using raw RGB delta as confidence (baseline)

Results at 30° (macro over 8 models):

| Method | mean angle ° | boundary AP | recall % | aligned recall % | false edge % |
|---|---:|---:|---:|---:|---:|
| SpriteLab | 38.74 | 0.290 | 0.06 | 0.05 | 0.04 |
| PAL upstream | 40.03 | 0.287 | 6.75 | 4.75 | 4.42 |
| @xprite/lighter object | 40.47 | **0.450** | 7.36 | 5.42 | 1.03 |
| object + per-pixel round blend | 35.13 | 0.430 | 3.00 | 2.51 | 0.56 |
| object regions re-oriented, re-quantized | 37.25 | 0.430 | **20.15** | **14.04** | 2.63 |
| same regions + GT mean direction (diagnostic oracle) | 26.58 | 0.537 | 44.00 | 40.82 | 3.74 |

Key insight from this diagnostic: our segmentation keeps real fold structure
(AP 0.45 beats SpriteLab's 0.29, recall 7.4% vs 0.06%) but our per-region
*direction* assignment is often wrong — freezing our own regions and just
re-orienting each toward its blended contour+prior normal doubles
aligned recall (5.4→14.0%). A GT-mean-direction oracle on the same regions
reaches 26.6°/44% recall, showing the headroom available before touching
segmentation.

Full per-case tables live in `bench/metrics-detail/<method>/`. The
`knight-normal-detail.png` figure shows the knight case: SpriteLab predicts
zero ≥30° internal bonds while our output keeps 14/17 hits.

## Light-mask rows

`object+mask` and `pal-mask` run the full pipeline: normals + a generated light
mask (occlusion-style receive map), relit with the mask attenuating the diffuse
term (`shade_masked` in `run-relit.py`). Their normal metrics equal the unmasked
rows; relit MAE rises to ~38 because the GT renders contain no self-shadowing —
on this clean-mesh corpus occlusion is pure additive noise. Mask earns its keep
on hand-painted inputs, which this GT set doesn't cover.

Only PAL upstream and @xprite/lighter generate light masks (SpriteLab, Bump It,
SpriteFusion, Laigter output normals only).

## External reference

The original pack also cross-checked against
[DmytroKhitro/pixel-art-normal-maps](https://huggingface.co/datasets/DmytroKhitro/pixel-art-normal-maps)
(14,497 pairs): Xprite Object/Character 41.13°/40.77° vs author-reported
EDT Bevel 37.00° and U-Net 32.16° on the same 274 validation crops. Those targets
are stylized quantized normals, so scores aren't directly comparable to this
suite's unmodified mesh normals. No public learned model ships an easy
run-locally checkpoint; see DATASET.zh.md for provenance.

## Licensing notes

`competitors/pal-upstream.mjs` is verbatim MIT code (notice in the file header).
`competitors/{spritelab,bumpit}.mjs` are verbatim engines from publicly served
pages with no declared license — kept for local benchmarking only, not shipped
to npm. Laigter was evaluated headlessly and scored 47.10° / relit 33.24, but
its GPL-3 license is incompatible with this package's MIT distribution, so the
port file `competitors/laigter.mjs` is gitignored rather than committed — it
still runs locally via `node bench/run.mjs bench bench/run-laigter laigter`.
