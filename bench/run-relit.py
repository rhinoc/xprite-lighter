"""Re-render each case with predicted normals + already-lit input as albedo, then score."""
import argparse, json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).with_name("tools")))
import numpy as np
from PIL import Image
from lighting import BANDS, EDGES, FLOOR, POWER, LIGHTS, decode_normal, linear_to_rgb, shade
from score import image, score, TARGETS


def shade_masked(rgba, normal, direction, mask):
    """Cel shade like lighting.shade but attenuate the diffuse term by the
    light-mask value (0..1), ambient passes through untouched."""
    x = rgba[..., :3].astype(float) / 255
    color = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    dot = np.clip(normal @ LIGHTS[direction], 0, 1)
    dot = BANDS[np.digitize(dot, EDGES)]
    atten = mask[..., 0].astype(float) / 255 if mask is not None else np.ones(normal.shape[:2])
    out = np.dstack(
        [linear_to_rgb(color * (FLOOR + POWER * dot[..., None] * atten[..., None])), rgba[..., 3]]
    )
    out[rgba[..., 3] == 0, :3] = 0
    return out


def run(root: Path, out: Path):
    manifest = json.loads((root / "manifest.json").read_text())
    normals = out / "normals"
    for c in manifest["cases"]:
        cid = c["id"]
        n = decode_normal(image(normals / f"{cid}.png"))
        source = image(root / "cases" / cid / "input.png")
        dest = out / "relit" / cid
        mask_path = out / "masks" / f"{cid}.png"
        mask = image(mask_path) if mask_path.exists() else None
        dest.mkdir(parents=True, exist_ok=True)
        for light in TARGETS:
            Image.fromarray(shade_masked(source, n, light, mask)).save(dest / f"{light}.png")
    score(root, normals, out / "relit", out / "metrics")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", type=Path, default=Path(__file__).parent)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    run(a.dataset, a.out)
