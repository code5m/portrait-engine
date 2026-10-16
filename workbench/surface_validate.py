"""Real Chromium measurements and negative controls, not an artistic verdict.
Pixel access is confined to this evaluator; the numerical compiler never imports
this module or reads its captures. All predeclared cases, including failures, stay.
"""
from __future__ import annotations
import copy,json,os,re,shutil,sys
import numpy as np
from shapely import union_all,contains_xy
from PIL import Image
from playwright.sync_api import sync_playwright
from model import ROOT,CACHE,CONFIG,HeadModel,canonical,sha,save_json
from study_light import content_hash,source_digest as s3_digest
from study_edges import source_digest as s4_digest
from validate import assess,erode
from validate_studies import capture as capture_base,rgb,ref_rgb,contour_geometry,calibration_check
from surface_registry import S5,S6,source_digest,sample_id,case
from surface_document import document


def read(path):return json.loads(path.read_text())


def capture(page,descriptor,path,mode='tone'):
    path.with_suffix('.html').write_text(document(descriptor,mode),encoding='utf8')
    page.goto(path.with_suffix('.html').as_uri());page.wait_for_selector('body[data-ready="1"]')
    target=page.locator('#portrait')
    assert target.locator('img,svg,canvas,video,iframe,object').count()==0,'Forbidden drawing primitive'
    assert target.locator('*').count()<=S5['thresholds']['maxDOM'],'DOM budget exceeded'
    assert target.evaluate('(el)=>getComputedStyle(el).filter')=='none','Full-face filter'
    assert target.evaluate('(el)=>getComputedStyle(el).clipPath')=='none','Full-face reclip'
    target.screenshot(path=str(path));return sha(path.read_bytes())


def variants(spec):
    return {'alternate-material':{**spec,'material':'charcoal' if spec['material']=='graphite' else 'graphite'},
            'no-hair':{**spec,'hair':'none'},'short-hair':{**spec,'hair':'short'}}


