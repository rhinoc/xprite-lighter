"""Re-render the bench inputs under lights and shading styles the defaults were not tuned on.

Usage: python bench/tools/holdout.py OUT_ROOT
Writes OUT_ROOT/<set>/{manifest.json,cases/<id>/input.png}; each case's gt/ is a symlink to
the original. Score with `node bench/run.mjs OUT_ROOT/<set> OUT METHOD` and
`python bench/run-relit.py --dataset OUT_ROOT/<set> --out OUT`.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from lighting import linear_to_rgb  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def direction(azimuth, elevation):
    a, e = np.radians(azimuth), np.radians(elevation)
    return np.array([np.cos(a) * np.cos(e), np.sin(a) * np.cos(e), np.sin(e)])


# name: (light, ambient floor, diffuse power, (band levels, band edges) or None for smooth)
SETS = {
    "tr_cel5": (direction(40, 35), 0.26, 0.83, ([0, 0.24, 0.49, 0.74, 1], [0.12, 0.37, 0.62, 0.87])),
    "top_cel3": (direction(100, 50), 0.30, 0.80, ([0, 0.5, 1], [0.3, 0.7])),
    "right_smooth": (direction(15, 30), 0.35, 0.70, None),
}


def main(out_root):
    manifest = json.loads((ROOT / "manifest.json").read_text())
    for name, (light, floor, power, bands) in SETS.items():
        out = Path(out_root) / name
        (out / "cases").mkdir(parents=True, exist_ok=True)
        (out / "manifest.json").write_text(json.dumps(manifest))
        for case in manifest["cases"]:
            src = ROOT / "cases" / case["id"]
            dst = out / "cases" / case["id"]
            dst.mkdir(exist_ok=True)
            if not (dst / "gt").exists():
                os.symlink(src / "gt", dst / "gt")
            albedo = np.asarray(Image.open(src / "gt/albedo.png").convert("RGBA"))
            normal = np.load(src / "gt/normal.npy").astype(float)
            normal /= np.maximum(np.linalg.norm(normal, axis=-1, keepdims=True), 1e-12)
            x = albedo[..., :3] / 255
            color = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
            dot = np.clip(normal @ light, 0, 1)
            if bands:
                dot = np.asarray(bands[0])[np.digitize(dot, bands[1])]
            rgb = linear_to_rgb(color * (floor + power * dot[..., None]))
            image = np.dstack([rgb, albedo[..., 3]])
            image[albedo[..., 3] == 0, :3] = 0
            Image.fromarray(image.astype(np.uint8)).save(dst / "input.png")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "bench/holdout")
