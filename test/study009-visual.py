"""Research 009: reproducible REAL Chromium comparison of CSS graphite strokes.

24 frames = tonal/strokes x width 80/120 x jaw 82/118 x light -60/0/+60.
This is rendering/geometry evidence, NOT a human likeness or art-quality verdict.
"""
import asyncio
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from PIL import Image, ImageChops, ImageDraw, ImageStat
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results' / 'research-009'
ARMS = ('tonal', 'strokes')
WIDTHS = (80, 120)
JAWS = (82, 118)
LIGHTS = (-60, 0, 60)


def filename(arm, width, jaw, light):
    return f'{arm}-w{width}-j{jaw}-light{light:+d}.png'


async def run():
    OUT.mkdir(parents=True, exist_ok=True)
    results, exceptions = [], []

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    fallback = os.getenv('PORTRAIT_QA_INLINE') == '1'
    try:
        async with async_playwright() as driver:
            browser = await driver.chromium.launch(headless=True,
                executable_path=os.getenv('CHROMIUM_PATH') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None),
                args=['--no-sandbox'])
            try:
                for arm in ARMS:
                    page = await browser.new_page(viewport={'width': 1280, 'height': 900}, device_scale_factor=1)
                    page.on('pageerror', lambda e: exceptions.append(str(e)))
                    if not fallback:
                        try:
                            await page.goto(f'{origin}/standalone.html?r009={arm}', wait_until='load')
                        except Exception as exc:
                            if 'ERR_BLOCKED_BY_ADMINISTRATOR' not in str(exc):
                                raise
                            fallback = True
                            await page.close()
                            page = await browser.new_page(viewport={'width': 1280, 'height': 900}, device_scale_factor=1)
                            page.on('pageerror', lambda e: exceptions.append(str(e)))
                    if fallback:
                        html = (ROOT / 'standalone.html').read_text(encoding='utf8')
                        assert "const strokeVariant = qs.get('r009');" in html
                        html = html.replace("const strokeVariant = qs.get('r009');", f"const strokeVariant = '{arm}';")
                        await page.set_content(html, wait_until='load')
                    root = page.locator('#portrait')
                    assert await root.get_attribute('data-r009') == arm
                    assert await root.get_attribute('data-r008') == 'field'
                    assert await root.get_attribute('data-r007') == 'structured'
                    assert await page.locator('#portrait img,#portrait canvas,#portrait svg').count() == 0
                    assert await page.locator('input[type=range]').count() == 9
                    assert await page.locator('#param-faceWidth').is_visible()
                    assert await page.locator('.sf-stroke').count() == 11
                    display = await page.locator('.stroke-field').evaluate('e=>getComputedStyle(e).display')
                    assert display == ('block' if arm == 'strokes' else 'none')
                    for width in WIDTHS:
                        for jaw in JAWS:
                            for light in LIGHTS:
                                await page.locator('#param-faceWidth').fill(str(width))
                                await page.locator('#param-jaw').fill(str(jaw))
                                await page.locator('#param-lightDirection').fill(str(light))
                                await page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
                                shot = filename(arm, width, jaw, light)
                                await page.locator('#portrait-paper').screenshot(path=str(OUT / shot))
                                obs = await page.evaluate('''() => {
                                  const root=document.querySelector('#portrait');
                                  const get=n=>root.style.getPropertyValue(n);
                                  const rect=selector=>{
                                    const {x,y,width,height}=document.querySelector(selector).getBoundingClientRect();
                                    return {x,y,width,height};
                                  };
                                  return {
                                    left:Number.parseFloat(get('--r009-cheekLeft-opacity')),
                                    right:Number.parseFloat(get('--r009-cheekRight-opacity')),
                                    angleLeft:get('--r009-cheekLeft-angle'),
                                    angleJaw:get('--r009-jawLeft-angle'),
                                    strokeOpacity:getComputedStyle(document.querySelector('.sf-stroke-cheekLeft')).opacity,
                                    face:rect('.face'), leftEye:rect('.eye-left'), rightEye:rect('.eye-right'),
                                    scrollWidth:document.documentElement.scrollWidth
                                  };
                                }''')
                                assert obs['leftEye']['x'] < obs['rightEye']['x']
                                assert obs['scrollWidth'] <= 1280
                                if arm == 'strokes':
                                    assert 0 <= obs['left'] <= .39
                                    assert 0 <= obs['right'] <= .39
                                    assert obs['strokeOpacity'] != '0' or (obs['left'] == 0)
                                    assert obs['angleLeft'].endswith('deg')
                                    assert obs['angleJaw'].endswith('deg')
                                    if light == -60:
                                        assert obs['left'] < obs['right']
                                    elif light == 60:
                                        assert obs['left'] > obs['right']
                                obs.update(arm=arm, width=width, jaw=jaw, light=light, file=shot)
                                results.append(obs)
                    if arm == 'strokes':
                        await page.set_viewport_size({'width':390,'height':844})
                        await page.screenshot(path=str(OUT / 'mobile-strokes.png'), full_page=True)
                        assert await page.evaluate('document.documentElement.scrollWidth') <= 390
                    await page.close()
            finally:
                await browser.close()
    finally:
        server.shutdown()
    assert len(results) == 24
    assert not exceptions, exceptions
    for width in WIDTHS:
        for jaw in JAWS:
            light = -60
            a=Image.open(OUT / filename('tonal',width,jaw,light)).convert('RGB')
            b=Image.open(OUT / filename('strokes',width,jaw,light)).convert('RGB')
            difference=max(ImageStat.Stat(ImageChops.difference(a,b)).mean)
            assert difference > .05, f'New paint not visible for w{width} j{jaw}: {difference}'
    sheet=Image.new('RGB',(3*442,2*516),'#eae6dd')
    draw=ImageDraw.Draw(sheet)
    for row,arm in enumerate(ARMS):
        for col,light in enumerate(LIGHTS):
            source=Image.open(OUT / filename(arm,120,118,light)).convert('RGB')
            source.thumbnail((428,485),Image.Resampling.LANCZOS)
            x=col*442+(442-source.width)//2
            y=row*516+26
            sheet.paste(source,(x,y))
            draw.text((col*442+9,row*516+5),f'{arm}, light {light:+d}, w120 jaw118',fill='#313632')
    sheet.save(OUT / 'contact-sheet.png')
    (OUT / 'observations.json').write_text(json.dumps({
        'experiment':'R009 / unified relief-driven graphite stroke field',
        'frames':len(results),'inline_fallback':fallback,
        'observations':results,
        'art_quality':'ART_UNVERIFIED: 0 external observers',
        'render_perf':'No paint/memory benchmark claimed'
    },ensure_ascii=False,indent=2),encoding='utf8')
    print(f'RESEARCH_009_VISUAL_PASS: {len(results)} real Chromium frames; CSS strokes, light reversal, mobile and no JS errors; ART_UNVERIFIED; inline_fallback={fallback}')


if __name__ == '__main__':
    asyncio.run(run())
