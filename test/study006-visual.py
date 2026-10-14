"""Research 006: CSS-only independent A/B value-plane experiment.
Records DOM geometry, key-light response, screenshot pixels, and a sampled frame-time
proxy. The evidence is NOT proof that the drawing is more realistic to humans.
"""
import asyncio
import json
import os
from pathlib import Path
from statistics import median
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from PIL import Image, ImageDraw, ImageChops, ImageStat
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=Path(os.environ.get('PORTRAIT_STUDY006_DIR',ROOT/'test-results'/'research-006'))
WIDTHS=(80,100,120)
LIGHTS=(-60,0,60)

async def run():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    observations=[]
    errors=[]
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    Thread(target=server.serve_forever,daemon=True).start()
    base_url=f'http://127.0.0.1:{server.server_port}'
    inline_fallback=os.getenv('PORTRAIT_QA_INLINE')=='1'
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_PATH') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None),args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':1280,'height':900},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        for variant in ('baseline','volume'):
            if not inline_fallback:
                try:
                    await page.goto(f'{base_url}/standalone.html?r006={variant}')
                except Exception as e:
                    if 'ERR_BLOCKED_BY_ADMINISTRATOR' not in str(e): raise
                    inline_fallback=True
                    await page.close()
                    page=await browser.new_page(viewport={'width':1280,'height':900},device_scale_factor=1)
                    page.on('pageerror',lambda err:errors.append(str(err)))
            if inline_fallback:
                html=(ROOT/'standalone.html').read_text(encoding='utf8')
                assert "const volumeVariant = qs.get('r006');" in html
                html=html.replace("const volumeVariant = qs.get('r006');", f"const volumeVariant = '{variant}';")
                await page.set_content(html)
            assert await page.locator('#portrait .volume-field .v-plane').count()==12
            assert await page.locator('#portrait img, #portrait svg, #portrait canvas').count()==0
            assert await page.locator('input[type="range"]').count()==9
            if variant=='volume':
                assert await page.locator('#portrait').get_attribute('data-r006')=='volume'
                assert await page.locator('.volume-field').evaluate('el=>getComputedStyle(el).display')=='block'
            else:
                assert await page.locator('.volume-field').evaluate('el=>getComputedStyle(el).display')=='none'
            frame_samples=[]
            for _ in range(6):
                frame_samples.append(await page.evaluate('''async ()=>{
                    const t=performance.now();
                    await new Promise(ok=>requestAnimationFrame(()=>requestAnimationFrame(ok)));
                    return performance.now()-t;
                }'''))
            # This measures two-frame scheduling, not isolated GPU paint duration.
            observations.append({'variant':variant,'probe':'two-frame-scheduling',
                                 'median_ms':round(median(frame_samples),2)})
            for width in WIDTHS:
                for light in LIGHTS:
                    await page.locator('#param-faceWidth').fill(str(width))
                    await page.locator('#param-lightDirection').fill(str(light))
                    await page.wait_for_timeout(70)
                    # Force paint after CSS variables changed, not just DOM events.
                    await page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
                    img_name=f'{variant}-width-{width}-light-{light:+d}.png'
                    await page.locator('#portrait-paper').screenshot(path=str(OUTPUT/img_name))
                    obs=await page.evaluate('''() => {
                      const b=(sel)=>{const r=document.querySelector(sel).getBoundingClientRect();return [r.x,r.y,r.width,r.height].map(x=>Math.round(x*100)/100)};
                      const portrait=document.querySelector('#portrait');
                      const shadow=(id)=>Number(portrait.style.getPropertyValue(`--v-${id}-shade`));
                      const volume=document.querySelector('.v-cheek-left');
                      return {face:b('.face'),leftEye:b('.eye-left'),rightEye:b('.eye-right'),
                        shadowLeft:shadow('cheekLeft'),shadowRight:shadow('cheekRight'),
                        planeOpacity:getComputedStyle(volume).opacity,
                        bodyWidth:document.documentElement.scrollWidth};
                    }''')
                    assert obs['leftEye'][0]<obs['rightEye'][0]
                    assert obs['leftEye'][0]>obs['face'][0]
                    assert obs['rightEye'][0]+obs['rightEye'][2]<obs['face'][0]+obs['face'][2]+5
                    obs.update({'variant':variant,'width':width,'light':light,'file':img_name})
                    observations.append(obs)
            if variant=='volume':
                await page.locator('#param-graphite').fill('20')
                shadow_before=await page.locator('#portrait').evaluate('el=>el.style.getPropertyValue("--v-cheekLeft-shade")')
                await page.locator('#param-graphite').fill('100')
                shadow_after=await page.locator('#portrait').evaluate('el=>el.style.getPropertyValue("--v-cheekLeft-shade")')
                assert float(shadow_before)<float(shadow_after)
                await page.set_viewport_size({'width':390,'height':844})
                await page.screenshot(path=str(OUTPUT/'mobile-volume.png'),full_page=True)
                assert await page.evaluate('document.documentElement.scrollWidth')<=390
        await browser.close()
    server.shutdown()
    assert not errors,errors
    # Numerical consistency is tested separately from the actual visual output.
    vol=[o for o in observations if o['variant']=='volume' and 'width' in o]
    for width in WIDTHS:
        left=next(o for o in vol if o['width']==width and o['light']==-60)
        right=next(o for o in vol if o['width']==width and o['light']==60)
        assert left['shadowLeft']<left['shadowRight']
        assert right['shadowRight']<right['shadowLeft']
        a=Image.open(OUTPUT/left['file']).convert('RGB')
        b=Image.open(OUTPUT/right['file']).convert('RGB')
        assert max(ImageStat.Stat(ImageChops.difference(a,b)).mean)>0.5
    old=Image.open(OUTPUT/'baseline-width-100-light-+0.png').convert('RGB')
    new=Image.open(OUTPUT/'volume-width-100-light-+0.png').convert('RGB')
    diff=ImageStat.Stat(ImageChops.difference(old,new)).mean
    assert max(diff)>0.5, f'Candidate did not visibly change the rendered pixels: {diff}'
    sheet=Image.new('RGB',(3*420+4*20,2*500+3*46),'#eceae4')
    draw=ImageDraw.Draw(sheet)
    for row,variant in enumerate(('baseline','volume')):
        for col,light in enumerate(LIGHTS):
            im=Image.open(OUTPUT/f'{variant}-width-100-light-{light:+d}.png').convert('RGB')
            im.thumbnail((420,475),Image.Resampling.LANCZOS)
            x=20+col*440+(420-im.width)//2
            y=42+row*546
            sheet.paste(im,(x,y))
            draw.text((20+col*440,y-19),f'{variant} / light {light:+d}',fill='#3a413d')
    sheet.save(OUTPUT/'contact-sheet.png')
    (OUTPUT/'observations.json').write_text(json.dumps({'cases':observations,'difference_r006_vs_baseline_rgb':diff,'inline_fallback':inline_fallback,'automated_conclusion':'Geometry, browser rendering and pixel change verified; human aesthetic judgment NOT assessed.'},indent=2),encoding='utf8')
    print(f'RESEARCH_006_VISUAL_PASS: 18 CSS images; 9 matched pairs; directional light; mobile; diff={diff}; no JS errors')

if __name__=='__main__':
    asyncio.run(run())
