"""Explicit S5/S6 inputs and provenance. No file paths or commands from clients."""
from __future__ import annotations
import hashlib,json,math
from model import ROOT,CONFIG,canonical

S5=json.loads((ROOT/'research/sketch/s5-protocol.json').read_text())
S6=json.loads((ROOT/'research/sketch/s6-protocol.json').read_text())
STAGES=('S5','S6')
SOURCE_FILES=(
 'research/sketch/s5-protocol.json','research/sketch/s6-protocol.json',
 'workbench/surface-sources.lock.json','workbench/surface_registry.py',
 'workbench/surface_model.py','workbench/surface.py','workbench/surface_service.py',
 'workbench/surface_renderer.mjs','workbench/pipeline_renderer.mjs',
 'workbench/surface_document.py','workbench/surface_reference.py',
 'workbench/surface_validate.py','workbench/run_surface_matrix.py',
 'workbench/test_surface.py','workbench/test_surface_ui.py',
 'workbench/archive_surface.py','workbench/server.py','workbench/app.mjs')


def source_digest(stage):
    if stage not in STAGES:raise ValueError('Unknown surface stage')
    names=set(SOURCE_FILES)
    for name in ('s3-sources.json','s4-sources.json'):
        names.update(json.loads((ROOT/'research/sketch'/name).read_text()))
    h=hashlib.sha256((stage+'\0').encode())
    for name in sorted(names):h.update(name.encode()+b'\0'+(ROOT/name).read_bytes()+b'\0')
    return h.hexdigest()


def geometry_source_digest():
    from study_light import source_digest as light_digest
    from study_edges import source_digest as edge_digest
    h=hashlib.sha256((light_digest()+edge_digest()).encode())
    for name in ('workbench/surface_model.py','workbench/surface_registry.py','workbench/surface-sources.lock.json',
                 'research/sketch/s2-protocol.json','research/sketch/s6-protocol.json'):
        h.update(name.encode()+b'\0'+(ROOT/name).read_bytes()+b'\0')
    return h.hexdigest()


def catalog():
    return {'identities':S6['identities'],'expressions':list(S6['expressions']),
            'materials':list(S5['materials']),'hairstyles':S5['hairstyles'],
            'humanReview':'DEFERRED_BY_OWNER','artStatus':'ART_UNVERIFIED',
            'scope':'Shared-topology new PCA modes and expression poses, not unseen real-person recognition'}


def validate_payload(data):
    if not isinstance(data,dict) or set(data)-{'stage','identity','weights','expression','light','material','hair'}:
        raise ValueError('Unknown surface render field')
    stage=data.get('stage')
    if stage not in STAGES:raise ValueError('Choose S5 or S6')
    material=data.get('material','graphite');hair=data.get('hair','swept')
    if material not in S5['materials'] or hair not in S5['hairstyles']:raise ValueError('Unknown material or hairstyle')
    expression=data.get('expression','neutral')
    if expression not in S6['expressions'] or (stage=='S5' and expression!='neutral'):
        raise ValueError('Expression is not registered for this stage')
    identities=CONFIG['identities'] if stage=='S5' else S6['identities']
    by_id={i['id']:i for i in identities}
    if 'weights' in data:
        if stage!='S5' or 'identity' in data:raise ValueError('Custom coefficients belong to S5 only and cannot also name an identity')
        weights=data['weights'];identity='custom';extra=[0.,0.,0.]
    else:
        identity=data.get('identity')
        if identity not in by_id:raise ValueError('Unknown identity for this stage')
        item=by_id[identity];weights=item['weights'];extra=item.get('extraWeights',[0.,0.,0.])
    if not isinstance(weights,list) or len(weights)!=6 or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>1.5 for x in weights):
        raise ValueError('Six finite coefficients in [-1.5,1.5] required')
    light_id=data.get('light','left');lights={l['id']:l['direction'] for l in CONFIG['lights']}
    if light_id not in lights:raise ValueError('Unknown light')
    return {'stage':stage,'identity':identity,'weights':list(weights),'extraWeights':list(extra),
            'expression':expression,'lightId':light_id,'light':lights[light_id],
            'material':material,'hair':hair}


def cases(stage):
    if stage not in STAGES:raise ValueError('Unknown stage')
    identities=CONFIG['identities'] if stage=='S5' else S6['identities']
    expressions=['neutral'] if stage=='S5' else list(S6['expressions'])
    return [{'id':i['id']+'-'+e,'stage':stage,'identity':i['id'],'expression':e}
            for i in identities for e in expressions]


def case(case_id):
    matches=[c for s in STAGES for c in cases(s) if c['id']==case_id]
    if len(matches)!=1:raise ValueError('Unknown registered surface case')
    return matches[0]


def case_specs(case_id):
    c=case(case_id)
    return [validate_payload({'stage':c['stage'],'identity':c['identity'],'expression':c['expression'],'light':l['id']}) for l in CONFIG['lights']]


def geometry_spec(spec):
    return {k:spec[k] for k in ('weights','extraWeights','expression')}


def sample_id(spec):return spec['identity']+'-'+spec['expression']+'-'+spec['lightId']
