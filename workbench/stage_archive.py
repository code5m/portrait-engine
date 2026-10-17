"""Read-only, source-bound S0-S6 research results and allowlisted image evidence.
Stage reviews are separate from machine results and cannot certify ART_PASS.
"""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from model import ROOT

EVIDENCE=ROOT/'research/sketch/evidence'
VALID_STAGES=frozenset('S'+str(i) for i in range(7))
LIGHTS=('left','front','right')
DIMENSIONS=('structure','volume','eyes','identity','realism')
ARCHIVES={
    'S3':'raw/38866567327',
    'S4':'raw/38866567327',
    'S5':'raw-surface/38912892498',
    'S6':'raw-surface/38912892498'
}
SURFACE_KINDS=(
    ('surface.png','候选素描'),('reference.png','独立参考'),
    ('S4.png','S4 结构对照'),('no-hair.png','去除头发'),
    ('short-hair.png','短发对照'),('alternate-material.png','材料对照')
)

def valid_stage(stage):
    if stage not in VALID_STAGES:raise ValueError('Invalid research stage')
    return stage

def evidence(stage):
    stage=valid_stage(stage)
    path=EVIDENCE/(stage+'.json')
    binary=path.read_bytes()
    data=json.loads(binary)
    if data.get('stage')!=stage:raise ValueError('Stage evidence mismatch')
    return data,hashlib.sha256(binary).hexdigest()

def manifest(stage):
    if stage not in ARCHIVES:return {}
    return json.loads((EVIDENCE/ARCHIVES[stage]/'manifest.json').read_text(encoding='utf8'))['files']

def public_image(stage,relative,expected_hash,index):
    entry=index.get(relative)
    if not entry or not re.fullmatch(r'[a-f0-9]{64}',expected_hash or '') or entry.get('sha256')!=expected_hash:
        return None
    path=ROOT/relative
    if path.suffix!='.png' or not path.resolve().is_relative_to(EVIDENCE.resolve()) or not path.is_file():
        return None
    return {'label':'','sha256':expected_hash,'path':relative}

def image_choices(stage,row,index):
    if stage not in ARCHIVES:return []
    ident=row.get('id') or row.get('renderId') or row.get('scene')
    images=[]
    if stage in ('S3','S4'):
        if not isinstance(ident,str) or not re.fullmatch(r'(head-[abc]|reserved-[def])-(left|front|right)',ident):return []
        group=ident.rsplit('-',1)[0]
        base='research/sketch/evidence/'+ARCHIVES[stage]+'/assets/'+group
        variants=[('images/'+ident+'-'+stage+'.png','候选素描'),
                  ('reference/'+ident+'-shadow.png','独立参考')]
        if stage=='S4':variants.extend([('images/'+ident+'-S3.png','S3 对照'),('images/'+ident+'-all-edges.png','全硬边对照')])
        else:variants.append(('images/'+ident+'-masses.png','三大灰阶'))
        for suffix,label in variants:
            rel=base+'/'+suffix
            item=index.get(rel)
            if item:
                img=public_image(stage,rel,item.get('sha256'),index)
                if img:img['label']=label;images.append(img)
    else:
        if not isinstance(ident,str) or '-' not in ident:return []
        group=ident.rsplit('-',1)[0]
        base='research/sketch/evidence/'+ARCHIVES[stage]+'/'+group+'/'
        hashes=row.get('imageHashes') or {}
        for suffix,label in SURFACE_KINDS:
            names=[name for name in hashes if name.endswith('-'+suffix)]
            if len(names)!=1:continue
            name=names[0]
            img=public_image(stage,base+name,hashes[name],index)
            if img:img['label']=label;images.append(img)
    for n,img in enumerate(images):
        img['url']='/api/v1/stage-results/'+stage+'/images/'+str(ident)+'/'+str(n)
    return images

