"""Explicit S3/S4 API operations; no arbitrary paths, commands or uploads."""
import copy,json,os,shutil,subprocess,sys
import numpy as np
from model import ROOT,CACHE,CONFIG,canonical,sha,save_json,source_digest as s2_digest,unit
from study_light import compile_light,describe,source_digest as s3_digest,content_hash
from study_edges import describe_edges,source_digest as s4_digest

STAGES=('S2','S3','S4')

def current_digest(stage):
    if stage not in STAGES:raise ValueError('Unregistered sketch stage')
    return {'S2':s2_digest,'S3':s3_digest,'S4':s4_digest}[stage]()


def checked(path,stage):
    if not path.exists():return None
    d=json.loads(path.read_text())
    if d.get('sourceDigest')!=current_digest(stage) or d.get('contentHash')!=content_hash(d):return None
    return d


def render(payload,model):
    stage=payload['stage'];weights=payload['weights'];light=unit(payload['light']).tolist()
    key=stage.lower()+'-'+sha(canonical({'weights':weights,'light':light,'stage':stage,'source':current_digest(stage)}))[:24]
    cached=checked(CACHE/'renders'/(key+'.json'),stage)
    if cached:return {'renderId':key,'contentHash':cached['contentHash'],'sourceDigest':cached['sourceDigest'],'cached':True}
    source_id=None;objects={}
    for identity in CONFIG['identities']:
        if identity['weights']!=weights:continue
        for item in CONFIG['lights']:
            if np.max(np.abs(unit(item['direction'])-light))<1e-10:source_id=identity['id']+'-'+item['id']
    if source_id:
        for name in ['control','tone','masses']:
            objects[name]=checked(CACHE/'studies/S3'/source_id/(name+'.json'),'S3')
        objects['edges']=checked(CACHE/'studies/S4'/source_id/'tone.json','S4')
    reused=bool(objects) and all(objects.values())
    if not reused:
        scene=compile_light(model,weights,light)
        objects={name:describe(scene,cast,levels) for name,cast,levels in [('control',False,31),('tone',True,31),('masses',True,3)]}
        objects['edges']=describe_edges(scene,objects['tone'])
    for name in ['control','tone','masses']:save_json(CACHE/'studies/S3'/key/(name+'.json'),objects[name])
    save_json(CACHE/'studies/S4'/key/'tone.json',objects['edges'])
    d=copy.deepcopy(objects['tone' if stage=='S3' else 'edges']);d['id']=key
    d['massRegions']=objects['masses']['toneRegions']
    d['contourPoints']+=sum(len(r) for x in d['massRegions'] for r in x['rings'])
    if d['contourPoints']>60000:raise ValueError('Combined view budget exceeded')
    d['contentHash']=content_hash(d)
    save_json(CACHE/'renders'/(key+'.json'),d)
    save_json(CACHE/'specs'/(key+'.json'),{'id':key,'weights':weights,'light':light,'stage':stage})
    return {'renderId':key,'contentHash':d['contentHash'],'sourceDigest':d['sourceDigest'],'cached':reused}


def verify(ident,descriptor):
    if descriptor['sourceDigest']!=current_digest(descriptor['stage']):raise ValueError('STALE_RENDER')
    blender=os.getenv('PORTRAIT_BLENDER') or shutil.which('blender')
    if not blender:raise RuntimeError('DEPENDENCY_MISSING: independent validation requires Blender')
    spec=CACHE/'specs'/(ident+'.json')
    if not spec.exists():raise ValueError('Missing frozen render specification; regenerate')
    log=CACHE/'logs'/(ident+'.log');log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w') as out:
        for command in [[blender,'--background','--python-exit-code','1','--python',str(ROOT/'workbench/study_reference.py'),'--',str(spec)],
                        [sys.executable,str(ROOT/'workbench/validate_studies.py'),'--render-id',ident]]:
            subprocess.run(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=600,check=True,env=os.environ.copy())
    (CACHE/'reference').mkdir(parents=True,exist_ok=True)
    shutil.copy2(CACHE/'studies/reference'/(ident+'-shadow.png'),CACHE/'reference'/(ident+'.png'))
    return json.loads((CACHE/'machine'/(ident+'.json')).read_text())
