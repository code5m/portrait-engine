"""Actual S3/S4 API and controls; synthetic reviews live only in a temp DB."""
import json,os,re,shutil,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'workbench'))
from model import CACHE,sha


def run():
    with tempfile.TemporaryDirectory() as td:
        data=Path(td)
        for folder in ['vendor','studies']:shutil.copytree(CACHE/folder,data/folder)
        shutil.copy2(CACHE/'source-verification.json',data/'source-verification.json')
        env={**os.environ,'PORTRAIT_DATA':str(data),'PORTRAIT_TEST_MODE':'1'}
        proc=subprocess.Popen([sys.executable,str(ROOT/'workbench/server.py'),'--port','4197'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        try:
            for _ in range(60):
                try:urllib.request.urlopen('http://127.0.0.1:4197/api/v1/health',timeout=1);break
                except OSError:time.sleep(.5)
            else:raise AssertionError('Server not ready')
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1080});errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                response=page.goto('http://127.0.0.1:4197/')
                assert 'unsafe-eval' not in response.headers['content-security-policy']
                page.fill('#reviewer-name','AUTOMATED_STUDY_TEST');page.click('#login-form button')
                expect(page.locator('#pipeline option')).to_have_count(3)
                sample_hashes=[]
                for stage in ['S3','S4']:
                    page.select_option('#pipeline',stage);page.select_option('#identity','head-a');page.click('#generate')
                    expect(page.locator('#sample-name')).to_contain_text(stage,timeout=600000)
                    expect(page.locator('#machine-badge')).to_have_text(re.compile(r'\u672a\u8fd0\u884c$'))
                    sample_hashes.append(page.locator('#candidate').get_attribute('data-content-hash'))
                    page.select_option('#view','masses');assert page.locator('#candidate i').count()==3
                    page.select_option('#view','structure');assert page.locator('#candidate i').count()==8
                    if stage=='S4':
                        page.select_option('#view','edges-control');assert page.locator('#candidate .edge-ribbon').count()==1
                    page.select_option('#view','tone')
                    assert page.locator('#candidate img,#candidate svg,#candidate canvas').count()==0
                    if stage=='S4':assert page.locator('#candidate .edge-ribbon').count()==2
                    page.click('#verify');expect(page.locator('#machine-badge')).to_have_text(re.compile(r'\u901a\u8fc7$'),timeout=600000)
                    expect(page.locator('#reference')).to_be_visible()
                    page.screenshot(path=str(CACHE/'studies'/('workbench-'+stage+'.png')),full_page=True)
                    for key in ['structure','volume','eyes','identity','realism']:page.select_option('#score-'+key,'3')
                    page.select_option('#verdict','revise');page.fill('#note','AUTOMATED TEST, NOT HUMAN EVIDENCE');page.check('#human-confirmed');page.click('#submit-review')
                    expect(page.locator('#review-receipt')).to_contain_text('\u5df2\u4fdd\u5b58')
                    expect(page.locator('#human-badge')).to_have_text(re.compile(r'\u9700\u4fee\u6539$'))
                    with page.expect_download() as event:page.click('#download')
                    exported=data/(stage+'.html');event.value.save_as(str(exported))
                    other=browser.new_page();other.goto(exported.as_uri());other.wait_for_selector('#portrait i');assert other.locator('#portrait img,#portrait svg,#portrait canvas').count()==0;other.close()
                assert sample_hashes[0]!=sample_hashes[1],'Stage-specific evidence collided'
                page.click('[data-tab=history]');page.wait_for_selector('#history button')
                with page.expect_download() as event:page.click('#export')
                exported=data/'reviews.json';event.value.save_as(str(exported));records=json.loads(exported.read_text())['reviews']
                payloads=[json.loads(x['payload']) for x in records]
                assert {x['stage'] for x in payloads}=={'S3','S4'}
                assert all(x['reviewType']=='AUTOMATED_TEST' and x['artStatus']=='ART_UNVERIFIED' for x in payloads)
                page.click('[data-tab=lab]');page.set_viewport_size({'width':390,'height':844});assert page.evaluate('() => document.documentElement.scrollWidth <= innerWidth+2')
                assert not errors,errors
                browser.close()
            receipt={'status':'PASS','sourceHead':os.getenv('SOURCE_HEAD_SHA'),'ciRun':os.getenv('GITHUB_RUN_ID'),
                     'steps':['S3 generation','S4 generation','independent verify','three-tone view','structure view','edge control','stage-bound isolated reviews','HTML exports','mobile layout'],
                     'humanObservers':0,'reviewData':'temporary AUTOMATED_TEST database only'}
            (CACHE/'studies/UI-result.json').write_text(json.dumps(receipt,indent=2));print('STUDY_UI_PASS '+json.dumps(receipt),flush=True)
        finally:
            proc.terminate()
            try:proc.wait(10)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
if __name__=='__main__':run()
