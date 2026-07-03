"""
FIF 站点专属处理器
本节包含 FIF 平台特有的复杂处理逻辑：
  - PPTX 翻页（iframe 内找按钮 + 右半区域点击）
  - HTML/PDF 滚动（PDF.js viewer + 页面滚动容器）
  - 视频播放（自动播放 + 卡住检测 + 续播）
  - 自适应训练（AI 答题 + 页面/iframe 内查找题目）
"""
import asyncio
import random
import re

from core.registry import registry


async def ai_ask(question: str, options: list) -> str:
    from config import config as _cfg
    if not _cfg.AI_API_KEY:
        return random.choice(options) if options else ""
    try:
        import httpx
        timeout = httpx.Timeout(30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{_cfg.AI_API_BASE.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {_cfg.AI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _cfg.AI_MODEL,
                    "temperature": _cfg.AI_TEMPERATURE,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个学习助手。请根据题目和选项，选择正确答案。只回复选项的完整文本内容，不要加其他文字。",
                        },
                        {
                            "role": "user",
                            "content": f"题目：{question}\n\n选项：\n"
                                       + "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options)),
                        },
                    ],
                },
            )
            result = resp.json()
            return result["choices"][0]["message"]["content"].strip()
    except Exception:
        return random.choice(options) if options else ""


async def select_answer(page, opts, question: str, option_texts: list, logger=None):
    opt_count = len(option_texts)
    if opt_count == 0:
        return False
    answer = await ai_ask(question, option_texts)
    selected = False
    if answer:
        for oi in range(opt_count):
            try:
                ot = await opts.nth(oi).inner_text()
                if answer.strip() in ot.strip() or ot.strip() in answer.strip():
                    if logger:
                        await logger(f"[自适应] AI选选项 {oi+1}: {ot.strip()[:50]}")
                    await opts.nth(oi).click()
                    selected = True
                    break
            except Exception:
                continue
    if not selected:
        idx = random.randint(0, opt_count - 1)
        try:
            ot = await opts.nth(idx).inner_text()
            if logger:
                await logger(f"[自适应] 随机选 {idx+1}: {ot.strip()[:50]}")
            await opts.nth(idx).click()
        except Exception:
            pass
    return True


async def pptx_handle_next_button(page, pptx_frame, logger=None, pptx_page_interval=1.5):
    pptx_frame_first = pptx_frame.first
    from core.base_page import BasePage
    bp = BasePage(page, None)
    bp._page_key = "content_page"
    bp.site = page.__dict__.get("_site_config")

    if bp.site is None:
        next_btn_selectors = [
            ".next-btn", ".nextPage", ".page-next",
            "button:has-text('下一页')", "button:has-text('下一张')",
            '[aria-label="下一页"]', '[aria-label="下一张"]',
            ".ppt-next", "#nextPage", '[class*="next"]',
            ".icon-arrow-right", ".right-arrow",
        ]
        for sel in next_btn_selectors:
            try:
                btn = pptx_frame_first.locator(sel)
                if await btn.count() > 0 and await btn.first.is_visible():
                    disabled = await btn.first.get_attribute("disabled")
                    cls = await btn.first.get_attribute("class") or ""
                    if disabled or "disabled" in cls:
                        return True
                    await btn.first.click()
                    await asyncio.sleep(pptx_page_interval)
                    return False
            except Exception:
                continue
        return None
    else:
        selectors = bp.el_group("pptx_next_button")
        for sel in selectors:
            try:
                btn = pptx_frame_first.locator(sel)
                if await btn.count() > 0 and await btn.first.is_visible():
                    disabled = await btn.first.get_attribute("disabled")
                    cls = await btn.first.get_attribute("class") or ""
                    if disabled or "disabled" in cls:
                        return True
                    await btn.first.click()
                    await asyncio.sleep(pptx_page_interval)
                    return False
            except Exception:
                continue
        return None


async def pptx_get_page_info(pptx_frame, bp=None):
    pptx_frame_first = pptx_frame.first
    if bp is None:
        page_num_selectors = [
            ".page-num", ".pageNumber", ".current-page", ".pageIndex",
            ".btnWrap", '[class*="pageNum"]', '[class*="currentPage"]',
        ]
    else:
        page_num_selectors = bp.el_group("pptx_page_number") or [
            ".page-num", ".pageNumber", ".current-page", ".pageIndex",
            ".btnWrap", '[class*="pageNum"]', '[class*="currentPage"]',
        ]
    for sel in page_num_selectors:
        try:
            el = pptx_frame_first.locator(sel)
            if await el.count() > 0:
                text = await el.first.inner_text()
                nums = re.findall(r'\d+', text)
                if len(nums) >= 2:
                    return int(nums[0]), int(nums[1])
        except Exception:
            continue
    return None, None


