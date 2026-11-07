"""Deterministic orthographic glTF 2 triangle rasterizer for synthetic sprite ground truth.

One center sample per native pixel. Input base colors are approximated as purely
diffuse Lambert colors; material normal maps, AO, specularity, emission,
cast shadows and metallic BRDFs are deliberately outside this benchmark.
See https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
"""
from dataclasses import dataclass
from pathlib import Path
import argparse
import base64
import io
import json
import struct
from urllib.parse import unquote, unquote_to_bytes
import numpy as np
from PIL import Image


def unit(x):
    return x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-15)


def srgb_decode(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def srgb_encode(c):
    c=np.clip(c,0.,1.)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1/2.4) - 0.055)


def transform(node):
    if 'matrix' in node:
        return np.array(node['matrix'],dtype=float).reshape(4,4).T
    x,y,z,w = node.get('rotation',(0.,0.,0.,1.))
    rot = np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                    [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                    [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
    out=np.eye(4)
    out[:3,:3]=rot * np.asarray(node.get('scale',(1.,1.,1.)))
    out[:3,3]=node.get('translation',(0.,0.,0.))
    return out


class GLTF:
    def __init__(self,path):
        self.path=Path(path)
        data=self.path.read_bytes()
        binchunk=None
        if data[:4]==b'glTF':
            _,ver,length=struct.unpack_from('<4sII',data)
            if ver!=2 or length!=len(data):raise ValueError('Invalid GLB header')
            at=12
            while at<length:
                size,kind=struct.unpack_from('<II',data,at)
                chunk=data[at+8:at+8+size]
                if kind==0x4e4f534a:self.doc=json.loads(chunk)
                if kind==0x004e4942:binchunk=chunk
                at+=8+size
        else:
            self.doc=json.loads(data)
        if self.doc['asset']['version']!='2.0':raise ValueError('glTF 2.0 required')
        self.buffers=[self.resource(b['uri']) if 'uri' in b else binchunk for b in self.doc.get('buffers',[])]
        self.accessors={}; self.images={}

    def resource(self,uri):
        if uri.startswith('data:'):
            mime,content=uri.split(',',1)
            return base64.b64decode(content) if ';base64' in mime else unquote_to_bytes(content)
        return (self.path.parent/unquote(uri)).read_bytes()

    def view(self,id):
        bv=self.doc['bufferViews'][id]
        at=bv.get('byteOffset',0)
        return memoryview(self.buffers[bv['buffer']])[at:at+bv['byteLength']]

    def accessor(self,id):
        if id in self.accessors:return self.accessors[id]
        a=self.doc['accessors'][id]
        dtype=np.dtype({5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'}[a['componentType']])
        width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
        count=a['count']
        if 'bufferView' in a:
            vi=a['bufferView'];bv=self.doc['bufferViews'][vi]
            val=np.ndarray((count,width),dtype,buffer=self.view(vi),offset=a.get('byteOffset',0),
                           strides=(bv.get('byteStride',dtype.itemsize*width),dtype.itemsize)).copy()
        else: val=np.zeros((count,width),dtype=dtype)
        if 'sparse' in a:
            s=a['sparse'];ind=s['indices'];vs=s['values']
            itype={5121:'u1',5123:'<u2',5125:'<u4'}[ind['componentType']]
            ii=np.frombuffer(self.view(ind['bufferView']),dtype=itype,count=s['count'],offset=ind.get('byteOffset',0))
            vv=np.frombuffer(self.view(vs['bufferView']),dtype=dtype,count=s['count']*width,offset=vs.get('byteOffset',0))
            val[ii]=vv.reshape(-1,width)
        if a.get('normalized'):
            val=val.astype(float)/np.iinfo(dtype).max
            if dtype.kind=='i':val=np.maximum(-1.,val)
        self.accessors[id]=val
        return val

    def texture(self,tex):
        ti=self.doc['textures'][tex['index']]
        if 'source' not in ti:raise ValueError('Unsupported compressed texture')
        ii=ti['source'];i=self.doc['images'][ii]
        if ii not in self.images:
            body=self.resource(i['uri']) if 'uri' in i else self.view(i['bufferView'])
            with Image.open(io.BytesIO(body)) as im:
                c=np.array(im.convert('RGBA'),dtype=float)/255.
            c[:,:,:3]=srgb_decode(c[:,:,:3])
            self.images[ii]=c
        sampler=self.doc.get('samplers',[])[ti['sampler']] if 'sampler' in ti else {}
        return self.images[ii],(sampler.get('wrapS',10497),sampler.get('wrapT',10497))


@dataclass
class Scene:
    positions: np.ndarray
    normals: np.ndarray
    uv: np.ndarray
    colors: np.ndarray
    material_ids: np.ndarray
    winding_sign: np.ndarray
    materials: list
    info: dict


def load(path):
    g=GLTF(path);d=g.doc
    mats=[]
    for m in d.get('materials',[])+[{}]:
        pbr=m.get('pbrMetallicRoughness',{})
        tex=pbr.get('baseColorTexture')
        mats.append(dict(name=m.get('name','default'),factor=np.array(pbr.get('baseColorFactor',[1.]*4)),
                         texture=g.texture(tex) if tex else None,tex_info=tex,alpha=m.get('alphaMode','OPAQUE'),
                         cutoff=m.get('alphaCutoff',.5),double=m.get('doubleSided',False)))
    nodes=d['nodes']
    roots=d['scenes'][d.get('scene',0)]['nodes']
    world={}
    def visit(i,parent):
        world[i]=parent@transform(nodes[i])
        for j in nodes[i].get('children',[]):visit(j,world[i])
    for i in roots:visit(i,np.eye(4))
    pos_all=[]; nor_all=[]; uv_all=[]; col_all=[]; mids=[]; parity=[]
    skinned=0; primitives=0
    for ni,mat in world.items():
        node=nodes[ni]
        if 'mesh' not in node: continue
        if 'EXT_mesh_gpu_instancing' in node.get('extensions',{}):raise ValueError('GPU instancing unsupported')
        mesh=d['meshes'][node['mesh']]
        skin_mats=None
        if 'skin' in node:
            skinned+=1; skin=d['skins'][node['skin']]; joints=skin['joints']
            binds=(g.accessor(skin['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1)
                   if 'inverseBindMatrices' in skin else np.tile(np.eye(4),(len(joints),1,1)))
            skin_mats=np.stack([world[j] for j in joints])@binds
        for p in mesh['primitives']:
            mode=p.get('mode',4)
            if mode not in (4,5,6):raise ValueError(f'Unsupported primitive mode {mode}')
            primitives+=1; att=p['attributes'];pos=g.accessor(att['POSITION']).astype(float)
            nor=g.accessor(att['NORMAL']).astype(float) if 'NORMAL' in att else None
            for target,weight in zip(p.get('targets',[]),node.get('weights',mesh.get('weights',[]))):
                if weight!=0 and 'POSITION' in target:pos+=weight*g.accessor(target['POSITION'])
                if weight!=0 and nor is not None and 'NORMAL' in target:nor+=weight*g.accessor(target['NORMAL'])
            if skin_mats is not None:
                if 'JOINTS_0' not in att:raise ValueError('Skinned primitive without joints')
                vm=np.zeros((len(pos),4,4)); total=np.zeros(len(pos))
                for joint_key in sorted(k for k in att if k.startswith('JOINTS_')):
                    suffix=joint_key.split('_')[-1]; jj=g.accessor(att[joint_key]);ww=g.accessor(att['WEIGHTS_'+suffix])
                    vm+=np.einsum('nv,nvij->nij',ww,skin_mats[jj]); total+=ww.sum(1)
                if np.any(total<=1e-9):raise ValueError('Unweighted vertex in skinned mesh')
                vm/=total[:,None,None]
                pos=np.einsum('nij,nj->ni',vm[:,:3,:3],pos)+vm[:,:3,3]
                if nor is not None:nor=unit(np.einsum('nji,nj->ni',np.linalg.inv(vm[:,:3,:3]),nor))
                # In a typical bind pose the joint products agree in determinant sign.
                dets=np.linalg.det(vm[:,:3,:3])
                if np.any(dets*np.sign(dets[0])<=0):raise ValueError('Mixed reflection signs in skinned default pose')
                sign=np.sign(dets[0])
            else:
                pos=pos@mat[:3,:3].T+mat[:3,3]
                if nor is not None:nor=unit(nor@np.linalg.inv(mat[:3,:3]))
                sign=np.sign(np.linalg.det(mat[:3,:3]))
            indices=g.accessor(p['indices']).reshape(-1).astype(np.int64) if 'indices' in p else np.arange(len(pos))
            if mode==4:ids=indices.reshape(-1,3)
            elif mode==5:
                ids=np.stack((indices[:-2],indices[1:-1],indices[2:]),axis=1)
                ids[1::2]=ids[1::2][:,[1,0,2]]
            else:ids=np.stack((np.full(len(indices)-2,indices[0]),indices[1:-1],indices[2:]),axis=1)
            corners=pos[ids]
            if nor is None:
                face=unit(np.cross(corners[:,1]-corners[:,0],corners[:,2]-corners[:,0]))*sign
                normals=np.repeat(face[:,None,:],3,axis=1)
            else:normals=nor[ids]
            mid=p.get('material',len(mats)-1);tex=mats[mid]['tex_info']
            uv=np.zeros((len(pos),2))
            if tex is not None:
                tr=tex.get('extensions',{}).get('KHR_texture_transform',{})
                uv=g.accessor(att['TEXCOORD_'+str(tr.get('texCoord',tex.get('texCoord',0)))]).astype(float)
                angle=tr.get('rotation',0);a,b=np.cos(angle),np.sin(angle)
                uv=(uv*tr.get('scale',[1.,1.]))@np.array([[a,b],[-b,a]])+tr.get('offset',[0.,0.])
            col=np.ones((len(pos),4))
            if 'COLOR_0' in att:
                c=g.accessor(att['COLOR_0']);col[:,:c.shape[1]]=c
            pos_all.append(corners);nor_all.append(normals);uv_all.append(uv[ids]);col_all.append(col[ids])
            mids.append(np.full(len(ids),mid,int));parity.append(np.full(len(ids),sign,float))
    if not pos_all:raise ValueError('No triangle meshes in default scene')
    return Scene(*(np.concatenate(v) for v in (pos_all,nor_all,uv_all,col_all,mids,parity)),mats,
                 dict(mesh_nodes=sum('mesh' in nodes[i] for i in world),skinned_nodes=skinned,
                      primitives=primitives,triangles=sum(len(a) for a in mids),materials=[m['name'] for m in mats]))


def wrap_uv(u,mode):
    if mode==10497:return np.mod(u,1)
    if mode==33071:return np.clip(u,0.,1.)
    if mode==33648:return 1.-np.abs(np.mod(u,2.)-1.)
    raise ValueError(f'Unknown wrap mode {mode}')


def render(scene,size=96,az=25.,el=12.,margin=.06):
    """Render default-pose world geometry; az/el in degrees, +Y world up, az zero facing +Z."""
    w,h=(int(size),int(size)) if np.isscalar(size) else map(int,size)
    azr,elr=np.deg2rad([az,el])
    front=np.array([np.sin(azr)*np.cos(elr),np.sin(elr),np.cos(azr)*np.cos(elr)])
    right=np.array([np.cos(azr),0.,-np.sin(azr)])
    up=np.cross(front,right)
    basis=np.stack((right,up,front))
    view=scene.positions@basis.T
    lo=view.min(axis=(0,1));hi=view.max(axis=(0,1));ctr=(lo+hi)*.5
    scale=min(w/max(1e-12,hi[0]-lo[0]),h/max(1e-12,hi[1]-lo[1]))*(1-2*margin)
    projected=view[...,:2].copy()
    projected[...,0]=(projected[...,0]-ctr[0])*scale+w*.5
    projected[...,1]=-(projected[...,1]-ctr[1])*scale+h*.5
    a,b,c=projected[:,0],projected[:,1],projected[:,2]
    ab=b-a;ac=c-a
    cross=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]
    front_facing=(-cross*scene.winding_sign)>0.
    double=np.array([m['double'] for m in scene.materials])[scene.material_ids]
    xy0=np.maximum(np.ceil(projected.min(1)-.5).astype(int),0)
    xy1=np.minimum(np.floor(projected.max(1)-.5).astype(int)+1,[w,h])
    lengths=np.maximum(xy1-xy0,0); area=lengths.prod(1)
    viable=(np.abs(cross)>1e-10)&(front_facing|double)
    area[~viable]=0
    # Expand candidate samples inside triangle bounding boxes; chunk by sample count.
    depth_buffer=np.full(w*h,-np.inf)
    hit=np.full(w*h,-1,np.int32); bary=np.zeros((w*h,3)); linear_rgb=np.zeros((w*h,3))
    cumulative=np.r_[0,np.cumsum(area)]; start=0
    while start<len(view):
        end=max(start+1,np.searchsorted(cumulative,cumulative[start]+250000,side='right')-1)
        end=min(end,len(view)); n=int(cumulative[end]-cumulative[start])
        if n==0:start=end;continue
        face_index=np.repeat(np.arange(start,end),area[start:end])
        offset=np.arange(n)-np.repeat(cumulative[start:end]-cumulative[start],area[start:end])
        xx=xy0[face_index,0]+offset%lengths[face_index,0]
        yy=xy0[face_index,1]+offset//lengths[face_index,0]
        dx=xx+.5-a[face_index,0];dy=yy+.5-a[face_index,1]
        u=(dx*ac[face_index,1]-dy*ac[face_index,0])/cross[face_index]
        v=(ab[face_index,0]*dy-ab[face_index,1]*dx)/cross[face_index]
        weights=np.column_stack((1-u-v,u,v))
        inside=np.all(weights>=-1e-10,axis=1)
        ti=face_index[inside]; weights=weights[inside]; pix=(yy*w+xx)[inside]
        z=np.einsum('ni,ni->n',view[ti,:,2],weights)
        vert_color=np.einsum('ni,nij->nj',weights,scene.colors[ti]); visible=np.ones(len(z),bool)
        for mi in np.unique(scene.material_ids[ti]):
            inds=np.flatnonzero(scene.material_ids[ti]==mi);m=scene.materials[mi]
            color=vert_color[inds]*m['factor']
            if m['texture'] is not None:
                texture,modes=m['texture'];th,tw=texture.shape[:2]
                uv=np.einsum('ni,nij->nj',weights[inds],scene.uv[ti[inds]])
                tu=np.minimum((wrap_uv(uv[:,0],modes[0])*tw).astype(int),tw-1)
                tv=np.minimum((wrap_uv(uv[:,1],modes[1])*th).astype(int),th-1)
                color*=texture[tv,tu]
            if m['alpha']=='MASK':visible[inds]=color[:,3]>=m['cutoff']
            elif m['alpha']=='BLEND':
                al=color[:,3]
                if np.any((al>1e-5)&(al<1.-1e-5)):raise ValueError('Fractional alpha BLEND requires multilayer ground truth')
                visible[inds]=al>.5
            vert_color[inds]=color
        keep=visible&(z>depth_buffer[pix])
        ti,weights,pix,z,color=ti[keep],weights[keep],pix[keep],z[keep],vert_color[keep,:3]
        if len(pix):
            order=np.lexsort((ti,-z,pix))
            sorted_pix=pix[order]
            winners=order[np.r_[True,sorted_pix[1:]!=sorted_pix[:-1]]]
            dest=pix[winners];hit[dest]=ti[winners];bary[dest]=weights[winners]
            depth_buffer[dest]=z[winners];linear_rgb[dest]=color[winners]
        start=end
    fg=hit>=0;tri=hit[fg]
    camera_n=np.zeros((h*w,3),np.float32);camera_n[:,2]=1.
    raw=np.einsum('ni,nij->nj',bary[fg],scene.normals[tri])@basis.T
    side=np.where(front_facing[tri],1.,-1.)[:,None]
    camera_n[fg]=unit(raw)*side
    face_n=np.zeros_like(camera_n);face_n[:,2]=1.
    face_n[fg]=unit(np.cross(view[tri,1]-view[tri,0],view[tri,2]-view[tri,0]))*scene.winding_sign[tri,None]*side
    eye_z=hi[2]+max(np.linalg.norm(hi-lo),1e-3)
    depth=np.zeros(w*h,np.float32);depth[fg]=eye_z-depth_buffer[fg]
    rgba=np.zeros((w*h,4),np.uint8)
    rgba[fg,:3]=np.rint(255*srgb_encode(linear_rgb[fg])).astype(np.uint8);rgba[fg,3]=255
    material=np.full(w*h,-1,np.int32);material[fg]=scene.material_ids[tri]
    return dict(albedo=rgba.reshape(h,w,4),normal=camera_n.reshape(h,w,3),face_normal=face_n.reshape(h,w,3),
                depth=depth.reshape(h,w),triangle_id=hit.reshape(h,w),material_id=material.reshape(h,w),coverage=fg.reshape(h,w),
                camera=dict(azimuth_deg=az,elevation_deg=el,world_to_camera_rotation_rows=basis.tolist(),
                            view_center_xy=ctr[:2].tolist(),camera_eye_z=eye_z,px_per_world_unit=scale,margin=margin,
                            resolution_wh=[w,h],projection='orthographic',sample='pixel centers',
                            depth='positive camera-axis distance, zero in background'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('model',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--size',type=int,default=96);p.add_argument('--az',type=float,default=25);p.add_argument('--el',type=float,default=12)
    args=p.parse_args(); scene=load(args.model); data=render(scene,args.size,args.az,args.el)
    args.out.mkdir(parents=True,exist_ok=True)
    Image.fromarray(data['albedo']).save(args.out/'albedo.png')
    normal_rgba=np.dstack((np.rint((np.clip(data['normal'],-1,1)+1)*127.5).astype(np.uint8),data['albedo'][...,3]))
    Image.fromarray(normal_rgba).save(args.out/'normal.png')
    np.savez_compressed(args.out/'geometry.npz',**{k:v for k,v in data.items() if isinstance(v,np.ndarray)})
    (args.out/'camera.json').write_text(json.dumps(data['camera'],indent=2))
    print(json.dumps(scene.info))
