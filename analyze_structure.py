"""
FIF平台章节内部资源页面结构分析脚本
分析内容：资源列表、资源切换导航、PPTX/HTML/PDF/视频/自适应训练页面结构
"""

import asyncio
import json
import os
from datetime import datetime

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# 配置
CONFIG = {
    "login_url": "https://www.fifedu.com/iplat/fifLogin/index.html?v=5.4.4",
    "course_url": (
        "https://icourse.fifedu.com/istp-learning-center/"
        "index?courseId=0bbe8331f3ae41d4ade3618c31e5c0d9"
        "&classId=2811000226001709298&termId=0ebfcb74812d4e5ab9f8f1919a341d97"
    ),
    "username": "gduf231543223",
    "password": "gduf231543223",
    "headless": False,
    "timeout": 30000,
}

# 截图保存目录
SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analysis_screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

result = {
    "resource_list": {},
    "resource_nav": {},
    "pptx": {},
    "html_pdf": {},
    "video": {},
    "quiz": {},
}


async def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


async def save_screenshot(page, name: str):
    """保存截图到 analysis_screenshots 目录"""
    path = os.path.join(SCREENSHOTS_DIR, name)
    await page.screenshot(path=path, full_page=True)
    await log(f"  截图已保存: {name}")


async def analyze_page_html(page, label: str, selector: str = None) -> str:
    """获取页面/指定区域的HTML进行分析"""
    if selector:
        html = await page.evaluate(f"""
            () => {{
                const el = document.querySelector('{selector}');
                return el ? el.outerHTML.substring(0, 5000) : 'NOT_FOUND';
            }}
        """)
    else:
        html = await page.evaluate("document.body.innerHTML.substring(0, 10000)")
    return html


async def login(page) -> bool:
    """登录FIF平台"""
    await log("=== 登录 ===")
    await page.goto(CONFIG["login_url"], wait_until="networkidle", timeout=60000)
    await asyncio.sleep(3)
    await save_screenshot(page, "01_login_page.png")

    # 填写账号
    username_input = page.locator('input[name="user"]')
    await username_input.wait_for(state="visible", timeout=10000)
    await username_input.click()
    await username_input.fill("")
    await username_input.type(CONFIG["username"], delay=20)

    # 填写密码
    password_input = page.locator("#passWord")
    await password_input.wait_for(state="visible", timeout=10000)
    await password_input.click()
    await password_input.fill("")
    await password_input.type(CONFIG["password"], delay=20)

    await asyncio.sleep(1)
    await save_screenshot(page, "02_login_filled.png")

    # 点击登录
    login_btn = page.locator("button.cursor_p").get_by_text("登录", exact=True)
    await login_btn.wait_for(state="visible", timeout=10000)
    await login_btn.click()

    await log("等待登录完成...")
    try:
        await page.wait_for_url(
            lambda url: "fifedu.com" in url and "login" not in url.lower(),
            timeout=15000,
        )
        await log("登录成功!")
    except PlaywrightTimeout:
        current_url = page.url
        if "login" in current_url.lower():
            await log("登录未成功，请检查")
            return False
        await log(f"登录成功 (当前URL: {current_url})")

    await asyncio.sleep(3)
    await save_screenshot(page, "03_after_login.png")
    return True


async def navigate_to_course(page):
    """导航到课程页面"""
    await log("\n=== 访问课程页面 ===")
    await page.goto(CONFIG["course_url"], wait_until="networkidle", timeout=60000)
    await log("课程页面加载完成，等待动态内容渲染...")
    await asyncio.sleep(8)
    await save_screenshot(page, "04_course_page.png")
    return True


async def expand_all_chapters(page):
    """展开所有可展开的章节节点"""
    await log("展开所有章节节点...")
    for attempt in range(5):
        collapsed_arrows = await page.evaluate("""
            () => {
                const arrows = document.querySelectorAll('.left-arrow:not(.is-open):not(.dian)');
                return arrows.length;
            }
        """)
        if collapsed_arrows == 0:
            await log("所有章节已展开")
            break

        await log(f"还有 {collapsed_arrows} 个折叠箭头，尝试展开...")
        arrows = page.locator('.left-arrow:not(.is-open):not(.dian)')
        count = await arrows.count()
        for i in range(min(count, 20)):
            try:
                await arrows.nth(i).click()
                await asyncio.sleep(0.3)
            except Exception:
                pass
        await asyncio.sleep(1.5)
    else:
        await log("仍有未展开的节点")


