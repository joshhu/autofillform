"""選配：真實自動填表執行器（Playwright）。

把填寫計畫裡的座標換算成實際頁面上的點擊與輸入。截圖是對某網址擷取的，
因此這裡用同一網址開頁、依 viewport 縮放座標、逐欄點擊輸入，最後回傳結果截圖。
需要時才安裝 playwright（見 README）。
"""
from __future__ import annotations

from app.schemas import AutofillResponse


async def execute_plan(url: str, result: AutofillResponse, viewport_width: int = 1280) -> bytes:
    """對 url 開頁，依計畫填入並回傳填好後的截圖 (PNG bytes)。"""
    from playwright.async_api import async_playwright

    scale = viewport_width / result.image_width
    viewport_height = int(result.image_height * scale)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": viewport_width, "height": viewport_height}
        )
        await page.goto(url, wait_until="networkidle")
        for item in result.plan:
            if not item.point:
                continue
            x, y = item.point[0] * scale, item.point[1] * scale
            await page.mouse.click(x, y)
            await page.keyboard.type(item.value, delay=20)
        png = await page.screenshot()
        await browser.close()
        return png