async def process_pptx(page, params: dict = None):
    p = params or {}
    logger = p.get("log_cb")
    site_config = p.get("site_config")
    pptx_interval = p.get("pptx_page_interval", 1.5)
    max_pages = p.get("pptx_max_pages", 200)
    no_next_threshold = p.get("pptx_no_next_threshold", 5)
    click_ratio = p.get("pptx_right_click_ratio", 0.85)

    if logger:
        await logger("[PPTX] 开始翻页...")
    pptx_frame = page.frame_locator("iframe.pptIframe")
    try:
        await pptx_frame.first.locator("body").wait_for(state="attached", timeout=15000)
    except Exception:
        await asyncio.sleep(5)

    total_pages = None
    current_page = 0
    no_next_count = 0

    bp = None
    if site_config:
        from core.base_page import BasePage
        bp = BasePage(page, site_config)
        bp._page_key = "content_page"

    for p_idx in range(max_pages):
        if total_pages is None:
            cp, tp = await pptx_get_page_info(pptx_frame, bp)
            if cp is not None and tp is not None:
                current_page, total_pages = cp, tp
                if current_page >= total_pages:
                    break

        result = await pptx_handle_next_button(page, pptx_frame, logger, pptx_interval)
        if result is True:
            break
        elif result is None:
            no_next_count += 1
            if no_next_count >= no_next_threshold:
                break
            try:
                area = pptx_frame.first.locator(".previewBox, .videoBox, .pptContainer, body")
                if await area.count() > 0:
                    box = await area.first.bounding_box()
                    if box:
                        x = box["x"] + box["width"] * click_ratio
                        y = box["y"] + box["height"] * 0.5
                        await page.mouse.click(x, y)
                        await asyncio.sleep(pptx_interval)
            except Exception:
                break

        if total_pages:
            cp, _ = await pptx_get_page_info(pptx_frame, bp)
            if cp is not None and cp >= total_pages:
                break
    if logger:
        await logger("[PPTX] 翻页完成")
    return True


