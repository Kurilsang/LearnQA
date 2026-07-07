import asyncio

from core.registry import registry


class ResourceService:

    @staticmethod
    async def process_resource(page, course, content, res: dict, site_config, stats: dict = None, log_cb=None):
        if log_cb is None:
            log_cb = lambda msg: None

        if res["isFinish"]:
            await log_cb(f"  [{res['type']}] {res['name']} 已完成，跳过")
            return

        await log_cb(f"  --- [{res['type']}] {res['name']} ---")

        if not await course.click_resource(res):
            await log_cb(f"  [!] 无法点击资源")
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
                    "log_cb": log_cb,
                    "resource_idx": res["idx"],
                    "site_config": site_config,
                    **site_config.default_params,
                }
                await registry.execute(handler_name, page, params)

                if handler_name in ("process_adaptive", "handle_adaptive_questions"):
                    if stats is not None:
                        stats["adaptive_answered"] = stats.get("adaptive_answered", 0) + 1
            else:
                await log_cb(f"  [?] 未知资源类型: {res_type}，等待 60 秒")
                await asyncio.sleep(60)
        except Exception as e:
            await log_cb(f"  [!] 处理 {res_type} 时出错: {e}")
            if stats is not None:
                stats["errors"] = stats.get("errors", 0) + 1

        await log_cb("  等待资源标记完成...")
        finished = await course.wait_resource_finish(res["idx"], timeout=120)
        if finished:
            await log_cb(f"  {res['name']} 已完成")
        else:
            await log_cb(f"  可能未标记完成，继续下一步")
        if stats is not None:
            stats["processed_resources"] = stats.get("processed_resources", 0) + 1

    @staticmethod
    async def process_chapter_content(page, course, content, site_config, stats: dict = None, log_cb=None):
        if log_cb is None:
            log_cb = lambda msg: None

        await log_cb("--- 处理章节内容 ---")
        await asyncio.sleep(5)

        if len(page.context.pages) > 1:
            await log_cb("检测到新标签页，切换到新标签页")
            np = page.context.pages[-1]
            await np.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            from pages.course_page import CoursePage
            from pages.content_page import ContentPage
            await ResourceService.process_chapter_content(
                np, CoursePage(np, site_config), ContentPage(np, site_config), site_config, stats, log_cb
            )
            await np.close()
            return

        resources = await course.scan_resources()
        if not resources:
            await log_cb("未找到资源列表，等待后继续")
            await asyncio.sleep(5)
            return

        for res in resources:
            await ResourceService.process_resource(page, course, content, res, site_config, stats, log_cb)

        await log_cb("返回课程首页...")
        await course.go_back()
