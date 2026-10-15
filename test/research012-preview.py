"""Visual-first R012 baseline contact sheet. Native HTML/CSS only.

This is diagnostic evidence, not an automatic art-quality pass. Browser
screenshots are not imported into the portrait renderer or served as images.
"""
import asyncio
import base64
import io
import json
import os
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test-results" / "research-012"
IDENTITIES = ("lin-che", "zhou-qishan")
LIGHTS = ("front", "side")
MODES = ("baseline", "form")


async def run():
    OUT.mkdir(parents=True, exist_ok=True)
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)
        def log_message(self, *_args): pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    scenes = []
    errors = []
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                page = await browser.new_page(viewport={"width": 1440, "height": 1050}, device_scale_factor=1)
                page.on("pageerror", lambda error: errors.append(str(error)))
                await page.goto(f"http://127.0.0.1:{server.server_port}/standalone.html")
                for mode in MODES:
                    await page.goto(f"http://127.0.0.1:{server.server_port}/standalone.html" + ("?r012=form" if mode == "form" else ""))
                    for identity in IDENTITIES:
                        await page.locator(f'[data-identity="{identity}"]').click()
                        for light in LIGHTS:
                            await page.locator(f'[data-light-mode="{light}"]').click()
                            await page.evaluate("()=>new Promise(ok=>requestAnimationFrame(()=>requestAnimationFrame(ok)))")
                            evidence = await page.locator("#portrait").evaluate("""el => ({
                                engine: el.dataset.faceEngine,
                                head: el.style.getPropertyValue('--fg-leftJaw-x'),
                                orbit: el.style.getPropertyValue('--fg-leftOrbit-y'),
                                cheek: el.style.getPropertyValue('--v-cheekLeft-shade'),
                                light: el.style.getPropertyValue('--light-elevation')
                            })""")
                            assert evidence["engine"] == "v1", evidence
                            file = OUT / f"{mode}-{identity}-{light}.png"
                            await page.locator("#portrait-paper").screenshot(path=str(file))
                            scenes.append((mode, identity, light, file, evidence))
                assert not errors, errors
            finally:
                await browser.close()
    finally:
        server.shutdown()

    tiles = []
    for mode, identity, light, file, _evidence in scenes:
        photo = Image.open(file).convert("RGB")
        photo.thumbnail((330, 440), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (354, 483), "#ece9e0")
        tile.paste(photo, ((354-photo.width)//2, 31))
        ImageDraw.Draw(tile).text((12, 10), f"{mode.upper()} | {identity} | {light}", fill="#292d28")
        tiles.append(tile)
    contact = Image.new("RGB", (354 * 2, 483 * 4), "#f2efea")
    for index, tile in enumerate(tiles):
        contact.paste(tile, ((index % 2) * 354, (index // 2) * 483))
    contact.save(OUT / "comparison-contact-sheet.jpg", quality=78, optimize=True)
    (OUT / "baseline-metrics.json").write_text(
        json.dumps([{"mode": mode, "identity": i, "light": l, "props": e} for mode, i, l, _, e in scenes], indent=2)
    )
    if os.environ.get("R012_PRINT_PREVIEW") == "1":
        buf = io.BytesIO()
        contact.save(buf, format="JPEG", quality=65, optimize=True)
        print("R012_PREVIEW_BEGIN")
        print(base64.b64encode(buf.getvalue()).decode("ascii"))
        print("R012_PREVIEW_END")
    print("R012_COMPARISON_CAPTURED: 8 real CSS scenes; subjective quality still unverified")


if __name__ == "__main__":
    asyncio.run(run())
