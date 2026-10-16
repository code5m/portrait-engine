"""Independent S1 ray/normal evaluator. Pixel sampling is evaluation ONLY."""
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_erosion,binary_dilation
ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/'research/sketch/s1-scenes.json').read_text())

def unit(v):
    a=np.asarray(v,dtype=float)
    return a/np.maximum(np.linalg.norm(a,axis=-1,keepdims=True),1e-20)

def rotation(axis,degrees):
    a=np.radians(degrees);c,s=np.cos(a),np.sin(a)
    return np.array([[1,0,0],[0,c,-s],[0,s,c]]) if axis=='x' else np.array([[c,0,s],[0,1,0],[-s,0,c]])

def wedge(shape):
    x,y,z=shape['half'];R=rotation('y',shape['yaw'])
    v=np.array([[-x,-y,-z],[x,-y,-z],[x,-y,z],[-x,-y,z],[-x,y,-z],[x,y,-z],[x,.15*y,z],[-x,.15*y,z]])@R.T
    faces=[[0,3,2,1],[0,1,5,4],[3,7,6,2],[0,4,7,3],[1,2,6,5],[4,5,6,7]]
    result=[]
    for ids in faces:
        p=v[ids];n=unit(np.cross(p[1]-p[0],p[2]-p[0]))
        if np.dot(n,p[0]-v.mean(0))<0:n=-n;p=p[::-1]
        result.append((p,n,float(n@p[0])))
    return v,result

def hit(shape,origin,direction):
    o=np.asarray(origin,dtype=float);d=np.broadcast_to(np.asarray(direction,dtype=float),o.shape)
    dims=o.shape[:-1];best=np.full(dims,np.inf);normal=np.zeros_like(o)
    def accept(t,n,valid):
        nonlocal best,normal
        keep=valid&(t>1e-7)&(t<best)
        best=np.where(keep,t,best);normal=np.where(keep[...,None],n,normal)
    if shape['kind']=='ellipsoid':
        r=np.asarray(shape['radii']);A=np.sum((d/r)**2,axis=-1);B=2*np.sum(o*d/r**2,axis=-1);C=np.sum((o/r)**2,axis=-1)-1
        disc=B*B-4*A*C
        for sign in [-1,1]:
            t=(-B+sign*np.sqrt(np.maximum(0,disc)))/(2*A)
            n=unit((o+t[...,None]*d)/r**2)
            accept(t,n,disc>=0)
    elif shape['kind']=='cylinder':
        R=rotation('x',shape['tilt']);ol=o@R;dl=d@R;r=shape['radius'];h=shape['halfHeight']
        A=dl[...,0]**2+dl[...,2]**2;B=2*(ol[...,0]*dl[...,0]+ol[...,2]*dl[...,2]);C=ol[...,0]**2+ol[...,2]**2-r*r;disc=B*B-4*A*C
        for sign in [-1,1]:
            t=(-B+sign*np.sqrt(np.maximum(0,disc)))/np.maximum(2*A,1e-20)
            p=ol+t[...,None]*dl;n=p.copy();n[...,1]=0;n=unit(n)@R.T
            accept(t,n,(disc>=0)&(np.abs(p[...,1])<=h+1e-10))
        for sign in [-1,1]:
            safe=np.where(np.abs(dl[...,1])>1e-12,dl[...,1],1e-12)
            t=(sign*h-ol[...,1])/safe;p=ol+t[...,None]*dl
            accept(t,np.broadcast_to(np.array([0,sign,0])@R.T,o.shape),(p[...,0]**2+p[...,2]**2<=r*r+1e-10)&(np.abs(dl[...,1])>1e-12))
    else:
        _,faces=wedge(shape)
        for _,n,offset in faces:
            den=d@n;safe=np.where(np.abs(den)>1e-12,den,1e-12)
            t=(offset-o@n)/safe;p=o+t[...,None]*d
            valid=np.abs(den)>1e-12
            for _,nn,off in faces:valid=valid&(p@nn<=off+1e-8)
            accept(t,np.broadcast_to(n,o.shape),valid)
    return best,normal,np.isfinite(best)

def grid(config=CONFIG):
    size=config['frameSize'];step=config['orthoScale']/size
    yy,xx=np.mgrid[:size,:size]
    return (xx+.5-size/2)*step,(size/2-yy-.5)*step

def field(shape,light,bounce=False,config=CONFIG):
    x,y=grid(config);o=np.stack([x,y,np.full_like(x,10)],-1)
    _,n,mask=hit(shape,o,[0,0,-1]);l=unit(light['direction']);g=unit(config['groundNormal'])
    gain=config['bounceStrength']*config['receiverAlbedo']*config['direct']*max(0,float(g@l)) if bounce else 0
    radiance=config['ambient']+config['direct']*np.maximum(0,n@l)+gain*(1-n@g)/2
    clipped=np.clip(radiance,0,1);image=255*np.where(clipped<=.0031308,12.92*clipped,1.055*clipped**(1/2.4)-.055)
    return np.where(mask,image,255),mask,n

def shadow_mask(shape,light,offset,config=CONFIG):
    x,y=grid(config);g=unit(config['groundNormal']);z=(offset-g[0]*x-g[1]*y)/g[2]
    _,_,mask=hit(shape,np.stack([x,y,z],-1),unit(light['direction']))
    return mask

def image_metrics(actual,expected,mask):
    inner=binary_erosion(mask,iterations=4);edge=binary_dilation(mask,iterations=4)&~inner
    error=np.abs(actual-expected)
    gx=np.abs(np.diff(actual,axis=1)-np.diff(expected,axis=1));gy=np.abs(np.diff(actual,axis=0)-np.diff(expected,axis=0))
    ix=inner[:,:-1]&inner[:,1:];iy=inner[:-1,:]&inner[1:,:]
    return {key:round(float(value),5) for key,value in {
        'interiorMAE':error[inner].mean(),'fullMAE':error.mean(),'edgeMAE':error[edge].mean(),
        'gradientError':np.r_[gx[ix],gy[iy]].mean(),'p95Interior':np.percentile(error[inner],95)}.items()}

def overlap(a,b):
    union=np.count_nonzero(a|b);intersection=np.count_nonzero(a&b)
    ca=np.argwhere(a).mean(0);cb=np.argwhere(b).mean(0)
    return {'iou':round(intersection/max(1,union),6),'centroidPixels':round(float(np.linalg.norm(ca-cb)),5)}

def all_cases(config=CONFIG):
    return [{'id':s['id']+'-'+l['id'],'shape':s,'light':l} for s in config['profiles'] for l in (config['holdoutLights'] if s['split']=='holdout' else config['lights'])]
