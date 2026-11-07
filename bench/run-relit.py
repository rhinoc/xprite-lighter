"""Re-render each case with predicted normals + already-lit input as albedo, then score."""
import argparse, json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).with_name("tools")))
import numpy as np
from PIL import Image
from lighting import decode_normal, shade
from score import image, score, TARGETS


def run(root: Path, out: Path):
    manifest = json.loads((root / "manifest.json").read_text())
    normals = out / "normals"
    for c in manifest["cases"]:
        cid = c["id"]
        n = decode_normal(image(normals / f"{cid}.png"))
        source = image(root / "cases" / cid / "input.png")
        dest = out / "relit" / cid
        dest.mkdir(parents=True, exist_ok=True)
        for light in TARGETS:
            Image.fromarray(shade(source, n, light, "cel")).save(dest / f"{light}.png")
    score(root, normals, out / "relit", out / "metrics")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", type=Path, default=Path(__file__).parent)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    run(a.dataset, a.out)
