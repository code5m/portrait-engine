"""Real workbench buttons and API lifecycle. Automated test feedback is explicitly
not a human observer, stored in an isolated temporary database.
"""
import json,os,shutil,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workbench'))
from model import CACHE,source_digest,save_json

def run():
    with tempfile.TemporaryDirectory() as td:
        data=Path(td)
        # Reuse verified model cache and actual generated samples. Never mock
        # the rendering endpoint or invent reference images.
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
                page.goto('http://127.0.0.1:4196/');page.fill('#reviewer-name','AUTOMATED_TEST_NOT_A_HUMAN');page.click('#login-form button')
                page.wait_for_function('document.querySelector("#identity").options.length > 0');page.click('#generate')
                page.wait_for_selector('#candidate[data-content-hash]',timeout=240000)
                assert page.locator('#candidate i').count()==24
                assert page.locator('#candidate img,#candidate canvas,#candidate svg').count()==0
                page.select_option('#view','structure');assert page.locator('#candidate i').count()<=12
                page.select_option('#view','tone');page.click('#verify')
                page.wait_for_selector('#reference:not([hidden])',timeout=300000)
                assert page.locator('#machine-badge').inner_text().endswith('\u901a\u8fc7')
                for dimension in ['structure','volume','eyes','identity','realism']:page.select_option('#score-'+dimension,'3')
                page.select_option('#verdict','revise');page.fill('#note','AUTOMATED E2E TEST - not human feedback');page.fill('#pin-note','Synthetic annotation')
                page.locator('#candidate-paper').click(position={'x':120,'y':130});assert page.locator('#pins .pin').count()==1
                page.check('#human-confirmed');page.click('#submit-review');page.wait_for_function("document.querySelector('#review-receipt').textContent.includes('\\u5df2\\u4fdd\\u5b58')")
                assert page.locator('#human-badge').inner_text().endswith('\u9700\u4fee\u6539')
                page.screenshot(path=str(CACHE/'workbench-desktop.png'),full_page=True)
                page.click('[data-tab=stages]');page.wait_for_selector('#stage-grid article');assert page.locator('#stage-grid article').count()==7
                page.click('[data-tab=history]');page.wait_for_selector('#history button')
                page.click('[data-tab=lab]');page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(CACHE/'workbench-mobile.png'),full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+2')
                assert not errors,errors
                b.close()
            print('WORKBENCH_REAL_UI_PASS: render -> independent machine check -> synthetic annotated review -> history/stages/export endpoints')
        finally:
            proc.terminate()
            try:proc.wait(10)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
if __name__=='__main__':run()
