"""用 Playwright 驅動前端，截圖驗證填表展示流程。"""
import asyncio
import sys

from playwright.async_api import async_playwright

URL = "http://127.0.0.1:5173/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/demo_shot.png"
IMG = sys.argv[2] if len(sys.argv) > 2 else "/home/joshhu/workspace/autofillform/example.jpg"


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        page = await b.new_page(viewport={"width": 1366, "height": 820})
        await page.goto(URL, wait_until="networkidle")
        # 上傳表單截圖
        await page.set_input_files("input[type=file]", IMG)
        await page.wait_for_timeout(800)
        # 按「開始填表」
        await page.click("text=開始填表")
        # 等串流跑完（出現「完成」或逾時）；中途也存一張
        mid_saved = False
        for i in range(240):
            await page.wait_for_timeout(1000)
            txt = await page.inner_text("body")
            if not mid_saved and ("定位" in txt or "📍" in txt):
                await page.screenshot(path=OUT.replace(".png", "_mid.png"))
                mid_saved = True
            if "✅ 完成" in txt:
                break
        await page.wait_for_timeout(1500)
        await page.screenshot(path=OUT, full_page=False)
        print("screenshot ->", OUT)
        await b.close()


asyncio.run(main())
