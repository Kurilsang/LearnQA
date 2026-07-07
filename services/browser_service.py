import asyncio
from playwright.async_api import async_playwright

from config import config


class BrowserService:

    @staticmethod
    async def launch():
        p = await async_playwright().start()
        browser = await p.chromium.launch(
            headless=config.HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        return p, browser, context, page

    @staticmethod
    async def close(browser, playwright):
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()
