"""
FIF 自适应学习平台 - 自动刷课脚本 v2.0
使用 Playwright 自动登录、遍历未完成章节、按资源类型分别处理学习内容

支持的资源类型:
  - PPTX: 在 iframe 内自动翻页到最后一页
  - HTML/PDF: 自动滚动内容到底部
  - 视频: 自动播放并等待完成
  - 自适应训练: 获取题目 -> 调用 AI -> 选择答案 -> 提交
"""

import asyncio
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from enum import Enum
from urllib.parse import urlparse, parse_qs

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ============================================================
# 从 .env 加载配置（如果存在）
# ============================================================
# 确保始终从脚本所在目录加载 .env
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_env_path = os.path.join(_SCRIPT_DIR, ".env")
try:
    from dotenv import load_dotenv
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
        print(f"[配置] 已加载 .env: {_env_path}")
    else:
        print(f"[配置] 未找到 .env 文件 (预期路径: {_env_path})")
except ImportError:
    print("[配置] python-dotenv 未安装，请执行: pip install python-dotenv")

def env(key: str, default=None):
    """从环境变量取值，支持 .env"""
    return os.environ.get(key, default)

# ============================================================
# 配置
# ============================================================
# 优先级：环境变量 > .env 文件 > 硬编码默认值
CONFIG = {
    "login_url": env("LOGIN_URL", "https://www.fifedu.com/iplat/fifLogin/index.html?v=5.4.4"),
    "course_url": env("COURSE_URL", (
        "https://icourse.fifedu.com/istp-learning-center/"
        "index?courseId=0bbe8331f3ae41d4ade3618c31e5c0d9"
        "&classId=2811000226001709298&termId=0ebfcb74812d4e5ab9f8f1919a341d97"
    )),
    "username": env("FIF_USERNAME", env("USERNAME")),  # 优先使用 FIF_USERNAME，兼容旧写法
    "password": env("FIF_PASSWORD", env("PASSWORD")),  # 优先使用 FIF_PASSWORD，兼容旧写法
    "headless": env("HEADLESS", "false").lower() == "true",
    "timeout": int(env("TIMEOUT", "30000")),
    "max_chapters": int(env("MAX_CHAPTERS", "100")),

    # AI 配置（用于自适应训练答题）- 支持 OpenAI 兼容 API
    # 默认使用 DeepSeek，可在 .env 中修改
    "ai_api_base": env("AI_API_BASE", "https://api.deepseek.com"),
    "ai_api_key": env("AI_API_KEY", ""),  # 设为 "" 则使用随机选择答案
    "ai_model": env("AI_MODEL", "deepseek-chat"),
    "ai_temperature": float(env("AI_TEMPERATURE", "0.1")),

    # 资源处理超时
    "pptx_page_interval": float(env("PPTX_PAGE_INTERVAL", "1.5")),
    "scroll_step_delay": float(env("SCROLL_STEP_DELAY", "0.5")),
    "video_max_wait": int(env("VIDEO_MAX_WAIT", "300")),
}

STATS = {
    "processed_chapters": 0,
    "processed_resources": 0,
    "errors": 0,
    "adaptive_answered": 0,
}


# ============================================================
# 工具函数
# ============================================================

