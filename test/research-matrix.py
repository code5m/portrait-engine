"""Render a reproducible 3x3 head-width by key-light study in Chromium.

This is QA evidence, not a runtime image asset. All nine source portraits are CSS.
Run: python3 test/research-matrix.py
"""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageStat, ImageChops
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(os.environ.get('PORTRAIT_MATRIX_DIR', str(ROOT / 'test-results' / 'research-003')))
WIDTHS = (80, 100, 120)
LIGHTS = (-60, 0, 60)

def embed():
    spec = importlib.util.spec_from_file_location('browser_qa', ROOT / 'test' / 'browser-qa.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.embedded_page()

async def run():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    observations = []
    errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_PATH') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None), args=['--no-sandbox'])
        page = await browser.new_page(viewport={'width':1440,'height':1050},device_scale_factor=1)
        page.on('pageerror', lambda err: errors.append(str(err)))
        await page.set_content(embed())
        assert await page.locator('input[type=range]').count() == 9
        for width in WIDTHS:
            for light in LIGHTS:
                await page.locator('#param-faceWidth').fill(str(width))
                await page.locator('#param-lightDirection').fill(str(light))
                await page.wait_for_timeout(80)
                root = page.locator('#portrait')
                box = await root.bounding_box()
                face = await page.locator('.face').bounding_box()
                l_eye = await page.locator('.eye-left').bounding_box()
                r_eye = await page.locator('.eye-right').bounding_box()
                ear_l = await page.locator('.ear-left').bounding_box()
                ear_r = await page.locator('.ear-right').bounding_box()
                hair = await page.locator('.hair-cap').bounding_box()
                paper = page.locator('#portrait-paper')
                name = f'head-{width}-light-{light:+d}.png'
                await paper.screenshot(path=str(OUTPUT/name))
                def rel(ob):
                    return {'x':round(ob['x']-box['x'],2),'y':round(ob['y']-box['y'],2),'w':round(ob['width'],2),'h':round(ob['height'],2)}
                facts={'width':width,'light':light,'file':name,
                       'face':rel(face),'left_eye':rel(l_eye),'right_eye':rel(r_eye),
                       'left_ear':rel(ear_l),'right_ear':rel(ear_r),'hair_cap':rel(hair),
                       'plane_shadow_left':await root.evaluate('(x)=>x.style.getPropertyValue("--plane-shade-left")'),
                       'plane_shadow_right':await root.evaluate('(x)=>x.style.getPropertyValue("--plane-shade-right")')}
                # All eyes and ears must stay inside the 380px portrait coordinate space.
                assert 0 <= facts['left_eye']['x'] < facts['right_eye']['x']
                assert 0 <= facts['left_ear']['x'] < facts['right_ear']['x']
                assert facts['left_eye']['x'] > facts['face']['x']
                assert facts['right_eye']['x'] + facts['right_eye']['w'] <= facts['face']['x']+facts['face']['w'] + 2
                observations.append(facts)
                print(f"captured width={width} light={light:+d}: face={facts['face']} shadowL/R={facts['plane_shadow_left']}/{facts['plane_shadow_right']}")
        await page.set_viewport_size({'width':390,'height':844})
        assert await page.evaluate('document.documentElement.scrollWidth') <= 390
        await page.locator('#portrait-paper').screenshot(path=str(OUTPUT/'phone-paper.png'))
        await browser.close()
    assert not errors, errors
    # Constrain rendering invariants to observable DOM and pixels; do not claim
    # these tests can judge whether a drawing is aesthetically realistic.
    for width in WIDTHS:
        samples=[next(x for x in observations if x['width']==width and x['light']==v) for v in LIGHTS]
        assert float(samples[0]['plane_shadow_right'])>float(samples[0]['plane_shadow_left'])
        assert float(samples[2]['plane_shadow_left'])>float(samples[2]['plane_shadow_right'])
        im_l=Image.open(OUTPUT/samples[0]['file']).convert('RGB')
        im_r=Image.open(OUTPUT/samples[2]['file']).convert('RGB')
        diff=ImageStat.Stat(ImageChops.difference(im_l, im_r)).mean
        assert max(diff)>0.4, f'Lighting change did not change visible pixels: {diff}'
    sheet=Image.new('RGB',(3*410+4*17,3*540+4*48),(238,235,227))
    draw=ImageDraw.Draw(sheet)
    for ri, width in enumerate(WIDTHS):
        for ci,light in enumerate(LIGHTS):
            im=Image.open(OUTPUT/f'head-{width}-light-{light:+d}.png').convert('RGB')
            im.thumbnail((410,500),Image.Resampling.LANCZOS)
            left=17+ci*(410+17)+(410-im.width)//2
            top=45+ri*(540+48)
            sheet.paste(im,(left,top))
            draw.text((17+ci*(410+17),top-24),f'face width {width}% / light {light:+d} deg',fill=(52,52,48))
    sheet.save(OUTPUT/'contact-sheet.png')
    (OUTPUT/'measurements.json').write_text(json.dumps({'cases':observations,'browser':'Chromium','viewport':'1440 x 1050','note':'These are structural/pixel smoke checks, NOT a professional art quality certification.'},indent=2))
    print('RESEARCH_MATRIX_PASS: 9 screenshots, distinct light direction, containment, mobile, no page errors')

if __name__ == '__main__':
    asyncio.run(run())
