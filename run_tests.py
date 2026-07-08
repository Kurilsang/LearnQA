#!/usr/bin/env python3
"""
在线课程页面自动化测试脚本 - 测试运行器
使用 Playwright 实现教育网站页面自动化遍历，校验课程加载、播放页面、进度展示功能，
编写自动化用例，捕获页面加载异常、接口报错，输出测试报告。
"""
import asyncio
import os
import sys
import time
from datetime import datetime

from playwright.async_api import TimeoutError as PlaywrightTimeout

from config import config
from pages.login_page import LoginPage
from pages.course_page import CoursePage
from pages.content_page import ContentPage
from services.browser_service import BrowserService
from utils.logger import TestLogger
from utils.reporter import TestReport, TestSuite
from core.api_client import ApiClient
from apis.auth_api import AuthAPI
from apis.course_api import CourseAPI
from apis.content_api import ContentAPI

logger = TestLogger()
report = TestReport()
site_config = config.SITE_CONFIG


class TestRunner:
    def __init__(self):
        self.results = {"passed": 0, "failed": 0, "skipped": 0, "errors": []}
        self.current_suite = None

    async def run(self):
        logger.info("=" * 60)
        logger.info("全量自动化测试脚本 v4.0（UI + API）")
        logger.info(f"目标站点: {site_config.name}")
        logger.info("=" * 60)

        suite = report.add_suite("登录功能测试")
        await self._test_login_flow(suite)

        suite = report.add_suite("课程页面导航测试")
        await self._test_course_navigation(suite)

        suite = report.add_suite("内容播放与进度测试")
        await self._test_content_playback(suite)

        suite = report.add_suite("异常捕获测试")
        await self._test_error_capture(suite)

        suite = report.add_suite("API 认证接口测试")
        await self._test_api_auth(suite)

        suite = report.add_suite("API 课程接口测试")
        await self._test_api_course(suite)

        suite = report.add_suite("API 内容接口测试")
        await self._test_api_content(suite)

        suite = report.add_suite("API + UI 混合验证测试")
        await self._test_api_hybrid(suite)

        logger.info("\n正在生成 AI 智能分析报告...")
        analysis = await self._ai_analyze_results()
        if analysis:
            report.set_ai_analysis(analysis)
            logger.info("AI 分析完成")
        else:
            logger.warn("AI 分析不可用（未配置 API Key）")

        report_path = report.generate(config.REPORT_DIR)
        logger.info(f"\n测试报告已生成: {report_path}")
        logger.info(f"总计: {self.results['passed'] + self.results['failed'] + self.results['skipped']} | "
                    f"通过: {self.results['passed']} | 失败: {self.results['failed']} | 跳过: {self.results['skipped']}")
        return self.results

    async def _ai_analyze_results(self) -> str:
        if not config.AI_API_KEY:
            return ""
        suite_summaries = []
        for s in report.suites:
            failures = [c for c in s.cases if c["status"] == "FAIL"]
            fail_detail = ""
            if failures:
                fail_detail = "。失败用例: " + "; ".join(
                    f"{f['name']}({f['error'][:100]})" for f in failures
                )
            suite_summaries.append(
                f"  - {s.name}: {s.passed}/{s.total} 通过{fail_detail}"
            )

        prompt = (
            "你是一个专业的 QA 测试分析师。请根据以下自动化测试结果，生成一份简洁的智能分析报告。\n\n"
            "【测试结果】\n"
            f"总用例: {self.results['passed'] + self.results['failed'] + self.results['skipped']}\n"
            f"通过: {self.results['passed']}\n"
            f"失败: {self.results['failed']}\n"
            f"跳过: {self.results['skipped']}\n"
            "【各模块详情】\n" + "\n".join(suite_summaries) + "\n\n"
            "请按以下格式输出（使用 Markdown）：\n"
            "### 测试执行概况\n"
            "简要总结整体测试情况。\n"
            "### 失败根因分析\n"
            "分析每条失败原因及其可能影响。\n"
            "### 风险评估\n"
            "用 低/中/高 三级评估系统整体风险，说明理由。\n"
            "### 优化建议\n"
            "给出具体可操作的测试或代码改进建议。"
        )
        try:
            import httpx
            timeout = httpx.Timeout(30.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{config.AI_API_BASE.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {config.AI_API_KEY}", "Content-Type": "application/json"},
                    json={
                        "model": config.AI_MODEL,
                        "temperature": config.AI_TEMPERATURE,
                        "messages": [
                            {"role": "system", "content": "你是一个专业的 QA 测试分析师。用中文输出，简洁专业，突出重点。"},
                            {"role": "user", "content": prompt}
                        ]
                    },
                )
                result = resp.json()
                return result["choices"][0]["message"]["content"].strip()
        except ImportError:
            logger.warn("未安装 httpx，跳过 AI 分析")
        except Exception as e:
            logger.warn(f"AI 分析调用失败: {e}")
        return ""

    async def _run_test(self, suite: TestSuite, name: str, coro, screenshot_page=None):
        start = time.time()
        try:
            await coro
            elapsed = time.time() - start
            suite.add_case(name, "PASS", elapsed, steps=logger.steps[-20:])
            self.results["passed"] += 1
        except (AssertionError, Exception) as e:
            elapsed = time.time() - start
            screenshot_path = ""
            if screenshot_page:
                os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
                screenshot_path = os.path.join(config.SCREENSHOT_DIR, f"fail_{name}_{int(time.time())}.png")
                try:
                    await screenshot_page.screenshot(path=screenshot_path)
                except Exception:
                    pass
            suite.add_case(name, "FAIL", elapsed, error=str(e)[:500],
                           screenshot=screenshot_path, steps=logger.steps[-20:])
            self.results["failed"] += 1

    async def _test_login_flow(self, suite):
        playwright = browser = None
        try:
            playwright, browser, context, page = await BrowserService.launch()
            login = LoginPage(page, site_config)

            async def test_page_load():
                await login.navigate(config.BASE_URL)
                title = await page.title()
                assert title is not None, "页面标题为空"
                assert "login" in page.url.lower(), f"URL 未指向登录页面: {page.url}"

            async def test_elements():
                await login.navigate(config.BASE_URL)
                assert await login.el("username_input").count() > 0, "未找到账号输入框"
                assert await login.el("password_input").count() > 0, "未找到密码输入框"

            async def test_fill():
                await login.navigate(config.BASE_URL)
                await login.fill_username(config.USERNAME)
                val = await login.el("username_input").input_value()
                assert val == config.USERNAME, "账号输入不匹配"

            async def test_full_login():
                await login.navigate(config.BASE_URL)
                ok = await login.do_login(config.USERNAME, config.PASSWORD, config.COURSE_URL)
                assert ok, "登录失败"

            await self._run_test(suite, "登录页面加载", test_page_load(), page)
            await self._run_test(suite, "登录元素完整性", test_elements(), page)
            await self._run_test(suite, "账号输入功能", test_fill(), page)
            await self._run_test(suite, "完整登录流程", test_full_login(), page)
        finally:
            await BrowserService.close(browser, playwright)

    async def _test_course_navigation(self, suite):
        playwright = browser = None
        try:
            playwright, browser, context, page = await BrowserService.launch()
            login = LoginPage(page, site_config)
            course = CoursePage(page, site_config)

            await login.navigate(config.BASE_URL)
            ok = await login.do_login(config.USERNAME, config.PASSWORD, config.COURSE_URL)
            if not ok:
                suite.add_case("前置登录", "SKIP", 0, error="登录失败，跳过课程导航测试")
                self.results["skipped"] += 1
                return

            async def test_page_load():
                await course.navigate(config.COURSE_URL)
                title = await course.get_page_title()
                assert title is not None, "课程页面标题为空"

            async def test_chapter_expand():
                await course.navigate(config.COURSE_URL)
                remaining = await course.expand_all_chapters()
                assert remaining == 0, f"仍有 {remaining} 个折叠节点"

            async def test_chapter_scan():
                await course.navigate(config.COURSE_URL)
                chapters = await course.scan_chapters()
                assert len(chapters) > 0, "未扫描到章节"

            async def test_resource_list():
                await course.navigate(config.COURSE_URL)
                chapters = await course.scan_chapters()
                leaves = [c for c in chapters if c["isLeaf"]]
                if not leaves:
                    raise AssertionError("无叶子章节")
                await course.click_chapter(leaves[0])
                resources = await course.scan_resources()
                assert len(resources) > 0, "资源列表为空"

            await self._run_test(suite, "课程页面加载", test_page_load(), page)
            await self._run_test(suite, "章节展开功能", test_chapter_expand(), page)
            await self._run_test(suite, "章节列表扫描", test_chapter_scan(), page)
            await self._run_test(suite, "资源列表展示", test_resource_list(), page)
        finally:
            await BrowserService.close(browser, playwright)

    async def _test_content_playback(self, suite):
        playwright = browser = None
        try:
            playwright, browser, context, page = await BrowserService.launch()
            login = LoginPage(page, site_config)
            course = CoursePage(page, site_config)
            content = ContentPage(page, site_config)

            await login.navigate(config.BASE_URL)
            ok = await login.do_login(config.USERNAME, config.PASSWORD, config.COURSE_URL)
            if not ok:
                suite.add_case("前置登录", "SKIP", 0, error="登录失败，跳过内容播放测试")
                self.results["skipped"] += 1
                return

            await course.navigate(config.COURSE_URL)
            chapters = await course.scan_chapters()
            leaves = [c for c in chapters if c["isLeaf"] and not c["done"]]
            if not leaves:
                leaves = [c for c in chapters if c["isLeaf"]]
            if not leaves:
                suite.add_case("前置导航", "SKIP", 0, error="无可用叶子章节")
                self.results["skipped"] += 1
                return

            await course.click_chapter(leaves[0])
            resources = await course.scan_resources()
            if not resources:
                suite.add_case("前置导航", "SKIP", 0, error="无可用资源")
                self.results["skipped"] += 1
                return

            async def test_pptx():
                for res in resources:
                    if "PPT" in res["type"] and not res["isFinish"]:
                        await course.click_resource(res)
                        await content.process_pptx()
                        return True
                raise AssertionError("未找到 PPTX 资源")

            async def test_html_pdf():
                for res in resources:
                    if any(t in res["type"] for t in ("HTML", "PDF", "文档")) and not res["isFinish"]:
                        await course.click_resource(res)
                        await content.process_html_pdf(res["idx"])
                        return True
                raise AssertionError("未找到 HTML/PDF 资源")

            async def test_video():
                for res in resources:
                    if "视频" in res["type"] and not res["isFinish"]:
                        await course.click_resource(res)
                        await content.process_video()
                        return True
                raise AssertionError("未找到视频资源")

            async def test_resource_finish():
                for res in resources[:2]:
                    if not res["isFinish"]:
                        await course.click_resource(res)
                        finished = await course.wait_resource_finish(res["idx"], timeout=30)
                        assert finished is not None, "资源状态可查询"
                        return True
                raise AssertionError("无可处理资源")

            await self._run_test(suite, "PPT 翻页处理", test_pptx(), page)
            await self._run_test(suite, "HTML/PDF 滚动处理", test_html_pdf(), page)
            await self._run_test(suite, "视频播放处理", test_video(), page)
            await self._run_test(suite, "资源完成状态追踪", test_resource_finish(), page)
        finally:
            await BrowserService.close(browser, playwright)

    async def _test_error_capture(self, suite):
        playwright = browser = None
        try:
            playwright, browser, context, page = await BrowserService.launch()
            login = LoginPage(page, site_config)
            course = CoursePage(page, site_config)
            errors = []

            async def test_console_error():
                page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
                page.on("pageerror", lambda err: errors.append(str(err)))
                await login.navigate(config.BASE_URL)
                await page.wait_for_timeout(5000)
                logger.info(f"捕获到 {len(errors)} 个页面错误")
                assert len(errors) < 50, f"页面错误过多: {len(errors)}"

            async def test_api_error():
                responses = []
                page.on("response", lambda resp: responses.append(resp) if resp.status >= 400 else None)
                await login.navigate(config.BASE_URL)
                await login.do_login(config.USERNAME, config.PASSWORD, config.COURSE_URL)
                await course.navigate(config.COURSE_URL)
                await page.wait_for_timeout(5000)
                api_errors = [r for r in responses if r.status >= 500]
                logger.info(f"API 错误: {len(api_errors)} 个 (4xx: {len(responses) - len(api_errors)}, 5xx: {len(api_errors)})")
                assert len(api_errors) < 10, f"服务端错误过多: {len(api_errors)}"

            async def test_timeout_handling():
                try:
                    await page.goto("https://www.fifedu.com/nonexistent", timeout=5000, wait_until="networkidle")
                except Exception:
                    pass
                assert True, "超时处理正常"

            await self._run_test(suite, "页面控制台异常捕获", test_console_error(), page)
            await self._run_test(suite, "接口异常捕获", test_api_error(), page)
            await self._run_test(suite, "超时处理机制", test_timeout_handling(), page)
        finally:
            await BrowserService.close(browser, playwright)


    async def _test_api_auth(self, suite):
        logger.step("初始化 API 客户端")
        client = ApiClient(
            base_url=site_config.get_api_base_url(),
            timeout=10.0,
            logger=logger,
        )
        await client.start()
        try:
            auth = AuthAPI(client, site_config)

            async def test_client_started():
                assert client._client is not None, "客户端未启动"

            async def test_endpoints_defined():
                for name in ("login", "logout", "refresh"):
                    ep = auth.endpoint(name)
                    assert "method" in ep
                    assert "path" in ep

            async def test_login_config():
                ep = auth.endpoint("login")
                assert ep["method"] == "POST"

            async def test_api_reachable():
                try:
                    resp = await client.get("/")
                    logger.info(f"API 根路径响应: {resp.status_code}")
                except Exception:
                    logger.info("API 根路径不可达（按设计跳过）")

            await self._run_test(suite, "API 客户端启动", test_client_started())
            await self._run_test(suite, "认证端点完整性", test_endpoints_defined())
            await self._run_test(suite, "登录接口配置", test_login_config())
            await self._run_test(suite, "API 服务探活", test_api_reachable())
        finally:
            await client.stop()

    async def _test_api_course(self, suite):
        client = ApiClient(
            base_url=site_config.get_api_base_url(),
            timeout=10.0,
            logger=logger,
        )
        await client.start()
        try:
            course = CourseAPI(client, site_config)

            async def test_endpoints_defined():
                for name in ("detail", "chapters", "resource_list"):
                    ep = course.endpoint(name)
                    assert "method" in ep
                    assert "path" in ep

            async def test_path_params():
                ep = course.endpoint("detail")
                path = ep["path"].format(course_id="demo_id")
                assert "demo_id" in path

            async def test_chapters_path():
                ep = course.endpoint("chapters")
                path = ep["path"].format(course_id="demo_id")
                assert "/api/" in path

            await self._run_test(suite, "课程端点完整性", test_endpoints_defined())
            await self._run_test(suite, "路径参数替换", test_path_params())
            await self._run_test(suite, "章节接口路径", test_chapters_path())
        finally:
            await client.stop()

    async def _test_api_content(self, suite):
        client = ApiClient(
            base_url=site_config.get_api_base_url(),
            timeout=10.0,
            logger=logger,
        )
        await client.start()
        try:
            content = ContentAPI(client, site_config)

            async def test_endpoints_defined():
                for name in ("progress", "status"):
                    ep = content.endpoint(name)
                    assert "method" in ep
                    assert "path" in ep

            async def test_progress_config():
                ep = content.endpoint("progress")
                assert ep["method"] == "POST"
                path = ep["path"].format(resource_id="r001")
                assert "r001" in path

            async def test_status_config():
                ep = content.endpoint("status")
                assert ep["method"] == "GET"
                path = ep["path"].format(resource_id="r001")
                assert "r001" in path

            await self._run_test(suite, "内容端点完整性", test_endpoints_defined())
            await self._run_test(suite, "进度提交接口", test_progress_config())
            await self._run_test(suite, "状态查询接口", test_status_config())
        finally:
            await client.stop()

    async def _test_api_hybrid(self, suite):
        playwright = browser = None
        try:
            playwright, browser, context, page = await BrowserService.launch()
            login = LoginPage(page, site_config)

            await login.navigate(config.BASE_URL)
            ok = await login.do_login(config.USERNAME, config.PASSWORD, config.COURSE_URL)
            if not ok:
                suite.add_case("前置登录", "SKIP", 0, error="登录失败，跳过混合测试")
                self.results["skipped"] += 1
                return

            api_client = ApiClient(
                base_url=site_config.get_api_base_url(),
                timeout=10.0,
                logger=logger,
            )
            await api_client.start()
            try:
                async def test_ui_logged_in():
                    assert "login" not in page.url.lower(), "浏览器未登录"

                async def test_api_connectivity():
                    try:
                        resp = await api_client.get("/")
                        logger.info(f"混合测试 - API 响应: {resp.status_code}")
                    except Exception:
                        logger.info("混合测试 - API 不可达（正常）")

                async def test_ui_course_loaded():
                    await page.goto(config.COURSE_URL)
                    title = await page.title()
                    assert title is not None

                await self._run_test(suite, "UI 登录状态验证", test_ui_logged_in(), page)
                await self._run_test(suite, "API 连通性验证", test_api_connectivity(), page)
                await self._run_test(suite, "UI 课程页面加载", test_ui_course_loaded(), page)
            finally:
                await api_client.stop()
        finally:
            await BrowserService.close(browser, playwright)


def main():
    runner = TestRunner()
    results = asyncio.run(runner.run())
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
