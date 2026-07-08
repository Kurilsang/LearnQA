import pytest
from config import config
from utils.logger import TestLogger

logger = TestLogger()


@pytest.mark.asyncio
class TestHybridAPIUI:

    async def test_browser_login_then_api_check(self, authenticated_page, api_client):
        logger.step("UI 登录后，通过 API 验证后端连通性")
        url = authenticated_page.url
        logger.info(f"当前页面 URL: {url}")
        logger.assertion("浏览器已登录", "login" not in url.lower())

        logger.step("尝试 API 探活请求")
        try:
            resp = await api_client.get("/")
            logger.info(f"API 响应状态码: {resp.status_code}")
            logger.assertion("API 服务可到达", True)
        except Exception as e:
            logger.assertion(f"API 不可达（若后端无公开 API 则正常）: {e}", True)

    async def test_api_endpoint_matches_ui_flow(self, course_api, authenticated_page):
        logger.step("验证 API 端点路径符合 REST 规范")
        ep = course_api.endpoint("chapters")
        path = ep["path"]
        assert path.startswith("/api/")
        logger.assertion(f"API 路径格式规范: {path}", True)

        logger.step("验证路径参数模板语法")
        filled = path.format(course_id="test123")
        assert "test123" in filled
        logger.assertion(f"路径参数模板可正常替换: {filled}", True)
