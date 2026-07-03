import asyncio
from typing import Optional
from playwright.async_api import Page
from core.base_page import BasePage


class CoursePage(BasePage):
    page_key = "course_page"

    async def navigate(self, url: str) -> None:
        await self.page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(8)

    async def get_page_title(self) -> str:
        return await self.page.title()

    async def expand_all_chapters(self, max_attempts: int = 5) -> int:
        for attempt in range(max_attempts):
            collapsed = await self.evaluate_script("count_collapsed_arrows")
            if collapsed == 0:
                return 0
            arrows = self.el("chapter_expand_arrow")
            cnt = await arrows.count()
            for i in range(min(cnt, 30)):
                try:
                    await arrows.nth(i).click()
                    await asyncio.sleep(0.2)
                except Exception:
                    pass
            await asyncio.sleep(1.5)
        return collapsed

    async def scan_chapters(self) -> list:
        await self.expand_all_chapters()
        return await self.evaluate_script("scan_chapters")

    async def click_chapter(self, chapter: dict) -> None:
        node = self.page.locator(chapter["sel"])
        await node.scroll_into_view_if_needed()
        await asyncio.sleep(0.5)
        await node.click()
        await asyncio.sleep(3)

    async def scan_resources(self) -> list:
        return await self.evaluate_script("scan_resources")

    async def click_resource(self, resource: dict) -> bool:
        res_loc = self.page.locator(resource["sel"])
        try:
            await res_loc.wait_for(state="visible", timeout=10000)
            await res_loc.click()
            return True
        except Exception:
            return False

    async def wait_resource_finish(self, resource_idx: int, timeout: int = 120) -> bool:
        for _ in range(timeout):
            done = await self.page.evaluate(
                self.script("check_resource_finished"), resource_idx
            )
            if done:
                return True
            await asyncio.sleep(1)
        return False

    async def go_back(self) -> None:
        btn = await self.retry_find("back_button")
        if btn:
            await btn.click()
        else:
            await self.page.go_back(wait_until="networkidle", timeout=30000)
        await asyncio.sleep(5)

    async def get_chapter_count(self) -> dict:
        chapters = await self.scan_chapters()
        total = len(chapters)
        finished = sum(1 for c in chapters if c["done"])
        unfinished = total - finished
        return {"total": total, "finished": finished, "unfinished": unfinished}

    async def get_chapter_progress(self) -> list:
        chapters = await self.scan_chapters()
        result = []
        for c in chapters:
            if c["prog"] or (not c["done"] and c["isLeaf"]):
                result.append({"name": c["name"], "done": c["done"], "progress": c["prog"]})
        return result
