"""S3 geometry-derived direct visibility and bounded hemispheric fill.
No screen-space sampling, pixels, raster mask or reference-image input.
S2 is immutable: this module composes its projection, not overwrites it.
"""
from __future__ import annotations
import json, time
import numpy as np
from shapely.geometry import Polygon, GeometryCollection, LineString
from shapely.affinity import affine_transform
from shapely import union_all
from model import ROOT, CACHE, CONFIG, HeadModel, canonical, sha, save_json, unit
from geometry import Projection, clip, precision_geometry, region_data, srgb, linear, REGIONS


def frame(direction):
    l=np.asarray(direction,dtype=float)
    if l.shape!=(3,) or not np.isfinite(l).all() or np.linalg.norm(l)<1e-10:
        raise ValueError('Nonzero finite light direction required')
    l=unit(l); seed=np.array([0.,1.,0.]) if abs(l[1])<.9 else np.array([1.,0.,0.])
    right=unit(np.cross(seed,l)); up=np.cross(l,right)
    return np.array([right,up,l])


def to_camera(geometry, plane, rotation):
    """Lift a 2D light-view polygon to its triangle plane, then inverse-rotate."""
    a,b,c=plane; r=rotation
    return affine_transform(geometry,[r[0,0]+r[2,0]*a,r[1,0]+r[2,0]*b,
                                      r[0,1]+r[2,1]*a,r[1,1]+r[2,1]*b,
                                      r[2,0]*c,r[2,1]*c])


class LightView:
    def __init__(self,model,rotation):self.model=model;self.rotation=rotation;self.camera=model.camera
    def mesh(self,weights):
        v,f,n,s=self.model.mesh(weights)
        v=v@self.rotation.T; f=f.copy()
        tri=v[f]; backwards=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])[:,2]<0
        # Shadow rays hit both sides. Reorient only the light-view culling
        # adapter, leaving the original geometry and camera normals untouched.
        f[backwards]=f[backwards,::-1]
        return v,f,n@self.rotation.T,s
    def signature(self,weights):return self.model.signature(weights)


def source_digest():
    import hashlib
    paths=json.loads((ROOT/'research/sketch/s3-sources.json').read_text())
    h=hashlib.sha256()
    for path in sorted(paths):h.update(path.encode()+b'\0'+(ROOT/path).read_bytes()+b'\0')
    return h.hexdigest()


def protocol():return json.loads((ROOT/'research/sketch/s3-protocol.json').read_text())


def content_hash(d):
    ignored={'contentHash','timingSeconds','fixtureId','split','id'}
    return sha(canonical({k:v for k,v in d.items() if k not in ignored}))


def forward_faces(vertices,faces):
    tri=vertices[faces]
    return np.flatnonzero(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])[:,2]>1e-9)


def compile_light(model, weights, direction, projection=None):
    """Resolve visibility in CAMERA and LIGHT coordinate systems independently."""
    start=time.perf_counter(); p=projection or Projection(model,weights)
    r=frame(direction); l=r[2]; light_projection=Projection(LightView(model,r),weights)
    vertices,faces,normals,regions=model.mesh(weights)
    face_camera=forward_faces(vertices,faces)
    light_vertices,light_faces,_,_=LightView(model,r).mesh(weights)
    face_light=forward_faces(light_vertices,light_faces)
    lookup={int(face):i for i,face in enumerate(face_light)}
    lit=[];dark=[]
    for i,face in enumerate(face_camera):
        visible=p.visible[i];j=lookup.get(int(face))
        if j is None or visible.is_empty:
            yes=GeometryCollection()
        else:
            lifted=to_camera(light_projection.visible[j],light_projection.planes[j],r)
            yes=visible.intersection(precision_geometry(lifted,p.grid))
        lit.append(yes);dark.append(visible.difference(yes))
    settings=protocol(); up=unit(settings['fillUp'])
    gain=float(settings['fillStrength'])
    fill=gain*(1+p.normals@up)/2
    unlit=CONFIG['ambient']+fill
    direct=CONFIG['direct']*np.maximum(0,p.normals@l)
    shaded=unlit+direct
    return {'projection':p,'weights':weights,'direction':l,'lit':lit,'dark':dark,
            'shaded':shaded,'unlit':unlit,'direct':direct,'faceIndices':face_camera,
            'cameraVertices':vertices,'cameraFaces':faces,'timeSeconds':round(time.perf_counter()-start,3),
            'lightVisibility':light_projection.visibility}


