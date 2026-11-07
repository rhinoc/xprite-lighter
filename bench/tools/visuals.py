"""Preview the model-derived benchmark without altering light exposure or scene geometry."""
import argparse, json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from math import acos, cos, sin, pi, atan2, hypot
PAPER='#f1f2ec'; INK='#172b34'; MUTED='#3f5961'; ACCENT='#0d726e'; RULE='#b7c5c0'; STAGE='#96a4a7'; GOLD='#e9ab3d'
FONT=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
BOLD=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc')
ENG=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
ENG_B=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
def text(draw,xy,label,size=18,color=INK,bold=False,mono=False,anchor='lt'):
    font=(ENG_B if bold else ENG) if mono else (BOLD if bold else FONT)
    f=ImageFont.truetype(str(font),size,index=0 if mono else 2)
    draw.text(xy,str(label),font=f,fill=color,anchor=anchor)
def rgba(path):
    with Image.open(path) as img:return np.asarray(img.convert('RGBA')).copy()
def place(canvas,sprite,box,maxsize):
    cx,cy=box;limw,limh=maxsize
    scale=max(1,int(min(limw/sprite.width,limh/sprite.height)))
    chip=sprite.resize((scale*sprite.width,scale*sprite.height),Image.Resampling.NEAREST)
    canvas.paste(chip,(round(cx-chip.width/2),round(cy-chip.height/2)),chip)
CN={'knight':'挥剑骑士','mage':'持杖法师','rogue':'兜帽游侠','skeleton-warrior':'骷髅战士','chest':'宝箱','rover':'探测车','watermill':'水磨坊','shrine':'神龛'}
def extract(root,c,lighting):
    case=root/'cases'/c['id'];gt=case/'gt'
    n=rgba(root/'baseline'/'normals'/(c['id']+'.png'))
    inp=rgba(case/'input.png');col=rgba(gt/'albedo.png');gg=np.load(gt/'normal.npy').astype('float64');gg=gg/np.maximum(1.e-12,np.linalg.norm(gg,axis=-1,keepdims=True));p=lighting.decode_normal(n)
    gr=rgba(gt/'cel-right.png');pg=lighting.shade(col,p,'right','cel')
    assert np.any(col[...,3]>0)
    assert np.max(np.abs(gr.astype(int)-lighting.shade(col,gg,'right','cel').astype(int)))<=1
    ims=[Image.fromarray(x) for x in (inp,n,rgba(gt/'normal.png'),pg,gr)]
    bbox=ims[0].getchannel('A').getbbox()
    return [im.crop(bbox) for im in ims],(col,p,gg,bbox)
def choose(rows,name):
    a=[r for r in rows if r.get('model')==name or r['id'].startswith(name+'-')]
    # Avoid other yaw and native sizes when a fixed comparable model view is available.
    return next((r for r in a if r['id']==name+'-a-64'),None) or next((r for r in a if r['id'].endswith('64')),None) or (a[0] if a else None)
def sheet(root,rows,lighting):
    selected=[choose(rows,m) for m in ['knight','mage','skeleton-warrior','rover','watermill','shrine']];selected=[r for r in selected if r]
    if len(selected)<3:selected=rows[:6]
    W=1196; start=232; margin=28; colw=185; rowh=156
    H=226+len(selected)*rowh+74
    im=Image.new('RGB',(W,H),PAPER);d=ImageDraw.Draw(im)
    text(d,(margin,21),'XPRITE   /   LIGHTING BENCH',16,ACCENT,True,True)
    text(d,(W-margin,22),'NORMAL ESTIMATION     /     V3',13,MUTED,False,True,'rt')
    text(d,(margin,57),'角色与道具的法线真值对照',39,INK,True)
    text(d,(margin,120),'从同一像素的可见三角形取 GT 法线。右侧两列共用底色、灯位、曝光与五档着色。',20,MUTED)
    d.line((margin,166,W-margin,166),fill=RULE,width=2)
    text(d,(margin,189),'样例 / 原生尺寸',17,MUTED,True)
    for j,label in enumerate(['左光输入','Xprite 预测法线','模型 GT 法线','预测法线 · 右光','GT 法线 · 右光']):
        text(d,(start+colw*(j+.5),189),label,18,INK,True,anchor='mt')
    for i,r in enumerate(selected):
        model=r['id'].rsplit('-',2)[0]; name=CN.get(r.get('model'),CN.get(model,model))
        sprites,_=extract(root,r,lighting)
        y=224+i*rowh
        text(d,(margin,y+21),f'{i+1:02d}',14,ACCENT,True,True)
        text(d,(margin,y+48),name,26,INK,True)
        text(d,(margin,y+94),r['id'],14,MUTED,False,True)
        d.rounded_rectangle((start,y,start+5*colw-1,y+rowh-11),radius=5,fill=STAGE)
        for j,sprite in enumerate(sprites):
            if j: d.line((start+colw*j,y+16,start+colw*j,y+rowh-27),fill='#abb7b8',width=1)
            place(im,sprite,(start+colw*(j+.5),y+(rowh-11)/2),(colw-12,rowh-22))
    d.line((margin,H-54,W-margin,H-54),fill=RULE,width=1)
    text(d,(margin,H-34),'GT 与 Xprite 法线均使用相机空间坐标     +X 向右   /   +Y 向上   /   +Z 朝观察者',15,MUTED)
    text(d,(W-margin,H-34),'BENCH   /   03',13,ACCENT,True,True,'rt')
    im.save(root/'overview.png',optimize=True)
