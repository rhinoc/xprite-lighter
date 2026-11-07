"""Freeze KayKit GLB animations and selected equipment into static, self-contained glTF 2 GLBs.
Requires numpy and scipy. Usage: python bake_kaykit_pose.py <original-chars-dir> <output-dir>
Uses world-space joints multiplied by official inverse bind matrices and normal inverse transpose.
"""
import sys,json,struct,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
CONFIG={
 'Knight':('Adventures','1H_Melee_Attack_Slice_Diagonal',.38,{'1H_Sword','Badge_Shield','Knight_Helmet','Knight_Cape'}),
 'Mage':('Adventures','2H_Melee_Idle',.23,{'2H_Staff','Mage_Hat','Mage_Cape'}),
 'Skeleton_Warrior':('Skeletons','Idle',.27,{'Skeleton_Warrior_Helmet'}),
 'Rogue_Hooded':('Adventures','Idle',.30,{'Knife','Knife_Offhand','Rogue_Cape'}),
 'Barbarian':('Adventures','Idle',.28,{'1H_Axe','Barbarian_Round_Shield','Barbarian_Hat','Barbarian_Cape'}),
 'Skeleton_Mage':('Skeletons','Idle',.42,{'Skeleton_Mage_Hat'}),
}
def bake(path,dst,action,time,keep):
 raw=path.read_bytes();js_size=struct.unpack_from('<I',raw,12)[0];g=json.loads(raw[20:20+js_size]);binraw=raw[28+js_size:]
 dtype={5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'}
 width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
 def acc(i):
  a=g['accessors'][i];v=g['bufferViews'][a['bufferView']];typ=np.dtype(dtype[a['componentType']]);n=width[a['type']]
  x=np.ndarray((a['count'],n),typ,buffer=binraw,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',typ.itemsize*n),typ.itemsize)).copy()
  return x / np.iinfo(typ).max if a.get('normalized') else x
 nodes=g['nodes']; trs=[dict(translation=np.array(n.get('translation',[0.,0,0])),rotation=np.array(n.get('rotation',[0.,0,0,1])),scale=np.array(n.get('scale',[1.,1,1]))) for n in nodes]
 clip=next(a for a in g['animations'] if a['name']==action)
 for ch in clip['channels']:
  s=clip['samplers'][ch['sampler']];target=ch['target'];prop=target['path'];times=acc(s['input']).reshape(-1);vec=acc(s['output']).astype(float)
  assert s.get('interpolation','LINEAR') in ('LINEAR','STEP')
  i=max(0,min(np.searchsorted(times,time,side='right')-1,len(times)-1));j=min(i+1,len(times)-1)
  f=0 if i==j or s.get('interpolation')=='STEP' else np.clip((time-times[i])/(times[j]-times[i]),0,1)
  a,b=vec[i],vec[j]
  if prop=='rotation':
   dot=np.dot(a,b)
   if dot<0:b=-b;dot=-dot
   if dot<.9995:
    theta=np.arccos(np.clip(dot,-1,1));v=(np.sin((1-f)*theta)*a+np.sin(f*theta)*b)/np.sin(theta)
   else:v=(1-f)*a+f*b
   v=v/np.linalg.norm(v)
  else:v=(1-f)*a+f*b
  trs[target['node']][prop]=v
 world={}
 def visit(i,parent):
  n=nodes[i];x=trs[i];m=np.eye(4)
  if 'matrix'in n:m=np.array(n['matrix']).reshape(4,4).T
  else:m[:3,:3]=Rotation.from_quat(x['rotation']).as_matrix()@np.diag(x['scale']);m[:3,3]=x['translation']
  world[i]=parent@m
  for child in n.get('children',[]):visit(child,world[i])
 for root in g['scenes'][g.get('scene',0)]['nodes']:visit(root,np.eye(4))
 data=bytearray();views=[];access=[];meshes=[];outnodes=[]
 def append(rawdata):
  while len(data)%4:data.append(0)
  start=len(data);data.extend(rawdata);views.append({'buffer':0,'byteOffset':start,'byteLength':len(rawdata)});return len(views)-1
 def outacc(arr,kind,ctype='f4',pos=False):
  a=np.asarray(arr,dtype=ctype);v=append(a.tobytes());o=dict(bufferView=v,componentType={'f4':5126,'u4':5125}[ctype],count=len(a),type=kind)
  if pos:o.update(min=a.min(axis=0).tolist(),max=a.max(axis=0).tolist())
  access.append(o);return len(access)-1
 images=[]
 for x in g['images']:
  v=g['bufferViews'][x['bufferView']];start=v.get('byteOffset',0);images.append(dict(x,bufferView=append(binraw[start:start+v['byteLength']])))
 bounds=[];selected=[]
 for i,n in enumerate(nodes):
  if i not in world or 'mesh' not in n or ('skin' not in n and n['name'] not in keep):continue
  selected.append(n['name']);pout=[]
  for p in g['meshes'][n['mesh']]['primitives']:
   attr=p['attributes'];xyz=acc(attr['POSITION']);norm=acc(attr['NORMAL']);uv=acc(attr['TEXCOORD_0'])
   if 'skin'in n:
    skin=g['skins'][n['skin']];bind=acc(skin['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1);joint=np.stack([world[j] for j in skin['joints']])@bind
    ix=acc(attr['JOINTS_0']).astype(int);weights=acc(attr['WEIGHTS_0']).astype(float);weights/=weights.sum(axis=1,keepdims=True);blend=np.einsum('vi,vijk->vjk',weights,joint[ix])
   else:blend=np.broadcast_to(world[i],(len(xyz),4,4))
   xyz=np.einsum('vij,vj->vi',blend[:,:3,:3],xyz)+blend[:,:3,3]
   norm=np.einsum('vij,vj->vi',np.linalg.inv(blend[:,:3,:3]).transpose(0,2,1),norm);norm/=np.linalg.norm(norm,axis=1,keepdims=True)
   assert np.isfinite(xyz).all() and np.isfinite(norm).all()
   bounds.append(xyz)
   pout.append({'attributes':{'POSITION':outacc(xyz,'VEC3',pos=True),'NORMAL':outacc(norm,'VEC3'),'TEXCOORD_0':outacc(uv,'VEC2')},'indices':outacc(acc(p['indices']).reshape(-1),'SCALAR','u4'),'material':p['material']})
  outnodes.append(dict(name=n['name'],mesh=len(meshes)));meshes.append(dict(name=n['name'],primitives=pout))
 meta=dict(source=path.name,source_sha256=hashlib.sha256(raw).hexdigest(),animation=action,seconds=time,retained_nodes=selected,rigid_options_included=sorted(keep),geometry_space='glTF world coordinates, right handed, +Y up',author='Kay Lousberg',license='CC0-1.0',processing='Freeze animated node transforms and skinned geometry, select rigid equipment; preserve source normals, triangle topology, author palette texture, UVs and material.')
 out=dict(asset=dict(version='2.0',generator='xprite benchmark static pose baker'),scene=0,scenes=[dict(nodes=list(range(len(outnodes))))],nodes=outnodes,meshes=meshes,buffers=[dict(byteLength=len(data))],bufferViews=views,accessors=access,materials=g['materials'],textures=g['textures'],images=images,samplers=g.get('samplers',[]),extras=meta)
 chunk=json.dumps(out,separators=(',',':')).encode('utf8');chunk+=b' '*((-len(chunk))%4);data+=bytes((-len(data))%4)
 output=b'glTF'+struct.pack('<II',2,28+len(chunk)+len(data))+struct.pack('<I4s',len(chunk),b'JSON')+chunk+struct.pack('<I4s',len(data),b'BIN\x00')+data
 dst.write_bytes(output);xyz=np.concatenate(bounds);meta.update(bbox_world=[xyz.min(0).tolist(),xyz.max(0).tolist()],sha256=hashlib.sha256(output).hexdigest());dst.with_suffix('.json').write_text(json.dumps(meta,indent=2));print(dst.stem, xyz.min(0).round(3), xyz.max(0).round(3), flush=True)
if __name__=='__main__':
 origin=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
 for name,(folder,action,time,keep) in CONFIG.items():bake(origin/folder/(name+'.glb'),out/(name+'.glb'),action,time,keep)