async def log(msg: str):
    """带时间戳的日志"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


async def safe_click(locator, timeout=10000):
    """安全点击元素"""
    try:
        await locator.wait_for(state="visible", timeout=timeout)
        await locator.click()
        return True
    except Exception:
        return False


async def retry_find(page, selectors: list, timeout=5000):
    """依次尝试多个选择器直到找到可见元素"""
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if await loc.count() > 0:
                await loc.first.wait_for(state="visible", timeout=timeout)
                return loc.first
        except Exception:
            continue
    return None


# ============================================================
# 登录 & 导航
# ============================================================

async def login(page) -> bool:
    await log("=== 步骤1: 登录 ===")
    await log(f"访问登录页面: {CONFIG['login_url']}")
    await page.goto(CONFIG["login_url"], wait_until="networkidle", timeout=60000)
    await asyncio.sleep(3)

    await log("填写账号...")
    uname = page.locator('input[name="user"]')
    await uname.wait_for(state="visible", timeout=10000)
    await uname.click()
    await uname.fill("")
    await uname.type(CONFIG["username"], delay=30)

    await log("填写密码...")
    pwd = page.locator("#passWord")
    await pwd.wait_for(state="visible", timeout=10000)
    await pwd.click()
    await pwd.fill("")
    await pwd.type(CONFIG["password"], delay=30)
    await asyncio.sleep(1)

    await log("点击登录按钮...")
    login_btn = page.locator("button.cursor_p").get_by_text("登录", exact=True)
    await login_btn.wait_for(state="visible", timeout=10000)
    await login_btn.click()

    # 等待登录：先等 URL 变化，再确认能访问课程页面
    await log("等待登录完成...")
    await page.screenshot(path="debug_after_click_login.png")
    
    # 策略1: 等待 20 秒看 URL 是否变化
    for i in range(20):
        await asyncio.sleep(1)
        current = page.url
        await log(f"  等待登录... ({i+1}s) URL: {current[:80]}")
        # 不包含 login 关键词（只检查路径部分）
        path = current.split("?")[0].lower()
        if "login" not in path:
            await log(f"登录成功! URL: {current}")
            await page.screenshot(path="debug_login_ok.png")
            await asyncio.sleep(3)
            return True

    # 策略2: 直接导航到课程页面验证
    await log("尝试直接导航到课程页面验证登录状态...")
    await page.goto(CONFIG["course_url"], wait_until="networkidle", timeout=30000)
    await asyncio.sleep(5)
    await page.screenshot(path="debug_after_nav_to_course.png")
    
    title = await page.title()
    text = await page.evaluate("document.body.innerText.substring(0, 300)")
    await log(f"课程页标题: {title}")
    await log(f"课程页文本(前300字): {text[:200]}")
    
    if "课程" in text or "学习" in text or "章节" in text or "自适应" in text:
        await log("成功访问课程页面，登录有效!")
        return True
    
    await log("登录似乎未成功，请检查 .env 中的 USERNAME 和 PASSWORD")
    return False


async def navigate_to_course(page):
    await log("\n=== 步骤2: 访问课程页面 ===")
    await page.goto(CONFIG["course_url"], wait_until="networkidle", timeout=60000)
    await log("等待动态内容加载...")
    await asyncio.sleep(8)


# ============================================================
# 章节扫描
# ============================================================

async def expand_all_chapters(page):
    await log("展开所有章节节点...")
    for attempt in range(5):
        collapsed = await page.evaluate("""
            () => document.querySelectorAll('.left-arrow:not(.is-open):not(.dian)').length
        """)
        if collapsed == 0:
            await log("所有章节已展开")
            return
        await log(f"还有 {collapsed} 个折叠箭头")
        arrows = page.locator('.left-arrow:not(.is-open):not(.dian)')
        cnt = await arrows.count()
        for i in range(min(cnt, 30)):
            try:
                await arrows.nth(i).click()
                await asyncio.sleep(0.2)
            except Exception:
                pass
        await asyncio.sleep(1.5)
    await log("展开完成（可能仍有未展开的节点）")


async def scan_chapters(page) -> list:
    await log("\n=== 步骤3: 扫描章节列表 ===")
    await expand_all_chapters(page)

    chapters_info = await page.evaluate("""
        () => {
            const nodes = document.querySelectorAll('.index-tree-node');
            const results = [];
            nodes.forEach((node, index) => {
                const tn = node.querySelector('.tree-node-name');
                if (!tn) return;
                const isLevel1 = tn.classList.contains('level_1');
                const hasChild = node.querySelector('.index-tree-node') !== null;
                const noChild = tn.classList.contains('no-child');
                // 使用 tn (当前节点的tree-node-name) 而不是 node 来限制搜索范围
                // 避免搜到子节点中的 icon-isfinished
                const done = tn.querySelector('.icon-isfinished') !== null;
                const prog = tn.querySelector('.study-progress-wrapper') !== null;
                const cur = tn.querySelector('.current-study-icon') !== null;
                const pad = parseInt(window.getComputedStyle(tn).paddingLeft) || 0;
                const level = Math.round(pad / 20) + 1;
                node.setAttribute('data-chapter-id', String(index));
                results.push({
                    idx: index,
                    name: tn.innerText.trim(),
                    level, isLevel1,
                    isLeaf: !hasChild || noChild,
                    done, prog, cur,
                    // 使用 > 子选择器避免匹配到下级节点的 .tree-node-name
                    sel: `.index-tree-node[data-chapter-id="${index}"] > .aside-row > .tree-name-title > .tree-node-name`,
                });
            });
            return results;
        }
    """)

    await log(f"共 {len(chapters_info)} 个节点")
    # 调试：打印所有有进度圈(prog=true)或未完成(done=false)的节点
    pending_nodes = [c for c in chapters_info if not c["done"] or c["prog"]]
    if pending_nodes:
        await log(f"有进度或未完成的节点: {len(pending_nodes)} 个:")
        for ch in pending_nodes:
            st = "已完成" if ch["done"] else ("当前" if ch["cur"] else ("部分" if ch["prog"] else "未开始"))
            lv = "L1" if ch["isLevel1"] else ("叶子" if ch["isLeaf"] else "中间")
            await log(f"  [{lv}] {ch['name']} ({st})")
    else:
        await log("没有找到有进度或未完成的节点")

    # 包含所有有进度(study-progress-wrapper)的节点（包括L1级别）
    # 以及未完成的非L1节点
    unfinished = [c for c in chapters_info if c["prog"] or (not c["done"] and not c["isLevel1"])]
    await log(f"未完成非L1节点: {len(unfinished)} 个")
    for ch in unfinished:
        st = "当前" if ch["cur"] else ("部分" if ch["prog"] else "未开始")
        lv = "叶子" if ch["isLeaf"] else "中间"
        await log(f"  [{lv}] {ch['name']} ({st})")
    return unfinished


# ============================================================
# 资源列表扫描（在章节内容页内）
# ============================================================

async def scan_resources(page) -> list:
    """扫描当前章节内容页的资源列表"""
    resources = await page.evaluate("""
        () => {
            const items = document.querySelectorAll('.activity-list-item');
            return Array.from(items).map((item, i) => {
                const nameEl = item.querySelector('.show-line-text');
                const name = nameEl ? nameEl.innerText.trim() : '';
                const statuses = item.querySelectorAll('.activityStatus span');
                const typeText = statuses.length > 0 ? statuses[0].innerText.trim() : '';
                const stateText = statuses.length > 1 ? statuses[1].innerText.trim() : '';
                const isActive = item.classList.contains('is-active');
                const isFinish = item.querySelector('.is-finished') !== null;
                // 给每个资源项标记 data-resource-id 方便后续定位
                item.setAttribute('data-resource-id', String(i));
                return {
                    idx: i,
                    name: name,
                    type: typeText,
                    state: stateText,
                    isActive,
                    isFinish,
                    sel: `.activity-list-item[data-resource-id="${i}"]`,
                };
            });
        }
    """)
    await log(f"  资源列表: 共 {len(resources)} 个")
    for r in resources:
        mark = "✓" if r["isFinish"] else " "
        act = "←当前" if r["isActive"] else ""
        await log(f"    [{mark}] [{r['type']}] {r['name']} {act}")
    return resources


async def wait_resource_finish(page, resource_idx, timeout=120):
    """等待资源变为已完成状态（根据资源在列表中的索引定位）"""
    for _ in range(timeout):
        done = await page.evaluate(f"""
            () => {{
                const items = document.querySelectorAll('.activity-list-item');
                const el = items[{resource_idx}];
                if (!el) return false;
                return el.querySelector('.is-finished') !== null
                    || (el.querySelector('.activityStatus:last-child span')
                        && el.querySelector('.activityStatus:last-child span').innerText.includes('已完成'));
            }}
        """)
        if done:
            return True
        await asyncio.sleep(1)
    return False


# ============================================================
# 各资源类型处理逻辑
# ============================================================

async def process_pptx(page):
    """处理 PPTX 资源 - 在 iframe 内翻页到最后一页"""
    await log("[PPTX] 检测到PPT资源，准备翻页...")

    # 查找 PPTX iframe
    pptx_frame = page.frame_locator("iframe.pptIframe")
    try:
        # 等待 iframe 加载
        await pptx_frame.first.locator("body").wait_for(state="attached", timeout=15000)
    except Exception:
        await log("[PPTX] iframe 未加载，尝试直接等待")
        await asyncio.sleep(5)

    await log("[PPTX] iframe 已加载，开始翻页...")

    # 尝试在 iframe 中查找下一页按钮
    # 常见的PPT翻页按钮选择器
    next_btn_selectors = [
        ".next-btn",
        ".nextPage",
        ".page-next",
        "button:has-text('下一页')",
        "button:has-text('下一张')",
        '[aria-label="下一页"]',
        '[aria-label="下一张"]',
        ".ppt-next",
        "#nextPage",
        '[class*="next"]',
        "svg[class*='next']",
        "img[class*='next']",
        ".icon-arrow-right",
        ".right-arrow",
    ]

    page_num_selectors = [
        ".page-num",
        ".pageNumber",
        ".current-page",
        ".pageIndex",
        ".btnWrap",            # Bubbty 编辑器页码 (如 "1 / 1")
        '[class*="pageNum"]',
        '[class*="currentPage"]',
    ]

    # 尝试获取总页数
    total_pages = None
    current_page = 0
    max_pages = 200  # 安全上限
    no_next_count = 0  # 连续未找到翻页按钮次数

    for p in range(max_pages):
        # 检查是否到了最后一页
        # 尝试在 iframe 中找总页数信息
        if total_pages is None:
            for sel in page_num_selectors:
                try:
                    el = pptx_frame.first.locator(sel)
                    if await el.count() > 0:
                        text = await el.first.inner_text()
                        # 可能格式为 "1/15" 或 "第1页 共15页"
                        nums = re.findall(r'\d+', text)
                        if len(nums) >= 2:
                            current_page = int(nums[0])
                            total_pages = int(nums[1])
                            await log(f"[PPTX] 总页数: {total_pages}, 当前: {current_page}")
                            break
                        elif len(nums) == 1:
                            current_page = int(nums[0])
                except Exception:
                    continue
            # 如果有翻页信息且已完成，跳出
            if total_pages and current_page >= total_pages:
                await log("[PPTX] 已达到最后一页")
                break

        # 查找并点击下一页按钮
        clicked = False
        for sel in next_btn_selectors:
            try:
                btn = pptx_frame.first.locator(sel)
                if await btn.count() > 0 and await btn.first.is_visible():
                    # 检查是否禁用
                    disabled = await btn.first.get_attribute("disabled")
                    cls = await btn.first.get_attribute("class") or ""
                    if disabled or "disabled" in cls:
                        await log("[PPTX] 下一页按钮已禁用，到达最后一页")
                        clicked = True
                        break
                    await btn.first.click()
                    clicked = True
                    no_next_count = 0
                    await asyncio.sleep(CONFIG["pptx_page_interval"])
                    break
            except Exception:
                continue

        if not clicked:
            no_next_count += 1
            # 超过 5 次没找到翻页按钮，认为已到最后一页
            if no_next_count >= 5:
                await log("[PPTX] 连续 5 次未找到翻页按钮，认为已到最后一页")
                break
            # 如果找不到按钮，尝试点击 PPT 内容区域右半部分
            await log("[PPTX] 未找到翻页按钮，尝试点击右半区域...")
            try:
                ppt_area = pptx_frame.first.locator(".previewBox, .videoBox, .pptContainer, body")
                if await ppt_area.count() > 0:
                    box = await ppt_area.first.bounding_box()
                    if box:
                        # 点击右半部分
                        x = box["x"] + box["width"] * 0.85
                        y = box["y"] + box["height"] * 0.5
                        await page.mouse.click(x, y)
                        await asyncio.sleep(CONFIG["pptx_page_interval"])
            except Exception:
                await log("[PPTX] 无法翻页，等待超时")
                break

        # 如果已有总页数信息，检查是否到最后一页
        if total_pages:
            for sel in page_num_selectors:
                try:
                    el = pptx_frame.first.locator(sel)
                    if await el.count() > 0:
                        text = await el.first.inner_text()
                        nums = re.findall(r'\d+', text)
                        if nums:
                            cp = int(nums[0])
                            if cp >= total_pages:
                                await log(f"[PPTX] 翻页完成 ({cp}/{total_pages})")
                                return True
                except Exception:
                    continue

        # 每10页输出一次进度
        if (p + 1) % 10 == 0:
            await log(f"[PPTX] 已翻页 {p+1} 次")

    await log(f"[PPTX] 翻页结束 (共操作 {max_pages} 次)")
    return True


async def process_html_pdf(page, resource_idx=None):
    """处理 HTML/PDF 资源 - 滚动内容到底部"""
    await log("[HTML/PDF] 检测到文档资源...")

    # 查找 PDF viewer iframe（PDF.js viewer）
    pdf_iframe = None
    pdf_frame = None
    for _ in range(15):  # 最多等待 15 秒让 PDF viewer 加载
        frames = await page.evaluate("""
            () => Array.from(document.querySelectorAll('iframe')).map(f => ({
                cls: f.className,
                src: (f.src || '').substring(0,120)
            }))
        """)
        for f in frames:
            if "pdfv-resource" in f["src"] or "pdf-viewer" in f["src"] or "viewer.html" in f["src"]:
                await log(f"[HTML/PDF] 发现 PDF viewer iframe: {f['src']}")
                pdf_iframe = page.locator(f"iframe[src*='{f['src'][:60]}']").first
                if await pdf_iframe.count() > 0:
                    el_h = await pdf_iframe.element_handle()
                    pdf_frame = await el_h.content_frame()
                break
        if pdf_frame:
            break
        await asyncio.sleep(1)

    if pdf_frame:
        # 等待 PDF viewer 内部加载完成
        await log("[HTML/PDF] 等待 PDF viewer 加载...")
        viewer_ready = False
        for retry in range(15):
            try:
                ready = await pdf_frame.evaluate("""
                    () => !!(document.querySelector('#viewerContainer') || document.querySelector('#viewer') || document.querySelector('.pdfViewer'))
                """)
                if ready:
                    viewer_ready = True
                    break
            except:
                pass
            await asyncio.sleep(1)

        if not viewer_ready:
            await log("[HTML/PDF] PDF viewer 加载超时")
        else:
            await log("[HTML/PDF] PDF viewer 已就绪")
        # 在 PDF.js viewer 内滚动
        await log("[HTML/PDF] 在 PDF viewer 中操作...")
        max_retry = 3
        for retry in range(max_retry):
            try:
                info = await pdf_frame.evaluate("""
                    () => {
                        const vc = document.querySelector('#viewerContainer') || document.querySelector('#viewer') || document.querySelector('.pdfViewer');
                        if (!vc) return { error: 'no viewer' };
                        const sh = vc.scrollHeight || 0;
                        const ch = vc.clientHeight || vc.parentElement?.clientHeight || 0;
                        const pages = document.querySelectorAll('.page').length || 0;
                        const cp = (document.querySelector('.page[data-page-number]') || {}).dataset?.pageNumber || 0;
                        return { scrollHeight: sh, clientHeight: ch, pages, currentPage: parseInt(cp) || 0 };
                    }
                """)
                await log(f"  PDF viewer: {info}")
                if info and "scrollHeight" in info and info["scrollHeight"] > 0:
                    sh = info["scrollHeight"]
                    ch = info.get("clientHeight", 800)
                    if sh > ch:
                        steps = max(10, min(50, (sh - ch) // 200))
                        delta = (sh - ch) / steps
                        for i in range(steps + 1):
                            st = min(i * delta, sh - ch)
                            await pdf_frame.evaluate(f"""
                                (() => {{
                                    const vc = document.querySelector('#viewerContainer') || document.querySelector('#viewer') || document.querySelector('.pdfViewer');
                                    if (vc) {{
                                        vc.scrollTop = {st};
                                        vc.dispatchEvent(new Event('scroll', {{bubbles: true}}));
                                    }}
                                }})()
                            """)
                            await asyncio.sleep(CONFIG["scroll_step_delay"])
                            if (i + 1) % 5 == 0 and resource_idx is not None:
                                sts = await page.evaluate(f"""
                                    () => {{
                                        const items = document.querySelectorAll('.activity-list-item');
                                        const el = items[{resource_idx}];
                                        if (!el) return null;
                                        const spans = el.querySelectorAll('.activityStatus span');
                                        return spans.length > 1 ? spans[1].innerText.trim() : '';
                                    }}
                                """)
                                if sts and "已完成" in sts:
                                    await log("[HTML/PDF] PDF 已完成")
                                    break
                                if sts:
                                    await log(f"[HTML/PDF] 进度: [{sts}]")
                        await log("[HTML/PDF] PDF 滚动完成")
                        await asyncio.sleep(3)
                        return True
                    else:
                        await log("[HTML/PDF] PDF 无需滚动")
                        await asyncio.sleep(3)
                        return True
            except Exception as e:
                await log(f"[HTML/PDF] PDF viewer 操作失败(第{retry+1}次): {str(e)[:60]}")
                await asyncio.sleep(2)
                continue

    # 没有 PDF viewer iframe，使用页面级滚动（HTML 文档）
    scroll_selectors = [
        ".el-scrollbar.page-scroll",
        ".el-scrollbar.main-warp",
        ".el-scrollbar.app-warp",
        ".el-scrollbar__wrap",
        ".main-scrollview",
        ".row-table",
        ".contentBody",
        ".pdfViewer",
        "#pdf-viewer",
        "[class*='scroll']",
        ".el-scrollbar__view",
    ]

    scroll_el = None
    scroll_target = None
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
        await log("[HTML/PDF] 未找到滚动容器")
        await asyncio.sleep(3)
        return True

    scroll_target = scroll_target or scroll_el
    sh = await scroll_el.evaluate("el => el.scrollHeight || 0")
    ch = await scroll_target.evaluate("el => el.clientHeight || 800")

    if sh <= ch:
        await log(f"[HTML/PDF] 无滚动需求 (sh={sh} ch={ch})")
        await asyncio.sleep(3)
        return True

    steps = max(10, min(50, sh // 200))
    delta = (sh - ch) / steps
    await log(f"[HTML/PDF] 开始滚动 (sh={sh} ch={ch} steps={steps})...")

    for i in range(steps + 1):
        st = min(i * delta, sh - ch)
        try:
            await scroll_target.evaluate(f"el => el.scrollTop = {st}; el.dispatchEvent(new Event('scroll', {{bubbles: true}}))")
        except:
            await scroll_el.evaluate(f"el => el.scrollTop = {st}")
        await asyncio.sleep(CONFIG["scroll_step_delay"])
        if (i + 1) % 5 == 0 and resource_idx is not None:
            state = await page.evaluate(f"""
                () => {{
                    const items = document.querySelectorAll('.activity-list-item');
                    const el = items[{resource_idx}];
                    if (!el) return '';
                    const spans = el.querySelectorAll('.activityStatus span');
                    return spans.length > 1 ? spans[1].innerText.trim() : '';
                }}
            """)
            if "已完成" in (state or ""):
                await log("[HTML/PDF] 已完成")
                break
            if state:
                await log(f"[HTML/PDF] 进度: [{state}]")

    await log("[HTML/PDF] 滚动完成")
    await asyncio.sleep(3)
    return True


async def process_video(page):
    """处理视频资源 - 播放并等待完成"""
    await log("[视频] 检测到视频资源...")

    # 查找 video 元素
    video = page.locator("video")
    cnt = await video.count()
    if cnt == 0:
        await log("[视频] 未找到 video 元素")
        return False

    await log(f"[视频] 找到 {cnt} 个 video 元素")

    for i in range(cnt):
        v = video.nth(i)
        try:
            duration = await v.evaluate("el => el.duration || 0")
            current = await v.evaluate("el => el.currentTime || 0")
            paused = await v.evaluate("el => el.paused")

            await log(f"[视频{i+1}] 时长={duration:.1f}s, 当前={current:.1f}s, 暂停={paused}")

            if duration > 0 and duration < 3:
                await log("[视频] 视频很短，等5秒")
                await asyncio.sleep(5)
                continue

            # 尝试播放
            if paused:
                await log("[视频] 尝试播放...")
                try:
                    await v.evaluate("el => el.play()")
                except Exception:
                    # 找播放按钮
                    play_btn = await retry_find(page, [
                        ".video-play-btn",
                        ".play-button",
                        "button:has-text('播放')",
                        "[class*=play]",
                        "button:has-text('开始')",
                    ])
                    if play_btn:
                        await play_btn.click()

            # 等待播放完成
            wait_max = CONFIG["video_max_wait"]
            check_int = 10
            waited = 0
            last = -1
            stall = 0

            while waited < wait_max:
                await asyncio.sleep(check_int)
                waited += check_int
                cur = await v.evaluate("el => el.currentTime || 0")
                dur = await v.evaluate("el => el.duration || 0")
                paused = await v.evaluate("el => el.paused")

                if dur > 0:
                    await log(f"[视频] {cur:.0f}/{dur:.0f}s ({(cur/dur*100):.0f}%)")
                    if cur >= dur - 2:
                        await log("[视频] 播放完成!")
                        break
                else:
                    await log(f"[视频] 当前 {cur:.0f}s")

                if paused and cur > 0:
                    await log("[视频] 暂停，重播...")
                    try:
                        await v.evaluate("el => el.play()")
                    except Exception:
                        pass

                if abs(cur - last) < 1:
                    stall += 1
                else:
                    stall = 0
                if stall >= 4:
                    await log("[视频] 卡住，跳过")
                    break
                last = cur
        except Exception as e:
            await log(f"[视频] 出错: {e}")

    return True


# ============================================================
# AI 接口（用于自适应训练）
# ============================================================

async def ai_ask(question: str, options: list) -> str:
    """调用 AI API 获取题目答案，返回选项文本或索引"""
    if not CONFIG["ai_api_key"]:
        await log("[AI] 未配置 API Key，随机选择答案")
        return random.choice(options) if options else ""

    await log(f"[AI] 发送题目到 AI: {question[:80]}...")
    try:
        import httpx
        timeout = httpx.Timeout(30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{CONFIG['ai_api_base'].rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {CONFIG['ai_api_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": CONFIG["ai_model"],
                    "temperature": CONFIG["ai_temperature"],
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个学习助手。请根据题目和选项，选择正确答案。"
                                       "只回复选项的完整文本内容，不要加其他文字。"
                        },
                        {
                            "role": "user",
                            "content": f"题目：{question}\n\n选项：\n" + "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options))
                        }
                    ]
                },
            )
            result = resp.json()
            answer = result["choices"][0]["message"]["content"].strip()
            await log(f"[AI] 回答: {answer}")
            return answer
    except ImportError:
        await log("[AI] 未安装 httpx，使用随机选择")
        return random.choice(options) if options else ""
    except Exception as e:
        await log(f"[AI] API 调用失败: {e}，使用随机选择")
        return random.choice(options) if options else ""


# ============================================================
# 自适应训练处理
# ============================================================

async def process_adaptive(page):
    """处理自适应训练 - 点击继续练习 → 在iframe中答题 → 交卷"""
    await log("[自适应] 检测到自适应训练资源...")
    await asyncio.sleep(3)

    # 检测是否有新标签页
    if len(page.context.pages) > 1:
        await log("[自适应] 检测到新标签页，切换到新页")
        ap = page.context.pages[-1]
        await ap.wait_for_load_state("networkidle")
        await asyncio.sleep(3)
        await _handle_adaptive_questions(ap)
        await ap.close()
        return

    # 查找"继续练习"按钮并点击
    continue_btn = await retry_find(page, [
        "button:has-text('继续练习')",
        "button:has-text('开始练习')",
        "button:has-text('继续学习')",
        "button.el-button--gradient",
    ], timeout=8000)
    if continue_btn:
        btn_text = await continue_btn.inner_text()
        await log(f"[自适应] 点击按钮: [{btn_text}]")
        await continue_btn.click()
        await asyncio.sleep(5)
    else:
        await log("[自适应] 未找到继续练习按钮，可能已进入答题")

    # 检查是否有对话框弹窗（学习目标掌握度测评等）
    dialog = page.locator(".el-overlay-dialog, .el-dialog, [role=dialog]")
    if await dialog.count() > 0:
        await log("[自适应] 检测到对话框")
        # 如果在对话框中，检查是否有确定/开始按钮
        dlg_btn = await retry_find(page, [
            ".el-overlay-dialog button.el-button--primary",
            ".el-dialog button.el-button--primary",
            "button:has-text('确定')",
            "button:has-text('开始')",
        ], timeout=3000)
        if dlg_btn:
            await dlg_btn.click()
            await log("[自适应] 点击对话框按钮")
            await asyncio.sleep(3)

    # 先在主页面中找题目，如果找不到，再切换到 iframe
    found = await _try_find_questions_in_page(page)
    if not found:
        await log("[自适应] 主页面未找到题目，尝试在 iframe 中查找...")
        await _try_find_questions_in_iframe(page)
    else:
        await log("[自适应] 在主页面找到题目并完成答题")


async def _try_find_questions_in_page(page):
    """在主页面中查找答题元素"""
    await log("[自适应] 在主页面搜索题目...")
    return await _handle_adaptive_questions(page)


async def _try_find_questions_in_iframe(page):
    """在 PPT iframe 中查找答题元素"""
    await log("[自适应] 切换到 iframe.pptIframe 查找...")
    pptx_frame = page.frame_locator("iframe.pptIframe")
    try:
        await pptx_frame.first.locator("body").wait_for(state="attached", timeout=10000)
    except Exception:
        await log("[自适应] iframe 未加载")
        return False

    # 在 iframe 中搜索题目
    found_questions = await pptx_frame.first.evaluate("""
        () => {
            const radios = document.querySelectorAll('.el-radio');
            const checks = document.querySelectorAll('.el-checkbox');
            const questions = document.querySelectorAll('[class*="question"], [class*="topic"], [class*="title"]');
            return {
                radioCount: radios.length,
                checkCount: checks.length,
                questionCount: questions.length,
                hasNextBtn: !!document.querySelector('button:has-text("下一题"), button:has-text("交卷")'),
            };
        }
    """)
    await log(f"[自适应] iframe 内: 单选={found_questions['radioCount']}, 多选={found_questions['checkCount']}, 题目元素={found_questions['questionCount']}")

    if found_questions["radioCount"] == 0 and found_questions["checkCount"] == 0:
        await log("[自适应] iframe 内未找到选择题，等待后重试...")
        await asyncio.sleep(5)

    # 在 iframe 中循环答题
    max_rounds = 100
    for r in range(max_rounds):
        await asyncio.sleep(2)

        # 检测 iframe 中的选项和按钮
        info = await pptx_frame.first.evaluate("""
            () => {
                const radios = document.querySelectorAll('.el-radio');
                const checks = document.querySelectorAll('.el-checkbox');
                const options = radios.length > 0 ? radios : checks;

                // 获取选项文本
                const optTexts = Array.from(options).slice(0, 10).map(o => (o.innerText || '').trim());

                // 查找题目文本
                let question = '';
                const qEl = document.querySelector('[class*="question"], .el-form-item__label, .subject, .topic');
                if (qEl) question = qEl.innerText.trim();

                // 查找按钮——支持 button 和 div
                const btns = document.querySelectorAll('button, div.CloseBtn, div.text');
                let nextBtn = null;
                let submitBtn = null;
                let doneBtn = null;
                btns.forEach(b => {
                    const t = b.innerText.trim();
                    if (t.includes('选完了')) doneBtn = t;
                    if (t.includes('下一题')) nextBtn = t;
                    if (t.includes('交卷')) submitBtn = t;
                });

                return {
                    optCount: options.length,
                    optTexts: optTexts,
                    question: question.substring(0, 200),
                    hasNext: !!nextBtn,
                    nextText: nextBtn,
                    hasSubmit: !!submitBtn,
                    submitText: submitBtn,
                    hasDone: !!doneBtn,
                    doneText: doneBtn,
                };
            }
        """)

        if info["optCount"] == 0 and not info["hasNext"] and not info["hasSubmit"]:
            await log(f"[自适应] iframe 内无选项和按钮 (第{r+1}次), 退出")
            if r > 3:
                break
            continue

        await log(f"[自适应] iframe 第{r+1}轮: 选项={info['optCount']}, 下一题={info['nextText']}, 交卷={info['submitText']}")
        if info["question"]:
            await log(f"[自适应] 题目: {info['question'][:80]}")

        # 有选项 → 答题
        if info["optCount"] > 0:
            answer = await ai_ask(info["question"], info["optTexts"])
            selected = False
            if answer:
                for oi, ot in enumerate(info["optTexts"]):
                    if answer.strip() in ot or ot in answer.strip():
                        await log(f"[自适应] 选择选项 {oi+1}: {ot[:50]}")
                        await pptx_frame.first.locator(".el-radio, .el-checkbox").nth(oi).click()
                        selected = True
                        break
            if not selected:
                idx = random.randint(0, info["optCount"] - 1)
                await log(f"[自适应] 随机选 {idx+1}: {info['optTexts'][idx][:50]}")
                await pptx_frame.first.locator(".el-radio, .el-checkbox").nth(idx).click()
            STATS["adaptive_answered"] += 1
            await asyncio.sleep(1)

        # 点击按钮——优先选完了 > 交卷 > 下一题
        if info["hasDone"]:
            await log(f"[自适应] 点击选完了: [{info['doneText']}]")
            btn = pptx_frame.first.locator("button").filter(has_text="选完了")
            await btn.click()
            await asyncio.sleep(2)
        elif info["hasSubmit"]:
            await log(f"[自适应] 点击交卷: [{info['submitText']}]")
            btn = pptx_frame.first.locator("div.CloseBtn, div:has-text('交卷'), button:has-text('交卷')").first
            await btn.click()
            await asyncio.sleep(2)
            # 确认交卷弹窗
            confirm = await retry_find(page, [
                ".el-message-box__btns .el-button--primary",
                ".el-button--primary",
                "button:has-text('确定')",
                "button:has-text('确认')",
            ])
            if confirm:
                await confirm.click()
                await log("[自适应] 确认交卷")
            await asyncio.sleep(3)
            break
        elif info["hasNext"]:
            await log(f"[自适应] 点击下一题: [{info['nextText']}]")
            btn = pptx_frame.first.locator("button").filter(has_text="下一题")
            await btn.click()
            await asyncio.sleep(2)
        else:
            await log("[自适应] 无按钮，退出循环")
            break

    return True


async def _handle_adaptive_questions(page, dialog_sel=None):
    """在页面或对话框中答题"""
    max_questions = 100
    for q_idx in range(max_questions):
        await log(f"\n[自适应] --- 第 {q_idx+1} 题 ---")

        # 等待题目加载
        await asyncio.sleep(2)

        # 查找题目文本
        question = ""
        question_selectors = [
            ".question-title",
            ".question-content",
            ".el-form-item__label",
            "[class*='question']",
            ".subject",
            ".topic",
            ".title",
        ]
        if dialog_sel:
            question_selectors = [f"{dialog_sel} {s}" for s in question_selectors] + question_selectors

        for qs in question_selectors:
            try:
                qel = page.locator(qs).first
                if await qel.count() > 0:
                    question = await qel.inner_text()
                    if question.strip():
                        break
            except Exception:
                continue

        await log(f"[自适应] 题目: {question.strip()[:100] if question else '（未找到题目文本）'}")

        # 查找选项
        options = []
        option_selectors = [
            ".el-radio",
            ".el-checkbox",
            ".option-item",
            ".choice-item",
            "[class*='option']",
            ".select-item",
        ]
        if dialog_sel:
            option_selectors = [f"{dialog_sel} {s}" for s in option_selectors] + option_selectors

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
            await log("[自适应] 未找到选项，可能已完成或加载中")
            # 检查是否有提交/下一题按钮
            sub_btn = await retry_find(page, [
                "button:has-text('选完了')",
                "button:has-text('下一题')",
                "button:has-text('交卷')",
                "div.CloseBtn",
                "div:has-text('交卷')",
                "button:has-text('提交')",
                "button:has-text('确定')",
                ".next-btn",
                ".submit-btn",
            ])
            if sub_btn:
                text = await sub_btn.inner_text()
                await log(f"[自适应] 点击按钮: [{text}]")
                await sub_btn.click()
                await asyncio.sleep(1)
                if "交卷" in text or "提交" in text:
                    # 处理确认弹窗
                    await asyncio.sleep(1)
                    confirm_btn = await retry_find(page, [
                        ".el-message-box__btns .el-button--primary",
                        ".el-button--primary",
                        "button:has-text('确定')",
                        "button:has-text('确认')",
                        "button:has-text('是')",
                    ])
                    if confirm_btn:
                        await confirm_btn.click()
                        await log("[自适应] 确认交卷")
                    await asyncio.sleep(3)
                continue
            else:
                await log("[自适应] 无更多题目，退出")
                break

        # 收集选项文本
        opt_count = await opts.count()
        option_texts = []
        for oi in range(opt_count):
            try:
                ot = await opts.nth(oi).inner_text()
                option_texts.append(ot.strip())
            except Exception:
                option_texts.append(f"选项{oi+1}")

        await log(f"[自适应] 共 {opt_count} 个选项")

        # 调用 AI 获取答案
        answer = await ai_ask(question.strip() if question else "", option_texts)

        # 选择答案
        selected = False
        if answer:
            # 尝试按文本匹配
            for oi in range(opt_count):
                try:
                    ot = await opts.nth(oi).inner_text()
                    if answer.strip() in ot.strip() or ot.strip() in answer.strip():
                        await log(f"[自适应] 选择选项 {oi+1}: {ot.strip()[:50]}")
                        await opts.nth(oi).click()
                        selected = True
                        break
                except Exception:
                    continue

        if not selected:
            # 随机选择一个（不是第一个）
            idx = random.randint(0, opt_count - 1)
            try:
                ot = await opts.nth(idx).inner_text()
                await log(f"[自适应] 随机选择选项 {idx+1}: {ot.strip()[:50]}")
                await opts.nth(idx).click()
            except Exception:
                pass

        await asyncio.sleep(1)
        STATS["adaptive_answered"] += 1

        # 查找下一题/提交按钮
        next_btn = await retry_find(page, [
            "button:has-text('选完了')",
            "button:has-text('下一题')",
            "button:has-text('交卷')",
            "div.CloseBtn",
            "div:has-text('交卷')",
            "button:has-text('提交')",
            "button:has-text('确定')",
            ".next-btn",
        ])
        if next_btn:
            btn_text = await next_btn.inner_text()
            await log(f"[自适应] 点击按钮: [{btn_text}]")
            await next_btn.click()
            await asyncio.sleep(1)

            # 如果是交卷，确认弹窗
            if "交卷" in btn_text or "提交" in btn_text:
                await asyncio.sleep(1.5)
                confirm = await retry_find(page, [
                    ".el-message-box__btns .el-button--primary",
                    ".el-button--primary",
                    "button:has-text('确定')",
                    "button:has-text('确认')",
                    "button:has-text('是')",
                ])
                if confirm:
                    await confirm.click()
                    await log("[自适应] 确认交卷")
                await asyncio.sleep(3)
                # 检查是否有"关闭"/"知道了"按钮
                close_btn = await retry_find(page, [
                    "button:has-text('关闭')",
                    "button:has-text('知道了')",
                    "button:has-text('确定')",
                ])
                if close_btn:
                    await close_btn.click()
                    await asyncio.sleep(1)
                break
        else:
            await log("[自适应] 无下一题按钮，退出")
            break

    await log(f"[自适应] 答题完成，共回答 {STATS['adaptive_answered']} 题")


# ============================================================
# 内容页面主处理逻辑
# ============================================================

async def process_chapter_content(page):
    """处理章节内容页 - 遍历资源列表，按类型处理"""
    await log("\n--- 处理章节内容 ---")

    # 等待内容加载
    await asyncio.sleep(5)

    # 检查是否弹出了新窗口
    if len(page.context.pages) > 1:
        await log("检测到新标签页，切换到新标签页")
        np = page.context.pages[-1]
        await np.wait_for_load_state("networkidle")
        await asyncio.sleep(3)
        await process_chapter_content(np)
        await np.close()
        return

    # 扫描资源列表
    resources = await scan_resources(page)
    if not resources:
        await log("未找到资源列表，可能页面尚未加载或已进入资源内部")
        await asyncio.sleep(5)
        return

    # 按顺序处理每个未完成的资源
    for res in resources:
        if res["isFinish"]:
            await log(f"  ✓ [{res['type']}] {res['name']} 已完成，跳过")
            STATS["skipped_completed"] = STATS.get("skipped_completed", 0) + 1
            continue

        await log(f"\n  --- 资源: [{res['type']}] {res['name']} ---")

        # 点击该资源
        res_loc = page.locator(res["sel"])
        if not await safe_click(res_loc):
            await log(f"  [!] 无法点击资源 {res['name']}")
            continue
        await asyncio.sleep(3)

        # 根据类型处理
        res_type = res["type"]
        try:
            if "PPT" in res_type:
                await process_pptx(page)
            elif "HTML" in res_type or "PDF" in res_type or "文档" in res_type:
                await process_html_pdf(page, res["idx"])
            elif "视频" in res_type or "video" in res_type.lower():
                await process_video(page)
            elif "自适应" in res_type or "练习" in res_type or "训练" in res_type:
                # 自适应训练可能需要先点击进入
                # 查找"开始学习"/"进入"按钮
                start_btn = await retry_find(page, [
                    "button:has-text('开始学习')",
                    "button:has-text('进入')",
                    "button:has-text('开始')",
                    "button:has-text('答题')",
                    ".start-btn",
                ])
                if start_btn:
                    await start_btn.click()
                    await asyncio.sleep(2)
                await process_adaptive(page)
            else:
                await log(f"  [?] 未知资源类型: {res_type}，尝试通用处理")
                # 通用处理：等待60秒
                await asyncio.sleep(60)
        except Exception as e:
            await log(f"  [!] 处理 {res_type} 时出错: {e}")
            STATS["errors"] += 1

        # 等待资源标记为已完成
        await log(f"  等待资源标记完成...")
        finished = await wait_resource_finish(page, res["idx"], timeout=120)
        if finished:
            await log(f"  ✓ 资源已完成: {res['name']}")
        else:
            await log(f"  △ 资源可能未标记完成，继续下一步")

        STATS["processed_resources"] += 1

    # 返回课程页面（由主循环负责下一章的点击）
    await log("\n资源处理完成，返回课程首页...")
    back_btn = await retry_find(page, [
        ".return-icon",
        "text=返回",
        "button:has-text('返回')",
    ])
    if back_btn:
        await back_btn.click()
    else:
        await page.goto(CONFIG["course_url"], wait_until="networkidle", timeout=30000)
    await asyncio.sleep(5)


# ============================================================
# 章节处理
# ============================================================

async def process_leaf_chapter(page, chapter):
    """点击并处理一个叶子章节"""
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

        # 处理内容页
        await process_chapter_content(page)

        STATS["processed_chapters"] += 1
        await log(f"✓ 章节处理完成: {chapter['name']}")
        return True
    except PlaywrightTimeout as e:
        await log(f"✗ 超时: {chapter['name']} - {e}")
        STATS["errors"] += 1
        return False
    except Exception as e:
        await log(f"✗ 错误: {chapter['name']} - {e}")
        import traceback
        traceback.print_exc()
        STATS["errors"] += 1
        return False


# ============================================================
# 主函数
# ============================================================

async def main():
    await log("=" * 60)
    await log("FIF 自动刷课脚本 v2.0 启动")
    await log("=" * 60)
    await log(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    async with async_playwright() as p:
        await log("\n启动浏览器...")
        browser = await p.chromium.launch(
            headless=CONFIG["headless"],
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

        try:
            login_ok = await login(page)
            if not login_ok:
                await log("登录失败")
                await asyncio.sleep(10)
                return

            await navigate_to_course(page)
            chapters = await scan_chapters(page)

            if not chapters:
                await log("\n没有未完成的章节！")
                await asyncio.sleep(5)
                return

            await log(f"\n=== 步骤4: 开始处理 {len(chapters)} 个章节 ===")
            for i, ch in enumerate(chapters[:CONFIG["max_chapters"]]):
                await log(f"\n--- 进度: {i+1}/{min(len(chapters), CONFIG['max_chapters'])} ---")
                await process_leaf_chapter(page, ch)
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
            await log(f"\n主流程出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await log("\n浏览器将在 30 秒后关闭...")
            await asyncio.sleep(30)
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
