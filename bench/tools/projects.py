"""Make one editable diagnostic project per model, two 64px views and named output layers."""
import argparse,json
from pathlib import Path
from PIL import Image
from ase import write_ase
from score import image
from lighting import decode_normal,shade

def projects(root):
    dest=root/'projects';dest.mkdir(exist_ok=True)
    rows=json.loads((root/'manifest.json').read_text())['cases']
    for model in sorted({r['model'] for r in rows}):
        frames=[]
        for c in [j for j in rows if j['model']==model and j['size']==64]:
            id=c['id'];case=root/'cases'/id;gt=case/'gt';pred=image(root/'baseline/normals'/(id+'.png'));base=image(gt/'albedo.png')
            imgs=[image(case/'input.png'),base,pred,image(gt/'normal.png'),shade(base,decode_normal(pred),'right'),image(gt/'cel-right.png'),image(root/'baseline/relit'/id/'right.png')]
            frames.append([Image.fromarray(a) for a in imgs])
        names=['01 Input - left light','02 GT base color','03 Xprite predicted normal','04 GT mesh shading normal','05 Right - Xprite normal with GT base','06 GT right light','07 Single-input benchmark baseline - right']
        write_ase(dest/(model+'-64.aseprite'),[(s,i==0) for i,s in enumerate(names)],frames,[450]*len(frames))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset',type=Path,default=Path('.'));projects(p.parse_args().dataset)
