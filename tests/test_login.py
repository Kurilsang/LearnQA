import pytest
from config import config
from utils.logger import TestLogger

logger = TestLogger()


@pytest.mark.asyncio
class TestLogin:

    async def test_login_page_load(self, browser_page, login_page):
        logger.step("验证登录页面加载")
        await login_page.navigate(config.BASE_URL)
        title = await browser_page.title()
        assert title is not None, "页面标题为空"
        logger.assertion(f"登录页面标题: {title}", True)
        url = browser_page.url
        assert "login" in url.lower(), f"URL 未指向登录页面: {url}"
        logger.assertion("URL 包含 login 路径", True)

    async def test_login_page_elements(self, browser_page, login_page):
        logger.step("验证登录页面元素完整性")
        await login_page.navigate(config.BASE_URL)
        username_input = browser_page.locator('input[name="user"]')
        password_input = browser_page.locator("#passWord")
        login_button = browser_page.locator("button.cursor_p").get_by_text("登录", exact=True)
        assert await username_input.count() > 0, "未找到账号输入框"
        assert await password_input.count() > 0, "未找到密码输入框"
        assert await login_button.count() > 0, "未找到登录按钮"
        logger.assertion("账号输入框存在", await username_input.count() > 0)
        logger.assertion("密码输入框存在", await password_input.count() > 0)
        logger.assertion("登录按钮存在", await login_button.count() > 0)

    async def test_login_input_fill(self, browser_page, login_page):
        logger.step("验证登录输入框可填写")
        await login_page.navigate(config.BASE_URL)
        await login_page.fill_username(config.USERNAME)
        value = await browser_page.locator('input[name="user"]').input_value()
        assert value == config.USERNAME, f"账号输入值不匹配: {value}"
        logger.assertion("账号输入正确", value == config.USERNAME)

    async def test_login_password_fill(self, browser_page, login_page):
        logger.step("验证密码输入框可填写")
        await login_page.navigate(config.BASE_URL)
        await login_page.fill_password(config.PASSWORD)
        value = await browser_page.locator("#passWord").input_value()
        assert value == config.PASSWORD, f"密码输入值不匹配"
        logger.assertion("密码输入正确", value == config.PASSWORD)

    async def test_login_success(self, browser_page, login_page):
        logger.step("验证完整登录流程")
        await login_page.navigate(config.BASE_URL)
        success = await login_page.do_login(config.USERNAME, config.PASSWORD, config.COURSE_URL)
        assert success, "登录失败"
        logger.assertion("登录成功", success)
        title = await browser_page.title()
        logger.info(f"登录后页面标题: {title}")
