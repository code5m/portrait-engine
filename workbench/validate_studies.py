"""Actual CSS / independently ray-lit Blender / bounded edge experiments.
Every predeclared identity is retained, including failures. No ART_PASS.
"""
from __future__ import annotations
import base64,io,json,os,sys,time
import numpy as np
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from shapely.geometry import Polygon,GeometryCollection
from shapely import union_all,contains_xy,make_valid,symmetric_difference
from model import ROOT,CACHE,CONFIG,canonical,sha,save_json
from validate import assess,erode
from study_light import source_digest as s3_digest,protocol,srgb,content_hash,area_geometry
from study_edges import source_digest as s4_digest


def document(d,mode='tone',edge='selected'):
    base=(ROOT/'workbench/renderer.mjs').read_text().replace('export function','function')
    painter=(ROOT/'workbench/study_renderer.mjs').read_text()
    painter=painter.replace("import {draw as drawBase, clipPath} from './renderer.mjs';",'const {draw:drawBase,clipPath}=Base;').replace('export function','function')
    data=canonical(d).decode().replace('<','\\u003c')
    return '<!doctype html><meta charset="utf-8"><style>body{margin:0}.portrait{position:relative;width:320px;height:320px;background:white;overflow:hidden}.tone-region{position:absolute;inset:0;display:block}</style><div id="portrait" class="portrait"></div><script>const Base=(()=>{'+base+';return {draw,clipPath};})();'+painter+'\ndraw(document.getElementById("portrait"),'+data+','+json.dumps(mode)+','+json.dumps(edge)+');document.body.dataset.ready="1";</script>'


def rgb(path):return np.asarray(Image.open(path).convert('RGB'),dtype=float)
def ref_rgb(path):
    a=np.asarray(Image.open(path).convert('RGBA'),dtype=float);alpha=a[...,3:]/255
    return a[...,:3]*alpha+255*(1-alpha),a[...,3]>.5*255


def contour_geometry(rings):
    """Decode CSS even-odd area, including self-crossings after serialization.

    GEOS polygon validity is stricter than CSS polygon(evenodd). Linework
    repair keeps both bow-tie lobes; XOR retains holes and cancels duplicates.
    The 1e-7 percentage grid is far below a pixel, not a new error allowance.
    """
    grid=1e-7;g=Polygon()
    for ring in rings:
        if len(ring)>=3:
            area=area_geometry(make_valid(Polygon(ring)),grid)
            g=area_geometry(symmetric_difference(g,area,grid_size=grid),grid)
    return g


def capture(page,d,path,mode='tone',edge='selected'):
    html=path.with_suffix('.html');html.write_text(document(d,mode,edge),encoding='utf8')
    page.goto(html.as_uri());page.wait_for_selector('body[data-ready="1"]')
    target=page.locator('#portrait')
    assert target.locator('img,canvas,svg,video,iframe,object').count()==0
    assert target.locator('*').count()<=40,'Unbounded DOM complexity'
    assert target.evaluate('(el)=>getComputedStyle(el).filter')=='none','Full face filtering forbidden'
    assert target.evaluate('(el)=>getComputedStyle(el).clipPath')=='none','S4 must not reclip the entire S3 face'
    if d['stage']=='S4' and edge=='selected' and mode=='tone':
        assert target.locator('.edge-ribbon').count()==2
    target.screenshot(path=str(path));return sha(path.read_bytes())


