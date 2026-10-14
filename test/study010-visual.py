#!/usr/bin/env python3
"""Real Chromium QA of R010 single-blind workflow. Dummy ratings are DELETED.
Only an external human can provide evidence of aesthetic preference.
"""
import asyncio
import json
import os
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from PIL import Image, ImageChops, ImageStat
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results'/'research-010'

def offline_bundle(page_name):
    # The same generated offline file is distributable to independent reviewers.
    # No synthetic renderer or alternative drawing implementation exists here.
    path=ROOT/'study'/f'010-{page_name}-offline.html'
    return path.read_text(encoding='utf-8')

async def run():
    OUT.mkdir(parents=True,exist_ok=True)
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,directory=str(ROOT),**kwargs)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_port}'
    errors=[];cases=[];inline_fallback=False
    try:
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(headless=True,
                executable_path=os.environ.get('CHROMIUM_PATH') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None),
                args=['--no-sandbox'])
            page=await browser.new_page(viewport={'width':1100,'height':900},accept_downloads=True)
            page.on('pageerror',lambda exc:errors.append(str(exc)))
            try:
                await page.goto(url+'/study/010-blind.html',wait_until='domcontentloaded')
            except Exception as exc:
                if 'ERR_BLOCKED_BY_ADMINISTRATOR' not in str(exc): raise
                inline_fallback=True
                await page.close()
                page=await browser.new_page(viewport={'width':1100,'height':900},accept_downloads=True)
                page.on('pageerror',lambda exc:errors.append(str(exc)))
                await page.set_content(offline_bundle('blind'))
            for step in range(3):
                await page.locator('#next:not([disabled])').wait_for(timeout=25000)
                progress=await page.locator('#progress').inner_text()
                cards=page.locator('.card')
                assert await cards.count()==2
                directions=[];variants=[]
                for j in range(2):
                    frame_locator=cards.nth(j).locator('iframe')
                    light=await frame_locator.get_attribute('data-light-direction')
                    variant=await frame_locator.get_attribute('data-variant')
                    assert variant in {'tonal','strokes'}
                    assert light in {'-60','0','60'}
                    frame=await frame_locator.element_handle()
                    content=await frame.content_frame()
                    assert content
                    assert await content.locator('#portrait').get_attribute('data-r009')==variant
                    for key,val in [('faceWidth','100'),('jaw','100'),('graphite','65'),('lightDirection',light)]:
                        assert await content.locator('#param-'+key).input_value()==val
                    assert await content.locator('#portrait img, #portrait svg, #portrait canvas').count()==0
                    await frame_locator.screenshot(path=str(OUT/f'scene-{step+1}-{j+1}.png'))
                    directions.append(light);variants.append(variant)
                assert len(set(directions))==1 and set(variants)=={'tonal','strokes'}
                before=Image.open(OUT/f'scene-{step+1}-1.png').convert('RGB')
                after=Image.open(OUT/f'scene-{step+1}-2.png').convert('RGB')
                pixels=ImageStat.Stat(ImageChops.difference(before,after)).mean
                assert max(pixels)>0.02, 'Paint candidates have identical pixels'
                cases.append({'scene':step+1,'lightDirection':int(directions[0]),'variants':variants,
                              'pixelDifferenceMean':round(max(pixels),5),'progress':progress})
                for select in await page.locator('#rating-form select').all():
                    await select.select_option('4')
                await page.locator('input[name=preference][value=tie]').check()
                await page.locator('#next').click()
            assert set(case['lightDirection'] for case in cases)=={-60,0,60}
            assert await page.locator('#finished').is_visible()
            assert await page.locator('#download').is_disabled()
            await page.locator('#independent').check()
            async with page.expect_download() as info:
                await page.locator('#download').click()
            downloaded=await info.value
            assert downloaded.suggested_filename=='portrait-r010-human-evaluation.json'
            with tempfile.TemporaryDirectory() as temporary:
                path=Path(temporary)/'synthetic-browser-form.json'
                await downloaded.save_as(str(path))
                response=json.loads(path.read_text())
                assert response['protocol']=='portrait-engine-r010-blind'
                assert len(response['trials'])==3
                assert set(x['lightDirection'] for x in response['trials'])=={-60,0,60}
                assert all(x['preference']=='tie' for x in response['trials'])
                # This is a computer-generated form test. Never retain/aggregate it.
                if inline_fallback:
                    await page.set_content(offline_bundle('results'))
                else:
                    await page.goto(url+'/study/010-results.html')
                await page.locator('#files').set_input_files(str(path))
                await page.locator('#analyze').click()
                await page.locator('#summary').get_by_text('INSUFFICIENT_HUMAN_EVIDENCE').wait_for(timeout=7000)
                assert '"evaluatedSessions": 1' in await page.locator('#summary').inner_text()
            await page.set_viewport_size({'width':390,'height':844})
            if inline_fallback:
                await page.set_content(offline_bundle('blind'))
            else:
                await page.goto(url+'/study/010-blind.html')
            await page.locator('#next:not([disabled])').wait_for(timeout=25000)
            assert await page.evaluate('document.documentElement.scrollWidth')<=390
            frame=page.locator('.card').first.locator('iframe')
            assert await frame.evaluate('el=>el.clientWidth')==410
            await page.screenshot(path=str(OUT/'blind-mobile.png'),full_page=True)
            # Public distributable single-file version MUST work without
            # any external module, HTTP fetch, iframe navigation or telemetry.
            portable=await browser.new_page(viewport={'width':1080,'height':900})
            offline_requests=[]
            portable.on('request',lambda request: offline_requests.append(request.url))
            portable.on('pageerror',lambda exc:errors.append(str(exc)))
            await portable.set_content(offline_bundle('blind'))
            await portable.locator('#next:not([disabled])').wait_for(timeout=25000)
            assert await portable.locator('.card iframe').count()==2
            assert not offline_requests, f'Offline reviewer attempted network I/O: {offline_requests}'
            await portable.screenshot(path=str(OUT/'offline-desktop.png'),full_page=True)
            await portable.set_content(offline_bundle('results'))
            assert await portable.locator('#analyze').is_visible()
            assert not offline_requests, f'Offline results analyzer attempted network I/O: {offline_requests}'
            await portable.close()
            assert not errors,errors
            await browser.close()
    finally:
        server.shutdown()
    if os.environ.get('GITHUB_ACTIONS')=='true' and inline_fallback:
        raise AssertionError('GitHub CI must exercise real HTTP navigation, not a fallback')
    payload={'browser':'Chromium','scenes':cases,'inlineFallback':inline_fallback,'offlineNetworkRequests':0,'dummyRatingsRetained':False,
        'realHumanRatings':0,'artQuality':'ART_UNVERIFIED',
        'description':'Browser form testing and CSS pixel differences do not prove independent human aesthetic preference.'}
    (OUT/'metrics.json').write_text(json.dumps(payload,indent=2)+'\n')
    print('RESEARCH_010_BROWSER_PASS: 3 controlled scenes, anonymous A/B, JSON export, local analyzer, mobile; 0 actual reviewers')
if __name__=='__main__':
    asyncio.run(run())
