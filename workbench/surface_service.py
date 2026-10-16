"""S5/S6 service composes frozen S3/S4 and independent verification."""
from __future__ import annotations
import copy,json,os,re,shutil,subprocess,sys
from model import ROOT,CACHE,CONFIG,canonical,sha,save_json
from geometry import Projection
from study_light import compile_light,describe as light_description,content_hash,source_digest as s3_digest
from study_edges import describe_edges,source_digest as s4_digest
from surface_model import PoseModel
from surface_registry import source_digest,geometry_source_digest,geometry_spec
from surface import prepare_geometry,describe


def read(path):return json.loads(path.read_text())


def base_key(spec):
    return sha(canonical({'model':geometry_source_digest(),'geometry':geometry_spec(spec),'light':spec['light']}))[:32]


def valid_descriptor(path,digest,geometry=None):
    if not path.exists():return None
    try:d=read(path)
    except (ValueError,OSError):return None
    if d.get('sourceDigest')!=digest or d.get('contentHash')!=content_hash(d):return None
    if geometry is not None and d.get('geometry')!=geometry:return None
    return d


def base_assets(spec,pose,projection=None):
    key=base_key(spec);folder=CACHE/'surface/base'/key;signature=pose.signature(spec['weights'])
    d3=valid_descriptor(folder/'S3.json',s3_digest(),signature)
    d4=valid_descriptor(folder/'S4.json',s4_digest(),signature)
    masses=valid_descriptor(folder/'masses.json',s3_digest(),signature)
    if d3 is not None and d4 is not None and masses is not None:return key,d3,d4,masses,projection
    p=projection or Projection(pose,spec['weights']);scene=compile_light(pose,spec['weights'],spec['light'],p)
    d3=light_description(scene);masses=light_description(scene,True,3);d4=describe_edges(scene,d3)
    for name,d in [('S3',d3),('S4',d4),('masses',masses)]:save_json(folder/(name+'.json'),d)
    return key,d3,d4,masses,p


def render(spec,base_model,pose=None,projection=None,geometry=None):
    digest=source_digest(spec['stage']);ident=spec['stage'].lower()+'-'+sha(canonical({'spec':spec,'source':digest}))[:24]
    cached=valid_descriptor(CACHE/'renders'/(ident+'.json'),digest)
    key=base_key(spec)
    if cached is not None and (CACHE/'surface/base'/key/'S4.json').exists() and (CACHE/'specs'/(ident+'.json')).exists():
        return {'renderId':ident,'contentHash':cached['contentHash'],'sourceDigest':digest,'cached':True}
    pose=pose or PoseModel(base_model,spec['extraWeights'],spec['expression'])
    key,d3,d4,masses,projection=base_assets(spec,pose,projection)
    projection=projection or Projection(pose,spec['weights'])
    geometry=geometry or prepare_geometry(projection)
    parent=copy.deepcopy(d4);parent['massRegions']=masses['toneRegions']
    parent['contourPoints']+=sum(len(r) for x in parent['massRegions'] for r in x['rings'])
    if parent['contourPoints']>60000:raise ValueError('Combined S4 view budget exceeded')
    parent['contentHash']=content_hash(parent)
    d=describe(parent,geometry,spec['stage'],spec['material'],spec['hair'])
    d['surfaceBaseKey']=key;d['surfaceSpec']=spec;d['id']=ident;d['contentHash']=content_hash(d)
    save_json(CACHE/'renders'/(ident+'.json'),d);save_json(CACHE/'specs'/(ident+'.json'),{'id':ident,**spec})
    return {'renderId':ident,'contentHash':d['contentHash'],'sourceDigest':digest,'cached':False}


def verify(ident,descriptor):
    if not re.fullmatch(r's[56]-[a-f0-9]{24}',ident):raise ValueError('Invalid surface render identifier')
    if descriptor.get('sourceDigest')!=source_digest(descriptor.get('stage')) or descriptor.get('contentHash')!=content_hash(descriptor):
        raise ValueError('STALE_RENDER')
    if not (CACHE/'specs'/(ident+'.json')).exists():raise ValueError('Missing frozen surface specification')
    blender=os.getenv('PORTRAIT_BLENDER') or shutil.which('blender')
    if not blender:raise RuntimeError('DEPENDENCY_MISSING: independent surface validation requires Blender')
    log=CACHE/'logs'/(ident+'.log');log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w') as out:
        subprocess.run([blender,'--background','--python-exit-code','1','--python',str(ROOT/'workbench/surface_reference.py'),'--',ident],
                       cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=900,check=True,env=os.environ.copy())
        (CACHE/'reference').mkdir(parents=True,exist_ok=True)
        shutil.copy2(CACHE/'studies/reference'/(ident+'-shadow.png'),CACHE/'reference'/(ident+'.png'))
        subprocess.run([sys.executable,str(ROOT/'workbench/surface_validate.py'),'--render-id',ident],
                       cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=900,check=True,env=os.environ.copy())
    return read(CACHE/'machine'/(ident+'.json'))