def one(page,ident,d3,d4):
    out=CACHE/'studies/captures';out.mkdir(parents=True,exist_ok=True)
    refpath=CACHE/'studies/reference'/(ident+'-shadow.png')
    noreference=CACHE/'studies/reference'/(ident+'-unshadowed.png')
    meta=json.loads(refpath.with_suffix('.json').read_text())
    assert meta['sourceDigest']==s3_digest() and meta['imageHash']==sha(refpath.read_bytes())
    assert meta['geometryHash']==d3['geometry']['geometryHash'] and meta['camera']==d3['camera']
    assert d3['sourceDigest']==s3_digest() and d4['sourceDigest']==s4_digest()
    assert d3['contentHash']==content_hash(d3) and d4['contentHash']==content_hash(d4),'Descriptor hash drift'
    unshadowed_meta=json.loads(noreference.with_suffix('.json').read_text())
    assert unshadowed_meta['sourceDigest']==s3_digest() and unshadowed_meta['geometryHash']==d3['geometry']['geometryHash']
    assert unshadowed_meta['imageHash']==sha(noreference.read_bytes())
    base=CACHE/'studies/S3'/ident
    control=json.loads((base/'control.json').read_text());masses=json.loads((base/'masses.json').read_text())
    for data in [control,masses]:
        assert data['sourceDigest']==s3_digest() and data['contentHash']==content_hash(data)
        assert data['geometry']==d3['geometry'] and data['camera']==d3['camera']
    assert len(masses['toneRegions'])==3
    outputs={}
    for label,d,mode,edge in [('control',control,'tone','none'),('S3',d3,'tone','none'),('masses',masses,'tone','none'),
                              ('structure',d3,'structure','none'),('all-edges',d4,'tone','all'),('S4',d4,'tone','selected')]:
        path=out/(ident+'-'+label+'.png');outputs[label]=capture(page,d,path,mode,edge)
    css=rgb(out/(ident+'-S3.png'));control_pixels=rgb(out/(ident+'-control.png'))
    physical,mask=ref_rgb(refpath);noshadow,_=ref_rgb(noreference)
    m=assess(out/(ident+'-S3.png'),refpath);control_metrics=assess(out/(ident+'-control.png'),refpath)
    control_fidelity=assess(out/(ident+'-control.png'),noreference)
    shadow_roi=erode(mask)&(np.abs(noshadow.mean(-1)-physical.mean(-1))>10)
    t=protocol()['thresholds'];fail3=[]
    for k in ['fullMAE','interiorMAE','featureMAE']:
        if m[k]>=t[k]:fail3.append(k)
    if m['silhouetteIoU']<t['silhouetteIoU']:fail3.append('silhouetteIoU')
    if control_fidelity['interiorMAE']>=t['interiorMAE']:fail3.append('unshadowed-reference-calibration')
    shadow_error=float(np.abs(css-physical)[shadow_roi].mean()) if shadow_roi.any() else 0
    control_error=float(np.abs(control_pixels-physical)[shadow_roi].mean()) if shadow_roi.any() else 0
    if shadow_roi.sum()>=20 and shadow_error>control_error*protocol()['shadowErrorRatio']:
        fail3.append('shadow-local-improvement')
    row3={'id':ident,'geometryHash':d3['geometry']['geometryHash'],'metrics':m,'controlMetrics':control_metrics,
          'unshadowedFidelity':control_fidelity,'shadowPixels':int(shadow_roi.sum()),
          'shadowError':round(shadow_error,5),'controlShadowError':round(control_error,5),
          'toneRegions':len(d3['toneRegions']),'contourPoints':d3['contourPoints'],
          'status':'FAIL' if fail3 else 'PASS','failures':fail3,'captureHash':outputs['S3'],'referenceHash':meta['imageHash']}
    selected=rgb(out/(ident+'-S4.png'));all_edges=rgb(out/(ident+'-all-edges.png'))
    zones=union_all([contour_geometry(x['rings']).buffer((3*x['blurPixels']+1)*100/320) for x in d4['edgeRegions']])
    yy,xx=np.mgrid[:320,:320];allowed=contains_xy(zones,(xx+.5)*100/320,(yy+.5)*100/320)
    delta=np.abs(selected-css).mean(-1);ink=delta>1
    outside=float(delta[~allowed].max()) if (~allowed).any() else 0
    settings=json.loads((ROOT/'research/sketch/s4-protocol.json').read_text());fail4=[]
    m4=assess(out/(ident+'-S4.png'),refpath)
    ink_fraction=float(np.count_nonzero(ink&mask)/max(1,mask.sum()))
    if outside>settings['outsideEdgePixelTolerance']:fail4.append('changed-unselected-face-area')
    if ink_fraction>settings['maxInkFraction']:fail4.append('edge-ink-overwhelms-face')
    if m4['interiorMAE']>m['interiorMAE']+settings['maxAddedInteriorError']:fail4.append('edge-error-budget')
    if m4['silhouetteIoU']<settings['silhouetteIoU']:fail4.append('silhouette-drift')
    if d4['edgeClassification']['counts']['lost']<=0:fail4.append('no-edge-selection')
    if np.max(np.abs(selected-all_edges))<1:fail4.append('candidate-is-all-outlines')
    row4={'id':ident,'geometryHash':d4['geometry']['geometryHash'],'metrics':m4,'parentInteriorMAE':m['interiorMAE'],
          'inkFraction':round(ink_fraction,6),'outsideAllowedChange':round(outside,6),
          'classification':d4['edgeClassification']['counts'],'edgePoints':d4['edgeContourPoints'],
          'status':'FAIL' if fail4 else 'PASS','failures':fail4,'captureHash':outputs['S4'],'controlHash':outputs['all-edges']}
    return row3,row4


def calibration_check():
    calibration=[]
    for cosine in [.25,.65,1.0]:
        image=rgb(CACHE/'studies/reference'/('calibration-'+str(cosine)+'.png'))
        expected=255*float(srgb(CONFIG['ambient']+protocol()['fillStrength']/2+CONFIG['direct']*cosine))
        error=float(np.abs(image[80:240,80:240]-expected).mean());calibration.append(round(error,5))
        assert error<2.0,('Independent Cycles radiometry differs from declared Lambertian model',cosine,error)
    return calibration


