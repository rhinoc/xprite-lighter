"""Score exact pixel-pair boundaries on the Xprite normal benchmark.

Usage: python score_detail.py --dataset path/to/bench --normals path/to/normals
Dependencies: NumPy and Pillow. See README.md for definitions and controls.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image


def image(path):
    with Image.open(path) as img:
        if img.mode != "RGBA":
            raise ValueError(f"{path}: expected an RGBA PNG")
        return np.array(img)


def unit_normal(normals, mask):
    normals = np.array(normals, dtype=np.float64)
    if normals.shape != (*mask.shape, 3):
        raise ValueError("Normal shape must be (height, width, 3)")
    length = np.linalg.norm(normals, axis=-1)
    if not np.all(np.isfinite(length[mask])) or np.any(length[mask] < 0.05):
        raise ValueError("Invalid foreground normal")
    result = np.zeros_like(normals)
    result[mask] = normals[mask] / length[mask, None]
    return result


def read_prediction(folder, case_id, alpha):
    raw = folder / (case_id + ".npy")
    if raw.exists():
        return unit_normal(np.load(raw, allow_pickle=False), alpha > 0)
    rgba = image(folder / (case_id + ".png"))
    if not np.array_equal(rgba[..., 3], alpha):
        raise ValueError(f"{case_id}: prediction alpha differs from the input")
    return unit_normal(rgba[..., :3] / 127.5 - 1.0, alpha > 0)


def angle(a, b):
    return np.degrees(np.arctan2(np.linalg.norm(np.cross(a, b), axis=-1),
                                 np.sum(a * b, axis=-1)))


def average_precision(positive, confidence):
    """Non-interpolated AP. A tied block enters the PR curve in one step."""
    order = np.argsort(-confidence, kind="stable")
    score, label = confidence[order], positive[order]
    ends = np.r_[np.flatnonzero(score[1:] != score[:-1]), len(score) - 1]
    tp = np.cumsum(label)[ends]
    if not tp[-1]:
        return None
    return float(np.sum(np.diff(np.r_[0, tp]) * tp / (ends + 1)) / tp[-1])


def observations(gt, pred, rgba, albedo):
    """Each horizontal/vertical foreground bond occurs once, with fixed order."""
    endpoints = [
        ((slice(None), slice(None, -1)), (slice(None), slice(1, None))),
        ((slice(None, -1), slice(None)), (slice(1, None), slice(None))),
    ]
    collected = []
    for first, second in endpoints:
        good = (rgba[first][..., 3] > 0) & (rgba[second][..., 3] > 0)
        ga, gb = gt[first][good], gt[second][good]
        pa, pb = pred[first][good], pred[second][good]
        color_delta = rgba[first][good, :3].astype(float) - rgba[second][good, :3]
        rgb_contrast = np.linalg.norm(color_delta, axis=-1)
        change_albedo = np.any(albedo[first][good, :3] != albedo[second][good, :3], axis=-1)
        aligned = np.sum((gb - ga) * (pb - pa), axis=-1) > 0
        collected.append((angle(ga, gb), angle(pa, pb), aligned, rgb_contrast, change_albedo))
    return tuple(np.concatenate(pair) for pair in zip(*collected))


def pct(count, total):
    return 100.0 * count / total if total else None


def measure(observed, threshold):
    gt_jump, pred_jump, aligned, rgb_contrast, change_albedo = observed
    real = gt_jump >= threshold
    detected = pred_jump >= threshold
    hits = real & detected
    tp, positives, predictions = map(int, (hits.sum(), real.sum(), detected.sum()))
    texture = (gt_jump < 5.0) & change_albedo
    return {
        "num_bonds": len(real), "gt_edges": positives, "pred_edges": predictions,
        "gt_prevalence_pct": pct(positives, len(real)),
        "precision_pct": pct(tp, predictions), "recall_pct": pct(tp, positives),
        "f1_pct": pct(2 * tp, positives + predictions),
        "aligned_recall_pct": pct(int((hits & aligned).sum()), positives),
        "ap": average_precision(real, pred_jump),
        "input_rgb_ap": average_precision(real, rgb_contrast),
        "same_input_rgb_among_gt_edges_pct": pct(int(((rgb_contrast == 0) & real).sum()), positives),
        "false_edge_on_flat_albedo_change_pct": pct(int((detected & texture).sum()), int(texture.sum())),
    }


def average_present(rows, key):
    values = [r[key] for r in rows if r[key] is not None]
    return float(np.mean(values)) if values else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--normals", type=Path, help="folder containing <case-id>.npy or .png")
    source.add_argument("--control", choices=["gt", "front", "turn180", "checker"])
    parser.add_argument("--thresholds", type=float, nargs="+", default=[20.0, 30.0, 45.0])
    parser.add_argument("--report", type=Path, default=Path("detail-report"))
    args = parser.parse_args()
    if any(not 0 < t < 180 for t in args.thresholds):
        parser.error("thresholds must lie strictly between 0 and 180 degrees")
    cases = json.loads((args.dataset / "manifest.json").read_text())["cases"]
    rows = []
    for case in cases:
        folder = args.dataset / "cases" / case["id"]
        rgba, albedo = image(folder / "input.png"), image(folder / "gt/albedo.png")
        if not np.array_equal(rgba[..., 3], albedo[..., 3]):
            raise ValueError(f"{case['id']}: different foreground in input and GT")
        mask = rgba[..., 3] > 0
        gt = unit_normal(np.load(folder / "gt/normal.npy", allow_pickle=False), mask)
        if args.normals is not None:
            pred = read_prediction(args.normals, case["id"], rgba[..., 3])
        elif args.control == "gt":
            pred = gt
        elif args.control == "turn180":
            pred = gt * [-1, -1, 1]
        elif args.control == "checker":
            sign = 2 * (np.indices(mask.shape).sum(axis=0) % 2) - 1
            pred = np.stack((0.8 * sign, np.zeros_like(sign), np.full(mask.shape, 0.6)), axis=-1)
        else:
            pred = np.zeros_like(gt)
            pred[..., 2] = 1.0
        observed = observations(gt, pred, rgba, albedo)
        global_angle = float(np.mean(angle(gt[mask], pred[mask])))
        for t in args.thresholds:
            rows.append({"case": case["id"], "model": case["model"], "size": case["size"],
                         "view": case["view"], "threshold_deg": t, "global_angle_deg": global_angle,
                         **measure(observed, t)})
    args.report.mkdir(parents=True, exist_ok=True)
    with (args.report / "per-case.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    metrics = [k for k in rows[0] if k.endswith(("_pct", "_deg")) and k != "threshold_deg"] + ["ap", "input_rgb_ap"]
    summary = {}
    for t in args.thresholds:
        selected = [r for r in rows if r["threshold_deg"] == t]
        by_model = {m: {k: average_present([r for r in selected if r["model"] == m], k)
                        for k in metrics} for m in sorted({r["model"] for r in selected})}
        macro = {k: average_present(by_model.values(), k) for k in metrics}
        summary[str(t)] = {"model_macro": macro, "by_model": by_model,
                           "defined_cases": {k: sum(r[k] is not None for r in selected) for k in metrics}}
        print(f"{t:g} degrees: {json.dumps(macro, allow_nan=False)}")
    (args.report / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
