import pytest
from utils.logger import TestLogger

logger = TestLogger()


@pytest.mark.asyncio
class TestCourseAPI:

    async def test_course_endpoints_defined(self, course_api):
        logger.step("验证课程端点定义")
        for name in ("detail", "chapters", "resource_list"):
            ep = course_api.endpoint(name)
            assert "method" in ep
            assert "path" in ep
            logger.assertion(f"端点 '{name}' 配置完整", True)

    async def test_detail_endpoint_config(self, course_api):
        logger.step("验证课程详情端点")
        ep = course_api.endpoint("detail")
        assert "{course_id}" in ep["path"]
        logger.assertion(f"课程详情端点含路径参数: {ep['path']}", True)

    async def test_chapters_endpoint_config(self, course_api):
        logger.step("验证章节列表端点")
        ep = course_api.endpoint("chapters")
        assert "{course_id}" in ep["path"]
        logger.assertion(f"章节列表端点含路径参数: {ep['path']}", True)

    async def test_resources_endpoint_config(self, course_api):
        logger.step("验证资源列表端点")
        ep = course_api.endpoint("resource_list")
        assert "{course_id}" in ep["path"]
        assert "{chapter_id}" in ep["path"]
        logger.assertion(f"资源列表端点含双路径参数: {ep['path']}", True)

    async def test_request_with_path_params(self, course_api):
        logger.step("验证路径参数拼装")
        ep = course_api.endpoint("detail")
        path = ep["path"].format(course_id="test_123")
        assert "test_123" in path
        logger.assertion(f"路径参数替换正确: {path}", True)

    async def test_api_base_url_configured(self, course_api):
        logger.step("验证 API 基础地址")
        base_url = course_api.site.get_api_base_url()
        assert base_url, "API 基础地址未配置"
        logger.assertion(f"API 基础地址: {base_url}", True)
