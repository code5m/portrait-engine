"""Headless real CSS-rendering and anonymous scoring workflow regression, R005.

This is *not* a human likeness rating. Pixel differences, CSS computation and
playwright timing only establish that the code paths are real and stable.
"""
import asyncio
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from pathlib import Path
from statistics import median
from PIL import Image, ImageChops, ImageStat, ImageDraw
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results' / 'research-005'
VARIANTS = ('baseline', 'orbital', 'expression')

async def run():
    OUT.mkdir(parents=True, exist_ok=True)
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    base_url=f'http://127.0.0.1:{server.server_port}'
    inline_fallback = os.environ.get("PORTRAIT_QA_INLINE") == "1"
    observations = []
    errors = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_PATH') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None), args=['--no-sandbox'])
        page = await browser.new_page(viewport={'width':410,'height':535},device_scale_factor=1)
        page.on('pageerror', lambda error: errors.append(str(error)))
        for variant in VARIANTS:
            if not inline_fallback:
                try:
                    await page.goto(f'{base_url}/standalone.html?r005={variant}&embed=1')
                except Exception as e:
                    if 'ERR_BLOCKED_BY_ADMINISTRATOR' not in str(e): raise
                    inline_fallback = True
                    await page.close()
                    page = await browser.new_page(viewport={'width':410,'height':535},device_scale_factor=1)
                    page.on('pageerror', lambda error: errors.append(str(error)))
            if inline_fallback:
                html=(ROOT / 'standalone.html').read_text()
                assert "const researchVariant = qs.get('r005');" in html
                assert "const researchEmbed = qs.get('embed') === '1'" in html
                html=html.replace("const researchVariant = qs.get('r005');",f"const researchVariant = '{variant}';")
                html=html.replace("const researchEmbed = qs.get('embed') === '1'", 'const researchEmbed = true')
                await page.set_content(html)
            root = page.locator('#portrait')
            assert await root.get_attribute('data-r005') == variant
            assert await page.locator('input[type=range]').count() == 9
            assert await page.locator('#portrait img,#portrait svg,#portrait canvas').count() == 0
            assert await page.locator('.inspector').is_hidden()
            assert await page.locator('#param-faceWidth').input_value() == '100'
            assert await page.locator('#param-lightDirection').input_value() == '-30'
            face = await page.locator('.face').bounding_box()
            left_eye = await page.locator('.eye-left').bounding_box()
            right_eye = await page.locator('.eye-right').bounding_box()
            mouth = await page.locator('.mouth').bounding_box()
            assert face and left_eye and right_eye and mouth
            assert face['x'] <= left_eye['x'] <= right_eye['x'] <= face['x']+face['width']
            assert face['y'] < mouth['y'] < face['y']+face['height']
            # A repeatable, end-to-end two-frame visual update latency probe.
            # Does not measure pure GPU paint time; report median for comparisons.
            frame_ms = []
            for _ in range(4):
                t = await page.evaluate('''async () => {
                    const begin=performance.now();
                    await new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(done)));
                    return performance.now()-begin;
                }''')
                frame_ms.append(t)
            await page.screenshot(path=str(OUT/f'{variant}.png'))
            observations.append({'variant':variant,'lightDirection':-30,'faceWidth':100,
                                 'face':face,'eyeLeft':left_eye,'eyeRight':right_eye,'mouth':mouth,
                                 'frame_round_trip_ms_median':round(median(frame_ms),2)})
        # Visible per-arm samples must differ in the portrait area, not via labels.
        images = [Image.open(OUT/f'{v}.png').convert('RGB') for v in VARIANTS]
        # Evaluate the deliberately altered anatomical region; a mouth change
        # affects less than 1% of the full canvas and must not be diluted.
        for i,j,box,threshold in ((0,1,(110,215,300,350),1.0),
                                  (1,2,(150,350,275,435),.25)):
            a=images[i].crop(box)
            b=images[j].crop(box)
            delta=ImageStat.Stat(ImageChops.difference(a,b)).mean
            assert max(delta)>threshold, f'Anatomical variants not distinguishable in relevant region: {i}/{j}, {delta}'
        w,h=images[0].size
        sheet=Image.new('RGB',(w*3+56,h+88),'#f3f1ed')
        draw=ImageDraw.Draw(sheet)
        for i,img in enumerate(images):
            x=14+i*(w+14)
            sheet.paste(img,(x,38))
            draw.text((x+9,12),f'OPTION {chr(65+i)}  -  {VARIANTS[i]}',fill='#41443d')
        sheet.save(OUT/'candidate-contact-sheet.png')
        if inline_fallback:
            await page.set_content((ROOT/'study'/'005-blind.html').read_text())
        else:
            await page.goto(f'{base_url}/study/005-blind.html')
        assert await page.locator('.candidate').count()==3
        assert await page.locator('iframe').count()==3
        labels = await page.locator('iframe').evaluate_all('(els)=>els.map(el=>el.getAttribute("src"))')
        assert len(set(labels))==3
        # Wait for each actual, unlabelled iframe to render the original CSS face.
        if not inline_fallback:
            for frame in page.frames[1:]:
                await frame.wait_for_selector('#portrait .mouth')
        assert await page.locator('select[required]').count()==9
        async with page.expect_download() as download_info:
            for i in range(9):
                await page.locator('select[required]').nth(i).select_option('4')
            await page.locator('button[type=submit]').click()
        download = await download_info.value
        assert download.suggested_filename=='portrait-r005-blind-rating.json'
        file=OUT/'blind-protocol-example.json'
        await download.save_as(str(file))
        payload=json.loads(file.read_text())
        assert payload['protocol']=='portrait-engine-blind-r005'
        assert set(x['actual_variant'] for x in payload['conditions'])==set(VARIANTS)
        assert all(set(x['scores'].values())=={4} for x in payload['conditions'])
        # Simulated example rating is not human feedback. Delete it after test.
        file.unlink()
        await page.set_viewport_size({'width':390,'height':844})
        assert await page.evaluate('document.documentElement.scrollWidth')<=390
        await page.screenshot(path=str(OUT/'blind-mobile.png'),full_page=True)
        assert not errors, errors
        await browser.close()
    server.shutdown()
    (OUT/'metrics.json').write_text(json.dumps({'cases':observations,'observed_browser':'Chromium','inline_fallback':inline_fallback,
          'rating_source':'NONE - automated dummy form submission only',
          'timing_note':'Median two-requestAnimationFrame latency includes frame scheduling; not GPU paint cost.',
          'interpretation':'Different candidate pixels and functional anonymous scoring do not imply artistic superiority.'},indent=2))
    print(f'RESEARCH_005_BROWSER_PASS: 3 CSS render paths, visible pixel distinctions, blind form export, mobile, 0 JS errors; inline_fallback={inline_fallback}')

if __name__=='__main__':
    asyncio.run(run())