def one(page,ident,out,alternatives=None):
    if not re.fullmatch(r's[56]-[a-f0-9]{24}',ident):raise ValueError('Invalid surface identifier')
    out.mkdir(parents=True,exist_ok=True)
    d=read(CACHE/'renders'/(ident+'.json'));stage=d['stage'];spec=d['surfaceSpec'];key=d['surfaceBaseKey']
    assert d['sourceDigest']==source_digest(stage) and d['contentHash']==content_hash(d),'Stale surface descriptor'
    base=CACHE/'surface/base'/key;d3=read(base/'S3.json');d4=read(base/'S4.json')
    for value,digest in ((d3,s3_digest()),(d4,s4_digest())):
        assert value['sourceDigest']==digest and value['contentHash']==content_hash(value)
        assert value['geometry']==d['geometry'] and value['camera']==d['camera']
    assert d['toneRegions']==d4['toneRegions'] and d['edgeRegions']==d4['edgeRegions'],'Surface changed parent regions'
    reference=CACHE/'studies/reference'/(ident+'-shadow.png');meta=read(reference.with_suffix('.json'))
    assert meta['imageHash']==sha(reference.read_bytes()) and meta['geometryHash']==d['geometry']['geometryHash']
    assert meta['camera']==d['camera'] and meta['surfaceSourceDigest']==source_digest(stage)
    assert meta['identityHash']==d['geometry']['identityHash'] and meta['expression']==spec['expression']
    images={}
    def save_capture(label,descriptor,mode='tone',is_base=False):
        path=out/(ident+'-'+label+'.png')
        images[path.name]=capture_base(page,descriptor,path,mode) if is_base else capture(page,descriptor,path,mode)
        return path
    path3=save_capture('S3',d3,is_base=True);path4=save_capture('S4',d4,is_base=True)
    full=save_capture('surface',d);off=save_capture('material-control',d,'material-control')
    no_hair=save_capture('hair-control',d,'hair-control');repeat=save_capture('repeat',d)
    if alternatives is None:
        from surface_service import render
        model=HeadModel();alternatives={name:render(value,model)['renderId'] for name,value in variants(spec).items()}
    other_paths={}
    for name,render_id in alternatives.items():
        value=read(CACHE/'renders'/(render_id+'.json'))
        assert value['sourceDigest']==source_digest(stage) and value['contentHash']==content_hash(value)
        assert value['geometry']==d['geometry']
        other_paths[name]=save_capture(name,value)
    raw=rgb(full);parent=rgb(path4);control=rgb(off);physical,mask=ref_rgb(reference)
    delta=np.abs(raw-parent).mean(-1);thresholds=S5['thresholds'];fail=[]
    def check(ok,label):
        if not ok:fail.append(label)
    check(np.array_equal(parent,control),'material-off-does-not-restore-S4')
    check(np.array_equal(raw,rgb(repeat)),'nondeterministic-native-CSS')
    check(np.array_equal(rgb(no_hair),rgb(other_paths['no-hair'])),'hair-ablation-does-not-match-real-none-parameter')
    check(float(np.abs(raw-rgb(other_paths['alternate-material'])).max())>1,'material-parameter-no-effect')
    if spec['hair']!='none':check(float(np.abs(raw-rgb(no_hair)).max())>1,'hair-parameter-no-effect')
    if spec['hair']=='swept':check(float(np.abs(raw-rgb(other_paths['short-hair'])).max())>1,'hair-flow-parameter-no-effect')
    yy,xx=np.mgrid[:320,:320];px=(xx+.5)*100/320;py=(yy+.5)*100/320
    zones=union_all([contour_geometry(layer['rings']) for layer in d['surfaceRegions']]).buffer(1.25*100/320)
    allowed=contains_xy(zones,px,py)
    outside=float(delta[~allowed].max()) if (~allowed).any() else 0.
    protected=contour_geometry(d['surface']['protectedRings']).buffer(-100/320)
    protected_mask=contains_xy(protected,px,py)
    protected_delta=float(delta[protected_mask].max()) if protected_mask.any() else 0.
    scalp=contour_geometry(d['surface']['scalpRings']).buffer(100/320)
    skin_mask=erode(mask)&~contains_xy(scalp,px,py)
    added_error=float((np.abs(raw-physical).mean(-1)-np.abs(parent-physical).mean(-1))[skin_mask].mean()) if skin_mask.any() else 0.
    fraction=float(np.count_nonzero((delta>1)&mask)/max(1,mask.sum()))
    changed=int(np.count_nonzero(delta>1))
    check(outside<=thresholds['maxOutsideMaskDelta'],'changed-unselected-region')
    check(protected_delta<=thresholds['maxProtectedDelta'],'changed-protected-eyes-or-mouth')
    check(fraction<=thresholds['maxChangedFaceFraction'],'surface-overwhelms-form')
    check(added_error<=thresholds['maxAddedSkinError'],'surface-added-skin-error')
    check(changed>=thresholds['minChangedPixels'],'surface-is-a-noop')
    m3=assess(path3,reference);m4=assess(path4,reference);m5=assess(full,reference);t=S6['thresholds']
    for metric,key_name in [('fullMAE','referenceFullMAE'),('interiorMAE','referenceInteriorMAE'),('featureMAE','referenceFeatureMAE')]:
        check(m3[metric]<t[key_name],'base-reference-'+metric)
    check(m3['silhouetteIoU']>=t['referenceSilhouetteIoU'],'base-silhouette-drift')
    edge_fraction=float(np.count_nonzero((np.abs(rgb(path4)-rgb(path3)).mean(-1)>1)&mask)/max(1,mask.sum()))
    p4=read(ROOT/'research/sketch/s4-protocol.json')
    check(edge_fraction<=p4['maxInkFraction'],'parent-edge-ink-budget')
    check(m4['interiorMAE']<=m3['interiorMAE']+p4['maxAddedInteriorError'],'parent-edge-error-budget')
    signature=d['geometry']
    check(signature['nonAffineRMS']>t['minimumIdentityNonAffineRMS'],'identity-degenerated-to-affine-template')
    check(signature['maxExpressionDisplacementSpan']<=t['maxExpressionDisplacementSpan'],'unbounded-expression-displacement')
    if spec['expression']!='neutral':check(signature['expressionRMS']>=t['minimumExpressionRMS'],'expression-has-no-geometry-effect')
    else:check(signature['expressionRMS']==0,'neutral-expression-drift')
    for suffix in ('png','json'):
        dest=out/(ident+'-reference.'+suffix);shutil.copy2(reference.with_suffix('.'+suffix),dest)
        if suffix=='png':images[dest.name]=sha(dest.read_bytes())
    row={'id':sample_id(spec),'renderId':ident,'stage':stage,'identity':spec['identity'],'expression':spec['expression'],
         'light':spec['lightId'],'status':'FAIL' if fail else 'PASS','failures':fail,'metrics':m3,
         'metricsMeaning':'independent base-form/lighting error; not hair or artistic quality',
         'surfaceVsUntexturedReference':m5,'surfaceAddedSkinMAE':round(added_error,6),
         'protectedMaxDelta':round(protected_delta,6),'outsideMaskMaxDelta':round(outside,6),
         'changedFaceFraction':round(fraction,6),'changedPixels':changed,'parentEdgeInkFraction':round(edge_fraction,6),
         'geometryHash':signature['geometryHash'],'identityHash':signature['identityHash'],
         'nonAffineRMS':signature['nonAffineRMS'],'expressionRMS':signature['expressionRMS'],
         'maxExpressionDisplacementSpan':signature['maxExpressionDisplacementSpan'],
         'surfaceContourPoints':d['surfaceContourPoints'],'layerCount':len(d['surfaceRegions']),
         'contentHash':d['contentHash'],'sourceDigest':d['sourceDigest'],'imageHashes':images,
         'humanObservers':0,'artStatus':'ART_UNVERIFIED','humanReview':'DEFERRED_BY_OWNER'}
    save_json(CACHE/'machine'/(ident+'.json'),row)
    print('SURFACE_MEASURED '+canonical({k:row[k] for k in ('id','status','failures','protectedMaxDelta','outsideMaskMaxDelta','changedFaceFraction','surfaceAddedSkinMAE')}).decode(),flush=True)
    return row