async def process_html_pdf(page, params: dict = None):
    p = params or {}
    logger = p.get("log_cb")
    resource_idx = p.get("resource_idx")
    scroll_delay = p.get("scroll_step_delay", 0.5)
    scroll_factor = p.get("pdf_scroll_factor", 200)
    min_steps = p.get("pdf_scroll_min_steps", 10)
    max_steps = p.get("pdf_scroll_max_steps", 50)
    site_config = p.get("site_config")

    if logger:
        await logger("[HTML/PDF] 处理文档资源...")

    pdf_frame = None
    for _ in range(15):
        frames = await page.evaluate("""
            () => Array.from(document.querySelectorAll('iframe')).map(f => ({
                cls: f.className, src: (f.src || '').substring(0, 120)
            }))
        """)
        for f in frames:
            if any(kw in f["src"] for kw in ("pdfv-resource", "pdf-viewer", "viewer.html")):
                pdf_iframe = page.locator(f"iframe[src*='{f['src'][:60]}']").first
                if await pdf_iframe.count() > 0:
                    el_h = await pdf_iframe.element_handle()
                    pdf_frame = await el_h.content_frame()
                break
        if pdf_frame:
            break
        await asyncio.sleep(1)

    if pdf_frame:
        for retry in range(3):
            try:
                info = await pdf_frame.evaluate("""
                    () => {
                        const vc = document.querySelector('#viewerContainer')
                            || document.querySelector('#viewer')
                            || document.querySelector('.pdfViewer');
                        if (!vc) return { error: 'no viewer' };
                        return {
                            scrollHeight: vc.scrollHeight || 0,
                            clientHeight: vc.clientHeight || vc.parentElement?.clientHeight || 0
                        };
                    }
                """)
                if info and "scrollHeight" in info and info["scrollHeight"] > 0:
                    sh, ch = info["scrollHeight"], info.get("clientHeight", 800)
                    if sh > ch:
                        steps = max(min_steps, min(max_steps, (sh - ch) // scroll_factor))
                        delta = (sh - ch) / steps
                        for i in range(steps + 1):
                            st = min(i * delta, sh - ch)
                            await pdf_frame.evaluate(f"""
                                (() => {{
                                    const vc = document.querySelector('#viewerContainer')
                                        || document.querySelector('#viewer')
                                        || document.querySelector('.pdfViewer');
                                    if (vc) {{
                                        vc.scrollTop = {st};
                                        vc.dispatchEvent(new Event('scroll', {{bubbles: true}}));
                                    }}
                                }})()
                            """)
                            await asyncio.sleep(scroll_delay)
                        await asyncio.sleep(3)
                        return True
                    else:
                        await asyncio.sleep(3)
                        return True
            except Exception:
                await asyncio.sleep(2)

    scroll_el = None
    scroll_target = None
    scroll_selectors = [
        ".el-scrollbar.page-scroll", ".el-scrollbar.main-warp", ".el-scrollbar.app-warp",
        ".el-scrollbar__wrap", ".main-scrollview", ".row-table", ".contentBody",
        ".pdfViewer", "#pdf-viewer", "[class*='scroll']", ".el-scrollbar__view",
    ]
    for sel in scroll_selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                scroll_el = loc
                inner = scroll_el.locator(".el-scrollbar__wrap").first
                if await inner.count() > 0:
                    scroll_target = inner
                break
        except Exception:
            continue
    if not scroll_el:
        await asyncio.sleep(3)
        return True

    scroll_target = scroll_target or scroll_el
    sh = await scroll_el.evaluate("el => el.scrollHeight || 0")
    ch = await scroll_target.evaluate("el => el.clientHeight || 800")
    if sh <= ch:
        await asyncio.sleep(3)
        return True

    steps = max(min_steps, min(max_steps, sh // scroll_factor))
    delta = (sh - ch) / steps
    for i in range(steps + 1):
        st = min(i * delta, sh - ch)
        try:
            await scroll_target.evaluate(
                f"el => el.scrollTop = {st}; el.dispatchEvent(new Event('scroll', {{bubbles: true}}))"
            )
        except Exception:
            await scroll_el.evaluate(f"el => el.scrollTop = {st}")
        await asyncio.sleep(scroll_delay)
    await asyncio.sleep(3)
    return True


async def process_video(page, params: dict = None):
    p = params or {}
    logger = p.get("log_cb")
    max_wait = p.get("video_max_wait", 2000)
    check_interval = p.get("video_check_interval", 10)
    stall_threshold = p.get("video_stall_threshold", 4)

    if logger:
        await logger("[视频] 处理视频资源...")
    video = page.locator("video")
    cnt = await video.count()
    if cnt == 0:
        return False

    for i in range(cnt):
        v = video.nth(i)
        try:
            duration = await v.evaluate("el => el.duration || 0")
            paused = await v.evaluate("el => el.paused")
            if duration > 0 and duration < 3:
                await asyncio.sleep(5)
                continue
            if paused:
                try:
                    await v.evaluate("el => el.play()")
                except Exception:
                    from core.base_page import BasePage
                    bp = BasePage(page, p.get("site_config"))
                    bp._page_key = "content_page"
                    play_btn = await bp.retry_find("play_button") if bp.site else None
                    if play_btn is None:
                        for sel in [".video-play-btn", ".play-button",
                                    "button:has-text('播放')", "[class*=play]",
                                    "button:has-text('开始')"]:
                            loc = page.locator(sel).first
                            if await loc.count() > 0:
                                play_btn = loc
                                break
                    if play_btn:
                        await play_btn.click()

            waited = 0
            stall = 0
            last = -1
            while waited < max_wait:
                await asyncio.sleep(check_interval)
                waited += check_interval
                cur = await v.evaluate("el => el.currentTime || 0")
                dur = await v.evaluate("el => el.duration || 0")
                paused = await v.evaluate("el => el.paused")
                if dur > 0 and cur >= dur - 2:
                    break
                if paused and cur > 0:
                    try:
                        await v.evaluate("el => el.play()")
                    except Exception:
                        pass
                if abs(cur - last) < 1:
                    stall += 1
                else:
                    stall = 0
                if stall >= stall_threshold:
                    break
                last = cur
        except Exception:
            continue
    return True


async def handle_adaptive_questions(page, params: dict = None):
    p = params or {}
    logger = p.get("log_cb")
    max_questions = p.get("adaptive_max_questions", 100)
    site_config = p.get("site_config")

    bp = None
    if site_config:
        from core.base_page import BasePage
        bp = BasePage(page, site_config)
        bp._page_key = "content_page"

    for q_idx in range(max_questions):
        await asyncio.sleep(2)
        question = ""
        question_selectors = [
            ".question-title", ".question-content", ".el-form-item__label",
            "[class*='question']", ".subject", ".topic", ".title",
        ]
        for qs in question_selectors:
            try:
                qel = page.locator(qs).first
                if await qel.count() > 0:
                    question = await qel.inner_text()
                    if question.strip():
                        break
            except Exception:
                continue

        opts = None
        option_selectors = [
            ".el-radio", ".el-checkbox", ".option-item",
            ".choice-item", "[class*='option']", ".select-item",
        ]
        for os_ in option_selectors:
            try:
                loc = page.locator(os_)
                if await loc.count() > 0:
                    opts = loc
                    break
            except Exception:
                continue

        if opts is None or await opts.count() == 0:
            action_selectors = [
                "button:has-text('选完了')", "button:has-text('下一题')",
                "button:has-text('交卷')", "div.CloseBtn", "div:has-text('交卷')",
                "button:has-text('提交')", "button:has-text('确定')", ".next-btn", ".submit-btn",
            ]
            sub_btn = None
            for sel in action_selectors:
                try:
                    loc = page.locator(sel).first
                    if await loc.count() > 0:
                        sub_btn = loc
                        break
                except Exception:
                    continue
            if sub_btn:
                text = await sub_btn.inner_text()
                await sub_btn.click()
                await asyncio.sleep(1)
                if "交卷" in text or "提交" in text:
                    await asyncio.sleep(1)
                    confirm_selectors = [
                        ".el-message-box__btns .el-button--primary", ".el-button--primary",
                        "button:has-text('确定')", "button:has-text('确认')", "button:has-text('是')",
                    ]
                    for sel in confirm_selectors:
                        try:
                            confirm = page.locator(sel).first
                            if await confirm.count() > 0:
                                await confirm.click()
                                break
                        except Exception:
                            continue
                    await asyncio.sleep(3)
                continue
            else:
                break

        opt_count = await opts.count()
        option_texts = []
        for oi in range(opt_count):
            try:
                ot = await opts.nth(oi).inner_text()
                option_texts.append(ot.strip())
            except Exception:
                option_texts.append(f"选项{oi+1}")

        await select_answer(page, opts, question.strip(), option_texts, logger)

        await asyncio.sleep(1)
        action_selectors = [
            "button:has-text('选完了')", "button:has-text('下一题')",
            "button:has-text('交卷')", "div.CloseBtn", "div:has-text('交卷')",
            "button:has-text('提交')", "button:has-text('确定')", ".next-btn",
        ]
        next_btn = None
        for sel in action_selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    next_btn = loc
                    break
            except Exception:
                continue
        if next_btn:
            btn_text = await next_btn.inner_text()
            await next_btn.click()
            await asyncio.sleep(1)
            if "交卷" in btn_text or "提交" in btn_text:
                await asyncio.sleep(1.5)
                confirm_selectors = [
                    ".el-message-box__btns .el-button--primary", ".el-button--primary",
                    "button:has-text('确定')", "button:has-text('确认')", "button:has-text('是')",
                ]
                for sel in confirm_selectors:
                    try:
                        confirm = page.locator(sel).first
                        if await confirm.count() > 0:
                            await confirm.click()
                            break
                    except Exception:
                        continue
                await asyncio.sleep(3)
                close_selectors = [
                    "button:has-text('关闭')", "button:has-text('知道了')",
                    "button:has-text('确定')",
                ]
                for sel in close_selectors:
                    try:
                        close_btn = page.locator(sel).first
                        if await close_btn.count() > 0:
                            await close_btn.click()
                            await asyncio.sleep(1)
                            break
                    except Exception:
                        continue
                break
        else:
            break
    if logger:
        await logger(f"[自适应] 答题完成")
    return True


async def handle_adaptive_in_iframe(page, params: dict = None):
    p = params or {}
    logger = p.get("log_cb")
    max_rounds = p.get("adaptive_iframe_max_rounds", 100)

    pptx_frame = page.frame_locator("iframe.pptIframe")
    try:
        await pptx_frame.first.locator("body").wait_for(state="attached", timeout=10000)
    except Exception:
        return False

    for r in range(max_rounds):
        await asyncio.sleep(2)
        info = await pptx_frame.first.evaluate("""
            () => {
                const radios = document.querySelectorAll('.el-radio');
                const checks = document.querySelectorAll('.el-checkbox');
                const options = radios.length > 0 ? radios : checks;
                const optTexts = Array.from(options).slice(0, 10).map(o => (o.innerText || '').trim());
                const qEl = document.querySelector('[class*="question"], .el-form-item__label, .subject, .topic');
                const question = qEl ? qEl.innerText.trim() : '';
                const btns = document.querySelectorAll('button, div.CloseBtn, div.text');
                let nextBtn = null, submitBtn = null, doneBtn = null;
                btns.forEach(b => {
                    const t = b.innerText.trim();
                    if (t.includes('选完了')) doneBtn = t;
                    if (t.includes('下一题')) nextBtn = t;
                    if (t.includes('交卷')) submitBtn = t;
                });
                return {
                    optCount: options.length, optTexts, question: question.substring(0, 200),
                    hasNext: !!nextBtn, hasSubmit: !!submitBtn, hasDone: !!doneBtn,
                    nextText: nextBtn, submitText: submitBtn, doneText: doneBtn
                };
            }
        """)
        if info["optCount"] == 0 and not info["hasNext"] and not info["hasSubmit"]:
            if r > 3:
                break
            continue

        if info["optCount"] > 0:
            answer = await ai_ask(info["question"], info["optTexts"])
            selected = False
            if answer:
                for oi, ot in enumerate(info["optTexts"]):
                    if answer.strip() in ot or ot in answer.strip():
                        await pptx_frame.first.locator(".el-radio, .el-checkbox").nth(oi).click()
                        selected = True
                        break
            if not selected:
                idx = random.randint(0, info["optCount"] - 1)
                await pptx_frame.first.locator(".el-radio, .el-checkbox").nth(idx).click()
            await asyncio.sleep(1)

        if info["hasDone"]:
            btn = pptx_frame.first.locator("button").filter(has_text="选完了")
            await btn.click()
            await asyncio.sleep(2)
        elif info["hasSubmit"]:
            btn = pptx_frame.first.locator("div.CloseBtn, div:has-text('交卷'), button:has-text('交卷')").first
            await btn.click()
            await asyncio.sleep(2)
            confirm_selectors = [
                ".el-message-box__btns .el-button--primary", ".el-button--primary",
                "button:has-text('确定')", "button:has-text('确认')",
            ]
            for sel in confirm_selectors:
                try:
                    confirm = page.locator(sel).first
                    if await confirm.count() > 0:
                        await confirm.click()
                        break
                except Exception:
                    continue
            await asyncio.sleep(3)
            break
        elif info["hasNext"]:
            btn = pptx_frame.first.locator("button").filter(has_text="下一题")
            await btn.click()
            await asyncio.sleep(2)
        else:
            break
    return True


async def process_adaptive(page, params: dict = None):
    p = params or {}
    logger = p.get("log_cb")
    site_config = p.get("site_config")

    if logger:
        await logger("[自适应] 处理自适应训练...")
    await asyncio.sleep(3)

    if len(page.context.pages) > 1:
        ap = page.context.pages[-1]
        await ap.wait_for_load_state("networkidle")
        await asyncio.sleep(3)
        await handle_adaptive_questions(ap, p)
        await ap.close()
        return True

    continue_selectors = [
        "button:has-text('继续练习')", "button:has-text('开始练习')",
        "button:has-text('继续学习')", "button.el-button--gradient",
    ]
    continue_btn = None
    for sel in continue_selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                await loc.wait_for(state="visible", timeout=8000)
                continue_btn = loc
                break
        except Exception:
            continue
    if continue_btn:
        await continue_btn.click()
        await asyncio.sleep(5)

    dialog = page.locator(".el-overlay-dialog, .el-dialog, [role=dialog]")
    if await dialog.count() > 0:
        dlg_selectors = [
            ".el-overlay-dialog button.el-button--primary",
            ".el-dialog button.el-button--primary",
            "button:has-text('确定')", "button:has-text('开始')",
        ]
        for sel in dlg_selectors:
            try:
                dlg_btn = page.locator(sel).first
                if await dlg_btn.count() > 0:
                    await dlg_btn.click()
                    await asyncio.sleep(3)
                    break
            except Exception:
                continue

    found = await handle_adaptive_questions(page, p)
    if not found:
        if logger:
            await logger("[自适应] 主页面未找到题目，尝试 iframe...")
        await handle_adaptive_in_iframe(page, p)
    return True
