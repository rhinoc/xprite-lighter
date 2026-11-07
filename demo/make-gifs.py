"""Assemble the relit PNG frames into looping GIFs next to them."""
from pathlib import Path
from PIL import Image

out = Path(__file__).parent / "out"
for kind in ("authored", "generated"):
    frames = [
        Image.open(p).convert("RGBA")
        for p in sorted(out.glob(f"relit-{kind}-*.png"))
    ]
    frames[0].save(
        out / f"relit-{kind}.gif",
        save_all=True,
        append_images=frames[1:],
        duration=80,
        loop=0,
        disposal=2,
    )
    print(kind, len(frames), "frames")
