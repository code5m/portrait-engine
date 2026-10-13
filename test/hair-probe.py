"""Reproducible, isolated CSS hair-opacity studies using a real browser.

All source pictures are direct CSS renderings. The screenshot files are QA
artifacts only and never enter the portrait's runtime rendering path.
"""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageStat, ImageChops
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path(os.getenv('PORTRAIT_MATRIX_DIR', str(ROOT / 'test-results' / 'research-004')))
VALUES = {
    'dense-previous': ('1', '.95', '.95'),
    'almost-clear': ('.05', '.6', '.95'),
    'light-ink-selected': ('.23', '.8', '.95'),
    'washed-graphite': ('.38', '.55', '.85'),
}


def embedded_page():
    spec = importlib.util.spec_from_file_location('browser_qa', ROOT / 'test' / 'browser-qa.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.embedded_page()


def tonal_coverage(im):
    # Defined paper-relative measurement, not a realism or beauty metric.
    head = im.convert('L').crop((50, 72, 414, 500))
    return sum(1 for value in head.get_flattened_data() if value < 90) / (head.width * head.height)


async def run():
    TARGET.mkdir(parents=True, exist_ok=True)
    errors = []
    images = {}
    metrics = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=os.getenv('CHROMIUM_PATH') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None),
            args=['--no-sandbox'],
        )
        page = await browser.new_page(viewport={'width': 1440, 'height': 1050})
        page.on('pageerror', lambda error: errors.append(str(error)))
        await page.set_content(embedded_page())
        await page.locator('#param-lightDirection').fill('0')
        assert await page.locator('#portrait .flyaway').count() == 4
        for name, (front, behind, cap) in VALUES.items():
            # Overrides are temporary test CSS: no source edits and no script-generated image.
            injection = await page.add_style_tag(content=(
                f'.portrait .hair-lock{{opacity:{front}!important}}'
                f'.portrait .hair-behind{{opacity:{behind}!important}}'
                f'.portrait .hair-cap{{opacity:{cap}!important}}'
            ))
            filepath = TARGET / f'hair-{name}.png'
            await page.locator('#portrait-paper').screenshot(path=str(filepath))
            images[name] = Image.open(filepath).convert('RGB')
            metrics.append({'name': name, 'hair_lock_opacity': front,
                            'rear_hair_opacity': behind, 'cap_opacity': cap,
                            'head_dark_fraction': round(tonal_coverage(images[name]), 5)})
            await injection.evaluate('(node) => node.remove()')
        await browser.close()
    assert not errors, errors
    assert len({round(v['head_dark_fraction'], 3) for v in metrics}) >= 3, 'Hair alternatives have indistinguishable tonal behavior'
    w, h = 4 * 470, 635
    sheet = Image.new('RGB', (w, h), (239, 237, 230))
    draw = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate(images.items()):
        sample = im.copy()
        sample.thumbnail((458, 585))
        sheet.paste(sample, (i*470+6, 22))
        draw.text((i*470+13, 7), name, fill=(44, 44, 42))
    sheet.save(TARGET / 'hair-alternatives.png')
    (TARGET/'hair-measurements.json').write_text(json.dumps({
        'environment': 'Chromium, 1440x1050, lightDirection=0',
        'head_region': [50, 72, 414, 500],
        'intensity_threshold': 90,
        'source': 'original HTML and CSS only',
        'warning': 'Dark coverage is an objective count, NOT an artist beauty score.',
        'variants': metrics,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print('HAIR_PROBE_PASS:', ', '.join(f"{x['name']}={x['head_dark_fraction']:.3f}" for x in metrics))

if __name__ == '__main__':
    asyncio.run(run())
