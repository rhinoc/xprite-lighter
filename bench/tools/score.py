"""Score predictions against mesh-derived GT. Supply screen-space normals and/or end-to-end relit RGBA."""
import argparse,csv,json
from pathlib import Path
import numpy as np
from PIL import Image
from lighting import decode_normal,shade

TARGETS=['right','top','bottom','front']


def image(p):
    with Image.open(p) as im:
        if im.mode!='RGBA':raise ValueError(f'{p}: expected RGBA PNG with an explicit alpha channel')
        return np.asarray(im).copy()


def check(a,b,case):
    if a.shape!=b.shape:raise ValueError(f'{case}: wrong dimensions')
    if not np.array_equal(a[...,3],b[...,3]):raise ValueError(f'{case}: source alpha must be preserved')


def render_error(img,truth,m):
    return float(np.abs(img[...,:3].astype(float)-truth[...,:3].astype(float))[m].mean())


def gt_edge_mask(gt,fg,frac=.2):
    """Top-frac foreground pixels by GT normal gradient magnitude."""
    g=np.zeros(gt.shape[:2])
    for c in range(3):
        dy,dx=np.gradient(gt[...,c])
        g+=dx*dx+dy*dy
    g=np.sqrt(g)
    vals=np.sort(g[fg])
    thresh=vals[max(0,int(len(vals)*(1-frac))-1)]
    return fg & (g>=thresh)


def merge(rows):
    keys=[k for k in rows[0] if k not in ['case','model','size','view']]
    by_model={}
    for model in sorted({r['model'] for r in rows}):
        selected=[r for r in rows if r['model']==model]
        by_model[model]={k:round(float(np.mean([r[k] for r in selected])),4) for k in keys}
    return {'by_model':by_model,'model_macro':{k:round(float(np.mean([v[k] for v in by_model.values()])),4) for k in keys}}


def score(root,normals,relit,report):
    manifest=json.loads((root/'manifest.json').read_text())
    rows=[]
    for c in manifest['cases']:
        id=c['id'];d=root/'cases'/id
        base=image(d/'gt/albedo.png');fg=base[...,3]>0
        gt=np.load(d/'gt/normal.npy',allow_pickle=False).astype(float)
        gt/=np.maximum(np.linalg.norm(gt,axis=-1,keepdims=True),1e-12)
        row={k:c[k] for k in ('model','size','view')};row['case']=id
        if normals:
            p=normals/(id+'.png')
            raw=normals/(id+'.npy')
            if raw.exists():
                pn=np.load(raw,allow_pickle=False).astype(float)
                if pn.shape!=gt.shape or not np.all(np.isfinite(pn[fg])):raise ValueError(f'{id}: invalid npy normal')
                length=np.linalg.norm(pn,axis=-1,keepdims=True)
                if np.any(length[...,0][fg]<.05):raise ValueError(f'{id}: invalid foreground normals')
                pn/=np.maximum(length,1e-12)
            else:
                n=image(p);check(n,base,id);pn=decode_normal(n)
            a,b=gt[fg],pn[fg]
            ang=np.degrees(np.arctan2(np.linalg.norm(np.cross(a,b),axis=-1),np.sum(a*b,axis=-1)))
            edge=gt_edge_mask(gt,fg)
            eang=np.degrees(np.arctan2(np.linalg.norm(np.cross(gt[edge],pn[edge]),axis=-1),np.sum(gt[edge]*pn[edge],axis=-1))) if edge.any() else np.array([0.])
            row.update(
                edge_angle_mean_deg=float(eang.mean()),
                angle_median_deg=float(np.median(ang)),
                within_11_25_pct=float((ang<=11.25).mean()*100),
                angle_mean_deg=float(ang.mean()),
                angle_p95_deg=float(np.percentile(ang,95)),
                within_22_5_pct=float((ang<=22.5).mean()*100),
            )
            row['known_albedo_smooth_mae']=float(np.mean([render_error(shade(base,pn,k,'smooth'),image(d/'gt'/('smooth-'+k+'.png')),fg) for k in TARGETS]))
        if relit:
            errs=[]
            for k in TARGETS:
                target=image(d/'gt'/('cel-'+k+'.png'));pred=image(relit/id/(k+'.png'));check(pred,base,id)
                errs.append(render_error(pred,target,fg))
            row['relit_cel_mae']=float(np.mean(errs))
        rows.append(row)
    report.mkdir(parents=True,exist_ok=True)
    with (report/'per-case.csv').open('w',newline='') as f:
        out=csv.DictWriter(f,fieldnames=list(rows[0]));out.writeheader();out.writerows(rows)
    summary=merge(rows);(report/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(summary['model_macro'])
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset',type=Path,default=Path('.'));p.add_argument('--normals',type=Path);p.add_argument('--relit',type=Path);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    if not a.normals and not a.relit:p.error('Supply --normals or --relit or both.')
    score(a.dataset,a.normals,a.relit,a.report)
