"""Real browser API lifecycle. Automatic scores go ONLY to a temporary test DB.
Product screenshots are made before synthetic feedback: human status PENDING.
CSP stays strict: no unsafe-eval and no bypass_csp browser option.
"""
import base64,io,json,os,re,shutil,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workbench'))
from model import CACHE


def wait_for_loaded_reference(page, timeout=30):
    """Poll a locator-bound function, not wait_for_function's string eval."""
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if page.locator('#reference').evaluate('(image) => image.complete && image.naturalWidth > 0'):
            return
        page.wait_for_timeout(100)
    raise AssertionError('Reference image did not load')


def run():
    with tempfile.TemporaryDirectory() as td:
        data=Path(td)
        for folder in ['vendor','renders','reference','machine']:
            if (CACHE/folder).exists():shutil.copytree(CACHE/folder,data/folder)
        if (CACHE/'source-verification.json').exists():shutil.copy2(CACHE/'source-verification.json',data/'source-verification.json')
        env={**os.environ,'PORTRAIT_DATA':str(data),'PORTRAIT_TEST_MODE':'1'}
        proc=subprocess.Popen([sys.executable,str(ROOT/'workbench/server.py'),'--port','4196'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        try:
            for _ in range(60):
                try:urllib.request.urlopen('http://127.0.0.1:4196/api/v1/health',timeout=1);break
                except OSError:time.sleep(.5)
            else:raise AssertionError('API failed to start')
            with sync_playwright() as p:
                opts={'headless':True,'args':['--no-sandbox']}
                if os.getenv('PORTRAIT_CHROMIUM'):opts['executable_path']=os.environ['PORTRAIT_CHROMIUM']
                b=p.chromium.launch(**opts);page=b.new_page(viewport={'width':1440,'height':1080});errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                response=page.goto('http://127.0.0.1:4196/workbench/')
                policy=response.headers.get('content-security-policy','')
                assert "script-src 'self'" in policy and 'unsafe-eval' not in policy,'Do not weaken production CSP to make E2E pass'
                page.fill('#reviewer-name','AUTOMATED_TEST_NOT_A_HUMAN');page.click('#login-form button')
                expect(page.locator('#identity option').first).to_be_attached();page.click('#generate')
                page.wait_for_selector('#candidate[data-content-hash]',timeout=240000)
                assert page.locator('#candidate i').count()==24
                assert page.locator('#candidate img,#candidate canvas,#candidate svg').count()==0
                page.select_option('#view','structure');assert page.locator('#candidate i').count()<=12
                page.select_option('#view','tone');page.click('#verify')
                page.wait_for_selector('#reference:not([hidden])',timeout=300000)
                expect(page.locator('#machine-badge')).to_have_text(re.compile(r'\u901a\u8fc7$'))
                wait_for_loaded_reference(page)
                page.screenshot(path=str(CACHE/'workbench-desktop.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('() => document.documentElement.scrollWidth <= innerWidth+2')
                page.screenshot(path=str(CACHE/'workbench-mobile.png'),full_page=True)
                page.set_viewport_size({'width':1440,'height':1080})
                with page.expect_download() as event:page.click('#download')
                exported=data/'exported-portrait.html';event.value.save_as(str(exported))
                assert 'Copyright (c) 2020 USC' in exported.read_text(), 'Derived export lost MIT notice'
                sample=b.new_page();sample.goto(exported.as_uri());sample.wait_for_selector('#portrait i')
                assert sample.locator('#portrait i').count()==24
                assert sample.locator('#portrait img,#portrait canvas,#portrait svg').count()==0
                sample.close()
                for dimension in ['structure','volume','eyes','identity','realism']:page.select_option('#score-'+dimension,'3')
                page.select_option('#verdict','revise');page.fill('#note','AUTOMATED E2E TEST - not human feedback');page.fill('#pin-note','Synthetic annotation')
                page.locator('#candidate-paper').click(position={'x':120,'y':130});assert page.locator('#pins .pin').count()==1
                page.check('#human-confirmed');page.click('#submit-review')
                expect(page.locator('#review-receipt')).to_contain_text('\u5df2\u4fdd\u5b58',timeout=30000)
                expect(page.locator('#human-badge')).to_have_text(re.compile(r'\u9700\u4fee\u6539$'))
                page.screenshot(path=str(data/'automated-review-test.png'),full_page=True)
                page.click('[data-tab=stages]');page.wait_for_selector('#stage-grid article');assert page.locator('#stage-grid article').count()==7
                page.click('[data-tab=history]');page.wait_for_selector('#history button')
                with page.expect_download() as event:page.click('#export')
                record=data/'test-reviews.json';event.value.save_as(str(record))
                reviews=json.loads(record.read_text())['reviews']
                assert reviews and all(json.loads(r['payload'])['reviewType']=='AUTOMATED_TEST' for r in reviews)
                page.click('[data-tab=lab]');page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('() => document.documentElement.scrollWidth <= innerWidth+2')
                assert not errors,errors
                b.close()
            for filename in ['workbench-desktop.png','workbench-mobile.png']:
                image=Image.open(CACHE/filename).convert('RGB');image.thumbnail((1000,1400));buf=io.BytesIO();image.save(buf,format='JPEG',quality=72,optimize=True)
                print('WORKBENCH_PREVIEW_JPEG '+filename+' '+base64.b64encode(buf.getvalue()).decode(),flush=True)
            print('WORKBENCH_REAL_UI_PASS: actual generate, verify, reference, synthetic review, annotations, history/stages and downloads')
        finally:
            proc.terminate()
            try:proc.wait(10)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
if __name__=='__main__':run()
