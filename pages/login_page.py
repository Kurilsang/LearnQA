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
        for i in range(timeout):
            await asyncio.sleep(1)
            current = self.page.url
            path = current.split("?")[0].lower()
            if "login" not in path:
                return True
        await self.page.goto(course_url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(5)
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
