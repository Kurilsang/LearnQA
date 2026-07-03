import asyncio
from typing import Optional, List

from playwright.async_api import Page


class BasePage:
    def __init__(self, page: Page, site_config):
        self.page = page
        self.site = site_config

    @property
    def page_key(self) -> str:
        name = type(self).__name__
        parts = []
        for i, c in enumerate(name):
            if c.isupper() and i > 0:
                parts.append("_")
            parts.append(c.lower())
        return "".join(parts)

    def el(self, name: str):
        selector = self.site.get_element(self.page_key, name)
        if selector is None:
            raise KeyError(
                f"Element '{name}' not found in page '{self.page_key}'"
            )
        return self.page.locator(selector)

    def el_group(self, name: str) -> list:
        return self.site.get_group(self.page_key, name)

    def script(self, name: str) -> Optional[str]:
        return self.site.get_script(self.page_key, name)

    async def evaluate_script(self, script_name: str, *args):
        js = self.script(script_name)
        if js is None:
            raise KeyError(f"Script '{script_name}' not found in page '{self.page_key}'")
        if args:
            return await self.page.evaluate(js, *args)
        return await self.page.evaluate(js)

    async def retry_find(self, group_name: str, timeout: int = 5000):
        selectors = self.el_group(group_name)
        for sel in selectors:
            try:
                loc = self.page.locator(sel)
                if await loc.count() > 0:
                    await loc.first.wait_for(state="visible", timeout=timeout)
                    return loc.first
            except Exception:
                continue
        return None

    async def safe_click(self, locator, timeout: int = 10000):
        try:
            await locator.wait_for(state="visible", timeout=timeout)
            await locator.click()
            return True
        except Exception:
            return False