def threshold_shape(scene, threshold, cast=True):
    p=scene['projection'];parts=[]
    branches=[(scene['lit'],scene['shaded']),(scene['dark'],scene['unlit'])] if cast else [(p.visible,scene['shaded'])]
    for visible,values in branches:
        for triangle,v,g in zip(p.tri,values,visible):
            if g.is_empty or v.max()<threshold:continue
            if v.min()>=threshold:parts.append(g);continue
            points=clip(triangle[:,:2],v,threshold)
            if len(points)>=3:
                cut=precision_geometry(Polygon(points),p.grid).intersection(g)
                if not cut.is_empty:parts.append(cut)
    return union_all(parts,grid_size=p.grid) if parts else GeometryCollection()


def describe(scene, cast=True, levels=31):
    settings=protocol()
    if levels not in (3,31):raise ValueError('S3 budgets are 3 or 31 regions')
    t=time.perf_counter();p=scene['projection']
    tol=p.camera['span']/CONFIG['frameSize']*CONFIG['simplifyPixels']
    lo=float(srgb(CONFIG['ambient'])); hi=float(srgb(CONFIG['ambient']+CONFIG['direct']+settings['fillStrength']))
    tones=[]
    for k in range(levels):
        shape=p.silhouette if k==0 else threshold_shape(scene,linear(lo+(hi-lo)*k/levels),cast)
        tones.append({'gray':round(255*(lo+(hi-lo)*(k+.5)/levels)),
                      'rings':region_data(shape,p.camera,tol)})
    structures=[]
    for k,label in enumerate(REGIONS):
        g=union_all([v for v,i in zip(p.visible,p.regions) if i==k],grid_size=p.grid)
        structures.append({'name':label,'gray':100+k*17,'rings':region_data(g,p.camera,tol)})
    actual_shadow=[]
    for area,normal in zip(scene['dark'],p.normals):
        if np.max(normal@scene['direction'])>0 and not area.is_empty:actual_shadow.append(area)
    cast_shape=union_all(actual_shadow,grid_size=p.grid)
    d={'schemaVersion':1,'renderer':'HTML_CSS_REGIONS','stage':'S3','artStatus':'ART_UNVERIFIED',
       'sourceDigest':source_digest(),'geometry':p.signature,'light':scene['direction'].tolist(),
       'frameSize':CONFIG['frameSize'],'camera':p.camera,'toneRegions':tones,'structureRegions':structures,
       'silhouetteRings':region_data(p.silhouette,p.camera,tol),
       'castShadowRings':region_data(cast_shape,p.camera,tol),
       'castShadowAreaRatio':float(cast_shape.area/max(p.silhouette.area,1e-20)),
       'lighting':{'castVisibility':cast,'ambient':CONFIG['ambient'],'direct':CONFIG['direct'],
                   'fillStrength':settings['fillStrength'],'fillUp':settings['fillUp'],
                   'model':'directional direct light with binary visibility plus a declared unoccluded hemisphere fill; not full GI'},
       'visibility':{'camera':p.visibility,'light':scene['lightVisibility']},
       'attribution':{'license':'MIT','notice':(ROOT/'workbench/ICT-LICENSE.txt').read_text()},
       'timingSeconds':{'visibility':scene['timeSeconds'],'toneCompile':round(time.perf_counter()-t,3)},
       'limitations':['Neutral frontal surface only','Finite tonal bands remain','Uniform hemisphere fill ignores indirect occlusion','No skin or hair and no artistic certification']}
    d['contourPoints']=sum(len(r) for region in tones+structures for r in region['rings'])
    if d['contourPoints']>settings['thresholds']['maxContourPoints']:raise ValueError('S3 contour budget exceeded')
    if len(canonical(d))>settings['thresholds']['maxDescriptorBytes']:raise ValueError('S3 byte budget exceeded')
    d['contentHash']=content_hash(d)
    return d


if __name__=='__main__':
    import sys
    model=HeadModel();split=sys.argv[1] if len(sys.argv)>1 else 'all'
    for identity in CONFIG['identities']:
        if split!='all' and identity['split']!=split:continue
        camera=Projection(model,identity['weights'])
        for light in CONFIG['lights']:
            ident=identity['id']+'-'+light['id']
            scene=compile_light(model,identity['weights'],light['direction'],camera)
            for label,cast,levels in [('control',False,31),('tone',True,31),('masses',True,3)]:
                result=describe(scene,cast,levels);result['fixtureId']=ident;result['split']=identity['split']
                save_json(CACHE/'studies/S3'/ident/(label+'.json'),result)
                if label=='tone':tone=result
            from study_edges import describe_edges
            edge=describe_edges(scene,tone)
            save_json(CACHE/'studies/S4'/ident/'tone.json',edge)
            print('S3_S4_COMPILED',ident,scene['timeSeconds'],flush=True)
