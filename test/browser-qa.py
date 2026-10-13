"""Optional real-browser test. Requires Python Playwright and Chromium.

Run: python3 test/browser-qa.py
Set CHROMIUM_PATH to override the system Chromium executable.
"""
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]

async def run():
    async with async_playwright() as p:
        chromium_path = os.getenv("CHROMIUM_PATH", "/usr/bin/chromium")
        browser = await p.chromium.launch(headless=True, executable_path=chromium_path, args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto((ROOT / "standalone.html").as_uri())
        assert await page.locator('input[type="range"]').count() == 7
        assert await page.locator("#portrait .eye").count() == 2
        assert await page.locator("#portrait img, #portrait svg, #portrait canvas").count() == 0
        await page.locator("#param-faceWidth").fill("115")
        assert await page.locator("#output-faceWidth").inner_text() == "115%"
        assert await page.locator("#portrait").evaluate('(el) => el.style.getPropertyValue("--face-x")') == "1.15"
        await page.locator('[data-preset="gentle"]').click()
        assert await page.locator('[data-preset="gentle"]').get_attribute("aria-pressed") == "true"
        await page.locator("#reset-btn").click()
        assert await page.locator("#output-faceWidth").inner_text() == "100%"
        await page.set_viewport_size({"width": 390, "height": 844})
        assert await page.evaluate("document.documentElement.scrollWidth") <= 390
        assert errors == [], f"Browser errors: {errors}"
        await browser.close()
    print("BROWSER_QA_PASS: portrait, 7 controls, live preview, preset, reset, responsive, no JS errors")

if __name__ == "__main__":
    asyncio.run(run())