def run_case(case_id):
    c=case(case_id);folder=CACHE/'surface/evidence'/case_id;folder.mkdir(parents=True,exist_ok=True)
    index=read(CACHE/'surface/cases'/case_id/'index.json');rows=[];errors=[];requests=[];calibration=calibration_check()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':640,'height':480},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append(r.url) if not r.url.startswith('file:') else None)
        for ident in index['renderIds']:
            try:rows.append(one(page,ident,folder,index['alternatives'][ident]))
            except Exception as exc:
                errors.append(type(exc).__name__+': '+str(exc));print('SURFACE_CAPTURE_ERROR',ident,errors[-1],flush=True)
        version=browser.version;browser.close()
    report={'schemaVersion':1,'stage':c['stage'],'caseId':case_id,'status':'PASS' if len(rows)==3 and all(r['status']=='PASS' for r in rows) and not errors and not requests else 'FAIL',
            'sourceDigest':source_digest(c['stage']),'ciRun':os.getenv('GITHUB_RUN_ID'),'ciCommit':os.getenv('GITHUB_SHA'),
            'sourceHeadCommit':os.getenv('SOURCE_HEAD_SHA'),'metrics':rows,'errors':errors,'externalRequests':requests,
            'browserVersion':version,'calibrationMAE':calibration,'humanObservers':0,'artStatus':'ART_UNVERIFIED','humanReview':'DEFERRED_BY_OWNER'}
    save_json(folder/'report.json',report)
    for cosine in (.25,.65,1.0):shutil.copy2(CACHE/'studies/reference'/f'calibration-{cosine}.png',folder/f'calibration-{cosine}.png')
    print('SURFACE_CASE '+canonical(report).decode(),flush=True)
    if report['status']!='PASS':raise SystemExit(1)


def run_sample(ident):
    calibration_check();out=CACHE/'surface/evidence/api'/ident;errors=[];requests=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':640,'height':480})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append(r.url) if not r.url.startswith('file:') else None)
        result=one(page,ident,out);browser.close()
    if errors or requests or result['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':
    if sys.argv[1:2]==['--render-id']:run_sample(sys.argv[2])
    elif len(sys.argv)==2:run_case(sys.argv[1])
    else:raise SystemExit('Usage: surface_validate.py CASE | --render-id RENDER_ID')
