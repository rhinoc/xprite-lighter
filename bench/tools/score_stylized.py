"""Score predictions against a *stylized* normal target: the mesh GT normal
quantized into the same facet space pixel-art normal tools actually output
(8 azimuth buckets x 4 tilt levels + front-facing). Pillow-shaped predictions
lose their advantage because the target is no longer a smooth field."""
import argparse, csv, json
from pathlib import Path
import numpy as np
from score import image, TARGETS, merge

AZ_STEP = np.pi / 4          # 8 directions
TILT_LEVELS = np.array([0.24, 0.48, 0.72, 0.9])   # same as PAL facet tilt
FRONT_LIMIT = 0.12


def stylize(normals):
    """Quantize continuous normals into facet directions, per-pixel."""
    n = normals / np.maximum(np.linalg.norm(normals, axis=-1, keepdims=True), 1e-12)
    az = np.arctan2(n[..., 1], n[..., 0])
    az_q = np.round(az / AZ_STEP) * AZ_STEP
    tilt = np.hypot(n[..., 0], n[..., 1])
    tilt_q = TILT_LEVELS[np.argmin(np.abs(tilt[..., None] - TILT_LEVELS), axis=-1)]
    front = tilt < FRONT_LIMIT
    tilt_q[front] = 0.0
    out = np.stack(
        [tilt_q * np.cos(az_q), tilt_q * np.sin(az_q), np.sqrt(np.maximum(1 - tilt_q**2, 0))],
        axis=-1,
    )
    out[front] = [0, 0, 1]
    return out / np.maximum(np.linalg.norm(out, axis=-1, keepdims=True), 1e-12)


def score(root, normals_dir, report):
    manifest = json.loads((root / "manifest.json").read_text())
    rows = []
    for c in manifest["cases"]:
        cid = c["id"]
        d = root / "cases" / cid
        base = image(d / "gt/albedo.png")
        fg = base[..., 3] > 0
        gt = np.load(d / "gt/normal.npy", allow_pickle=False).astype(float)
        gt /= np.maximum(np.linalg.norm(gt, axis=-1, keepdims=True), 1e-12)
        sgt = stylize(gt)

        p = normals_dir / (cid + ".png")
        n_img = image(p)
        if n_img.shape != base.shape:
            raise ValueError(f"{cid}: wrong dimensions")
        pn = n_img[..., :3].astype(float) / 127.5 - 1
        pn /= np.maximum(np.linalg.norm(pn, axis=-1, keepdims=True), 1e-12)

        row = {k: c[k] for k in ("model", "size", "view")}
        row["case"] = cid
        ang = np.degrees(
            np.arctan2(
                np.linalg.norm(np.cross(sgt[fg], pn[fg]), axis=-1),
                np.sum(sgt[fg] * pn[fg], axis=-1),
            )
        )
        row.update(
            s_angle_mean_deg=float(ang.mean()),
            s_angle_median_deg=float(np.median(ang)),
            s_within_22_5_pct=float((ang <= 22.5).mean() * 100),
            s_within_11_25_pct=float((ang <= 11.25).mean() * 100),
        )
        rows.append(row)

    report.mkdir(parents=True, exist_ok=True)
    with (report / "per-case.csv").open("w", newline="") as f:
        out = csv.DictWriter(f, fieldnames=list(rows[0]))
        out.writeheader()
        out.writerows(rows)
    summary = merge(rows)
    (report / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(summary["model_macro"])
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", type=Path, default=Path("."))
    p.add_argument("--normals", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    score(a.dataset, a.normals, a.report)
