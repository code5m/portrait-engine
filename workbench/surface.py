"""S5 object-space hatching, scalp fibres and bounded graphite granulation.
All inputs are geometry/scalars. No image input, screen grid, texture or per-face
DOM. Triangle sections are merged into five bounded native CSS region layers.
"""
from __future__ import annotations
import copy
import numpy as np
from shapely import union_all,make_valid,symmetric_difference
from shapely.geometry import Polygon,LineString,Point
from shapely.affinity import affine_transform
from model import CONFIG,canonical,unit
from geometry import clip,region_data
from study_light import area_geometry,content_hash
from surface_registry import S5,source_digest


def rings_area(rings):
    result=Polygon();grid=1e-7
    for ring in rings:
        if len(ring)>=3:
            area=area_geometry(make_valid(Polygon(ring)),grid)
            result=area_geometry(symmetric_difference(result,area,grid_size=grid),grid)
    return result


def from_percent(area,camera):
    cx,cy=camera['center'];scale=camera['span']/100
    return affine_transform(area,[scale,0,0,-scale,cx-50*scale,cy+50*scale])


def below_gray(parent,ceiling):
    silhouette=rings_area(parent['silhouetteRings'])
    above=next((r for r in parent['toneRegions'] if r['gray']>=ceiling),None)
    return from_percent(silhouette.difference(rings_area(above['rings'])) if above else silhouette,parent['camera'])


def sections(projection,values,count,domain):
    """Intersect scalar levels on a 3D triangulated surface, then visibility clip.
    An affine or smooth object-space scalar makes curved sections on the head;
    this is not a screen-space hatch raster and never generates triangle DOM.
    """
    p=projection;values=np.asarray(values,dtype=float)
    if values.shape!=p.tri.shape[:2] or not np.isfinite(values).all() or not 2<=count<=128:
        raise ValueError('Invalid object-space section field')
    eligible=np.array([not g.is_empty for g in p.visible])
    if not eligible.any() or domain.is_empty:return Polygon()
    lo=float(values[eligible].min());hi=float(values[eligible].max());segments=[]
    for level in np.linspace(lo,hi,count+2)[1:-1]:
        for i in np.flatnonzero(eligible&(values.min(axis=1)<level)&(values.max(axis=1)>=level)):
            points=[]
            for a,b in ((0,1),(1,2),(2,0)):
                va,vb=values[i,a]-level,values[i,b]-level
                if (va<0)!=(vb<0):points.append(p.tri[i,a]+(p.tri[i,b]-p.tri[i,a])*va/(va-vb))
            if len(points)==2 and np.linalg.norm(points[0][:2]-points[1][:2])>p.grid:
                line=LineString([points[0][:2],points[1][:2]])
                line=line.intersection(p.visible[i]).intersection(domain)
                if not line.is_empty:segments.append(line)
    return union_all(segments) if segments else Polygon()


