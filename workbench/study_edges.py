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
from study_light import content_hash,area_geometry


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


def visible_intensity(scene, visible_areas):
    """Local face means of the light model actually painted by S3.

    Crease contrast must not resurrect blocked direct light. Weight the lit
    and dark branches by camera-visible area, with no image/identity input.
    """
    shaded=np.asarray(scene['shaded'],dtype=float)
    unlit=np.asarray(scene['unlit'],dtype=float)
    if shaded.shape!=unlit.shape or shaded.shape!=(len(visible_areas),3):
        raise ValueError('Expected matching three-vertex irradiance arrays')
    if not np.isfinite(shaded).all() or not np.isfinite(unlit).all():
        raise ValueError('Finite irradiance required')
    if len(scene['lit'])!=len(visible_areas):raise ValueError('Mismatched visibility')
    fractions=np.array([min(1.,max(0.,lit.area/area.area)) if area.area>0 else 0.
                        for lit,area in zip(scene['lit'],visible_areas)])
    return fractions*shaded.mean(axis=1)+(1-fractions)*unlit.mean(axis=1)


def crease_support(line,left,right,grid):
    """A crease needs BOTH adjacent faces visible at its geometric edge.

    One-sided visible boundaries are already handled as camera occlusions;
    do not add an extra crease by unioning a hidden neighbor into the test.
    """
    if left.is_empty or right.is_empty:return GeometryCollection()
    return line.intersection(left.buffer(grid*4)).intersection(right.buffer(grid*4))


def describe_edges(scene,result):
    settings=json.loads((ROOT/'research/sketch/s4-protocol.json').read_text())
    p=scene['projection'];pixel=p.camera['span']/CONFIG['frameSize'];tol=.10*pixel
    visible_areas=[area_geometry(g,p.grid) for g in p.visible]
    silhouette=area_geometry(p.silhouette,p.grid)
    cuts=[]
    for visible,footprint in zip(visible_areas,p.footprints):
        if not visible.is_empty:
            footprint=area_geometry(footprint,p.grid)
            internal=visible.boundary.difference(footprint.boundary.buffer(pixel*.002))
            if internal.length>pixel*.5:cuts.append(internal)
    occlusion=union_all(cuts).simplify(tol,preserve_topology=True) if cuts else GeometryCollection()
    hard=[silhouette.boundary,occlusion];soft=[];counts={'hard':0,'soft':0,'lost':0}
    shared={}
    for local,face in enumerate(scene['faceIndices']):
        ids=scene['cameraFaces'][face]
        for a,b in [(ids[0],ids[1]),(ids[1],ids[2]),(ids[2],ids[0])]:
            key=tuple(sorted((int(a),int(b))));shared.setdefault(key,[]).append(local)
    tri=p.tri;normals=unit(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]))
    intensity=visible_intensity(scene,visible_areas)
    for (a,b),neighbors in shared.items():
        if len(neighbors)!=2:continue
        i,j=neighbors
        angle=float(np.degrees(np.arccos(np.clip(normals[i]@normals[j],-1,1))))
        contrast=float(abs(intensity[i]-intensity[j])*255)
        kind=classify(angle,contrast);counts[kind]+=1
        if kind=='lost':continue
        line=LineString(scene['cameraVertices'][[a,b],:2])
        visible=crease_support(line,visible_areas[i],visible_areas[j],p.grid)
        if visible.length>pixel*.3:(hard if kind=='hard' else soft).append(visible)
    def overlay(lines,width,opacity,blur,name):
        geometry=union_all(lines).buffer(width*pixel/2,quad_segs=3).intersection(silhouette)
        return {'name':name,'gray':settings['inkGray'],'opacity':opacity,'blurPixels':blur,
                'rings':region_data(geometry,p.camera,tol)}
    edges=[overlay(hard,settings['hardWidthPixels'],settings['hardOpacity'],0,'geometric-hard'),
           overlay(soft,settings['softWidthPixels'],settings['softOpacity'],settings['softFeatherPixels'],'geometric-soft')]
    boundaries=[]
    for region_id in np.unique(p.regions):
        areas=[v for v,r in zip(visible_areas,p.regions) if r==region_id and not v.is_empty]
        if areas:boundaries.append(area_geometry(union_all(areas,grid_size=p.grid),p.grid).boundary)
    control=[overlay(boundaries,settings['hardWidthPixels'],settings['hardOpacity'],0,'all-region-outlines')]
    d=copy.deepcopy(result)
    d.update(stage='S4',sourceDigest=source_digest(),parentSourceDigest=result['sourceDigest'],
             edgeRegions=edges,controlEdgeRegions=control,
             edgeClassification={'counts':counts,'occlusionLengthPixels':round(occlusion.length/pixel,2),
                                 'control':'every semantic boundary','candidate':'only camera occlusion, silhouette and contrast-supported creases',
                                 'contrastModel':'camera-visible area-weighted S3 lit and shadow branches; both crease sides must be visible',
                                 'automaticQualityVerdict':'NONE'})
    extra=sum(len(r) for layer in edges+control for r in layer['rings'])
    d['edgeContourPoints']=extra
    if extra>settings['maxEdgePoints']:raise ValueError('S4 edge complexity budget exceeded')
    if len(canonical(d))>settings['maxDescriptorBytes']:raise ValueError('S4 descriptor byte budget exceeded')
    d['limitations']+=['Edge selection is a hypothesis, not an artistic verdict','Only local crease ink is feathered; surface tones and true silhouettes are not globally blurred','Crease contrast uses area-weighted face means, not a continuous edge-local integral']
    d['contentHash']=content_hash(d)
    return d
