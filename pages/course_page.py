import asyncio
from typing import Optional
from playwright.async_api import Page


class CoursePage:
    def __init__(self, page: Page):
        self.page = page

    async def navigate(self, url: str) -> None:
        await self.page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(8)

    async def get_page_title(self) -> str:
        return await self.page.title()

    async def expand_all_chapters(self, max_attempts: int = 5) -> int:
        for attempt in range(max_attempts):
            collapsed = await self.page.evaluate("""
                () => document.querySelectorAll('.left-arrow:not(.is-open):not(.dian)').length
            """)
            if collapsed == 0:
                return 0
            arrows = self.page.locator('.left-arrow:not(.is-open):not(.dian)')
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
        chapters = await self.page.evaluate("""
            () => {
                const nodes = document.querySelectorAll('.index-tree-node');
                const results = [];
                nodes.forEach((node, index) => {
                    const tn = node.querySelector('.tree-node-name');
                    if (!tn) return;
                    const hasChild = node.querySelector('.index-tree-node') !== null;
                    const done = tn.querySelector('.icon-isfinished') !== null;
                    const prog = tn.querySelector('.study-progress-wrapper') !== null;
                    const pad = parseInt(window.getComputedStyle(tn).paddingLeft) || 0;
                    const level = Math.round(pad / 20) + 1;
                    node.setAttribute('data-chapter-id', String(index));
                    results.push({
                        idx: index,
                        name: tn.innerText.trim(),
                        level,
                        isLeaf: !hasChild,
                        done, prog,
                        sel: `.index-tree-node[data-chapter-id="${index}"] > .aside-row > .tree-name-title > .tree-node-name`,
                    });
                });
                return results;
            }
        """)
        return chapters

    async def click_chapter(self, chapter: dict) -> None:
        node = self.page.locator(chapter["sel"])
        await node.scroll_into_view_if_needed()
        await asyncio.sleep(0.5)
        await node.click()
        await asyncio.sleep(3)

    async def scan_resources(self) -> list:
        resources = await self.page.evaluate("""
            () => {
                const items = document.querySelectorAll('.activity-list-item');
                return Array.from(items).map((item, i) => {
                    const nameEl = item.querySelector('.show-line-text');
                    const name = nameEl ? nameEl.innerText.trim() : '';
                    const statuses = item.querySelectorAll('.activityStatus span');
                    const typeText = statuses.length > 0 ? statuses[0].innerText.trim() : '';
                    const stateText = statuses.length > 1 ? statuses[1].innerText.trim() : '';
                    const isActive = item.classList.contains('is-active');
                    const isFinish = item.querySelector('.is-finished') !== null;
                    item.setAttribute('data-resource-id', String(i));
                    return {
                        idx: i, name, type: typeText, state: stateText,
                        isActive, isFinish,
                        sel: `.activity-list-item[data-resource-id="${i}"]`,
                    };
                });
            }
        """)
        return resources

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
            done = await self.page.evaluate(f"""
                () => {{
                    const items = document.querySelectorAll('.activity-list-item');
                    const el = items[{resource_idx}];
                    if (!el) return false;
                    return el.querySelector('.is-finished') !== null
                        || (el.querySelector('.activityStatus:last-child span')
                            && el.querySelector('.activityStatus:last-child span').innerText.includes('已完成'));
                }}
            """)
            if done:
                return True
            await asyncio.sleep(1)
        return False

    async def go_back(self) -> None:
        back_btn = self.page.locator(".return-icon, text=返回, button:has-text('返回')").first
        if await back_btn.count() > 0:
            await back_btn.click()
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
