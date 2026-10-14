"""Research 007: A/B real Chromium CSS FaceGeometry evaluation.

54 screenshots = (fixed-anchor vs shared-anchor) x (3 face widths) x
(3 jaw shapes) x (3 light directions). These are geometry/paint assertions,
not human perception experiments or an isolated GPU benchmark.
"""
import asyncio
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from statistics import median
from threading import Thread

from PIL import Image, ImageChops, ImageDraw, ImageStat
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results' / 'research-007'
ARMS = ('baseline', 'structured')
WIDTHS = (80, 100, 120)
JAWS = (82, 100, 118)
LIGHTS = (-60, 0, 60)


def frame_name(arm, width, jaw, light):
    return f'{arm}-width-{width}-jaw-{jaw}-light-{light:+d}.png'


async def run():
    OUT.mkdir(parents=True, exist_ok=True)
    observations, page_errors, response_errors = [], [], []

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    base_url = f'http://127.0.0.1:{server.server_port}'
    inline_fallback = os.getenv('PORTRAIT_QA_INLINE') == '1'
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                executable_path=os.getenv('CHROMIUM_PATH') or
                ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None),
                args=['--no-sandbox'], headless=True)
            page = await browser.new_page(viewport={'width': 1280, 'height': 900},
                                          device_scale_factor=1)
            page.on('pageerror', lambda exc: page_errors.append(str(exc)))
            for arm in ARMS:
                if not inline_fallback:
                    try:
                        await page.goto(f'{base_url}/standalone.html?r007={arm}')
                    except Exception as exc:
                        if 'ERR_BLOCKED_BY_ADMINISTRATOR' not in str(exc):
                            raise
                        inline_fallback = True
                        await page.close()
                        page = await browser.new_page(viewport={'width': 1280, 'height': 900},
                                                      device_scale_factor=1)
                        page.on('pageerror', lambda error: page_errors.append(str(error)))
                if inline_fallback:
                    html = (ROOT / 'standalone.html').read_text(encoding='utf8')
                    assert "const faceVariant = qs.get('r007');" in html
                    html = html.replace("const faceVariant = qs.get('r007');",
                                        f"const faceVariant = '{arm}';")
                    await page.set_content(html)

                root = page.locator('#portrait')
                assert await root.get_attribute('data-r007') == arm
                assert await root.get_attribute('data-r006') == 'volume'
                assert await page.locator('.volume-field').evaluate(
                    '(el) => getComputedStyle(el).display') == 'block'
                assert await page.locator('input[type=range]').count() == 9
                assert await page.locator('#portrait img,#portrait svg,#portrait canvas').count() == 0
                assert await page.locator('.eye-left').count() == 1
                raf = []
                for _ in range(5):
                    raf.append(await page.evaluate('''async () => {
                        const start = performance.now();
                        await new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)));
                        return performance.now() - start;
                    }'''))
                observations.append({'arm':arm,'measure':'two-frame-scheduling',
                                     'median_ms':round(median(raf),2),
                                     'note':'includes rAF scheduling, NOT pure GPU paint time'})
                for width in WIDTHS:
                    for jaw in JAWS:
                        for light in LIGHTS:
                            await page.locator('#param-faceWidth').fill(str(width))
                            await page.locator('#param-jaw').fill(str(jaw))
                            await page.locator('#param-lightDirection').fill(str(light))
                            await page.evaluate('''() => new Promise(done =>
                              requestAnimationFrame(() => requestAnimationFrame(done)))''')
                            filename = frame_name(arm,width,jaw,light)
                            await page.locator('#portrait-paper').screenshot(path=str(OUT/filename))
                            obs = await page.evaluate('''() => {
                              const root = document.querySelector('#portrait');
                              const f = document.querySelector('.face');
                              const box = sel => {
                                const rect = document.querySelector(sel).getBoundingClientRect();
                                return {x:rect.x,y:rect.y,width:rect.width,height:rect.height};
                              };
                              const left = (sel) => parseFloat(getComputedStyle(document.querySelector(sel)).left);
                              const prop = key => parseFloat(root.style.getPropertyValue(`--fg-${key}-x`));
                              const shade = key => Number(root.style.getPropertyValue(`--v-${key}-shade`));
                              return { face:box('.face'),leftEye:box('.eye-left'),rightEye:box('.eye-right'),
                                nose:box('.nose'),jaw:box('.jaw-plane-left'),
                                leftEyeCss:left('.eye-left'),leftOrbitCss:left('.eye-socket-left'),
                                noseCss:left('.nose'),leftAlaCss:left('.nasal-plane-left'),
                                jawCss:left('.jaw-plane-left'),jawlineCss:left('.jawline-left'),
                                cheekCss:left('.malar-left'),cheekPlaneCss:left('.cheek-plane-left'),
                                fgEye:prop('leftEye'),fgAla:prop('leftAla'),fgNose:prop('noseRoot'),
                                fgJaw:prop('leftJaw'),fgCheek:prop('leftCheek'),
                                shadeLeft:shade('cheekLeft'),shadeRight:shade('cheekRight'),
                                scrollWidth:document.documentElement.scrollWidth,
                                htmlWidth:document.documentElement.clientWidth,
                                portraitNodes:root.querySelectorAll('*').length,
                                paintCandidates:getComputedStyle(f).transform
                              };
                            }''')
                            assert obs['leftEye']['x'] < obs['rightEye']['x'], obs
                            assert obs['leftEye']['x'] >= obs['face']['x'] - 4, obs
                            assert obs['rightEye']['x'] + obs['rightEye']['width'] <= (
                                obs['face']['x'] + obs['face']['width'] + 4), obs
                            assert obs['scrollWidth'] <= obs['htmlWidth'] + 1, obs
                            if arm == 'structured':
                                for actual, expected in (
                                    (obs['leftEyeCss']+30.5, obs['fgEye']),
                                    (obs['leftOrbitCss']+41.5, obs['fgEye']),
                                    (obs['noseCss']+32, obs['fgNose']),
                                    (obs['leftAlaCss']+14.5, obs['fgAla']),
                                    (obs['jawCss']+23.5, obs['fgJaw']),
                                    (obs['jawlineCss']+17.5, obs['fgJaw']),
                                    (obs['cheekCss']+39.5, obs['fgCheek']),
                                    (obs['cheekPlaneCss']+43.5, obs['fgCheek']),
                                ):
                                    assert abs(actual-expected)<0.7, (arm,width,jaw,light,actual,expected)
                            obs.update({'arm':arm,'width':width,'jaw':jaw,'light':light,
                                        'filename':filename})
                            observations.append(obs)
                if arm == 'structured':
                    await page.set_viewport_size({'width':390,'height':844})
                    await page.locator('#param-faceWidth').fill('120')
                    await page.locator('#param-jaw').fill('118')
                    await page.screenshot(path=str(OUT/'mobile-structured.png'),full_page=True)
                    assert await page.evaluate('document.documentElement.scrollWidth') <= 390
            # Test local-only anonymous ratings. This is a FORM workflow smoke test;
            # generated scores are discarded and are not human art preferences.
            if inline_fallback:
                await page.set_content((ROOT/'study'/'007-blind.html').read_text(encoding='utf8'))
            else:
                await page.goto(f'{base_url}/study/007-blind.html')
            assert await page.locator('iframe').count() == 2
            sources = await page.locator('iframe').evaluate_all(
                'els=>els.map(x=>x.getAttribute("src"))')
            assert any('r007=structured' in url for url in sources)
            assert any('r007=baseline' in url for url in sources)
            assert await page.locator('select').count() == 8
            for choice in await page.locator('select').all():
                await choice.select_option('4')
            async with page.expect_download() as expected:
                await page.get_by_role('button',name='导出匿名评分 JSON').click()
            download=await expected.value
            assert download.suggested_filename == 'portrait-engine-r007-blind-rating.json'
            data=json.loads(Path(await download.path()).read_text(encoding='utf8'))
            assert data['protocol']=='portrait-engine-r007-blind'
            assert len(data['candidates'])==2
            assert {x['variant'] for x in data['candidates']}==set(ARMS)
            assert all(x['scores']['whole']==4 for x in data['candidates'])
            # This mock export is intentionally never archived as a genuine score.
            await browser.close()
    finally:
        server.shutdown()

    assert not page_errors, page_errors
    assert not response_errors, response_errors
    # Light response remains the SAME for both A/B arms (Research 006 model).
    for arm in ARMS:
        left = next(o for o in observations if o.get('arm') == arm and o.get('width') == 100
                    and o.get('jaw') == 100 and o.get('light') == -60)
        right = next(o for o in observations if o.get('arm') == arm and o.get('width') == 100
                     and o.get('jaw') == 100 and o.get('light') == 60)
        assert left['shadeLeft'] < left['shadeRight']
        assert right['shadeRight'] < right['shadeLeft']

    # Detect a genuine paint change, not a label/UI change. Pixel differences
    # cannot tell which one a person prefers or which is more anatomically correct.
    pixel_differences = []
    for width in WIDTHS:
        for jaw in JAWS:
            a = Image.open(OUT/frame_name('baseline',width,jaw,0)).convert('RGB')
            b = Image.open(OUT/frame_name('structured',width,jaw,0)).convert('RGB')
            values = ImageStat.Stat(ImageChops.difference(a,b)).mean
            assert max(values) > 0.15, (width,jaw,values)
            pixel_differences.append({'faceWidth':width,'jaw':jaw,
                                      'rgb_mean_delta':[round(v,3) for v in values]})

    sample = Image.open(OUT/frame_name('baseline',100,100,-60)).convert('RGB')
    w,h = sample.size
    sheet = Image.new('RGB',(3*w+4*12,2*h+3*36),'#eeeae0')
    draw = ImageDraw.Draw(sheet)
    for row,arm in enumerate(ARMS):
        for col,light in enumerate(LIGHTS):
            img = Image.open(OUT/frame_name(arm,100,100,light)).convert('RGB')
            x = 12 + col*(w+12)
            y = 36 + row*(h+36)
            sheet.paste(img,(x,y))
            draw.text((x,y-20),f'{arm} / 100% face / 100% jaw / light {light:+d}',fill='#313a31')
    sheet.save(OUT/'contact-sheet.png')
    (OUT/'observations.json').write_text(json.dumps({
        'research':'Research 007 FaceGeometry', 'observations':observations,
        'pixel_differences':pixel_differences,'total_screenshots':54,
        'inline_fallback':inline_fallback,
        'art_quality':'ART_UNVERIFIED: no independent human blind scores',
        'performance':'Two-frame scheduling only, no GPU rendering time claimed'
    },indent=2), encoding='utf8')
    print('RESEARCH_007_VISUAL_PASS: 54 actual CSS frames (27 A/27 B),'
          ' shared geometry, light, mobile, screenshots; ART_UNVERIFIED')


if __name__ == '__main__':
    asyncio.run(run())
