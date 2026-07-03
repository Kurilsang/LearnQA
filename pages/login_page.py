import asyncio
from playwright.async_api import Page


class LoginPage:
    def __init__(self, page: Page):
        self.page = page

    async def navigate(self, url: str) -> None:
        await self.page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)

    async def fill_username(self, username: str) -> None:
        el = self.page.locator('input[name="user"]')
        await el.wait_for(state="visible", timeout=10000)
        await el.click()
        await el.fill("")
        await el.type(username, delay=30)

    async def fill_password(self, password: str) -> None:
        el = self.page.locator("#passWord")
        await el.wait_for(state="visible", timeout=10000)
        await el.click()
        await el.fill("")
        await el.type(password, delay=30)

    async def click_login(self) -> None:
        btn = self.page.locator("button.cursor_p").get_by_text("登录", exact=True)
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
        error = self.page.locator(".error-msg, .el-message--error, [class*='error']").first
        if await error.count() > 0:
            return await error.inner_text()
        return ""

    async def do_login(self, username: str, password: str, course_url: str) -> bool:
        await self.fill_username(username)
        await self.fill_password(password)
        await self.click_login()
        return await self.wait_for_login_success(course_url)
