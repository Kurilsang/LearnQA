import asyncio
import random
import re
from typing import Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from config import config
from utils.logger import TestLogger

logger = TestLogger()


async def retry_find(page, selectors: list, timeout=5000):
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if await loc.count() > 0:
                await loc.first.wait_for(state="visible", timeout=timeout)
                return loc.first
        except Exception:
            continue
    return None


class ContentPage:
    def __init__(self, page: Page):
        self.page = page

    async def process_pptx(self) -> bool:
        logger.step("处理 PPTX 资源 - 翻页校验")
        pptx_frame = self.page.frame_locator("iframe.pptIframe")
        try:
            await pptx_frame.first.locator("body").wait_for(state="attached", timeout=15000)
        except Exception:
            await asyncio.sleep(5)

        next_btn_selectors = [
            ".next-btn", ".nextPage", ".page-next",
            "button:has-text('下一页')", "button:has-text('下一张')",
            '[aria-label="下一页"]', '[aria-label="下一张"]',
            ".ppt-next", "#nextPage", '[class*="next"]',
            ".icon-arrow-right", ".right-arrow",
        ]
        page_num_selectors = [
            ".page-num", ".pageNumber", ".current-page", ".pageIndex",
            ".btnWrap", '[class*="pageNum"]', '[class*="currentPage"]',
        ]

        total_pages = None
        current_page = 0
        no_next_count = 0
        max_pages = 200

        for p in range(max_pages):
            if total_pages is None:
                for sel in page_num_selectors:
                    try:
                        el = pptx_frame.first.locator(sel)
                        if await el.count() > 0:
                            text = await el.first.inner_text()
                            nums = re.findall(r'\d+', text)
                            if len(nums) >= 2:
                                current_page, total_pages = int(nums[0]), int(nums[1])
                                break
                    except Exception:
                        continue
                if total_pages and current_page >= total_pages:
                    break

            clicked = False
            for sel in next_btn_selectors:
                try:
                    btn = pptx_frame.first.locator(sel)
                    if await btn.count() > 0 and await btn.first.is_visible():
                        disabled = await btn.first.get_attribute("disabled")
                        cls = await btn.first.get_attribute("class") or ""
                        if disabled or "disabled" in cls:
                            clicked = True
                            break
                        await btn.first.click()
                        clicked = True
                        no_next_count = 0
                        await asyncio.sleep(config.PPTX_PAGE_INTERVAL)
                        break
                except Exception:
                    continue

            if not clicked:
                no_next_count += 1
                if no_next_count >= 5:
                    break
                try:
                    ppt_area = pptx_frame.first.locator(".previewBox, .videoBox, .pptContainer, body")
                    if await ppt_area.count() > 0:
                        box = await ppt_area.first.bounding_box()
                        if box:
                            x = box["x"] + box["width"] * 0.85
                            y = box["y"] + box["height"] * 0.5
                            await self.page.mouse.click(x, y)
                            await asyncio.sleep(config.PPTX_PAGE_INTERVAL)
                except Exception:
                    break

            if total_pages:
                for sel in page_num_selectors:
                    try:
                        el = pptx_frame.first.locator(sel)
                        if await el.count() > 0:
                            text = await el.first.inner_text()
                            nums = re.findall(r'\d+', text)
                            if nums and int(nums[0]) >= total_pages:
                                return True
                    except Exception:
                        continue
        return True

    async def process_html_pdf(self, resource_idx: int = None) -> bool:
        logger.step("处理 HTML/PDF 资源 - 滚动加载校验")
        pdf_frame = None
        for _ in range(15):
            frames = await self.page.evaluate("""
                () => Array.from(document.querySelectorAll('iframe')).map(f => ({
                    cls: f.className, src: (f.src || '').substring(0, 120)
                }))
            """)
            for f in frames:
                if "pdfv-resource" in f["src"] or "pdf-viewer" in f["src"] or "viewer.html" in f["src"]:
                    pdf_iframe = self.page.locator(f"iframe[src*='{f['src'][:60]}']").first
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
                            const vc = document.querySelector('#viewerContainer') || document.querySelector('#viewer') || document.querySelector('.pdfViewer');
                            if (!vc) return { error: 'no viewer' };
                            return { scrollHeight: vc.scrollHeight || 0, clientHeight: vc.clientHeight || vc.parentElement?.clientHeight || 0 };
                        }
                    """)
                    if info and "scrollHeight" in info and info["scrollHeight"] > 0:
                        sh, ch = info["scrollHeight"], info.get("clientHeight", 800)
                        if sh > ch:
                            steps = max(10, min(50, (sh - ch) // 200))
                            delta = (sh - ch) / steps
                            for i in range(steps + 1):
                                st = min(i * delta, sh - ch)
                                await pdf_frame.evaluate(f"""
                                    (() => {{
                                        const vc = document.querySelector('#viewerContainer') || document.querySelector('#viewer') || document.querySelector('.pdfViewer');
                                        if (vc) {{ vc.scrollTop = {st}; vc.dispatchEvent(new Event('scroll', {{bubbles: true}})); }}
                                    }})()
                                """)
                                await asyncio.sleep(config.SCROLL_STEP_DELAY)
                            await asyncio.sleep(3)
                            return True
                        else:
                            await asyncio.sleep(3)
                            return True
                except Exception:
                    await asyncio.sleep(2)

        scroll_selectors = [
            ".el-scrollbar.page-scroll", ".el-scrollbar.main-warp", ".el-scrollbar.app-warp",
            ".el-scrollbar__wrap", ".main-scrollview", ".row-table", ".contentBody",
            ".pdfViewer", "#pdf-viewer", "[class*='scroll']", ".el-scrollbar__view",
        ]
        scroll_el = None
        scroll_target = None
        for sel in scroll_selectors:
            try:
                loc = self.page.locator(sel).first
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

        steps = max(10, min(50, sh // 200))
        delta = (sh - ch) / steps
        for i in range(steps + 1):
            st = min(i * delta, sh - ch)
            try:
                await scroll_target.evaluate(f"el => el.scrollTop = {st}; el.dispatchEvent(new Event('scroll', {{bubbles: true}}))")
            except Exception:
                await scroll_el.evaluate(f"el => el.scrollTop = {st}")
            await asyncio.sleep(config.SCROLL_STEP_DELAY)

        await asyncio.sleep(3)
        return True

    async def process_video(self) -> bool:
        logger.step("处理视频资源 - 播放校验")
        video = self.page.locator("video")
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
                        play_btn = await retry_find(self.page, [
                            ".video-play-btn", ".play-button", "button:has-text('播放')",
                            "[class*=play]", "button:has-text('开始')",
                        ])
                        if play_btn:
                            await play_btn.click()
                wait_max = config.VIDEO_MAX_WAIT
                check_int = 10
                waited = 0
                stall = 0
                last = -1
                while waited < wait_max:
                    await asyncio.sleep(check_int)
                    waited += check_int
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
                    if stall >= 4:
                        break
                    last = cur
            except Exception:
                continue
        return True

    async def process_adaptive(self) -> bool:
        logger.step("处理自适应训练 - 答题流程校验")
        await asyncio.sleep(3)

        if len(self.page.context.pages) > 1:
            ap = self.page.context.pages[-1]
            await ap.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            await self._handle_adaptive_questions(ap)
            await ap.close()
            return True

        continue_btn = await retry_find(self.page, [
            "button:has-text('继续练习')", "button:has-text('开始练习')",
            "button:has-text('继续学习')", "button.el-button--gradient",
        ], timeout=8000)
        if continue_btn:
            await continue_btn.click()
            await asyncio.sleep(5)

        dialog = self.page.locator(".el-overlay-dialog, .el-dialog, [role=dialog]")
        if await dialog.count() > 0:
            dlg_btn = await retry_find(self.page, [
                ".el-overlay-dialog button.el-button--primary",
                ".el-dialog button.el-button--primary",
                "button:has-text('确定')", "button:has-text('开始')",
            ], timeout=3000)
            if dlg_btn:
                await dlg_btn.click()
                await asyncio.sleep(3)

        found = await self._try_find_questions_in_page(self.page)
        if not found:
            await self._try_find_questions_in_iframe(self.page)
        return True

    async def _try_find_questions_in_page(self, page):
        return await self._handle_adaptive_questions(page)

    async def _try_find_questions_in_iframe(self, page):
        pptx_frame = page.frame_locator("iframe.pptIframe")
        try:
            await pptx_frame.first.locator("body").wait_for(state="attached", timeout=10000)
        except Exception:
            return False

        max_rounds = 100
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
                    return { optCount: options.length, optTexts, question: question.substring(0, 200),
                             hasNext: !!nextBtn, hasSubmit: !!submitBtn, hasDone: !!doneBtn,
                             nextText: nextBtn, submitText: submitBtn, doneText: doneBtn };
                }
            """)
            if info["optCount"] == 0 and not info["hasNext"] and not info["hasSubmit"]:
                if r > 3:
                    break
                continue

            if info["optCount"] > 0:
                answer = await self._ai_ask(info["question"], info["optTexts"])
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
                confirm = await retry_find(self.page, [
                    ".el-message-box__btns .el-button--primary", ".el-button--primary",
                    "button:has-text('确定')", "button:has-text('确认')",
                ])
                if confirm:
                    await confirm.click()
                await asyncio.sleep(3)
                break
            elif info["hasNext"]:
                btn = pptx_frame.first.locator("button").filter(has_text="下一题")
                await btn.click()
                await asyncio.sleep(2)
            else:
                break
        return True

    async def _handle_adaptive_questions(self, page):
        max_questions = 100
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

            option_selectors = [
                ".el-radio", ".el-checkbox", ".option-item",
                ".choice-item", "[class*='option']", ".select-item",
            ]
            opts = None
            for os_ in option_selectors:
                try:
                    loc = page.locator(os_)
                    if await loc.count() > 0:
                        opts = loc
                        break
                except Exception:
                    continue

            if opts is None or await opts.count() == 0:
                sub_btn = await retry_find(page, [
                    "button:has-text('选完了')", "button:has-text('下一题')", "button:has-text('交卷')",
                    "div.CloseBtn", "div:has-text('交卷')", "button:has-text('提交')",
                    "button:has-text('确定')", ".next-btn", ".submit-btn",
                ])
                if sub_btn:
                    text = await sub_btn.inner_text()
                    await sub_btn.click()
                    await asyncio.sleep(1)
                    if "交卷" in text or "提交" in text:
                        await asyncio.sleep(1)
                        confirm = await retry_find(page, [
                            ".el-message-box__btns .el-button--primary", ".el-button--primary",
                            "button:has-text('确定')", "button:has-text('确认')", "button:has-text('是')",
                        ])
                        if confirm:
                            await confirm.click()
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

            answer = await self._ai_ask(question.strip() if question else "", option_texts)
            selected = False
            if answer:
                for oi in range(opt_count):
                    try:
                        ot = await opts.nth(oi).inner_text()
                        if answer.strip() in ot.strip() or ot.strip() in answer.strip():
                            await opts.nth(oi).click()
                            selected = True
                            break
                    except Exception:
                        continue
            if not selected:
                idx = random.randint(0, opt_count - 1)
                try:
                    await opts.nth(idx).click()
                except Exception:
                    pass
            await asyncio.sleep(1)

            next_btn = await retry_find(page, [
                "button:has-text('选完了')", "button:has-text('下一题')", "button:has-text('交卷')",
                "div.CloseBtn", "div:has-text('交卷')", "button:has-text('提交')",
                "button:has-text('确定')", ".next-btn",
            ])
            if next_btn:
                btn_text = await next_btn.inner_text()
                await next_btn.click()
                await asyncio.sleep(1)
                if "交卷" in btn_text or "提交" in btn_text:
                    await asyncio.sleep(1.5)
                    confirm = await retry_find(page, [
                        ".el-message-box__btns .el-button--primary", ".el-button--primary",
                        "button:has-text('确定')", "button:has-text('确认')", "button:has-text('是')",
                    ])
                    if confirm:
                        await confirm.click()
                    await asyncio.sleep(3)
                    close_btn = await retry_find(page, [
                        "button:has-text('关闭')", "button:has-text('知道了')", "button:has-text('确定')",
                    ])
                    if close_btn:
                        await close_btn.click()
                        await asyncio.sleep(1)
                    break
            else:
                break
        return True

    async def _ai_ask(self, question: str, options: list) -> str:
        if not config.AI_API_KEY:
            return random.choice(options) if options else ""
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
                            {"role": "system", "content": "你是一个学习助手。请根据题目和选项，选择正确答案。只回复选项的完整文本内容，不要加其他文字。"},
                            {"role": "user", "content": f"题目：{question}\n\n选项：\n" + "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options))}
                        ]
                    },
                )
                result = resp.json()
                return result["choices"][0]["message"]["content"].strip()
        except Exception:
            return random.choice(options) if options else ""

    async def get_content_type(self) -> str:
        resource_list = self.page.locator(".activity-list-item")
        if await resource_list.count() > 0:
            statuses = self.page.locator(".activityStatus span").first
            if await statuses.count() > 0:
                return await statuses.inner_text()
        return "unknown"
