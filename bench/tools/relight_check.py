"""Compare input-as-albedo and source-light compensation in the v3 cel shader."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from score_detail import image, read_prediction


def linear_rgb(rgba):
    x = rgba[..., :3].astype(float) / 255
    return np.where(x <= .04045, x / 12.92, ((x + .055) / 1.055) ** 2.4)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', type=Path, required=True, help='directory with lighting.py')
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--normals', type=Path)
    group.add_argument('--gt', action='store_true', help='oracle using the exact float GT')
    args = p.parse_args()
    sys.path.insert(0, str(args.dataset.resolve()))
    from lighting import LIGHTS, BANDS, EDGES, FLOOR, POWER, linear_to_rgb, shade

    def coefficient(n, target):
        dot = np.clip(n @ LIGHTS[target], 0, 1)
        return (FLOOR + POWER * BANDS[np.digitize(dot, EDGES)])[..., None]

    by_model = {}
    for c in json.loads((args.dataset / 'manifest.json').read_text())['cases']:
        d = args.dataset / 'cases' / c['id']
        source, base = image(d / 'input.png'), image(d / 'gt/albedo.png')
        fg = source[..., 3] > 0
        n = (np.load(d / 'gt/normal.npy').astype(float) if args.gt else
             read_prediction(args.normals, c['id'], source[..., 3]))
        old = coefficient(n, 'left')
        errors = []
        for target in ('right', 'top', 'bottom', 'front'):
            truth = image(d / 'gt' / f'cel-{target}.png')[..., :3].astype(float)
            direct = shade(source, n, target, 'cel')[..., :3]
            ratio = linear_to_rgb(linear_rgb(source) * coefficient(n, target) / old)
            known = shade(base, n, target, 'cel')[..., :3]
            estimates = (source[..., :3], direct, ratio, known)
            errors.append([float(np.abs(value - truth)[fg].mean()) for value in estimates])
        by_model.setdefault(c['model'], []).append(np.mean(errors, axis=0))
    macro = np.mean([np.mean(rows, axis=0) for rows in by_model.values()], axis=0)
    names = ('copy_input', 'direct', 'ratio_known_old_light', 'known_albedo_diagnostic')
    print(json.dumps(dict(zip(names, macro)), indent=2))


if __name__ == '__main__':
    main()
