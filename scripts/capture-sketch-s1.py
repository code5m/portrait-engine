"""Real browser captures and independent A/B/C evaluation.
S1_INLINE=1 is sandbox debugging only. CI completion requires file navigation.
"""
import hashlib,json,os,time
import numpy as np
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from sketch_s1_model import CONFIG,ROOT,all_cases,field,shadow_mask,image_metrics,overlap
from sketch_s1_provenance import source_digest
OUT=ROOT/'test-results/sketch-s1'

def load(path):return np.asarray(Image.open(path).convert('RGB'),dtype=float).mean(-1)

def main():
    rows=[];errors=[];requests=[];inline=os.getenv('S1_INLINE')=='1';source=source_digest()
    with sync_playwright() as p:
        launch={'headless':True}
        if os.getenv('S1_CHROMIUM'):launch['executable_path']=os.environ['S1_CHROMIUM']
        browser=p.chromium.launch(**launch);page=browser.new_page(viewport={'width':1100,'height':850},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append(r.url) if not r.url.startswith('file:') else None)
        if inline:page.set_content((OUT/'lab.html').read_text())
        else:page.goto((OUT/'lab.html').as_uri())
        page.wait_for_function('document.documentElement.dataset.ready === "true"')
        assert page.locator('meta[name=source-digest]').get_attribute('content')==source,'Rebuild stale offline page'
        capture_style=page.add_style_tag(content='main{margin:0;padding:0}header,.notes,footer{display:none}.controls{position:absolute;top:300px;left:0}.viewport-frame{padding:0;border:0}.work{gap:0}')
        for case in all_cases():
            ident,s,l=case['id'],case['shape'],case['light']
            variants=['flat16','gradient16','flat32'] if s['kind']=='ellipsoid' else ['flat32']
            modes=[(v,False,'form') for v in variants]+[('flat32',True,'form'),('flat32',False,'shadow'),('flat32',True,'composite')]
            for variant,bounce,layer in modes:
                stat=page.evaluate('(a)=>S1.show(...a)',[ident,variant,bounce,layer])
                assert stat['patchCount']<=CONFIG['protocol']['regionBudget']
                assert page.locator('#viewport img,#viewport svg,#viewport canvas,#viewport video').count()==0
                filename=f'{ident}--{variant}--{int(bounce)}--{layer}.png';path=OUT/filename
                t=time.perf_counter();page.locator('#viewport').screenshot(path=str(path));stat['screenshotMs']=round((time.perf_counter()-t)*1000,4)
                stat.update(file=filename,split=s['split'],kind=s['kind'],sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                actual=load(path)
                if layer=='form':
                    expected,mask,_=field(s,l,bounce);stat.update(image_metrics(actual,expected,mask))
                elif layer=='shadow':
                    geo=page.evaluate('(a)=>S1.shadowGeometry(a[0],a[1],S1.config)',[s,l['direction']])
                    expected=shadow_mask(s,l,geo['offset']);stat.update(overlap(actual<128,expected));stat['ground']=geo
                rows.append(stat)
        page.select_option('#scene-select','sphere-left');page.select_option('#variant','flat16');page.select_option('#layer','form');page.uncheck('#bounce')
        assert page.locator('#viewport .form>i').count()==16
        repeat=page.locator('#viewport').screenshot()
        original=next(r for r in rows if r['scene']=='sphere-left' and r['variant']=='flat16' and r['layer']=='form' and not r['bounce'])
        assert hashlib.sha256(repeat).hexdigest()==original['sha256'],'nondeterministic rendering'
        page.select_option('#variant','flat32');page.check('#bounce');page.select_option('#layer','composite')
        assert page.locator('#viewport .cast-shadow').count()==1
        capture_style.evaluate('(el)=>el.remove()')
        page.screenshot(path=str(OUT/'workbench.png'),full_page=True)
        browser_version=browser.version;browser.close()
    assert not errors and not requests,(errors,requests)
    assert source==source_digest(),'Source changed during capture'
    report={'sourceDigest':source,'offlinePageSha256':hashlib.sha256((OUT/'lab.html').read_bytes()).hexdigest(),'transport':'inline-debug' if inline else 'file','browser':browser_version,'browserErrors':errors,'externalRequests':requests,'frames':rows}
    (OUT/'browser.json').write_text(json.dumps(report,indent=2))
    sheet=Image.new('RGB',(4*256,4*282),'white');d=ImageDraw.Draw(sheet)
    for y,ident in enumerate(['sphere-left','wide-left','cylinder-left','wedge-left']):
        for x,(variant,bounce,layer,label) in enumerate([('flat16',False,'form','A16'),('gradient16',False,'form','B16 candidate'),('flat32',False,'form','C32'),('flat32',True,'composite','C32 + ground bounce')]):
            if ident.startswith(('cylinder','wedge')) and x<2:variant='flat32';label='C32 / flat faces' if ident.startswith('wedge') else 'C32 / capped cylinder'
            path=OUT/f'{ident}--{variant}--{int(bounce)}--{layer}.png'
            sheet.paste(Image.open(path).convert('RGB'),(x*256,y*282+26));d.text((x*256+6,y*282+7),label+' / '+ident.split('-')[0],fill='black')
    sheet.save(OUT/'comparison.png')
    for split in ['baseline','holdout']:
        for variant in ['flat16','gradient16','flat32']:
            group=[r for r in rows if r['split']==split and r['kind']=='ellipsoid' and r['variant']==variant and r['layer']=='form' and not r['bounce']]
            print(split,variant,{k:round(float(np.mean([r[k] for r in group])),4) for k in ['interiorMAE','fullMAE','edgeMAE','gradientError']})
    for key in ['interiorMAE','fullMAE','edgeMAE']:
        selected=[r for r in rows if r['variant']=='flat32' and r['layer']=='form'];worst=max(selected,key=lambda r:r[key]);print('WORST',key,worst['scene'],worst['bounce'],worst[key])
    print('SHADOW_MIN_IOU',min(r['iou'] for r in rows if r['layer']=='shadow'))
    print('S1_BROWSER_CAPTURE',len(rows),report['transport'])

if __name__=='__main__':main()
