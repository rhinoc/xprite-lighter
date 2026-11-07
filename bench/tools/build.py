"""Build pixel-aligned geometry, shaded inputs and unseen-light GT from the bundled meshes."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
from lighting import RAW_LIGHTS,BANDS,EDGES,FLOOR,POWER,shade,encode_normal
from raster import load,render


def write(root):
    models=json.loads((root/'sources/models.json').read_text());cases=[]
    for md in models:
        scene=load(root/'models'/(md['id']+'.glb'))
        for view,(az,el) in md['views'].items():
            for n in (32,48,64,96):
                id=f"{md['id']}-{view}-{n}";dest=root/'cases'/id;gt=dest/'gt';gt.mkdir(parents=True,exist_ok=True)
                g=render(scene,size=n,az=az,el=el);base=g['albedo'];norm=g['normal'];fg=g['coverage']
                assert fg.any() and np.array_equal(fg,base[...,3]>0)
                assert np.allclose(np.linalg.norm(norm[fg],axis=-1),1.,atol=5e-6)
                assert np.array_equal(g['triangle_id']>=0,fg)
                Image.fromarray(base).save(gt/'albedo.png');Image.fromarray(encode_normal(norm,base[...,3])).save(gt/'normal.png')
                Image.fromarray(base[...,3]).save(gt/'mask.png')
                np.save(gt/'normal.npy',norm,allow_pickle=False)
                np.savez_compressed(gt/'geometry.npz',depth=g['depth'],triangle_id=g['triangle_id'],face_normal=g['face_normal'])
                (gt/'camera.json').write_text(json.dumps(g['camera'],indent=2)+'\n')
                Image.fromarray(shade(base,norm,'left','cel')).save(dest/'input.png')
                for style in ('cel','smooth'):
                    for light in ('right','top','bottom','front'):
                        Image.fromarray(shade(base,norm,light,style)).save(gt/f'{style}-{light}.png')
                cases.append(dict(id=id,model=md['id'],view=view,size=n,foreground=int(fg.sum())))
        print(md['id'],flush=True)
    (root/'manifest.json').write_text(json.dumps(dict(version='3.0-mesh-gt',cases=cases,lights=RAW_LIGHTS,normalize_light_vectors=True,
          ambient=FLOOR,power=POWER,cel_bands=BANDS.tolist(),cel_edges=EDGES.tolist(),normal_axes='camera-space x-right, y-up, z-toward-viewer'),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset',type=Path,default=Path('.'));write(p.parse_args().dataset)
