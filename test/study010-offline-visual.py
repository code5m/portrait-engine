#!/usr/bin/env python3
"""Real Chromium QA of the shareable, fully offline R010 study files.
Synthetic responses are deleted and never qualify as artistic evidence.
GitHub CI must exercise file:// rather than inline sandbox fallback.
"""
import asyncio
import json
import os
import tempfile
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT/'study'
OUT=ROOT/'test-results'/'research-010'

async def open_file(browser,page,path,errors,requests):
    try:
        await page.goto(path.resolve().as_uri(),wait_until='domcontentloaded',timeout=18000)
        return page,False
    except Exception as error:
        if 'ERR_BLOCKED_BY_ADMINISTRATOR' not in str(error):
            raise
        # Local execution environment blocks navigation. Chromium still paints
        # the exact shipped HTML; only real file navigation can pass on CI.
        viewport=page.viewport_size
        await page.close()
        page=await browser.new_page(viewport=viewport,accept_downloads=True)
        page.on('pageerror',lambda exc:errors.append(str(exc)))
        page.on('request',lambda req:requests.append(req.url))
        await page.set_content(path.read_text(encoding='utf-8'),wait_until='domcontentloaded')
        return page,True

async def run():
    OUT.mkdir(parents=True,exist_ok=True)
    errors=[]
    requests=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True,
            executable_path=os.environ.get('CHROMIUM_PATH') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None),
            args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':1100,'height':850},accept_downloads=True)
        page.on('pageerror',lambda exc:errors.append(str(exc)))
        page.on('request',lambda req:requests.append(req.url))
        page,fallback=await open_file(browser,page,STUDY/'010-blind-offline.html',errors,requests)
        scenes=[]
        for i in range(3):
            await page.locator('#next:not([disabled])').wait_for(timeout=25000)
            variants=[]
            lights=[]
            for j in range(2):
                loc=page.locator('.card').nth(j).locator('iframe')
                variant=await loc.get_attribute('data-variant')
                light=await loc.get_attribute('data-light-direction')
                frame=await (await loc.element_handle()).content_frame()
                assert variant in {'tonal','strokes'}
                assert light in {'-60','0','60'}
                assert await frame.locator('#portrait').get_attribute('data-r009')==variant
                assert await frame.locator('#param-lightDirection').input_value()==light
                assert await frame.locator('#param-faceWidth').input_value()=='100'
                assert await frame.locator('#portrait svg, #portrait img, #portrait canvas').count()==0
                if i==0:
                    await loc.screenshot(path=str(OUT/f'offline-{j+1}.png'))
                variants.append(variant)
                lights.append(int(light))
            assert set(variants)=={'tonal','strokes'}
            assert len(set(lights))==1
            scenes.append({'variants':variants,'lightDirection':lights[0]})
            for select in await page.locator('#rating-form select').all():
                await select.select_option('3')
            await page.locator('input[name=preference][value=tie]').check()
            await page.locator('#next').click()
        assert set(s['lightDirection'] for s in scenes)=={-60,0,60}
        await page.locator('#independent').check()
        async with page.expect_download() as download_info:
            await page.locator('#download').click()
        download=await download_info.value
        with tempfile.TemporaryDirectory() as folder:
            data=Path(folder)/'synthetic-qa.json'
            await download.save_as(str(data))
            response=json.loads(data.read_text())
            assert response['protocol']=='portrait-engine-r010-blind'
            assert len(response['trials'])==3
            page,second=await open_file(browser,page,STUDY/'010-results-offline.html',errors,requests)
            fallback|=second
            await page.locator('#files').set_input_files(str(data))
            await page.locator('#analyze').click()
            await page.locator('#summary').get_by_text('INSUFFICIENT_HUMAN_EVIDENCE').wait_for(timeout=7000)
            assert '"evaluatedSessions": 1' in await page.locator('#summary').inner_text()
        await page.set_viewport_size({'width':390,'height':844})
        page,third=await open_file(browser,page,STUDY/'010-blind-offline.html',errors,requests)
        fallback|=third
        await page.locator('#next:not([disabled])').wait_for(timeout=25000)
        assert await page.evaluate('document.documentElement.scrollWidth')<=390
        await page.screenshot(path=str(OUT/'offline-mobile.png'),full_page=True)
        assert not any(url.startswith(('http:','https:')) for url in requests),requests
        assert not errors,errors
        await browser.close()
    if os.environ.get('GITHUB_ACTIONS')=='true' and fallback:
        raise AssertionError('GitHub CI must exercise real file:// navigation')
    result={'fileNavigation':not fallback,'inlineFallback':fallback,'scenes':scenes,
        'networkRequests':0,'syntheticRatingsRetained':False,'realHumanRatings':0,
        'artQuality':'ART_UNVERIFIED'}
    (OUT/'offline-metrics.json').write_text(json.dumps(result,indent=2)+'\n')
    print('R010_OFFLINE_PASS: 3 lights, anonymous A/B, file export and import, mobile, zero network calls; no real human ratings')

if __name__=='__main__':
    asyncio.run(run())