def stage_result(stage,include_scenes=True):
    stages=json.loads((ROOT/'research/sketch/stages.json').read_text(encoding='utf8'))
    registered=next((s for s in stages['stages'] if s['id']==valid_stage(stage)),None)
    if not registered:raise ValueError('Unregistered research stage')
    ev,revision=evidence(stage)
    rows=ev.get('metrics',[])
    completed=sum(1 for r in rows if r.get('status','PASS')=='PASS')
    # Some old experiments recorded calibration measurements, not per-scene PASS.
    scene_count=ev.get('counts',{}).get('scenes') or ev.get('counts',{}).get('scenarios') or len(rows)
    has_images=stage in ARCHIVES
    result={
        'id':stage,'title':registered['title'],'status':registered['status'],
        'experimentStatus':ev.get('status'),'artStatus':'ART_UNVERIFIED',
        'humanObservers':ev.get('humanObservers',0),'revision':revision,
        'sourceDigest':ev.get('sourceDigest'),'ciRun':ev.get('ciRun'),
        'ciCommit':ev.get('ciCommit'),'count':len(rows),'sceneCount':scene_count,
        'measuredPassCount':completed,'imagesArchived':has_images,
        'imageAvailability':'已入库的原始 PNG 可查看' if has_images else '该阶段没有完整可检索的原始 PNG；不以截图替代',
        'reportUrl':'https://github.com/code5m/portrait-engine/blob/main/'+registered['report'],
        'ciUrl':'https://github.com/code5m/portrait-engine/actions/runs/'+str(ev['ciRun']) if ev.get('ciRun') else None,
        'limitations':ev.get('limitations') or ev.get('limits') or [],
    }
    if include_scenes:
        index=manifest(stage)
        scenes=[]
        for row in rows:
            ident=row.get('id') or row.get('renderId') or row.get('scene')
            if not isinstance(ident,str):continue
            metrics=row.get('metrics') or {k:v for k,v in row.items() if isinstance(v,(int,float)) and not isinstance(v,bool) and (k.endswith('MAE') or k.endswith('IoU'))}
            scenes.append({'id':ident,'status':row.get('status','MEASURED'),'metrics':metrics,
                           'images':image_choices(stage,row,index)})
        result['scenes']=scenes
        result['archivedImageCount']=sum(len(row['images']) for row in scenes)
    return result

def image_data(stage,scene_id,image_index):
    if not isinstance(scene_id,str) or len(scene_id)>100 or not re.fullmatch('[A-Za-z0-9-]+',scene_id):
        raise ValueError('Invalid scene')
    if not isinstance(image_index,str) or not re.fullmatch('[0-9]{1,2}',image_index):
        raise ValueError('Invalid image index')
    found=next((x for x in stage_result(stage)['scenes'] if x['id']==scene_id),None)
    if not found:raise FileNotFoundError('Scene not found')
    index=int(image_index)
    if index>=len(found['images']):raise FileNotFoundError('Image not found')
    info=found['images'][index]
    data=(ROOT/info['path']).read_bytes()
    if hashlib.sha256(data).hexdigest()!=info['sha256']:
        raise ValueError('ARCHIVE_INTEGRITY_FAILED: image SHA-256 mismatch')
    return data

def validate_stage_review(data):
    allowed={'stage','sceneId','revision','verdict','scores','note','humanConfirmed'}
    if set(data)-allowed:raise ValueError('Unknown stage review field')
    stage=valid_stage(data.get('stage'))
    info=stage_result(stage)
    if data.get('revision')!=info['revision']:raise ValueError('STALE_REVIEW: stage evidence has changed')
    if data.get('sceneId') not in {s['id'] for s in info['scenes']}:
        raise ValueError('Choose a measured scene')
    if data.get('humanConfirmed') is not True:raise ValueError('Human observation confirmation required')
    if data.get('verdict') not in ('accept','revise','reject'):raise ValueError('Invalid review verdict')
    scores=data.get('scores')
    if not isinstance(scores,dict) or set(scores)!=set(DIMENSIONS) or any(type(v) is not int or not 1<=v<=5 for v in scores.values()):
        raise ValueError('All five artistic scores must be integers 1..5')
    if not isinstance(data.get('note',''),str) or len(data['note'])>2000:
        raise ValueError('Note must be at most 2000 characters')
    return {**data,'sourceDigest':info['sourceDigest'],'artStatus':'ART_UNVERIFIED',
            'observerIndependence':'NOT_VERIFIED','humanReview':'OWNER_SELF_REPORTED'}
