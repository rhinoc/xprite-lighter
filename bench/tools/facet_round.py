"""Test direction changes with Xprite's final equal-normal regions held fixed.

Default inference reads the source alpha and Xprite Object's predicted RGBA
normal PNG. --oracle substitutes region-averaged GT directions as a diagnostic.
Outputs are float32 unit vectors in the benchmark's screen-space convention.
Requires numpy, Pillow and scipy.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def read_rgba(path):
    with Image.open(path) as im:
        if im.mode != 'RGBA':
            raise ValueError(f'{path}: expected RGBA image')
        return np.array(im)


def round_normals(alpha):
    mask = np.pad(alpha > 0.05 * 255, 2)
    components, _ = ndimage.label(mask)
    distance = np.maximum(0, ndimage.distance_transform_edt(mask) - 0.5)
    height = np.zeros(mask.shape)
    for label, area in enumerate(ndimage.find_objects(components), start=1):
        active = components[area] == label
        d = distance[area][active]
        height[area][active] = np.sqrt(np.maximum(0, d * (2 * d.max() - d)))
    dx = ndimage.sobel(height, axis=1) / 8
    dy = ndimage.sobel(height, axis=0) / 8
    n = unit(np.stack((-dx, dy, np.ones_like(dx)), axis=-1)[2:-2, 2:-2])
    # Match the existing contour estimator's intermediate 8-bit normal map.
    encoded = np.rint((n + 1) * 127.5)
    return unit(encoded / 127.5 - 1)


def normal_regions(rgb, foreground):
    """Four-connected regions of identical predicted normal-map RGB."""
    key = rgb.astype(np.int32) @ np.array([1, 256, 65536])
    labels = np.zeros(key.shape, dtype=np.int32)
    offset = 0
    for value in np.unique(key[foreground]):
        selected = foreground & (key == value)
        local, count = ndimage.label(selected)
        labels[selected] = local[selected] + offset
        offset += count
    return labels


def quantize_object(n):
    tilt = np.linalg.norm(n[:, :2], axis=1)
    xy = np.select([tilt < 0.12, tilt < 0.3, tilt < 0.6, tilt < 0.85],
                   [0, 0.24, 0.48, 0.72], default=0.9)
    step = np.pi / 4
    angle = np.floor(np.arctan2(n[:, 1], n[:, 0]) / step + 0.5) * step
    return np.stack((xy * np.cos(angle), xy * np.sin(angle), np.sqrt(1 - xy**2)), axis=-1)


def estimate(source, object_map, oracle=None):
    if source.shape != object_map.shape or not np.array_equal(source[..., 3], object_map[..., 3]):
        raise ValueError('Source and Object prediction must have matching dimensions and alpha')
    fg = source[..., 3] > 0
    labels = normal_regions(object_map[..., :3], fg)
    if oracle is None:
        original = unit(object_map[..., :3].astype(float) / 127.5 - 1)
        directions = unit(original + round_normals(source[..., 3]))
    else:
        directions = unit(oracle.astype(float))
    sums = np.stack([np.bincount(labels[fg], weights=directions[..., c][fg])
                     for c in range(3)], axis=-1)
    # Background label 0 has zero summed direction, mapped to (0, 0, 1).
    return quantize_object(unit(sums))[labels].astype(np.float32)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--normals', type=Path, required=True, help='Xprite Object RGBA PNG directory')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--oracle', '--oracle-directions', action='store_true',
                        help='Read gt/normal.npy for diagnosis only')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cases = json.loads((args.dataset / 'manifest.json').read_text())['cases']
    for case in cases:
        case_id = case['id']
        root = args.dataset / 'cases' / case_id
        source = read_rgba(root / 'input.png')
        object_map = read_rgba(args.normals / (case_id + '.png'))
        oracle = np.load(root / 'gt/normal.npy', allow_pickle=False) if args.oracle else None
        np.save(args.out / (case_id + '.npy'), estimate(source, object_map, oracle))


if __name__ == '__main__':
    main()
