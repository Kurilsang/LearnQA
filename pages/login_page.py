import asyncio
from playwright.async_api import Page
from core.base_page import BasePage


class LoginPage(BasePage):
    page_key = "login_page"

    async def navigate(self, url: str = None) -> None:
        target = url or self.site.get_page_url("login_page")
        await self.page.goto(target, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)

    async def fill_username(self, username: str) -> None:
        el = self.el("username_input")
        await el.wait_for(state="visible", timeout=10000)
        await el.click()
        await el.fill("")
        await el.type(username, delay=30)

    async def fill_password(self, password: str) -> None:
        el = self.el("password_input")
        await el.wait_for(state="visible", timeout=10000)
        await el.click()
        await el.fill("")
        await el.type(password, delay=30)

    async def click_login(self) -> None:
        btn = self.el("login_button").get_by_text("登录", exact=True)
        await btn.wait_for(state="visible", timeout=10000)
        await btn.click()

    async def wait_for_login_success(self, course_url: str, timeout: int = 30) -> bool:
        try:
            await self.page.wait_for_url(
                lambda url: "login" not in url.lower().split("?")[0],
                timeout=timeout * 1000,
            )
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            await asyncio.sleep(2)
        except Exception:
            err = await self.get_login_error()
            if err:
                self.page.evaluate(f"console.error('登录失败: {err}')")
                return False

        await self.page.goto(course_url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(5)
        try:
            await self.page.wait_for_selector(
                ".index-tree-node, .aside-row, .activity-list-item",
                timeout=10000,
            )
            return True
        except Exception:
            text = await self.page.evaluate("document.body.innerText.substring(0, 300)")
            return any(kw in text for kw in ("课程", "学习", "章节", "自适应"))

    async def get_login_error(self) -> str:
        error = self.el("error_selector").first
        if await error.count() > 0:
            return await error.inner_text()
        return ""

    async def do_login(self, username: str, password: str, course_url: str) -> bool:
        await self.fill_username(username)
        await self.fill_password(password)
        await self.click_login()
        return await self.wait_for_login_success(course_url)
