import pytest
from config import config
from utils.logger import TestLogger

logger = TestLogger()


@pytest.mark.asyncio
class TestCourseNavigation:

    async def test_course_page_load(self, authenticated_page, course_page):
        logger.step("验证课程页面加载")
        await course_page.navigate(config.COURSE_URL)
        title = await course_page.get_page_title()
        assert title is not None, "课程页面标题为空"
        logger.assertion(f"课程页面标题: {title}", True)
        text = await authenticated_page.evaluate("document.body.innerText.substring(0, 500)")
        has_course_content = any(kw in text for kw in ("课程", "学习", "章节", "自适应"))
        assert has_course_content, "页面未加载课程内容"
        logger.assertion("课程内容已加载", has_course_content)

    async def test_chapter_expansion(self, authenticated_page, course_page):
        logger.step("验证章节展开功能")
        await course_page.navigate(config.COURSE_URL)
        remaining = await course_page.expand_all_chapters()
        logger.assertion("章节展开完成", remaining == 0)

    async def test_chapter_list_scan(self, authenticated_page, course_page):
        logger.step("验证章节列表扫描")
        await course_page.navigate(config.COURSE_URL)
        chapters = await course_page.scan_chapters()
        assert len(chapters) > 0, "未扫描到任何章节"
        logger.assertion(f"扫描到 {len(chapters)} 个章节节点", len(chapters) > 0)
        leaf_chapters = [c for c in chapters if c["isLeaf"]]
        logger.info(f"叶子章节: {len(leaf_chapters)} 个")
        unfinished = [c for c in chapters if not c["done"]]
        logger.info(f"未完成章节: {len(unfinished)} 个")

    async def test_chapter_structure_integrity(self, authenticated_page, course_page):
        logger.step("验证章节结构完整性")
        await course_page.navigate(config.COURSE_URL)
        chapters = await course_page.scan_chapters()
        for c in chapters:
            assert c["name"], f"章节 {c['idx']} 名称为空"
            assert c["level"] >= 1, f"章节 {c['name']} 层级异常"
        logger.assertion("所有章节名称和层级完整", all(c["name"] and c["level"] >= 1 for c in chapters))

    async def test_chapter_progress_display(self, authenticated_page, course_page):
        logger.step("验证章节进度展示")
        await course_page.navigate(config.COURSE_URL)
        progress = await course_page.get_chapter_progress()
        for p in progress:
            logger.info(f"章节: {p['name']} | 完成: {p['done']} | 进度: {p['progress']}")
        logger.assertion(f"进度信息获取成功 ({len(progress)} 条)", True)

    async def test_resource_list_display(self, authenticated_page, course_page):
        logger.step("验证资源列表展示")
        await course_page.navigate(config.COURSE_URL)
        chapters = await course_page.scan_chapters()
        leaf_chapters = [c for c in chapters if c["isLeaf"] and not c["done"]]
        if not leaf_chapters:
            logger.warn("没有可用的叶子章节，跳过")
            return
        await course_page.click_chapter(leaf_chapters[0])
        resources = await course_page.scan_resources()
        assert len(resources) > 0, "资源列表为空"
        logger.assertion(f"资源列表: {len(resources)} 项", len(resources) > 0)
        for r in resources:
            logger.info(f"  资源 [{r['type']}]: {r['name']} | 状态: {r['state']}")
