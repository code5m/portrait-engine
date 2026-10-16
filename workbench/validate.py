"""Actual CSS screenshots and reference metrics. Never produces ART_PASS.
Can validate prepared fixtures or one frozen API render; no submitted scores
or uploaded images can replace the server-produced machine result.
"""
import base64,hashlib,io,json,os,sys,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from model import CONFIG,CACHE,ROOT,source_digest,save_json,canonical,sha

def html(descriptor,mode='tone'):
    code=(ROOT/'workbench/renderer.mjs').read_text().replace('export function','function')
    data=canonical(descriptor).decode().replace('<','\\u003c')
    return '<!doctype html><meta charset="utf-8"><style>body{margin:0}.portrait{width:320px;height:320px;position:relative;background:white;overflow:hidden}.tone-region{position:absolute;inset:0;display:block}</style><div id="portrait" class="portrait"></div><script>'+code+'\ndraw(document.getElementById("portrait"),'+data+','+json.dumps(mode)+');document.body.dataset.ready="1";</script>'

def erode(mask,steps=3):
    m=mask.copy()
    for _ in range(steps):m=m & np.roll(m,1,0)&np.roll(m,-1,0)&np.roll(m,1,1)&np.roll(m,-1,1)
    m[:steps]=False;m[-steps:]=False;m[:,:steps]=False;m[:,-steps:]=False
    return m

def assess(path,reference):
    c=np.asarray(Image.open(path).convert('RGB'),dtype=float).mean(-1)
    ref=np.asarray(Image.open(reference).convert('RGBA'),dtype=float);alpha=ref[...,3]/255
    b=ref[...,:3].mean(-1)*alpha+255*(1-alpha)
    mask=alpha>.5;cmask=c<248;union=np.count_nonzero(mask|cmask)
    inside=erode(mask);err=np.abs(c-b)
    feature=inside.copy();h,w=c.shape;feature[:int(h*.2)]=False;feature[int(h*.8):]=False;feature[:,:int(w*.22)]=False;feature[:,int(w*.78):]=False
    if not inside.any() or not feature.any():raise AssertionError('Blank reference head')
    return {'fullMAE':round(float(err.mean()),5),'interiorMAE':round(float(err[inside].mean()),5),
            'featureMAE':round(float(err[feature].mean()),5),'silhouetteIoU':round(float(np.count_nonzero(mask&cmask)/max(1,union)),6)}

