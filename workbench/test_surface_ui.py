"""Actual S5/S6 UI lifecycle. No human reviews are created, even synthetically."""
from __future__ import annotations
import json,os,re,shutil,sqlite3,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from model import ROOT,CACHE,canonical,save_json
from surface_registry import source_digest
from archive_surface import UI_CASES,UI_STEPS


def run(stage):
    if stage not in UI_CASES:raise ValueError('Choose S5 or S6')
    case_id=UI_CASES[stage];identity='head-a' if stage=='S5' else 'novel-a';expression='neutral' if stage=='S5' else 'smile'
    output=CACHE/'surface/evidence'/case_id;output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        data=Path(td)
        for folder in ['vendor','surface-vendor','surface/base','renders','specs']:
            if (CACHE/folder).exists():shutil.copytree(CACHE/folder,data/folder)
        for name in ['source-verification.json','surface-source-verification.json']:
            if (CACHE/name).exists():shutil.copy2(CACHE/name,data/name)
        env={**os.environ,'PORTRAIT_DATA':str(data),'PORTRAIT_TEST_MODE':'1'}
        with (data/'server.log').open('w') as log:
            proc=subprocess.Popen([sys.executable,str(ROOT/'workbench/server.py'),'--port','4195'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            try:
                for _ in range(60):
                    try:urllib.request.urlopen('http://127.0.0.1:4195/api/v1/health',timeout=1);break
                    except OSError:time.sleep(.5)
                else:raise AssertionError('Surface API did not start')
                with sync_playwright() as p:
                    browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1080});errors=[]
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    response=page.goto('http://127.0.0.1:4195/workbench/')
                    assert 'unsafe-eval' not in response.headers['content-security-policy']
                    page.fill('#reviewer-name','AUTOMATED_UI_NO_REVIEW');page.click('#login-form button')
                    expect(page.locator('#pipeline option')).to_have_count(5)
                    page.select_option('#pipeline',stage);page.select_option('#identity',identity)
                    if stage=='S6':page.select_option('#expression',expression)
                    page.select_option('#material','graphite');page.select_option('#hair','swept');page.click('#generate')
                    expect(page.locator('#sample-name')).to_contain_text(stage,timeout=900000)
                    expect(page.locator('#machine-badge')).to_have_text(re.compile(r'\u672a\u8fd0\u884c$'))
                    expect(page.locator('#candidate .surface-region')).to_have_count(5)
                    first_hash=page.locator('#candidate').get_attribute('data-content-hash');first_geometry=page.locator('#candidate').get_attribute('data-geometry-hash')
                    page.select_option('#view','masses');assert page.locator('#candidate i').count()==3
                    page.select_option('#view','structure');assert page.locator('#candidate i').count()==8
                    page.select_option('#view','material-control');assert page.locator('#candidate .surface-region').count()==0
                    page.select_option('#view','hair-control');assert page.locator('#candidate .surface-region').count()==3
                    page.select_option('#view','tone');page.click('#verify')
                    expect(page.locator('#machine-badge')).to_have_text(re.compile(r'\u901a\u8fc7$'),timeout=900000)
                    expect(page.locator('#reference')).to_be_visible()
                    for _ in range(100):
                        if page.locator('#reference').evaluate('(image)=>image.complete&&image.naturalWidth>0'):break
                        page.wait_for_timeout(100)
                    else:raise AssertionError('Independent reference image did not load')
                    assert page.locator('#candidate img,#candidate svg,#candidate canvas').count()==0
                    page.screenshot(path=str(output/('workbench-'+stage+'.png')),full_page=True)
                    page.set_viewport_size({'width':390,'height':844})
                    assert page.evaluate('()=>document.documentElement.scrollWidth<=innerWidth+2')
                    page.screenshot(path=str(output/('mobile-'+stage+'.png')),full_page=True)
                    page.set_viewport_size({'width':1440,'height':1080})
                    with page.expect_download() as event:page.click('#download')
                    exported=data/'surface-export.html';event.value.save_as(str(exported))
                    assert 'Copyright (c) 2020 USC' in exported.read_text()
                    other=browser.new_page();requests=[];other.on('request',lambda r:requests.append(r.url) if not r.url.startswith('file:') else None)
                    other.goto(exported.as_uri());other.wait_for_selector('#portrait .surface-region')
                    assert other.locator('#portrait img,#portrait svg,#portrait canvas').count()==0 and not requests;other.close()
                    # Input changes do not silently replace a frozen, verified sample.
                    page.select_option('#material','charcoal');assert page.locator('#candidate').get_attribute('data-content-hash')==first_hash
                    page.click('#generate');expect(page.locator('#candidate')).not_to_have_attribute('data-content-hash',first_hash,timeout=900000)
                    expect(page.locator('#machine-badge')).to_have_text(re.compile(r'\u672a\u8fd0\u884c$'))
                    assert page.locator('#candidate').get_attribute('data-geometry-hash')==first_geometry
                    charcoal_hash=page.locator('#candidate').get_attribute('data-content-hash')
                    page.select_option('#material','graphite');page.select_option('#hair','short');page.click('#generate')
                    expect(page.locator('#candidate')).not_to_have_attribute('data-content-hash',charcoal_hash,timeout=900000)
                    expect(page.locator('#status')).to_contain_text('\u4efb\u52a1\u5b8c\u6210',timeout=900000)
                    assert page.locator('#candidate').get_attribute('data-geometry-hash')==first_geometry
                    page.click('[data-tab=history]');page.wait_for_selector('#history button')
                    page.click('[data-tab=stages]');expect(page.locator('#stage-grid article')).to_have_count(7)
                    # Export belongs to history; use the real visible UI, never force-click a hidden tab.
                    page.click('[data-tab=history]');expect(page.locator('#export')).to_be_visible()
                    with page.expect_download() as event:page.click('#export')
                    exported_reviews=data/'reviews.json';event.value.save_as(str(exported_reviews));assert json.loads(exported_reviews.read_text())['reviews']==[]
                    page.click('[data-tab=lab]');expect(page.locator('#candidate')).to_be_visible()
                    assert not errors,errors;browser.close()
                with sqlite3.connect(data/'state.sqlite3') as db:assert db.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]==0
                receipt={'stage':stage,'status':'PASS','sourceHead':os.getenv('SOURCE_HEAD_SHA'),'ciRun':os.getenv('GITHUB_RUN_ID'),
                         'sourceDigest':source_digest(stage),'steps':sorted(UI_STEPS),'humanObservers':0,
                         'humanReview':'DEFERRED_BY_OWNER','artStatus':'ART_UNVERIFIED','reviewData':'no reviews created; temporary database'}
                save_json(output/'UI-result.json',receipt);print('SURFACE_UI_PASS '+canonical(receipt).decode(),flush=True)
            except Exception:
                print((data/'server.log').read_text()[-5000:],flush=True)
                for path in (data/'logs').glob('*.log') if (data/'logs').exists() else []:print(path.name,path.read_text()[-5000:],flush=True)
                raise
            finally:
                proc.terminate()
                try:proc.wait(10)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
if __name__=='__main__':run(sys.argv[1])