def sample(ident):
    import re
    if not re.fullmatch('[a-z0-9-]{1,80}',ident):raise ValueError('Bad frozen sample id')
    calibration_check()
    d=json.loads((CACHE/'renders'/(ident+'.json')).read_text())
    d3=json.loads((CACHE/'studies/S3'/ident/'tone.json').read_text())
    d4=json.loads((CACHE/'studies/S4'/ident/'tone.json').read_text())
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':640,'height':480})
        errors=[];requests=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append(r.url) if not r.url.startswith('file:') else None)
        a,b=one(page,ident,d3,d4);browser.close()
    assert not errors and not requests
    row=a if d['stage']=='S3' else b
    if d['stage']=='S4' and a['status']!='PASS':
        row['status']='FAIL';row['failures'].append('parent-S3-failed')
    result={**row,'renderId':ident,'contentHash':d['contentHash'],'sourceDigest':d['sourceDigest'],
            'stage':d['stage'],'artStatus':'ART_UNVERIFIED','transport':'file',
            'referenceHash':sha((CACHE/'studies/reference'/(ident+'-shadow.png')).read_bytes())}
    save_json(CACHE/'machine'/(ident+'.json'),result)
    print('ADVANCED_SAMPLE_CHECK '+canonical(result).decode(),flush=True)
    if result['status']!='PASS':raise SystemExit(1)


def main():
    split=sys.argv[1] if len(sys.argv)>1 else 'all'
    cases=[x['id']+'-'+l['id'] for x in CONFIG['identities'] if split=='all' or x['split']==split for l in CONFIG['lights']]
    calibration=calibration_check()
    rows3=[];rows4=[];errors=[];requests=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':640,'height':480},device_scale_factor=1,reduced_motion='reduce')
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append(r.url) if not r.url.startswith('file:') else None)
        for ident in cases:
            d3=json.loads((CACHE/'studies/S3'/ident/'tone.json').read_text())
            d4=json.loads((CACHE/'studies/S4'/ident/'tone.json').read_text())
            a,b=one(page,ident,d3,d4);rows3.append(a);rows4.append(b)
            print('S3_S4_MEASURED',ident,json.dumps(a['metrics']),a['status'],b['status'],flush=True)
        version=browser.version;browser.close()
    assert not errors and not requests,(errors,requests)
    assert len(set(x['id'] for x in rows3))==len(cases)
    assert sum(r['shadowPixels']>=20 for r in rows3)>=len(cases)//3,'No meaningful shadow evidence'
    for stage,rows,digest in [('S3',rows3,s3_digest()),('S4',rows4,s4_digest())]:
        report={'schemaVersion':1,'stage':stage,'split':split,'status':'PASS' if all(x['status']=='PASS' for x in rows) else 'FAIL',
                'sourceDigest':digest,'ciRun':os.getenv('GITHUB_RUN_ID'),'ciCommit':os.getenv('GITHUB_SHA'),
                'sourceHeadCommit':os.getenv('SOURCE_HEAD_SHA'),'artStatus':'ART_UNVERIFIED','humanObservers':0,
                'counts':{'identities':len(cases)//3,'scenes':len(cases),'cssFrames':len(cases)*(4 if stage=='S3' else 2)},
                'browserVersion':version,'transport':'file','calibrationMAE':calibration,'metrics':rows,
                'limits':['Same fixed frontal neutral heads; no natural expression study','No skin or hair','Independent humans have not evaluated artistic success']}
        save_json(CACHE/'studies'/(stage+'-'+split+'-result.json'),report)
        print(stage+'_SPLIT_JSON '+canonical(report).decode(),flush=True)
    ids=[x for x in cases if x.endswith('-left')]
    sheet=Image.new('RGB',(4*320,len(ids)*348),'white');pen=ImageDraw.Draw(sheet)
    for i,ident in enumerate(ids):
        for j,label in enumerate(['control','S3','all-edges','S4']):
            sheet.paste(Image.open(CACHE/'studies/captures'/(ident+'-'+label+'.png')).convert('RGB'),(j*320,i*348+28))
            pen.text((j*320+8,i*348+8),ident+' / '+label,fill='black')
    sheet.save(CACHE/'studies'/('comparison-'+split+'.png'))
    onehead=Image.open(CACHE/'studies/captures'/(ids[0]+'-S4.png')).convert('RGB');onehead.thumbnail((160,160))
    buf=io.BytesIO();onehead.save(buf,format='JPEG',quality=60,optimize=True)
    print('S4_SINGLE_PREVIEW '+base64.b64encode(buf.getvalue()).decode(),flush=True)
    assert all(x['status']=='PASS' for x in rows3+rows4),'One or more predeclared stage checks failed'
if __name__=='__main__':
    if sys.argv[1:2]==['--render-id']:sample(sys.argv[2])
    elif sys.argv[1:2]==['--calibration-only']:print('S3_RADIOMETRY',calibration_check())
    else:main()
