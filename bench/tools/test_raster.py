"""Analytical tests independent of image comparisons with the benchmark lighting code."""
import base64
import json
import tempfile
from pathlib import Path

import numpy as np

from raster import Scene, load, render, srgb_decode, srgb_encode, unit


def scene(triangles, colors, mats, ids=None, normals=None):
    a=np.array(triangles,float);n=len(a)
    f=unit(np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]))
    v=np.repeat(f[:,None,:],3,axis=1) if normals is None else normals
    attrs=np.ones((n,3,4))
    for i,c in enumerate(colors):attrs[i,:,0:3]=c
    uv=np.tile(np.array([[[0.,0.],[1.,0.],[.5,1.]]]),(n,1,1))
    return Scene(a,v,uv,attrs,np.array(ids if ids is not None else [0]*n),np.ones(n),mats,{})


def mat():
    return dict(name='lambert',texture=None,factor=np.ones(4),alpha='OPAQUE',cutoff=.5,double=False)


def test_surfaces():
    base=np.array([[-1,-1,0],[1,-1,0],[0,1,0]],float)
    tilted=base.copy();tilted[:,2]=.5*tilted[:,0]
    result=render(scene([tilted],[[.5,.2,0.]],[mat()]),128,az=0,el=0)
    fg=result['coverage']
    expected=unit(np.array([-.5,0.,1.]))
    assert np.allclose(result['normal'][fg],expected)
    assert np.allclose(result['face_normal'][fg],expected)
    assert np.all(result['albedo'][fg,:3]==np.rint(255*srgb_encode(np.array([.5,.2,0.]))))
    y,x=80,64
    dz=result['depth'][y,x+4]-result['depth'][y,x]
    assert abs(dz+4*.5/result['camera']['px_per_world_unit'])<1e-6
    assert np.all(result['triangle_id'][~fg]==-1)
    assert np.all(result['depth'][~fg]==0.)
    reverse=base[[1,0,2]]
    assert not render(scene([reverse],[[1,1,1]],[mat()]),32,0,0)['coverage'].any()
    mx=mat();mx['double']=True
    back=render(scene([reverse],[[1,1,1]],[mx]),32,0,0)
    assert np.all(back['normal'][back['coverage']]==[0.,0.,1.])
    top=base.copy();top[:,2]+=.2
    texmat=mat();texmat['alpha']='MASK'
    texmat['texture']=(np.array([[[0.,0.,0.,0.],[0.,0.,1.,1.]]]),[33071]*2)
    lay=render(scene([top,base],[np.ones(3),[1,0,0]],[texmat,mat()],[0,1]),64,0,0)
    for x,ti,col in [(25,1,[255,0,0]),(39,0,[0,0,255])]:
        assert lay['triangle_id'][36,x]==ti and np.all(lay['albedo'][36,x,:3]==col)


def test_loader_and_skin():
    p=np.array([[-1,-1,0],[1,-1,1],[0,1,.5]],np.float32)
    n=unit(np.cross(p[1]-p[0],p[2]-p[0]))
    blobs=[p,np.tile(n,(3,1)).astype('<f4'),np.zeros((3,4),np.uint8),
           np.tile([1.,0.,0.,0.],(3,1)).astype('<f4'),np.eye(4).T.astype('<f4')]
    types=['VEC3','VEC3','VEC4','VEC4','MAT4'];counts=[3,3,3,3,1]
    offsets=np.r_[0,np.cumsum([v.nbytes for v in blobs])]
    buf=b''.join(v.tobytes() for v in blobs)
    scale=np.array([2,1,.5])
    doc={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(buf),'uri':'data:application/octet-stream;base64,'+base64.b64encode(buf).decode()}],
         'bufferViews':[{'buffer':0,'byteOffset':int(o),'byteLength':v.nbytes} for o,v in zip(offsets,blobs)],
         'accessors':[{'bufferView':i,'type':t,'count':ct,'componentType':5121 if i==2 else 5126} for i,(t,ct) in enumerate(zip(types,counts))],
         'meshes':[{'primitives':[{'attributes':{'POSITION':0,'NORMAL':1,'JOINTS_0':2,'WEIGHTS_0':3}}]}],
         'nodes':[{'mesh':0,'skin':0,'translation':[77,0,0]},{'scale':scale.tolist(),'translation':[1.,3.,-2.]}],
         'skins':[{'joints':[1],'inverseBindMatrices':4}], 'scenes':[{'nodes':[0,1]}],'scene':0}
    with tempfile.TemporaryDirectory() as d:
        f=Path(d)/'triangle.gltf';f.write_text(json.dumps(doc));sc=load(f)
        assert np.allclose(sc.positions[0],p*scale+[1,3,-2])
        assert np.allclose(sc.normals[0],unit(n/scale))
        del doc['nodes'][0]['skin']; doc['nodes'][0]['scale']=[-2,1,.5]
        f.write_text(json.dumps(doc));mir=load(f)
        assert mir.winding_sign[0]==-1
        sr=render(mir,64,0,0)
        assert sr['coverage'].any()
        assert np.allclose(sr['normal'][sr['coverage']],unit(n/[-2,1,.5]))
        assert np.allclose(sr['face_normal'][sr['coverage']],unit(n/[-2,1,.5]))
    assert np.allclose(srgb_encode(srgb_decode(np.arange(256)/255)),np.arange(256)/255)


if __name__=='__main__':
    test_surfaces();test_loader_and_skin()
    print('Pass: analytic tilted-plane normals and depth slope, linear albedo, culled backs, two-sided normal flip, nearest masked texture over opaque occludee, IDs, default-pose skin, mirrored instances, inverse transpose and 8-bit sRGB round trip.')