async def analyze_course_chapters(page):
    """分析课程章节结构"""
    await log("\n=== 分析课程章节结构 ===")

    await expand_all_chapters(page)

    # 获取完整章节树HTML
    tree_html = await page.evaluate("""
        () => {
            const container = document.querySelector('.index-tree-body, .chapter-list, .tree-container, [class*=tree]');
            return container ? container.outerHTML.substring(0, 10000) : document.body.innerHTML.substring(0, 10000);
        }
    """)
    await log(f"章节树HTML（前5000字符）:")
    await log(tree_html[:5000])

    # 获取所有章节节点详细信息
    chapters_detail = await page.evaluate("""
        () => {
            const nodes = document.querySelectorAll('.index-tree-node');
            const results = [];
            
            nodes.forEach((node, index) => {
                const nameEl = node.querySelector('.tree-node-name');
                if (!nameEl) return;
                
                const name = nameEl.innerText.trim();
                const classList = nameEl.className;
                const isLevel1 = classList.includes('level_1');
                const noChild = classList.includes('no-child');
                
                // 完成状态标记
                const hasFinished = node.querySelector('.icon-isfinished') !== null;
                const hasUnfinish = node.querySelector('.icon-unfinish') !== null;
                const hasProgress = node.querySelector('.study-progress-wrapper') !== null;
                const isCurrent = node.querySelector('.current-study-icon') !== null;
                
                const style = window.getComputedStyle(nameEl);
                const paddingLeft = parseInt(style.paddingLeft) || 0;
                const level = Math.round(paddingLeft / 20) + 1;
                
                // 子节点数量
                const childCount = node.querySelectorAll('.index-tree-node').length;
                let hasChild = false;
                try { hasChild = node.querySelector(':scope > .index-tree-children, :scope > .children') !== null; } catch(e) {}
                const isLeaf = !hasChild || noChild;
                
                results.push({
                    index,
                    name,
                    level,
                    isLevel1,
                    isLeaf,
                    noChild,
                    isCompleted: hasFinished,
                    isUnfinished: hasUnfinish,
                    hasProgress,
                    isCurrent,
                    classList
                });
            });
            return results;
        }
    """)

    await log(f"\n共找到 {len(chapters_detail)} 个章节节点:")
    for ch in chapters_detail:
        status = "✓完成" if ch["isCompleted"] else ("★当前" if ch["isCurrent"] else ("◐进度" if ch["hasProgress"] else "○未开始"))
        await log(f"  L{ch['level']} [{status}] {ch['name']}  (leaf={ch['isLeaf']})")

    # 查找一个未完成的叶子节点（最好是level 2或3，有多个资源活动的）
    target = None
    for ch in chapters_detail:
        if not ch["isCompleted"] and ch["isLeaf"] and not ch["isLevel1"]:
            target = ch
            break

    if target:
        await log(f"\n选取目标章节: L{target['level']} {target['name']} (index={target['index']})")
    else:
        await log("未找到未完成的叶子节点!")
        # 选取第一个叶子节点
        for ch in chapters_detail:
            if ch["isLeaf"] and not ch["isLevel1"]:
                target = ch
                break

    return target, chapters_detail


async def click_chapter(page, chapter):
    """点击章节进入内容页"""
    await log(f"\n=== 点击章节: {chapter['name']} ===")

    # 给所有节点添加 data-chapter-index 属性，方便定位
    await page.evaluate("""
        () => {
            document.querySelectorAll('.index-tree-node').forEach((node, i) => {
                node.setAttribute('data-chapter-index', String(i));
            });
        }
    """)

    selector = f'.index-tree-node[data-chapter-index="{chapter["index"]}"] .tree-node-name'
    node = page.locator(selector)

    try:
        await node.scroll_into_view_if_needed()
        await asyncio.sleep(0.5)
        await node.click()
        await log("章节已点击，等待内容加载...")
        await asyncio.sleep(5)
        return True
    except Exception as e:
        await log(f"点击失败: {e}")
        # 尝试使用JavaScript点击
        await page.evaluate(f"""
            () => {{
                const node = document.querySelector('.index-tree-node[data-chapter-index="{chapter["index"]}"] .tree-node-name');
                if (node) node.click();
            }}
        """)
        await asyncio.sleep(5)
        return True


