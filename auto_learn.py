"""
FIF 自适应学习平台 - 自动刷课脚本 v3.0
基于可配置框架重构，将定位步骤与业务逻辑分离。

使用方式:
  1. 直接运行: python auto_learn.py
  2. 切换站点: 修改 config.py 中的 SITE_NAME 即可

支持的资源类型处理器（定义在 sites/{site}/handlers.py）:
  - process_pptx: 在 iframe 内自动翻页到最后一页
  - process_html_pdf: 自动滚动内容到底部
  - process_video: 自动播放并等待完成
  - process_adaptive: AI 答题 + 自动提交
"""

import asyncio
import os
import sys
from datetime import datetime

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

from config import config
from pages.login_page import LoginPage
from pages.course_page import CoursePage
from pages.content_page import ContentPage
from utils.logger import TestLogger
from core.registry import registry

logger = TestLogger()

STATS = {
    "processed_chapters": 0,
    "processed_resources": 0,
    "errors": 0,
    "adaptive_answered": 0,
}


async def log(msg: str):
    logger.info(msg)


async def process_resource(page, course, content, res: dict, site_config):
    if res["isFinish"]:
        await log(f"  [{res['type']}] {res['name']} 已完成，跳过")
        return

    await log(f"  --- [{res['type']}] {res['name']} ---")

    if not await course.click_resource(res):
        await log(f"  [!] 无法点击资源")
        return
    await asyncio.sleep(3)

    res_type = res["type"]
    try:
        handler_name = None
        for pattern, hname in site_config.resource_handlers.items():
            if pattern in res_type:
                handler_name = hname
                break

        if handler_name and registry.has(handler_name):
            if handler_name in ("process_adaptive",):
                from sites.fifedu.handlers import process_adaptive
                for sel in [
                    "button:has-text('开始学习')", "button:has-text('进入')",
                    "button:has-text('开始')", "button:has-text('答题')", ".start-btn",
                ]:
                    try:
                        btn = page.locator(sel).first
                        if await btn.count() > 0:
                            await btn.click()
                            await asyncio.sleep(2)
                            break
                    except Exception:
                        continue

            params = {
                "log_cb": log,
                "resource_idx": res["idx"],
                "site_config": site_config,
                **site_config.default_params,
            }
            await registry.execute(handler_name, page, params)

            if handler_name == "process_adaptive" or handler_name == "handle_adaptive_questions":
                STATS["adaptive_answered"] += 1
        else:
            await log(f"  [?] 未知资源类型: {res_type}，等待 60 秒")
            await asyncio.sleep(60)
    except Exception as e:
        await log(f"  [!] 处理 {res_type} 时出错: {e}")
        STATS["errors"] += 1

    await log("  等待资源标记完成...")
    finished = await course.wait_resource_finish(res["idx"], timeout=120)
    if finished:
        await log(f"  {res['name']} 已完成")
    else:
        await log(f"  可能未标记完成，继续下一步")
    STATS["processed_resources"] += 1


async def process_chapter_content(page, course, content, site_config):
    await log("--- 处理章节内容 ---")
    await asyncio.sleep(5)

    if len(page.context.pages) > 1:
        await log("检测到新标签页，切换到新标签页")
        np = page.context.pages[-1]
        await np.wait_for_load_state("networkidle")
        await asyncio.sleep(3)
        await process_chapter_content(np, CoursePage(np, site_config), ContentPage(np, site_config), site_config)
        await np.close()
        return

    resources = await course.scan_resources()
    if not resources:
        await log("未找到资源列表，等待后继续")
        await asyncio.sleep(5)
        return

    for res in resources:
        await process_resource(page, course, content, res, site_config)

    await log("返回课程首页...")
    await course.go_back()


async def process_leaf_chapter(page, course, content, chapter: dict, site_config):
    await log(f"\n{'='*60}")
    await log(f"处理章节: {chapter['name']}")
    await log(f"{'='*60}")

    try:
        node = page.locator(chapter["sel"])
        await node.scroll_into_view_if_needed()
        await asyncio.sleep(0.5)
        await log(f"点击章节: {chapter['name']}")
        await node.click()
        await asyncio.sleep(3)

        await process_chapter_content(page, course, content, site_config)

        STATS["processed_chapters"] += 1
        await log(f"章节处理完成: {chapter['name']}")
        return True
    except PlaywrightTimeout as e:
        await log(f"超时: {chapter['name']} - {e}")
        STATS["errors"] += 1
        return False
    except Exception as e:
        await log(f"错误: {chapter['name']} - {e}")
        import traceback
        traceback.print_exc()
        STATS["errors"] += 1
        return False


async def main():
    await log("=" * 60)
    await log(f"{config.SITE_NAME} 自动刷课 v3.0")
    await log("=" * 60)
    await log(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    site_config = config.SITE_CONFIG

    async with async_playwright() as p:
        await log("启动浏览器...")
        browser = await p.chromium.launch(
            headless=config.HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        login_page = LoginPage(page, site_config)
        course_page = CoursePage(page, site_config)
        content_page = ContentPage(page, site_config)

        try:
            await log("=== 步骤1: 登录 ===")
            await login_page.navigate()
            await log(f"访问登录页: {config.BASE_URL}")
            ok = await login_page.do_login(config.USERNAME, config.PASSWORD, config.COURSE_URL)
            if not ok:
                await log("登录失败")
                await asyncio.sleep(10)
                return

            await log("\n=== 步骤2: 访问课程页面 ===")
            await course_page.navigate(config.COURSE_URL)

            await log("\n=== 步骤3: 扫描章节 ===")
            chapters = await course_page.scan_chapters()
            if not chapters:
                await log("没有未完成的章节！")
                await asyncio.sleep(5)
                return

            await log(f"\n=== 步骤4: 处理 {len(chapters)} 个章节 ===")
            for i, ch in enumerate(chapters[:config.MAX_CHAPTERS]):
                await log(f"\n--- 进度: {i+1}/{min(len(chapters), config.MAX_CHAPTERS)} ---")
                await process_leaf_chapter(page, course_page, content_page, ch, site_config)
                await asyncio.sleep(2)

            await log("\n" + "=" * 60)
            await log("刷课完成!")
            await log(f"  总章节: {len(chapters)}")
            await log(f"  已处理章节: {STATS['processed_chapters']}")
            await log(f"  已处理资源: {STATS['processed_resources']}")
            await log(f"  自适应答题: {STATS['adaptive_answered']}")
            await log(f"  错误: {STATS['errors']}")
            await log("=" * 60)

        except Exception as e:
            await log(f"主流程出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await log("浏览器将在 30 秒后关闭...")
            await asyncio.sleep(30)
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
