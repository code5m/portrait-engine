"""Nine actual Chromium CSS renders: three DNA identities x three light rigs.
Snapshots are CI artifacts, not asset inputs or human aesthetic evidence.
"""
import asyncio
import json
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results'/'face-engine-v1'
IDS=('lin-che','zhou-qishan','third-portrait')
LIGHTS=('front','side','top')

async def run():
    OUT.mkdir(parents=True,exist_ok=True)
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    Thread(target=server.serve_forever,daemon=True).start()
    evidence=[]
    try:
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                page=await browser.new_page(viewport={'width':1280,'height':920},device_scale_factor=1)
                errors=[]
                page.on('pageerror',lambda exc:errors.append(str(exc)))
                await page.goto(f'http://127.0.0.1:{server.server_port}/standalone.html')
                assert await page.locator('#portrait').get_attribute('data-face-engine')=='v1'
                for identity in IDS:
                    await page.locator(f'[data-identity="{identity}"]').click()
                    for light in LIGHTS:
                        await page.locator(f'[data-light-mode="{light}"]').click()
                        await page.evaluate('()=>new Promise(ok=>requestAnimationFrame(()=>requestAnimationFrame(ok)))')
                        props=await page.locator('#portrait').evaluate('''el=>({
                          x:el.style.getPropertyValue("--fg-leftEye-x"),
                          y:el.style.getPropertyValue("--fg-leftJaw-y"),
                          shade:el.style.getPropertyValue("--v-cheekLeft-shade"),
                          elevation:el.style.getPropertyValue("--light-elevation")
                        })''')
                        assert all(props.values()),props
                        file=f'{identity}-{light}.png'
                        await page.locator('#portrait-paper').screenshot(path=str(OUT/file))
                        evidence.append({'identity':identity,'lighting':light,'file':file,'properties':props})
                assert not errors,errors
                assert len(evidence)==9
                assert len(set(json.dumps(x['properties'],sort_keys=True) for x in evidence))==9
            finally:
                await browser.close()
    finally:
        server.shutdown()
    (OUT/'manifest.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    print('FACE_ENGINE_V1_VISUAL_PASS: 9 browser CSS renders / 3 identities x 3 lights')

if __name__=='__main__':asyncio.run(run())