def anim(root,r,lighting):
    _,(col,n,g,b)=extract(root,r,lighting)
    W=746; H=399; stage_top=126; stage_bottom=361;xs=[189,557]
    model=r.get('model') or r['id'].rsplit('-',2)[0]
    label=CN.get(model,r['id']);frames=[]
    for i in range(32):
        u=(1-cos(2*pi*i/32))/2;end=atan2(.32,.84);phi=pi-end-u*(pi-2*end)
        L=np.array([hypot(.84,.32)*cos(phi),hypot(.84,.32)*sin(phi),.50]);L/=np.linalg.norm(L)
        lighting.LIGHTS['sweep']=L
        im=Image.new('RGB',(W,H),PAPER);d=ImageDraw.Draw(im)
        text(d,(17,15),label+' · 固定姿势扫光',26,INK,True)
        text(d,(W-17,22),'MESH GT   /   '+r['id'],12,ACCENT,True,True,'rt')
        text(d,(17,58),'左光',16,MUTED);text(d,(W-17,58),'右光',16,MUTED,anchor='rt')
        x0,x1=74,W-74;cy=68;d.line((x0,cy,x1,cy),fill=RULE,width=3);d.line((W/2,cy-4,W/2,cy+4),fill=MUTED,width=1)
        cx=round(x0+u*(x1-x0));d.ellipse((cx-7,cy-7,cx+7,cy+7),fill=GOLD,outline=INK,width=2)
        for j,(nx,lab) in enumerate(zip([n,g],['Xprite 预测法线','模型 GT 法线'])):
            text(d,(xs[j],95),lab,19,INK,True,anchor='mt'); d.rounded_rectangle((xs[j]-174,stage_top,xs[j]+174,stage_bottom),radius=5,fill=STAGE)
            spr=Image.fromarray(lighting.shade(col,nx,'sweep','cel')).crop(b)
            place(im,spr,(xs[j],(stage_top+stage_bottom)/2),(340,stage_bottom-stage_top-9))
        text(d,(17,376),'同一模型底色 · 同一方向光 · 同一五档着色',15,MUTED)
        text(d,(W-17,378),'XPRITE   /   LIGHTING BENCH',11,ACCENT,True,True,'rt')
        frames.append(im)
    palette_sheet=Image.new('RGB',(W*4,H*2))
    for i in range(8):palette_sheet.paste(frames[2*i],(i%4*W,i//4*H))
    pal=palette_sheet.quantize(colors=256,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
    q=[im.quantize(palette=pal,dither=Image.Dither.NONE) for im in frames]
    times=[95]*32;times[0]=times[16]=670
    q[0].save(root/'gt-comparison.gif',save_all=True,append_images=q[1:],duration=times,loop=0,disposal=1,comment=f"{r['id']}: Xprite-predicted normals vs known source mesh normals; same geometry albedo, light and quantization.".encode())
    print('Animated',r['id'],flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('pack',type=Path);ap.add_argument('--demo-model',default='knight');args=ap.parse_args();root=args.pack
    sys.path.insert(0,str(root/'tools'));import lighting
    rows=json.loads((root/'manifest.json').read_text())['cases']
    sheet(root,rows,lighting);anim(root,choose(rows,args.demo_model) or rows[0],lighting)