def validate_one(page,ident):
    d=json.loads((CACHE/'renders'/(ident+'.json')).read_text());frozen=d['contentHash'];source=source_digest()
    if d['sourceDigest']!=source:raise AssertionError('Stale descriptor; regenerate')
    out=CACHE/'captures';out.mkdir(parents=True,exist_ok=True)
    errors=[];requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append(r.url) if not r.url.startswith('file:') else None)
    for mode in ['tone','structure']:
        document=out/(ident+'-'+mode+'.html');document.write_text(html(d,mode),encoding='utf8')
        page.goto(document.as_uri());page.wait_for_selector('body[data-ready="1"]')
        target=page.locator('#portrait')
        if target.locator('img,canvas,svg,video,iframe').count():raise AssertionError('Non-CSS painting')
        if target.locator('i').count()>(25 if mode=='tone' else 12):raise AssertionError('DOM budget')
        target.screenshot(path=str(out/(ident+'-'+mode+'.png')))
    if errors or requests:raise AssertionError((errors,requests))
    meta=json.loads((CACHE/'reference'/(ident+'.json')).read_text())
    if meta['geometryHash']!=d['geometry']['geometryHash'] or meta['camera']!=d['camera']:raise AssertionError('Reference/CSS geometry differs')
    if sha((CACHE/'reference'/(ident+'.png')).read_bytes()) != meta['imageHash']:raise AssertionError('Reference image changed after rendering')
    metrics=assess(out/(ident+'-tone.png'),CACHE/'reference'/(ident+'.png'))
    failed=[]
    for key in ['fullMAE','interiorMAE','featureMAE']:
        if metrics[key]>=CONFIG['thresholds'][key]:failed.append(key)
    if metrics['silhouetteIoU']<CONFIG['thresholds']['silhouetteIoU']:failed.append('silhouetteIoU')
    result={'renderId':ident,'contentHash':frozen,'sourceDigest':source,'status':'FAIL' if failed else 'PASS','artStatus':'ART_UNVERIFIED','failures':failed,'metrics':metrics,'geometryHash':d['geometry']['geometryHash'],'nonAffineRMS':d['geometry']['nonAffineRMS'],'contourPoints':d['contourPoints'],'toneRegions':len(d['toneRegions']),'structureRegions':len(d['structureRegions']),
            'browserVersion':page.context.browser.version,'captureHash':sha((out/(ident+'-tone.png')).read_bytes()),'referenceHash':meta['imageHash'],'transport':'file',
            'checkedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    save_json(CACHE/'machine'/(ident+'.json'),result)
    print('S2_MACHINE_SAMPLE',ident,json.dumps(metrics),'FAIL' if failed else 'PASS',flush=True)
    return result

def run(ids):
    with sync_playwright() as p:
        launch={'headless':True,'args':['--no-sandbox']}
        if os.getenv('PORTRAIT_CHROMIUM'):launch['executable_path']=os.environ['PORTRAIT_CHROMIUM']
        b=p.chromium.launch(**launch);results=[]
        for ident in ids:
            page=b.new_page(viewport={'width':640,'height':480},device_scale_factor=1)
            try:results.append(validate_one(page,ident))
            finally:page.close()
        b.close()
    return results

if __name__=='__main__':
    full_run=not sys.argv[1:]
    ids=sys.argv[1:] or [x['id']+'-'+l['id'] for x in CONFIG['identities'] for l in CONFIG['lights']]
    results=run(ids)
    if full_run:
        assert len(ids)==18 and len(set(ids))==18
        assert len({x['geometryHash'] for x in results})==6, 'Identity geometry collided or changed with light'
        assert all(len({x['geometryHash'] for x in results if x['renderId'].startswith(i['id']+'-')})==1 for i in CONFIG['identities'])
        assert all(x['nonAffineRMS']>=CONFIG['thresholds']['minIdentityNonAffineRMS'] for x in results),'Registered identity fixture was only a global affine deformation'
    report={'stage':'S2','status':('STRUCTURE_STUDY_COMPLETE' if full_run else 'SAMPLE_CHECK_COMPLETE') if all(x['status']=='PASS' for x in results) else 'FAILED','artStatus':'ART_UNVERIFIED','humanObservers':0,
            'sourceDigest':source_digest(),'ciRun':os.getenv('GITHUB_RUN_ID'),'ciCommit':os.getenv('GITHUB_SHA'),'sourceHeadCommit':os.getenv('SOURCE_HEAD_SHA'),
            'counts':{'identities':6 if full_run else len({r['geometryHash'] for r in results}),'scenarios':len(ids),'cssFrames':2*len(ids),'referenceFrames':len(ids)},'metrics':results,
            'limitations':['Neutral frontal head surface only, not skull/muscle anatomy','No portrait artistic certification','No full GI, skin, hair or cast-light shadows','Numeric PCA identities, not identified real people']}
    save_json(CACHE/('S2-result.json' if full_run else 'sample-result.json'),report)
    print('S2_COMPLETION_JSON' if full_run else 'SAMPLE_CHECK_JSON',canonical(report).decode(),flush=True)
    if not full_run:raise SystemExit(1 if report['status']=='FAILED' else 0)
    contact=Image.new('RGB',(3*320,6*350),'white');pen=ImageDraw.Draw(contact)
    for i,ident in enumerate(ids):
        with Image.open(CACHE/'captures'/(ident+'-tone.png')) as im:contact.paste(im.convert('RGB'),(i%3*320,i//3*350+26))
        pen.text((i%3*320+8,i//3*350+6),ident,fill='black')
    contact.save(CACHE/'S2-contact.png')
    small=contact.copy();small.thumbnail((480,1050));buf=io.BytesIO();small.save(buf,format='JPEG',quality=65)
    print('S2_PREVIEW_JPEG '+base64.b64encode(buf.getvalue()).decode(),flush=True)
    if report['status']=='FAILED':raise SystemExit(1)
