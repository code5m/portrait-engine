"""Vector-only mesh to CSS compiler. No screen grid, image, depth texture or
triangle DOM. Visibility is resolved by overlapping projected triangle planes;
visible clipped polygons are UNIONED into bounded tone/semantic regions.
"""
from __future__ import annotations
import math,time
import numpy as np
from shapely.geometry import Polygon,GeometryCollection
from shapely.strtree import STRtree
from shapely import make_valid,set_precision,union_all
from model import CONFIG,ROOT,LOCK,canonical,sha,source_digest

REGIONS=['head','forehead','orbit','nose','cheek','mouth','jaw','eyes']

def precision_geometry(geometry,grid):
    """Robust overlay, not image smoothing: snap to 1e-5 pixel coordinates.
    This is 10000 times finer than the existing .1px simplifier. Preserve holes
    and disconnected polygons; never skip an identity or use its convex hull.
    """
    return set_precision(make_valid(geometry),grid,mode='valid_output')

def clip(points,values,threshold=0.):
    out=[]
    for i,a in enumerate(points):
        b=points[(i+1)%len(points)];va=values[i]-threshold;vb=values[(i+1)%len(points)]-threshold
        if va>=0:out.append(a)
        if (va>=0)!=(vb>=0):out.append(a+(b-a)*va/(va-vb))
    return out

def polygons(g):
    if g.is_empty:return []
    if g.geom_type=='Polygon':return [g]
    if hasattr(g,'geoms'):return [p for child in g.geoms for p in polygons(child)]
    return []

def region_data(g,camera,tolerance):
    g=make_valid(g).simplify(tolerance,preserve_topology=True)
    rings=[];cx,cy=camera['center'];span=camera['span']
    for p in polygons(g):
        if p.area<1e-9:continue
        for ring in [p.exterior,*p.interiors]:
            rings.append([[round(50+100*(x-cx)/span,5),round(50-100*(y-cy)/span,5)] for x,y in ring.coords])
    return rings

def srgb(x):
    x=np.clip(x,0,1);return np.where(x<=.0031308,x*12.92,1.055*x**(1/2.4)-.055)
def linear(x):return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4

