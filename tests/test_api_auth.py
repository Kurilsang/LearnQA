import pytest
import httpx
from utils.logger import TestLogger

logger = TestLogger()


@pytest.mark.asyncio
class TestAuthAPI:

    async def test_api_client_started(self, api_client):
        logger.step("验证 API 客户端已启动")
        assert api_client._client is not None
        logger.assertion("API 客户端状态正常", True)

    async def test_auth_endpoints_defined(self, auth_api):
        logger.step("验证认证端点定义")
        for name in ("login", "logout", "refresh"):
            ep = auth_api.endpoint(name)
            assert "method" in ep
            assert "path" in ep
            logger.assertion(f"端点 '{name}' 配置完整", True)

    async def test_login_endpoint_config(self, auth_api):
        logger.step("验证登录端点配置")
        ep = auth_api.endpoint("login")
        assert ep["method"] == "POST"
        logger.assertion(f"登录端点: {ep['method']} {ep['path']}", True)

    async def test_logout_endpoint_config(self, auth_api):
        logger.step("验证退出端点配置")
        ep = auth_api.endpoint("logout")
        assert ep["method"] == "POST"
        logger.assertion(f"退出端点: {ep['method']} {ep['path']}", True)

    async def test_refresh_endpoint_config(self, auth_api):
        logger.step("验证刷新端点配置")
        ep = auth_api.endpoint("refresh")
        assert ep["method"] == "POST"
        logger.assertion(f"刷新端点: {ep['method']} {ep['path']}, True")
