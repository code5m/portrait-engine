"""Capture CSS calibration. Pixels are QA output, never renderer input."""
import asyncio, hashlib, json, math, os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results/sketch-s0'
CONFIG=json.loads((ROOT/'research/sketch/s0-scenes.json').read_text())
def expected(profile,light):
    size=CONFIG['frameSize']; axes=np.array(profile['radii']); l=np.array(light['direction']);l/=np.linalg.norm(l)
    coords=(np.arange(size)+.5-size/2)*(CONFIG['orthoScale']/size)
    x,y=np.meshgrid(coords,-coords);q=(x/axes[0])**2+(y/axes[1])**2
    z=axes[2]*np.sqrt(np.maximum(0,1-q))
    normals=np.stack([x/axes[0]**2,y/axes[1]**2,z/axes[2]**2],axis=-1)
    normals/=np.maximum(np.linalg.norm(normals,axis=-1,keepdims=True),1e-9)
    value=CONFIG['ambient']+CONFIG['direct']*np.maximum(0,normals@l)
    value=np.where(value<=.0031308,12.92*value,1.055*value**(1/2.4)-.055)*255
    return value,q<.92
async def run():
    OUT.mkdir(parents=True,exist_ok=True); results=[];images=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_PATH') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None),args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':1100,'height':1000},device_scale_factor=1,reduced_motion='reduce')
        requests=[];errors=[]
        page.on('request',lambda req:requests.append(req.url) if req.url.startswith(('http:','https:')) else None)
        page.on('pageerror',lambda error:errors.append(str(error)))
        for profile in CONFIG['profiles']:
            for light in CONFIG['lights']:
                scene=profile['id']+'-'+light['id']
                if os.getenv('S0_INLINE') == '1':
                    assert not os.getenv('GITHUB_ACTIONS'), 'CI must use real file navigation'
                    text=(OUT/'lab.html').read_text().replace('new URLSearchParams(location.search)', 'new URLSearchParams('+json.dumps('?scene='+scene)+')')
                    await page.set_content(text)
                else:
                    await page.goto((OUT/'lab.html').as_uri()+'?scene='+scene)
                await page.wait_for_selector('html[data-ready="true"]')
                form=page.locator('.scene');assert await form.count()==1
                assert await form.locator('img,svg,canvas,video').count()==0
                assert await form.locator('i').count()==CONFIG['bands']
                file=OUT/('css-'+scene+'.png');await form.screenshot(path=str(file))
                img=Image.open(file).convert('RGB');actual=np.asarray(img).mean(axis=-1);value,mask=expected(profile,light)
                error=np.abs(actual-value)[mask]
                record={'scene':scene,'meanError':round(float(error.mean()),4),'p95Error':round(float(np.quantile(error,.95)),4),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'patchCount':CONFIG['bands']}
                results.append(record);images.append(img)
        for profile in CONFIG['profiles']:
            scene=profile['id']+'-left';query='?scene='+scene+'&levels=3'
            if os.getenv('S0_INLINE') == '1':
                text=(OUT/'lab.html').read_text().replace('new URLSearchParams(location.search)', 'new URLSearchParams('+json.dumps(query)+')')
                await page.set_content(text)
            else: await page.goto((OUT/'lab.html').as_uri()+query)
            await page.wait_for_selector('html[data-ready="true"]')
            assert await page.locator('.scene i').count()==3
            await page.locator('.scene').screenshot(path=str(OUT/('css3-'+scene+'.png')))
        assert not errors,errors;assert not requests,requests
        await browser.close()
    sheet=Image.new('RGB',(3*256,3*284),'white');draw=ImageDraw.Draw(sheet)
    for i,img in enumerate(images):
        x=i%3*256;y=i//3*284;sheet.paste(img,(x,y+28));draw.text((x+8,y+8),results[i]['scene'],fill='black')
    sheet.save(OUT/'css-contact.jpg',quality=85)
    (OUT/'css-metrics.json').write_text(json.dumps({'scope':'geometric calibration; not human realism','results':results,'browserErrors':errors,'externalRequests':requests,'transport':'sandbox-inline' if os.getenv('S0_INLINE')=='1' else 'file'},indent=2))
    print(json.dumps(results,indent=2))
if __name__=='__main__': asyncio.run(run())
