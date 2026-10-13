"""Optional browser smoke tests. Requires `python3 -m pip install playwright` and Chromium.
The test creates a self-contained in-memory page so it can run without HTTP access.
It DOES NOT replace testing real module HTTP serving before production deployment.
"""
import asyncio
import os
import pathlib
import re
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]

def embedded_page():
    html = (ROOT / 'index.html').read_text()
    for name in ('layout', 'portrait', 'anatomy', 'graphite', 'likeness'):
        css = (ROOT / 'styles' / f'{name}.css').read_text()
        html = html.replace(f'<link rel="stylesheet" href="./styles/{name}.css">', f'<style>{css}</style>')
    assert '<link rel="stylesheet"' not in html, 'QA did not inline every CSS file'
    code = '\n'.join(re.sub(r'^export ', '', (ROOT / 'src' / f'{name}.mjs').read_text(), flags=re.M) for name in ('parameters','geometry','i18n','app'))
    code = re.sub(r'^import .*?;\n', '', code, flags=re.M)
    return html.replace('<script type="module" src="./src/app.mjs"></script>',f'<script type="module">{code}</script>')

async def run():
    screenshot_dir = pathlib.Path(os.environ.get('PORTRAIT_QA_DIR', '/tmp'))
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_PATH') or ('/usr/bin/chromium' if pathlib.Path('/usr/bin/chromium').exists() else None), args=['--no-sandbox'])
        page = await browser.new_page(viewport={'width':1440,'height':1000})
        errors = []
        page.on('pageerror', lambda err: errors.append(str(err)))
        await page.set_content(embedded_page())
        assert await page.locator('input[type="range"]').count() == 9
        assert await page.locator('h1').inner_text() == '\u7528\u4ee3\u7801\uff0c\u753b\u51fa\u4e00\u5f20\u8138\u3002'
        assert await page.locator('#portrait img, #portrait svg, #portrait canvas').count() == 0
        await page.screenshot(path=str(screenshot_dir / 'portrait-desktop.png'),full_page=True)
        await page.locator('#param-faceWidth').fill('115')
        assert await page.locator('#output-faceWidth').inner_text() == '115%'
        assert await page.locator('#portrait').evaluate('(e)=>e.style.getPropertyValue("--face-x")') == '1.15'
        await page.locator('[data-preset="gentle"]').click()
        assert await page.locator('[data-preset="gentle"]').get_attribute('aria-pressed') == 'true'
        await page.locator('#param-lightDirection').fill('60')
        assert await page.locator('#portrait').evaluate('(e)=>e.style.getPropertyValue("--light-x")') == '72.0%'
        await page.locator('[data-study-mode="structure"]').click()
        assert await page.locator('#portrait').get_attribute('data-study') == 'structure'
        assert await page.locator('[data-study-mode="structure"]').get_attribute('aria-pressed') == 'true'
        assert await page.locator('.construction-guides').is_visible()
        await page.locator('[data-study-mode="graphite"]').click()
        assert await page.locator('.construction-guides').is_hidden()
        await page.locator('#reset-btn').click()
        assert await page.locator('#output-faceWidth').inner_text() == '100%'
        await page.set_viewport_size({'width':390,'height':844})
        await page.screenshot(path=str(screenshot_dir / 'portrait-mobile.png'),full_page=True)
        assert await page.evaluate('document.documentElement.scrollWidth') <= 390
        assert errors == [], f'Uncaught page errors: {errors}'
        await browser.close()
    print('BROWSER_QA_PASS: CSS portrait visible; 9 inputs; live params; presets; reset; responsive; no page errors')

if __name__ == '__main__':
    asyncio.run(run())