def prepare_geometry(projection):
    p=projection;pixel=p.camera['span']/CONFIG['frameSize']
    visible=[area_geometry(g,p.grid) for g in p.visible]
    skin=area_geometry(union_all([g for g,r in zip(visible,p.regions) if int(r) in S5['skinRegionIds']],grid_size=p.grid),p.grid)
    protected=area_geometry(union_all([g for g,r in zip(visible,p.regions) if int(r) in S5['protectedRegionIds']],grid_size=p.grid),p.grid)
    silhouette=area_geometry(p.silhouette,p.grid)
    x0,y0,x1,y1=silhouette.bounds;height=y1-y0;half=max((x1-x0)/2,pixel);cx=(x0+x1)/2
    x,y,z=p.tri[:,:,0],p.tri[:,:,1],p.tri[:,:,2]
    hair_value=y-y1+height*(S5['scalpHeightFraction']+S5['scalpTempleFraction']*((x-cx)/half)**2)
    scalp_parts=[]
    for i,values in enumerate(hair_value):
        if int(p.regions[i]) not in (0,1) or visible[i].is_empty:continue
        points=clip(p.tri[i,:,:2],values,0)
        if len(points)>=3:scalp_parts.append(Polygon(points).intersection(visible[i]))
    scalp=area_geometry(union_all(scalp_parts,grid_size=p.grid),p.grid).difference(protected)
    safe=skin.difference(protected.buffer(pixel*.2))
    primary=sections(p,.45*x+y+.18*z,S5['hatchSections'],safe)
    cross=sections(p,-.65*x+y-.18*z,S5['crossSections'],safe)
    short=sections(p,x+.10*z,S5['hairSections'],scalp)
    swept=sections(p,x+.38*y+.035*(y-y0)*(z-np.mean(z))/max(height,pixel),S5['hairSections'],scalp)
    # Fixed seed and face sampling count, independent of identity names and
    # measured pictures. Uniform barycentric samples live on visible geometry.
    rng=np.random.default_rng(S5['seed']);eligible=np.flatnonzero(np.isin(p.regions,S5['skinRegionIds']))
    grain=[]
    for i in rng.choice(eligible,size=S5['grainCandidates'],replace=True) if len(eligible) else []:
        u,v=rng.random(2)
        if u+v>1:u,v=1-u,1-v
        point=p.tri[i,0]*(1-u-v)+p.tri[i,1]*u+p.tri[i,2]*v
        xy=Point(*point[:2])
        if visible[i].covers(xy) and safe.covers(xy):grain.append(xy)
    return {'skin':safe,'protected':protected,'scalp':scalp,'primary':primary,'cross':cross,
            'short':short,'swept':swept,'grain':grain,'pixel':pixel,'camera':p.camera}


def describe(parent,geometry,stage='S5',material='graphite',hair='swept'):
    if stage not in ('S5','S6') or material not in S5['materials'] or hair not in S5['hairstyles']:
        raise ValueError('Unknown surface mode')
    settings=S5['materials'][material];g=geometry;pixel=g['pixel'];tol=pixel*.08
    dark=below_gray(parent,S5['hatchGrayCeiling']).intersection(g['skin'])
    darkest=below_gray(parent,S5['crossGrayCeiling']).intersection(g['skin'])
    def layer(name,shape,gray,opacity):
        return {'name':name,'rings':region_data(shape,g['camera'],tol),'gray':gray,'opacity':opacity}
    primary=g['primary'].buffer(settings['widthPixels']*pixel/2,quad_segs=2).intersection(dark)
    cross=g['cross'].buffer(settings['widthPixels']*pixel/2,quad_segs=2).intersection(darkest)
    grain=union_all([p.buffer(settings['grainRadiusPixels']*pixel,quad_segs=2) for p in g['grain']]).intersection(dark)
    scalp=g['scalp'] if hair!='none' else Polygon()
    fibres=g[hair].buffer(pixel*.17,quad_segs=2).intersection(scalp) if hair!='none' else Polygon()
    layers=[layer('form-hatching',primary,25,settings['hatchOpacity']),
            layer('cross-hatching',cross,25,settings['crossOpacity']),
            layer('graphite-granulation',grain,25,settings['grainOpacity']),
            layer('scalp-mass',scalp,45,.92),layer('scalp-fibres',fibres,150,.42)]
    d=copy.deepcopy(parent)
    d.update(stage=stage,sourceDigest=source_digest(stage),parentSourceDigest=parent['sourceDigest'],
             parentContentHash=parent['contentHash'],surfaceRegions=layers,
             surface={'material':material,'hair':hair,'method':'object-space sections and visible-surface barycentric grain',
                      'scalpRings':region_data(scalp,g['camera'],tol),
                      'protectedRings':region_data(g['protected'],g['camera'],tol),
                      'humanReview':'DEFERRED_BY_OWNER','automaticArtVerdict':'NONE'})
    points=sum(len(r) for layer in layers for r in layer['rings'])
    d['surfaceContourPoints']=points
    if points>S5['thresholds']['maxAddedContourPoints']:raise ValueError('Surface point budget exceeded')
    d['limitations'] += ['Procedural graphite/charcoal, not skin pores',
                         'Scalp-restricted 2D fibre ribbons, not complete 3D hair scattering',
                         'Expression blendshapes and new PCA modes are not independent real-person validation',
                         'Human artistic review deferred by owner; no default promotion']
    d['contentHash']=content_hash(d)
    if len(canonical(d))>S5['thresholds']['maxDescriptorBytes']:raise ValueError('Surface descriptor budget exceeded')
    return d
