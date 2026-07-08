import pytest
from utils.logger import TestLogger

logger = TestLogger()


@pytest.mark.asyncio
class TestContentAPI:

    async def test_content_endpoints_defined(self, content_api):
        logger.step("验证内容端点定义")
        for name in ("progress", "status"):
            ep = content_api.endpoint(name)
            assert "method" in ep
            assert "path" in ep
            logger.assertion(f"端点 '{name}' 配置完整", True)

    async def test_progress_endpoint_config(self, content_api):
        logger.step("验证进度提交端点")
        ep = content_api.endpoint("progress")
        assert "{resource_id}" in ep["path"]
        assert ep["method"] == "POST"
        logger.assertion(f"进度提交端点: {ep['method']} {ep['path']}", True)

    async def test_status_endpoint_config(self, content_api):
        logger.step("验证状态查询端点")
        ep = content_api.endpoint("status")
        assert "{resource_id}" in ep["path"]
        assert ep["method"] == "GET"
        logger.assertion(f"状态查询端点: {ep['method']} {ep['path']}", True)

    async def test_submit_progress_method(self, content_api):
        logger.step("验证 submit_progress 参数")
        ep = content_api.endpoint("progress")
        path = ep["path"].format(resource_id="res_001")
        assert "res_001" in path
        logger.assertion(f"资源 ID 路径参数替换正确: {path}", True)
