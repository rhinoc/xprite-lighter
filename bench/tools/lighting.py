"""Orthographic diffuse test rig: image pixels +X right, +Y up, +Z toward camera."""
import numpy as np

RAW_LIGHTS={'left':(-.84,.32,.50),'right':(.84,.32,.50),'top':(.05,.92,.39),'bottom':(-.22,-.81,.55),'front':(0,0,1)}
LIGHTS={k:np.asarray(v,dtype=float)/np.linalg.norm(v) for k,v in RAW_LIGHTS.items()}
FLOOR=.26
POWER=.83
BANDS=np.asarray([.00,.24,.49,.74,1.00])
EDGES=np.asarray([.12,.37,.62,.87])


def linear_to_rgb(x):
    return np.rint(255*np.clip(np.where(x<=.0031308,12.92*x,1.055*np.maximum(x,0.)**(1/2.4)-.055),0.,1.)).astype(np.uint8)


def shade(rgba,normal,direction,style='cel'):
    x=rgba[...,:3].astype(float)/255
    color=np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
    dot=np.clip(normal@LIGHTS[direction],0,1)
    if style=='cel':dot=BANDS[np.digitize(dot,EDGES)]
    elif style!='smooth':raise ValueError(style)
    out=np.dstack([linear_to_rgb(color*(FLOOR+POWER*dot[...,None])),rgba[...,3]])
    out[rgba[...,3]==0,:3]=0
    return out


def encode_normal(n,a):
    encoded=np.rint(255*(np.clip(n,-1,1)*.5+.5)).astype(np.uint8)
    encoded[a==0]=[128,128,255]
    return np.dstack([encoded,a])


def decode_normal(rgba):
    n=rgba[...,:3].astype(np.float64)/127.5-1
    length=np.linalg.norm(n,axis=-1,keepdims=True)
    if np.any((rgba[...,3]>0)&(length[...,0]<.05)):raise ValueError('Foreground contains zero or near-zero normal')
    return n/np.maximum(length,1.e-12)