class Projection:
    def __init__(self,model,weights):
        tick=time.perf_counter()
        v,f,n,r=model.mesh(weights);tri=v[f]
        cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);ok=cross[:,2]>1e-9
        self.tri=tri[ok];self.normals=n[f[ok]];self.regions=r[ok]
        points=self.tri[:,:,:2]
        self.grid=model.camera['span']/CONFIG['frameSize']*1e-5
        self.footprints=[precision_geometry(Polygon(x),self.grid) for x in points]
        self.tree=STRtree(self.footprints)
        self.planes=np.linalg.solve(np.concatenate([points,np.ones((len(points),3,1))],axis=2),self.tri[:,:,2,None])[...,0]
        self.visible=[];occluded=0;cut_count=0
        for i,p in enumerate(self.footprints):
            cuts=[]
            for j0 in self.tree.query(p):
                j=int(j0)
                if i==j:continue
                other=self.footprints[j]
                if not p.intersects(other):continue
                overlap=p.intersection(other)
                if overlap.area<1e-8:continue
                q=points[j];delta=np.c_[q,np.ones(3)]@(self.planes[j]-self.planes[i])
                if np.max(delta)<1e-7:continue
                cp=clip(q,delta,1e-7)
                if len(cp)>=3:
                    cut=precision_geometry(Polygon(cp),self.grid).intersection(p)
                    if cut.area>1e-9:cuts.append(cut)
            visible=p.difference(union_all(cuts,grid_size=self.grid)) if cuts else p
            if visible.area < p.area-1e-7:occluded+=1
            cut_count+=len(cuts);self.visible.append(visible)
        self.silhouette=union_all(self.visible,grid_size=self.grid)
        self.camera=model.camera;self.signature=model.signature(weights)
        self.source=source_digest();self.timing=round(time.perf_counter()-tick,3)
        self.visibility={'frontTriangles':len(points),'partlyOrFullyOccluded':occluded,'depthCuts':cut_count,'method':'projected plane-depth clipping; no raster depth buffer','overlayGridPixels':1e-5}
    def describe(self,light,levels=24):
        if levels not in (3,24):raise ValueError('Supported tone budgets: 3 or 24')
        tick=time.perf_counter();direction=np.asarray(light,dtype=float)
        if direction.shape!=(3,) or not np.isfinite(direction).all() or np.linalg.norm(direction)<1e-10:raise ValueError('Finite light vector required')
        direction/=np.linalg.norm(direction)
        shade=CONFIG['ambient']+CONFIG['direct']*np.maximum(0,self.normals@direction)
        lo=float(srgb(CONFIG['ambient']));hi=float(srgb(CONFIG['ambient']+CONFIG['direct']));span=hi-lo
        tol=self.camera['span']/CONFIG['frameSize']*CONFIG['simplifyPixels']
        regions=[]
        for k in range(levels):
            if k==0:shape=self.silhouette
            else:
                t=linear(lo+span*k/levels);parts=[]
                for tri,values,visible in zip(self.tri,shade,self.visible):
                    if visible.is_empty or values.max()<t:continue
                    if values.min()>=t:parts.append(visible);continue
                    cut=clip(tri[:,:2],values,t)
                    if len(cut)>=3:
                        part=visible.intersection(precision_geometry(Polygon(cut),self.grid))
                        if not part.is_empty:parts.append(part)
                shape=union_all(parts,grid_size=self.grid)
            regions.append({'gray':round(255*(lo+span*(k+.5)/levels)),'rings':region_data(shape,self.camera,tol)})
        semantic=[]
        for k,label in enumerate(REGIONS):
            g=union_all([p for p,r in zip(self.visible,self.regions) if r==k],grid_size=self.grid)
            semantic.append({'name':label,'gray':100+k*17,'rings':region_data(g,self.camera,tol)})
        result={'schemaVersion':1,'renderer':'HTML_CSS_REGIONS','stage':'S2','artStatus':'ART_UNVERIFIED','sourceDigest':self.source,
                'geometry':self.signature,'light':direction.tolist(),'frameSize':CONFIG['frameSize'],'camera':self.camera,
                'attribution':{'repository':LOCK['repository'],'commit':LOCK['commit'],'license':'MIT','notice':(ROOT/'workbench/ICT-LICENSE.txt').read_text()},
                'toneRegions':regions,'structureRegions':semantic,'visibility':self.visibility,
                'limitations':['Surface partitions are not actual skull or muscle anatomy','Fixed frontal orthographic view, neutral expression','No skin texture, hair, cast-light occlusion or bounce model','Finite tone bands; no human realism certification'],
                'timingSeconds':{'visibility':self.timing,'toneCompile':round(time.perf_counter()-tick,3)}}
        points=sum(len(r) for x in regions+semantic for r in x['rings'])
        result['contourPoints']=points
        if points>CONFIG['thresholds']['maxContourPoints']:raise ValueError('Contour complexity budget exceeded')
        if len(canonical(result))>CONFIG['thresholds']['maxDescriptorBytes']:raise ValueError('Descriptor byte budget exceeded')
        result['contentHash']=sha(canonical({k:v for k,v in result.items() if k!='timingSeconds'}))
        return result

if __name__=='__main__':
    from model import HeadModel,CACHE,save_json
    m=HeadModel()
    for ident in CONFIG['identities']:
        p=Projection(m,ident['weights']);print('S2_VISIBILITY',ident['id'],p.visibility,p.timing,flush=True)
        for light in CONFIG['lights']:
            d=p.describe(light['direction']);d['fixtureId']=ident['id']+'-'+light['id'];d['split']=ident['split']
            save_json(CACHE/'renders'/(d['fixtureId']+'.json'),d)
            print('S2_VECTOR_SCENE',d['fixtureId'],len(d['toneRegions']),d['contourPoints'],d['timingSeconds'],flush=True)
