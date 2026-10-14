"""Research 008: paired CSS-only render evidence, NOT an artistic realism test.

36 frames = 2 render arms x 3 face widths x 2 jaw extremes x 3 key lights.
Probes actual DOM/CSS, light direction, landmarks, and mobile clipping.
An in-memory fallback is used only where localhost navigation is prohibited.
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
OUT = ROOT / 'test-results' / 'research-008'
ARMS = ('legacy', 'field')
WIDTHS = (80, 100, 120)
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
                            await page.goto(f'{origin}/standalone.html?r008={arm}', wait_until='load')
                        except Exception as exc:
                            if 'ERR_BLOCKED_BY_ADMINISTRATOR' not in str(exc):
                                raise
                            fallback = True
                            await page.close()
                            page = await browser.new_page(viewport={'width': 1280, 'height': 900}, device_scale_factor=1)
                            page.on('pageerror', lambda e: exceptions.append(str(e)))
                    if fallback:
                        html = (ROOT / 'standalone.html').read_text(encoding='utf8')
                        assert "const surfaceVariant = qs.get('r008');" in html
                        html = html.replace("const surfaceVariant = qs.get('r008');", f"const surfaceVariant = '{arm}';")
                        await page.set_content(html, wait_until='load')
                    root = page.locator('#portrait')
                    assert await root.get_attribute('data-r008') == arm
                    assert await root.get_attribute('data-r007') == 'structured'
                    assert await root.get_attribute('data-r006') == 'volume'
                    assert await page.locator('#portrait img, #portrait svg, #portrait canvas').count() == 0
                    assert await page.locator('input[type=range]').count() == 9
                    assert await page.locator('#param-faceWidth').is_visible(), 'real HTTP study must expose interactive controls'
                    assert await page.locator('.volume-field .v-plane').count() == 12
                    assert await page.locator('.sf-nose-cast').count() == 1
                    cast_display = await page.locator('.sf-nose-cast').evaluate('e=>getComputedStyle(e).display')
                    assert cast_display == ('block' if arm == 'field' else 'none')
                    for width in WIDTHS:
                        for jaw in JAWS:
                            for light in LIGHTS:
                                await page.locator('#param-faceWidth').fill(str(width))
                                await page.locator('#param-jaw').fill(str(jaw))
                                await page.locator('#param-lightDirection').fill(str(light))
                                await page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
                                shot = filename(arm,width,jaw,light)
                                await page.locator('#portrait-paper').screenshot(path=str(OUT/shot))
                                observation = await page.evaluate('''() => {
                                  const root=document.querySelector('#portrait');
                                  const css=name=>root.style.getPropertyValue(name);
                                  const rectangle=selector=>{
                                    const r=document.querySelector(selector).getBoundingClientRect();
                                    return {x:r.x,y:r.y,width:r.width,height:r.height};
                                  };
                                  return {eyeL:rectangle('.eye-left'),eyeR:rectangle('.eye-right'),
                                    nose:rectangle('.nose'),face:rectangle('.face'),
                                    castX:Number.parseFloat(css('--sf-cast-x')),
                                    cheekL:Number.parseFloat(css('--v-cheekLeft-shade')),
                                    cheekR:Number.parseFloat(css('--v-cheekRight-shade')),
                                    hatchLeft:css('--sf-hatch-left-angle'),
                                    scrollWidth:document.documentElement.scrollWidth};
                                }''')
                                assert observation['eyeL']['x'] < observation['eyeR']['x']
                                assert observation['nose']['x'] > observation['eyeL']['x']
                                assert observation['nose']['x'] < observation['eyeR']['x']+observation['eyeR']['width']
                                assert observation['scrollWidth'] <= 1280
                                if arm == 'field':
                                    if light != 0:
                                        assert abs(observation['castX']) > 12
                                    else:
                                        assert abs(observation['castX']) < .1
                                    assert observation['hatchLeft'].endswith('deg')
                                    if light == -60:
                                        assert observation['cheekL'] < observation['cheekR']
                                    if light == 60:
                                        assert observation['cheekL'] > observation['cheekR']
                                observation.update(arm=arm,width=width,jaw=jaw,light=light,file=shot)
                                results.append(observation)
                    if arm == 'field':
                        await page.set_viewport_size({'width':390,'height':844})
                        await page.screenshot(path=str(OUT/'mobile-field.png'), full_page=True)
                        assert await page.evaluate('document.documentElement.scrollWidth') <= 390
                    await page.close()
            finally:
                await browser.close()
    finally:
        server.shutdown()
    assert not exceptions, exceptions
    assert len(results)==36
    for width in WIDTHS:
        for jaw in JAWS:
            l = next(r for r in results if r['arm']=='field' and r['width']==width and r['jaw']==jaw and r['light']==-60)
            r = next(r for r in results if r['arm']=='field' and r['width']==width and r['jaw']==jaw and r['light']==60)
            assert l['castX'] > 0 > r['castX']
            assert l['cheekL'] < l['cheekR'] and r['cheekL'] > r['cheekR']
            a=Image.open(OUT/l['file']).convert('RGB');b=Image.open(OUT/r['file']).convert('RGB')
            assert max(ImageStat.Stat(ImageChops.difference(a,b)).mean) > 0.4
    old=Image.open(OUT/filename('legacy',100,118,0)).convert('RGB')
    new=Image.open(OUT/filename('field',100,118,0)).convert('RGB')
    difference=ImageStat.Stat(ImageChops.difference(old,new)).mean
    assert max(difference) > 0.25, f'New surface field does not visibly change pixels: {difference}'
    sheet=Image.new('RGB',(3*440,2*515),'#eeeae0')
    painter=ImageDraw.Draw(sheet)
    for row,arm in enumerate(ARMS):
        for col,light in enumerate(LIGHTS):
            source=Image.open(OUT/filename(arm,100,118,light)).convert('RGB')
            source.thumbnail((425,490),Image.Resampling.LANCZOS)
            x=col*440+(440-source.width)//2;y=row*515+24
            sheet.paste(source,(x,y))
            painter.text((col*440+11,row*515+4),f'{arm} / jaw 118 / light {light:+d}',fill='#343a35')
    sheet.save(OUT/'contact-sheet.png')
    (OUT/'observations.json').write_text(json.dumps({
      'experiment':'Research 008: relief-derived face normals / CSS painter',
      'frames':len(results),'inline_fallback':fallback,
      'pixel_diff_legacy_vs_field_rgb':difference,
      'observations':results,
      'art_quality':'ART_UNVERIFIED: no independent external ratings',
      'performance':'No GPU/render timing measured in this run'
    },ensure_ascii=False,indent=2), encoding='utf8')
    print(f'RESEARCH_008_VISUAL_PASS: {len(results)} CSS frames, light reversal, nasal occlusion shift, cheek strokes, mobile, no JS exceptions; ART_UNVERIFIED')


if __name__=='__main__':
    asyncio.run(run())
