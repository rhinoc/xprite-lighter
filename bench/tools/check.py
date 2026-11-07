"""Check the oracle and naive baselines; verify PNG, float normals, geometry and target light pairing."""
import argparse,json,tempfile,shutil
from pathlib import Path
import numpy as np
from PIL import Image
from score import score,TARGETS,image
from lighting import encode_normal,shade
def check(root):
    cases=json.loads((root/'manifest.json').read_text())['cases']
    with tempfile.TemporaryDirectory() as tmp:
        w=Path(tmp)
        for name in ('oracle-normals','front-normals'):(w/name).mkdir()
        for case in cases:
            id=case['id'];d=root/'cases'/id;gt=d/'gt';a=image(gt/'albedo.png');g=np.load(gt/'normal.npy')
            fg=a[...,3]>0; depth=np.load(gt/'geometry.npz')
            assert np.array_equal(depth['triangle_id']>=0,fg) and np.all(depth['depth'][fg]>0)
            assert np.allclose(np.linalg.norm(g[fg],axis=1),1,atol=1e-6)
            assert np.array_equal(encode_normal(g,a[...,3]),image(gt/'normal.png'))
            assert np.array_equal(shade(a,g,'left'),image(d/'input.png'))
            for light in TARGETS:
                for mode in ('smooth','cel'):
                    assert np.array_equal(shade(a,g,light,mode),image(gt/(mode+'-'+light+'.png')))
            shutil.copyfile(gt/'normal.npy',w/'oracle-normals'/(id+'.npy'))
            n=np.zeros_like(g);n[...,2]=1;np.save(w/'front-normals'/(id+'.npy'),n)
            for key in ['oracle-relit','input-copy']:(w/key/id).mkdir(parents=True)
            for light in TARGETS:
                shutil.copyfile(gt/('cel-'+light+'.png'),w/'oracle-relit'/id/(light+'.png'))
                shutil.copyfile(d/'input.png',w/'input-copy'/id/(light+'.png'))
        oracle=score(root,w/'oracle-normals',w/'oracle-relit',root/'checks/oracle')
        assert oracle['model_macro']['angle_mean_deg']==0 and oracle['model_macro']['known_albedo_smooth_mae']<=.0001 and oracle['model_macro']['relit_cel_mae']==0
        score(root,w/'front-normals',w/'input-copy',root/'checks/naive')
    print(f'PASS: {len(cases)} cases, {len(cases)*len(TARGETS)*2} GT target images verified pixel for pixel.')


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset',type=Path,default=Path('.'));check(p.parse_args().dataset)