async def analyze_content_page(page):
    """分析内容页结构 - 核心分析函数"""
    await log("\n" + "="*70)
    await log("=== 内容页结构分析 ===")
    await log("="*70)

    # 保存完整截图
    await save_screenshot(page, "10_content_page_full.png")

    # 获取当前URL
    current_url = page.url
    await log(f"内容页URL: {current_url}")

    # 检查是否有iframe
    frames_count = len(page.frames)
    await log(f"页面frame数量: {frames_count}")

    # === A. 分析"本节资源"列表结构 ===
    await log("\n--- A. 分析资源列表结构 ---")
    try:
        await analyze_resource_list(page)
    except Exception as e:
        await log(f"  资源列表分析出错: {e}")

    # === B. 分析资源切换导航 ===
    await log("\n--- B. 分析资源切换导航 ---")
    try:
        await analyze_resource_nav(page)
    except Exception as e:
        await log(f"  资源导航分析出错: {e}")

    # === C. 分析PPTX页面结构 ===
    await log("\n--- C. 分析PPTX页面结构 ---")
    try:
        await analyze_pptx(page)
    except Exception as e:
        await log(f"  PPTX分析出错: {e}")

    # === D. 分析HTML/PDF页面结构 ===
    await log("\n--- D. 分析HTML/PDF页面结构 ---")
    try:
        await analyze_html_pdf(page)
    except Exception as e:
        await log(f"  HTML/PDF分析出错: {e}")

    # === E. 分析视频播放器结构 ===
    await log("\n--- E. 分析视频播放器结构 ---")
    try:
        await analyze_video(page)
    except Exception as e:
        await log(f"  视频分析出错: {e}")

    # === F. 分析自适应训练结构 ===
    await log("\n--- F. 分析自适应训练结构 ---")
    try:
        await analyze_quiz(page)
    except Exception as e:
        await log(f"  自适应训练分析出错: {e}")

    # 获取完整页面HTML用于分析
    await log("\n--- 获取完整页面HTML结构 ---")
    full_html = await page.evaluate("document.documentElement.outerHTML")
    # 保存到文件
    html_path = os.path.join(SCREENSHOTS_DIR, "content_page.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    await log(f"完整HTML已保存到: {html_path}")


async def analyze_resource_list(page):
    """A. 分析资源列表结构"""
    await log("查找资源列表容器...")

    # 尝试各种可能的资源列表选择器
    resource_selectors = [
        ".resource-list",
        ".material-list",
        ".content-list",
        "[class*=resource]",
        "[class*=material]",
        "[class*=content-list]",
        ".section-resource",
        ".lesson-resource",
        ".study-resource",
        "#resourceList",
        ".resourceContainer",
        ".list-container",
    ]

    for sel in resource_selectors:
        count = await page.evaluate(f"""sel => {{
            try {{
                const els = document.querySelectorAll(sel);
                return els.length;
            }} catch(e) {{ return -1; }}
        }}""", sel)
        if count and count > 0:
            await log(f"  找到选择器 '{sel}': {count} 个元素")

            # 获取第一个元素的详细信息
            info = await page.evaluate(f"""sel => {{
                const el = document.querySelector(sel);
                if (!el) return 'N/A';
                return {{
                    tagName: el.tagName,
                    id: el.id,
                    className: el.className.substring(0, 200),
                    childCount: el.children.length,
                    innerText: el.innerText.substring(0, 500),
                    html: el.outerHTML.substring(0, 2000)
                }};
            }}""", sel)
            if isinstance(info, dict):
                await log(f"    标签: {info['tagName']}, id: {info['id']}")
                await log(f"    类名: {info['className']}")
                await log(f"    子元素数: {info['childCount']}")
                await log(f"    文本内容: {info['innerText'][:300]}")
                result["resource_list"][sel] = info

    # 如果以上都没找到，尝试查找所有可能的资源项
    await log("\n尝试查找资源项...")
    item_info = await page.evaluate("""
        () => {
            const candidates = document.querySelectorAll('[class*="item"], [class*="card"], [class*="resource"], li, .list-item');
            const items = [];
            candidates.forEach(el => {
                const text = (el.innerText || '').trim();
                if (text && text.length < 200) {
                    items.push({
                        tag: el.tagName,
                        class: (el.className || '').substring(0, 100),
                        text: text.substring(0, 100),
                        hasIcon: el.querySelector('img, [class*=icon], i') !== null,
                    });
                }
            });
            return items.slice(0, 30);
        }
    """)
    await log(f"  找到 {len(item_info)} 个可能的资源项:")
    for it in item_info:
        await log(f"    <{it['tag']}> class={it['class']} icon={it['hasIcon']} text={it['text']}")

    # 获取页面中所有带"资源"或"PPT"或"视频"等字样的元素
    await log("\n查找资源类型标记...")
    type_info = await page.evaluate("""
        () => {
            const allElements = document.querySelectorAll('*');
            const results = [];
            const keywords = ['PPT', 'pptx', 'PDF', 'html', '视频', 'video', '训练', '练习', '答题', '资源', 'material'];
            allElements.forEach(el => {
                const text = (el.innerText || '').trim();
                if (text && keywords.some(k => text.includes(k)) && text.length < 100) {
                    try {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            results.push({
                                tag: el.tagName,
                                class: (el.className || '').substring(0, 80),
                                id: el.id || '',
                                text: text.substring(0, 80),
                                rect: Math.round(rect.width) + 'x' + Math.round(rect.height)
                            });
                        }
                    } catch(e) {}
                }
            });
            return results.slice(0, 50);
        }
    """)
    if type_info:
        await log(f"  找到 {len(type_info)} 个资源相关元素:")
        for t in type_info[:20]:
            await log(f"    <{t['tag']}#{t['id']}> [{t['rect']}] {t['text']}")

    # 截取资源列表区域
    await save_screenshot(page, "11_resource_list.png")


async def analyze_resource_nav(page):
    """B. 分析资源切换导航"""
    await log("查找资源切换导航...")

    nav_info = await page.evaluate("""
        () => {
            const results = {};
            
            // 查找"上一节资源"/"下一节资源"按钮
            const prevButtons = [];
            const nextButtons = [];
            
            const allBtns = document.querySelectorAll('button, a, [class*=btn], [class*=button], [class*=nav]');
            
            allBtns.forEach(btn => {
                const text = btn.innerText.trim();
                const cls = btn.className.substring(0, 80);
                if (text.includes('上一') || text.includes('prev') || text.includes('Prev') || text.includes('PREV')) {
                    prevButtons.push({tag: btn.tagName, class: cls, text: text.substring(0, 50)});
                }
                if (text.includes('下一') || text.includes('next') || text.includes('Next') || text.includes('NEXT')) {
                    nextButtons.push({tag: btn.tagName, class: cls, text: text.substring(0, 50)});
                }
            });
            
            results.prevButtons = prevButtons;
            results.nextButtons = nextButtons;
            
            // 查找进度指示器（如 "1/5" 或 "第1节"）
            const progressIndicators = [];
            allBtns.forEach(btn => {
                const text = btn.innerText.trim();
                if (/\\d+\\s*\\/\\s*\\d+/.test(text) || /第\\d+节/.test(text) || /资源\\s*\\d+/.test(text)) {
                    progressIndicators.push({tag: btn.tagName, class: cls, text: text.substring(0, 50)});
                }
            });
            results.progressIndicators = progressIndicators;
            
            // 查找序号/进度指示器
            const indicators = document.querySelectorAll('[class*=progress], [class*=step], [class*=index], [class*=page], [class*=count]');
            const indicatorInfo = [];
            indicators.forEach(el => {
                const text = el.innerText.trim();
                if (text && text.length < 50 && /\\d/.test(text)) {
                    indicatorInfo.push({
                        tag: el.tagName,
                        class: el.className.substring(0, 60),
                        text: text.substring(0, 50)
                    });
                }
            });
            results.indicators = indicatorInfo.slice(0, 20);
            
            return results;
        }
    """)
    
    await log("  上一节/下一节按钮:")
    for key in ['prevButtons', 'nextButtons']:
        for btn in nav_info.get(key, []):
            await log(f"    [{key}] <{btn['tag']}> class='{btn['class']}' text='{btn['text']}'")

    await log("  进度指示器:")
    for ind in nav_info.get('progressIndicators', []):
        await log(f"    <{ind['tag']}> class='{ind['class']}' text='{ind['text']}'")

    await log("  其他序号/进度元素:")
    for ind in nav_info.get('indicators', []):
        await log(f"    <{ind['tag']}> class='{ind['class']}' text='{ind['text']}'")

    result["resource_nav"] = nav_info


async def analyze_pptx(page):
    """C. 分析PPTX页面结构"""
    await log("检查PPTX页面结构...")
    
    # 检查是否有PPTX相关的元素
    pptx_indicators = [
        "slide", "ppt", "pptx", "presentation", "page", "翻页",
        "swiper", "carousel", "slider"
    ]
    
    pptx_info = await page.evaluate("""
        () => {
            const results = {};
            
            // 查找翻页按钮
            const pageBtns = [];
            document.querySelectorAll('button, [class*=btn], [class*=arrow], [class*=page]').forEach(el => {
                const text = el.innerText.trim();
                const cls = el.className.substring(0, 80);
                if (text.includes('上一页') || text.includes('下一页') || text.includes('<') || text.includes('>') || text.includes('‹') || text.includes('›') || text.includes('«') || text.includes('»')) {
                    pageBtns.push({tag: el.tagName, class: cls, text: text.substring(0, 30)});
                }
                // 左右箭头
                if (cls.includes('left') || cls.includes('right') || cls.includes('prev') || cls.includes('next') || cls.includes('previous') || cls.includes('forward')) {
                    if (text.length < 20) {
                        pageBtns.push({tag: el.tagName, class: cls, text: text.substring(0, 30)});
                    }
                }
            });
            results.pageButtons = pageBtns;
            
            // 查找页码显示
            const pageNumbers = [];
            document.querySelectorAll('[class*=page], [class*=slide], [class*=current], [class*=total]').forEach(el => {
                const text = el.innerText.trim();
                if (/^\\d+\\s*\\/\\s*\\d+$/.test(text) || /^\\d+$/.test(text)) {
                    pageNumbers.push({tag: el.tagName, class: cls, text: text.substring(0, 30)});
                }
            });
            results.pageNumbers = pageNumbers;
            
            // 检查是否有PPT容器
            const pptContainer = [];
            document.querySelectorAll('[class*=ppt], [class*=slide], [class*=swiper], [class*=carousel], iframe').forEach(el => {
                const cls = el.className.substring(0, 80);
                const src = el.src || '';
                pptContainer.push({
                    tag: el.tagName,
                    class: cls,
                    src: src.substring(0, 100),
                    rect: `${el.getBoundingClientRect().width}x${el.getBoundingClientRect().height}`
                });
            });
            results.pptContainers = pptContainer.slice(0, 10);
            
            // 检查iframe内容
            results.iframeCount = document.querySelectorAll('iframe').length;
            
            return results;
        }
    """)
    
    await log(f"  iframe数量: {pptx_info.get('iframeCount', 0)}")
    
    if pptx_info.get('pageButtons'):
        await log("  翻页按钮:")
        for btn in pptx_info['pageButtons']:
            await log(f"    <{btn['tag']}> class='{btn['class']}' text='{btn['text']}'")

    if pptx_info.get('pageNumbers'):
        await log("  页码显示:")
        for pn in pptx_info['pageNumbers']:
            await log(f"    <{pn['tag']}> class='{pn['class']}' text='{pn['text']}'")

    if pptx_info.get('pptContainers'):
        await log("  PPT/幻灯片容器:")
        for pc in pptx_info['pptContainers']:
            await log(f"    <{pc['tag']}> class='{pc['class']}' src='{pc['src']}' size={pc['rect']}")

    result["pptx"] = pptx_info


async def analyze_html_pdf(page):
    """D. 分析HTML/PDF页面结构"""
    await log("检查HTML/PDF页面结构...")
    
    pdf_html_info = await page.evaluate("""
        () => {
            const results = {};
            
            // 查找滚动容器
            const scrollContainers = [];
            document.querySelectorAll('[class*=scroll], [class*=content], [class*=body], main, article, [class*=reader], [class*=viewer]').forEach(el => {
                const rect = el.getBoundingClientRect();
                const isScrollable = el.scrollHeight > el.clientHeight + 5;
                if (isScrollable && rect.width > 200 && rect.height > 100) {
                    scrollContainers.push({
                        tag: el.tagName,
                        class: el.className.substring(0, 80),
                        id: el.id,
                        scrollHeight: el.scrollHeight,
                        clientHeight: el.clientHeight,
                        scrollTop: el.scrollTop,
                        size: `${Math.round(rect.width)}x${Math.round(rect.height)}`
                    });
                }
            });
            results.scrollContainers = scrollContainers.slice(0, 20);
            
            // 查找进度条
            const progressBars = [];
            document.querySelectorAll('[class*=progress], [class*=bar], [role=progressbar], [class*=scroll-indicator]').forEach(el => {
                const text = el.innerText.trim();
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    progressBars.push({
                        tag: el.tagName,
                        class: el.className.substring(0, 80),
                        text: text.substring(0, 50),
                        size: `${Math.round(rect.width)}x${Math.round(rect.height)}`
                    });
                }
            });
            results.progressBars = progressBars.slice(0, 10);
            
            // 查找PDF相关元素
            const pdfElements = [];
            document.querySelectorAll('[class*=pdf], embed[type*=pdf], object[type*=pdf], iframe[src*=pdf]').forEach(el => {
                pdfElements.push({
                    tag: el.tagName,
                    class: el.className.substring(0, 80),
                    src: el.src || el.data || ''
                });
            });
            results.pdfElements = pdfElements;
            
            // 检查是否有 iframe 内嵌 PDF/HTML 阅读器
            const iframes = document.querySelectorAll('iframe');
            const iframeInfo = [];
            iframes.forEach(iframe => {
                iframeInfo.push({
                    src: (iframe.src || '').substring(0, 150),
                    class: iframe.className.substring(0, 60),
                    id: iframe.id
                });
            });
            results.iframes = iframeInfo;
            
            return results;
        }
    """)
    
    await log(f"  滚动容器数量: {len(pdf_html_info.get('scrollContainers', []))}")
    for sc in pdf_html_info.get('scrollContainers', [])[:5]:
        await log(f"    <{sc['tag']}#{sc['id']}> class='{sc['class']}' scroll={sc['scrollHeight']}/{sc['clientHeight']}")
    
    await log(f"  进度条数量: {len(pdf_html_info.get('progressBars', []))}")
    for pb in pdf_html_info.get('progressBars', []):
        await log(f"    <{pb['tag']}> class='{pb['class']}' text='{pb['text']}'")

    if pdf_html_info.get('pdfElements'):
        await log("  PDF元素:")
        for pe in pdf_html_info['pdfElements']:
            await log(f"    <{pe['tag']}> class='{pe['class']}' src='{pe['src']}'")
    
    if pdf_html_info.get('iframes'):
        await log("  iframe列表:")
        for ifr in pdf_html_info['iframes']:
            await log(f"    <iframe> class='{ifr['class']}' src='{ifr['src']}'")

    result["html_pdf"] = pdf_html_info


async def analyze_video(page):
    """E. 分析视频播放器结构"""
    await log("检查视频播放器结构...")
    
    video_info = await page.evaluate("""
        () => {
            const results = {};
            
            // 查找video元素
            const videos = document.querySelectorAll('video');
            const videoData = [];
            videos.forEach((v, i) => {
                videoData.push({
                    index: i,
                    src: (v.src || '').substring(0, 150),
                    duration: v.duration || 0,
                    paused: v.paused,
                    currentTime: v.currentTime || 0,
                    width: v.videoWidth || 0,
                    height: v.videoHeight || 0,
                    controls: v.controls,
                    hasAttribute_controls: v.hasAttribute('controls'),
                    class: v.className.substring(0, 80),
                    id: v.id,
                    parentClass: (v.parentElement ? v.parentElement.className.substring(0, 80) : ''),
                    rect: `${Math.round(v.getBoundingClientRect().width)}x${Math.round(v.getBoundingClientRect().height)}`
                });
            });
            results.videos = videoData;
            
            // 查找播放器容器
            const playerContainers = [];
            document.querySelectorAll('[class*=player], [class*=video], [class*=media], [class*=live]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 100 && rect.height > 50) {
                    playerContainers.push({
                        tag: el.tagName,
                        class: el.className.substring(0, 100),
                        id: el.id,
                        size: `${Math.round(rect.width)}x${Math.round(rect.height)}`
                    });
                }
            });
            results.playerContainers = playerContainers.slice(0, 15);
            
            // 查找播放/暂停按钮
            const playButtons = [];
            document.querySelectorAll('button, [class*=btn], [class*=play], [class*=pause]').forEach(el => {
                const text = el.innerText.trim();
                const cls = el.className.substring(0, 80);
                if (cls.includes('play') || cls.includes('pause') || text.includes('播放') || text.includes('暂停')) {
                    playButtons.push({
                        tag: el.tagName,
                        class: cls,
                        text: text.substring(0, 30),
                        rect: `${Math.round(el.getBoundingClientRect().width)}x${Math.round(el.getBoundingClientRect().height)}`
                    });
                }
            });
            results.playButtons = playButtons;
            
            // 查找进度条
            const progressBars = [];
            document.querySelectorAll('[class*=progress], [class*=slider], [class*=timeline], [class*=seek]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 50) {
                    progressBars.push({
                        tag: el.tagName,
                        class: el.className.substring(0, 80),
                        size: `${Math.round(rect.width)}x${Math.round(rect.height)}`
                    });
                }
            });
            results.progressBars = progressBars;
            
            // 查找时间显示
            const timeDisplays = [];
            document.querySelectorAll('[class*=time], [class*=duration], [class*=current]').forEach(el => {
                const text = el.innerText.trim();
                if (/\\d+:\\d+/.test(text)) {
                    timeDisplays.push({
                        tag: el.tagName,
                        class: el.className.substring(0, 60),
                        text: text.substring(0, 30)
                    });
                }
            });
            results.timeDisplays = timeDisplays;
            
            return results;
        }
    """)
    
    await log(f"  video元素数量: {len(video_info.get('videos', []))}")
    for v in video_info.get('videos', []):
        await log(f"    video[{v['index']}]: src='{v['src']}' size={v['rect']} duration={v['duration']:.1f}s paused={v['paused']} controls={v['controls']}")
    
    if video_info.get('playerContainers'):
        await log("  播放器容器:")
        for pc in video_info['playerContainers'][:5]:
            await log(f"    <{pc['tag']}#{pc['id']}> class='{pc['class']}' size={pc['size']}")
    
    if video_info.get('playButtons'):
        await log("  播放/暂停按钮:")
        for pb in video_info['playButtons']:
            await log(f"    <{pb['tag']}> class='{pb['class']}' text='{pb['text']}'")

    if video_info.get('timeDisplays'):
        await log("  时间显示:")
        for td in video_info['timeDisplays']:
            await log(f"    <{td['tag']}> class='{td['class']}' text='{td['text']}'")

    result["video"] = video_info


async def analyze_quiz(page):
    """F. 分析自适应训练（题目）结构"""
    await log("检查自适应训练/题目结构...")
    
    quiz_info = await page.evaluate("""
        () => {
            const results = {};
            
            // 查找题目容器
            const questionContainers = [];
            document.querySelectorAll('[class*=question], [class*=quiz], [class*=exam], [class*=test], [class*=exercise], [class*=practice], [class*=topic], [class*=choice]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 100 && rect.height > 50) {
                    questionContainers.push({
                        tag: el.tagName,
                        class: el.className.substring(0, 100),
                        id: el.id,
                        text: el.innerText.trim().substring(0, 100),
                        size: `${Math.round(rect.width)}x${Math.round(rect.height)}`
                    });
                }
            });
            results.questionContainers = questionContainers.slice(0, 15);
            
            // 查找题目文本
            const questionTexts = [];
            document.querySelectorAll('h1, h2, h3, h4, h5, p, [class*=title], [class*=ques], [class*=stem]').forEach(el => {
                const text = el.innerText.trim();
                if (text && text.length > 5 && text.length < 300 && /[？?]/.test(text)) {
                    questionTexts.push({
                        tag: el.tagName,
                        class: el.className.substring(0, 60),
                        text: text.substring(0, 100)
                    });
                }
            });
            results.questionTexts = questionTexts.slice(0, 10);
            
            // 查找选项
            const options = [];
            document.querySelectorAll('[class*=option], [class*=choice], [class*=answer], label, [class*=radio], [class*=checkbox]').forEach(el => {
                const text = el.innerText.trim();
                if (text && text.length < 200 && /^[A-Z]\\./.test(text)) {
                    options.push({
                        tag: el.tagName,
                        class: el.className.substring(0, 60),
                        text: text.substring(0, 80)
                    });
                }
            });
            results.options = options.slice(0, 20);
            
            // 如果没有找到字母选项，尝试找所有可能的选项
            if (options.length === 0) {
                document.querySelectorAll('[class*=option], [class*=choice], [class*=select]').forEach(el => {
                    const text = el.innerText.trim();
                    if (text && text.length < 150) {
                        options.push({
                            tag: el.tagName,
                            class: el.className.substring(0, 60),
                            text: text.substring(0, 80)
                        });
                    }
                });
                results.optionsAll = options.slice(0, 20);
            }
            
            // 查找提交/下一题按钮
            const submitButtons = [];
            document.querySelectorAll('button, [class*=btn], [class*=button]').forEach(el => {
                const text = el.innerText.trim();
                if (text.includes('提交') || text.includes('下一题') || text.includes('交卷') || text.includes('确定') || text.includes('完成')) {
                    submitButtons.push({
                        tag: el.tagName,
                        class: el.className.substring(0, 80),
                        text: text.substring(0, 30),
                        rect: `${Math.round(el.getBoundingClientRect().width)}x${Math.round(el.getBoundingClientRect().height)}`
                    });
                }
            });
            results.submitButtons = submitButtons;
            
            return results;
        }
    """)
    
    await log(f"  题目容器数量: {len(quiz_info.get('questionContainers', []))}")
    for qc in quiz_info.get('questionContainers', [])[:5]:
        await log(f"    <{qc['tag']}#{qc['id']}> class='{qc['class']}' text='{qc['text'][:60]}'")
    
    if quiz_info.get('questionTexts'):
        await log("  题目文本:")
        for qt in quiz_info['questionTexts']:
            await log(f"    <{qt['tag']}> class='{qt['class']}' text='{qt['text']}'")
    
    await log(f"  选项数量: {len(quiz_info.get('options', []))}")
    for opt in quiz_info.get('options', [])[:10]:
        await log(f"    <{opt['tag']}> class='{opt['class']}' text='{opt['text']}'")
    
    if quiz_info.get('submitButtons'):
        await log("  提交/操作按钮:")
        for sb in quiz_info['submitButtons']:
            await log(f"    <{sb['tag']}> class='{sb['class']}' text='{sb['text']}'")
    
    result["quiz"] = quiz_info


async def analyze_iframes(page):
    """分析页面中的iframe内容"""
    await log("\n=== 分析iframe内容 ===")
    
    iframe_count = len(page.frames)
    await log(f"共有 {iframe_count} 个frame（含主页面）")
    
    for i, frame in enumerate(page.frames):
        try:
            url = frame.url
            await log(f"  frame[{i}]: {url[:150]}")
            
            # 尝试获取iframe中的可见文本
            try:
                text = await frame.evaluate("document.body?.innerText?.substring(0, 300) || 'No body'")
                if text and text != 'No body':
                    await log(f"    内容: {text[:200]}")
            except Exception as e:
                await log(f"    无法访问内容: {e}")
        except Exception as e:
            await log(f"  frame[{i}]: 错误 - {e}")


async def analyze_page_event_listeners(page):
    """分析页面事件监听"""
    await log("\n=== 分析页面事件/JavaScript特征 ===")
    
    js_info = await page.evaluate("""
        () => {
            const results = {};
            
            // 检查全局变量/函数
            results.globalKeys = Object.keys(window).filter(k => 
                k.includes('player') || k.includes('video') || k.includes('slide') || 
                k.includes('ppt') || k.includes('scroll') || k.includes('learn') ||
                k.includes('finish') || k.includes('complete') || k.includes('progress')
            ).slice(0, 20);
            
            // 检查是否有 MutationObserver 或 IntersectionObserver
            results.hasMutationObserver = typeof MutationObserver !== 'undefined';
            results.hasIntersectionObserver = typeof IntersectionObserver !== 'undefined';
            
            // 检查是否有完成学习的API
            results.finishFunctions = Object.keys(window).filter(k => 
                k.includes('finish') || k.includes('complete') || k.includes('done') ||
                k.includes('submitStudy') || k.includes('reportProgress')
            );
            
            return results;
        }
    """)
    
    await log(f"  相关全局变量: {js_info.get('globalKeys', [])}")
    await log(f"  MutationObserver: {js_info.get('hasMutationObserver')}")
    await log(f"  IntersectionObserver: {js_info.get('hasIntersectionObserver')}")
    await log(f"  完成学习相关函数: {js_info.get('finishFunctions', [])}")


async def main():
    """主函数"""
    await log("=" * 70)
    await log("FIF平台章节内部资源页面结构分析")
    await log("=" * 70)
    await log(f"截图保存目录: {SCREENSHOTS_DIR}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
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
            # 1. 登录
            login_ok = await login(page)
            if not login_ok:
                await log("登录失败，退出")
                await asyncio.sleep(5)
                return

            # 2. 导航到课程页面
            await navigate_to_course(page)

            # 3. 分析章节结构并选择目标章节
            target_chapter, all_chapters = await analyze_course_chapters(page)

            if not target_chapter:
                await log("未找到合适的章节，退出")
                await asyncio.sleep(5)
                return

            # 4. 点击目标章节进入内容页
            await click_chapter(page, target_chapter)

            # 5. 检查是否有新标签页
            if len(context.pages) > 1:
                await log("检测到新标签页，切换到新标签页...")
                # 保存旧页面截图
                await save_screenshot(page, "05_content_page_original.png")
                new_page = context.pages[-1]
                await new_page.wait_for_load_state("networkidle")
                await asyncio.sleep(3)
                await save_screenshot(new_page, "06_new_tab_content.png")
                page = new_page

            # 6. 核心分析
            await analyze_content_page(page)

            # 7. 分析iframe
            await analyze_iframes(page)

            # 8. 分析JavaScript特征
            await analyze_page_event_listeners(page)

            # 9. 输出分析结果摘要
            await log("\n" + "=" * 70)
            await log("分析完成！结果摘要:")
            await log("=" * 70)
            await log(f"截图已保存到: {SCREENSHOTS_DIR}")
            
            # 保存完整分析结果到JSON
            result_path = os.path.join(SCREENSHOTS_DIR, "analysis_result.json")
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            await log(f"分析结果JSON已保存到: {result_path}")

        except Exception as e:
            await log(f"\n主流程出错: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await log("\n浏览器将在 30 秒后关闭...")
            await asyncio.sleep(30)
            await browser.close()
            await log("浏览器已关闭。")


if __name__ == "__main__":
    asyncio.run(main())
