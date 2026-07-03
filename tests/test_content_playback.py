import pytest
from config import config
from pages.content_page import ContentPage
from utils.logger import TestLogger

logger = TestLogger()


@pytest.mark.asyncio
class TestContentPlayback:

    async def _navigate_to_first_resource(self, course_page):
        await course_page.navigate(config.COURSE_URL)
        chapters = await course_page.scan_chapters()
        leaf_chapters = [c for c in chapters if c["isLeaf"] and not c["done"]]
        if not leaf_chapters:
            leaf_chapters = [c for c in chapters if c["isLeaf"]]
        if not leaf_chapters:
            pytest.skip("无可用叶子章节")
        await course_page.click_chapter(leaf_chapters[0])
        resources = await course_page.scan_resources()
        if not resources:
            pytest.skip("无可用资源")
        return course_page, resources

    async def test_content_page_structure(self, authenticated_page, course_page, content_page):
        logger.step("验证内容页面结构加载")
        cp, resources = await self._navigate_to_first_resource(course_page)
        for res in resources:
            logger.info(f"资源: [{res['type']}] {res['name']} | 完成: {res['isFinish']}")
        assert len(resources) > 0, "内容页面未加载资源列表"
        logger.assertion("内容页面结构加载正常", True)

    async def test_resource_type_detection(self, authenticated_page, course_page, content_page):
        logger.step("验证资源类型检测")
        cp, resources = await self._navigate_to_first_resource(course_page)
        known_types = ("PPT", "HTML", "PDF", "视频", "文档", "自适应", "练习", "训练")
        for res in resources:
            has_type = any(t in res["type"] for t in known_types)
            logger.info(f"  [{res['type']}] {res['name']} -> {'已知类型' if has_type else '未知类型'}")
            logger.assertion(f"资源类型可识别: {res['type']}", has_type)

    async def test_resource_click_and_load(self, authenticated_page, course_page, content_page):
        logger.step("验证资源点击与加载")
        cp, resources = await self._navigate_to_first_resource(course_page)
        for res in resources[:3]:
            if res["isFinish"]:
                continue
            clicked = await course_page.click_resource(res)
            assert clicked, f"无法点击资源: {res['name']}"
            logger.assertion(f"点击资源: {res['name']}", clicked)
            await authenticated_page.wait_for_timeout(3000)
            break

    async def test_resource_progress_tracking(self, authenticated_page, course_page, content_page):
        logger.step("验证资源进度追踪")
        cp, resources = await self._navigate_to_first_resource(course_page)
        for res in resources[:2]:
            if res["isFinish"]:
                continue
            await course_page.click_resource(res)
            finished = await course_page.wait_resource_finish(res["idx"], timeout=10)
            logger.assertion(f"资源进度可追踪: {res['name']}", finished is not None)
            break

    async def test_content_type_specific_handling(self, authenticated_page, course_page, content_page):
        logger.step("验证不同内容类型的处理逻辑")
        cp, resources = await self._navigate_to_first_resource(course_page)
        for res in resources:
            if res["isFinish"]:
                continue
            await course_page.click_resource(res)
            if "PPT" in res["type"]:
                result = await content_page.process_pptx()
                logger.assertion(f"PPTX 翻页处理: {res['name']}", result)
            elif "视频" in res["type"]:
                result = await content_page.process_video()
                logger.assertion(f"视频播放处理: {res['name']}", result)
            elif "HTML" in res["type"] or "PDF" in res["type"] or "文档" in res["type"]:
                result = await content_page.process_html_pdf(res["idx"])
                logger.assertion(f"文档滚动处理: {res['name']}", result)
            break

    async def test_page_error_capture(self, authenticated_page, course_page, content_page):
        logger.step("验证页面异常捕获")
        errors = []
        authenticated_page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        authenticated_page.on("pageerror", lambda err: errors.append(str(err)))
        cp, resources = await self._navigate_to_first_resource(course_page)
        await authenticated_page.wait_for_timeout(5000)
        if errors:
            for e in errors[:10]:
                logger.warn(f"页面错误: {e[:200]}")
        logger.assertion("页面无严重异常", len(errors) == 0)
