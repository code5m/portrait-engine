"""S4: geometry-selected edge hierarchy. No full-face blur or painted identity.
Hard silhouettes/occlusions, feathered creases, deliberately omitted weak edges.
The all-semantic-outline control is retained; no automated aesthetic verdict.
"""
from __future__ import annotations
import copy,hashlib,json
import numpy as np
from shapely import union_all
from shapely.geometry import LineString,GeometryCollection
from model import ROOT,CONFIG,canonical,sha,unit
from geometry import region_data
from study_light import content_hash


def source_digest():
    paths=json.loads((ROOT/'research/sketch/s4-sources.json').read_text());h=hashlib.sha256()
    for path in sorted(paths):h.update(path.encode()+b'\0'+(ROOT/path).read_bytes()+b'\0')
    return h.hexdigest()


def classify(angle,contrast,occlusion=False):
    if not np.isfinite([angle,contrast]).all() or angle<0 or contrast<0:
        raise ValueError('Finite nonnegative edge evidence required')
    if occlusion:return 'hard'
    if angle<12 or contrast<5:return 'lost'
    return 'hard' if angle>=35 and contrast>=16 else 'soft'


def describe_edges(scene,result):
    settings=json.loads((ROOT/'research/sketch/s4-protocol.json').read_text())
    p=scene['projection'];pixel=p.camera['span']/CONFIG['frameSize'];tol=.10*pixel
    cuts=[]
    for visible,footprint in zip(p.visible,p.footprints):
        if not visible.is_empty:
            internal=visible.boundary.difference(footprint.boundary.buffer(pixel*.002))
            if internal.length>pixel*.5:cuts.append(internal)
    occlusion=union_all(cuts).simplify(tol,preserve_topology=True) if cuts else GeometryCollection()
    hard=[p.silhouette.boundary,occlusion];soft=[];counts={'hard':0,'soft':0,'lost':0}
    shared={}
    for local,face in enumerate(scene['faceIndices']):
        ids=scene['cameraFaces'][face]
        for a,b in [(ids[0],ids[1]),(ids[1],ids[2]),(ids[2],ids[0])]:
            key=tuple(sorted((int(a),int(b))));shared.setdefault(key,[]).append(local)
    tri=p.tri;normals=unit(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]))
    intensity=scene['shaded'].mean(axis=1)
    for (a,b),neighbors in shared.items():
        if len(neighbors)!=2:continue
        i,j=neighbors
        angle=float(np.degrees(np.arccos(np.clip(normals[i]@normals[j],-1,1))))
        contrast=float(abs(intensity[i]-intensity[j])*255)
        kind=classify(angle,contrast);counts[kind]+=1
        if kind=='lost':continue
        line=LineString(scene['cameraVertices'][[a,b],:2])
        visible=line.intersection(union_all([p.visible[i],p.visible[j]]).buffer(p.grid*4))
        if visible.length>pixel*.3:(hard if kind=='hard' else soft).append(visible)
    def overlay(lines,width,opacity,blur,name):
        geometry=union_all(lines).buffer(width*pixel/2,quad_segs=3).intersection(p.silhouette)
        return {'name':name,'gray':settings['inkGray'],'opacity':opacity,'blurPixels':blur,
                'rings':region_data(geometry,p.camera,tol)}
    edges=[overlay(hard,settings['hardWidthPixels'],settings['hardOpacity'],0,'geometric-hard'),
           overlay(soft,settings['softWidthPixels'],settings['softOpacity'],settings['softFeatherPixels'],'geometric-soft')]
    boundaries=[]
    for region_id in np.unique(p.regions):
        areas=[v for v,r in zip(p.visible,p.regions) if r==region_id and not v.is_empty]
        if areas:boundaries.append(union_all(areas,grid_size=p.grid).boundary)
    control=[overlay(boundaries,settings['hardWidthPixels'],settings['hardOpacity'],0,'all-region-outlines')]
    d=copy.deepcopy(result)
    d.update(stage='S4',sourceDigest=source_digest(),parentSourceDigest=result['sourceDigest'],
             edgeRegions=edges,controlEdgeRegions=control,
             edgeClassification={'counts':counts,'occlusionLengthPixels':round(occlusion.length/pixel,2),
                                 'control':'every semantic boundary','candidate':'only camera occlusion, silhouette and contrast-supported creases',
                                 'automaticQualityVerdict':'NONE'})
    extra=sum(len(r) for layer in edges+control for r in layer['rings'])
    d['edgeContourPoints']=extra
    if extra>settings['maxEdgePoints']:raise ValueError('S4 edge complexity budget exceeded')
    if len(canonical(d))>settings['maxDescriptorBytes']:raise ValueError('S4 descriptor byte budget exceeded')
    d['limitations']+=['Edge selection is a hypothesis, not an artistic verdict','Only local crease ink is feathered; surface tones and true silhouettes are not globally blurred']
    d['contentHash']=content_hash(d)
    return d
