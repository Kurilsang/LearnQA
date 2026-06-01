"""
FIF 自适应练习（自适应训练）页面结构分析脚本
使用 Playwright 自动化浏览器，分析自适应练习页面的完整结构
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# 确保脚本所在目录为工作目录
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(_SCRIPT_DIR)

# 从 .env 文件直接读取（避免 Windows USERNAME 环境变量冲突）
def _read_env(key, default=""):
    """直接从 .env 文件读取变量"""
    env_path = os.path.join(_SCRIPT_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() == key:
                    return v.strip().strip('"').strip("'")
    return default

USERNAME = _read_env("USERNAME", "")
PASSWORD = _read_env("PASSWORD", "")

# 同时尝试从 os.environ 读取（兼容 docker/linux 环境）
if not USERNAME:
    USERNAME = os.environ.get("USERNAME", "")
if not PASSWORD:
    PASSWORD = os.environ.get("PASSWORD", "")

# 截图输出目录
OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "adaptive_analysis")
os.makedirs(OUTPUT_DIR, exist_ok=True)

COURSE_URL = (
    "https://icourse.fifedu.com/istp-learning-center/"
    "index?courseId=0bbe8331f3ae41d4ade3618c31e5c0d9"
    "&classId=2811000226001709298&termId=0ebfcb74812d4e5ab9f8f1919a341d97"
)

LOGIN_URL = "https://www.fifedu.com/iplat/fifLogin/index.html?v=5.4.4"


def screenshot(page, name):
    """保存截图并返回路径"""
    path = os.path.join(OUTPUT_DIR, name)
    asyncio.create_task(page.screenshot(path=path, full_page=True))
    return path


async def safe_screenshot(page, name):
    """保存截图"""
    path = os.path.join(OUTPUT_DIR, name)
    await page.screenshot(path=path, full_page=True)
    print(f"    [截图] {path}")
    return path


async def log_element(page, selector, label=""):
    """查找并打印元素信息"""
    try:
        el = await page.query_selector(selector)
        if el:
            tag = await el.evaluate("el => el.tagName")
            text = await el.inner_text()
            html = await el.evaluate("el => el.outerHTML.substring(0, 300)")
            visible = await el.is_visible()
            print(f"  [{label}] <{tag}> visible={visible}")
            print(f"    text: {text[:100]}")
            print(f"    html: {html}")
            return el
        else:
            print(f"  [{label}] 未找到")
            return None
    except Exception as e:
        print(f"  [{label}] 错误: {e}")
        return None


async def main():
    print("=" * 80)
    print("FIF 自适应练习（自适应训练）页面结构分析")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"用户名: {USERNAME}")
    print("-" * 80)

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        # ---------- 启动浏览器 ----------
        print("\n[1/10] 启动浏览器...")
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

        # 监听新标签页和对话框
        new_pages = []
        dialogs = []

        async def on_page(pg):
            new_pages.append(pg)
            print(f"    [事件] 新页面打开: {pg.url}")

        async def on_dialog(dialog):
            dialogs.append(dialog)
            print(f"    [事件] 对话框: type={dialog.type} message='{dialog.message[:100]}'")

        context.on("page", on_page)
        page.on("dialog", on_dialog)

        # ---------- 步骤 1: 访问登录页 ----------
        print("\n[2/10] 访问登录页面...")
        await page.goto(LOGIN_URL, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)
        await safe_screenshot(page, "01_login_page.png")

        # 查找登录元素
        print("\n    --- 分析登录页结构 ---")
        login_html = await page.evaluate("() => document.body.innerHTML.substring(0, 3000)")
        print(f"    body HTML (前 3000 字符):\n{login_html}")

        # ---------- 步骤 2: 登录 ----------
        print("\n[3/10] 执行登录...")
        # 查找输入框 - 使用 analyze_login.py 中已知的策略
        username_input = None
        password_input = None
        login_button = None

        # 尝试各种选择器
        for sel in [
            'input[type="text"]',
            'input:not([type="hidden"]):not([type="password"])',
            'input[placeholder*="账号"]',
            'input[placeholder*="用户"]',
        ]:
            el = await page.query_selector(sel)
            if el:
                type_attr = await el.get_attribute("type")
                if type_attr in (None, "", "text"):
                    username_input = el
                    print(f"    账号输入框选择器: {sel}")
                    break

        for sel in [
            'input[type="password"]',
            'input[placeholder*="密码"]',
        ]:
            el = await page.query_selector(sel)
            if el:
                password_input = el
                print(f"    密码输入框选择器: {sel}")
                break

        for sel in [
            'button[type="submit"]',
            'button:has-text("登录")',
            '.login-btn',
            '.el-button--primary',
            'button:has-text("登 录")',
        ]:
            el = await page.query_selector(sel)
            if el:
                login_button = el
                print(f"    登录按钮选择器: {sel}")
                break

        if username_input and password_input:
            await username_input.fill("")
            await username_input.type(USERNAME, delay=50)
            print(f"    已输入账号: {USERNAME}")

            await password_input.fill("")
            await password_input.type(PASSWORD, delay=50)
            print("    已输入密码")

            await asyncio.sleep(1)

            if login_button:
                await login_button.click()
                print("    点击了登录按钮")
            else:
                await page.keyboard.press("Enter")
                print("    按 Enter 提交登录")
        else:
            print("    [!] 未找到输入框，使用 evaluate 直接填写")
            await page.evaluate(f"""
                () => {{
                    const inputs = document.querySelectorAll('input');
                    let textInp = null, pwdInp = null;
                    for (const inp of inputs) {{
                        if (inp.type === 'password') pwdInp = inp;
                        else if (!textInp && inp.type !== 'hidden') textInp = inp;
                    }}
                    if (textInp) {{
                        const setter = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value'
                        ).set;
                        setter.call(textInp, '{USERNAME}');
                        textInp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                    if (pwdInp) {{
                        const setter = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value'
                        ).set;
                        setter.call(pwdInp, '{PASSWORD}');
                        pwdInp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }}
            """)
            if login_button:
                await login_button.click()
            else:
                await page.keyboard.press("Enter")

        # ---------- 步骤 3: 等待登录成功 ----------
        print("\n[4/10] 等待登录成功 (10 秒)...")
        await asyncio.sleep(10)
        print(f"    当前 URL: {page.url}")
        await safe_screenshot(page, "02_after_login.png")

        # 检查是否有登录失败或需要额外验证
        page_text = await page.evaluate("() => document.body.innerText")
        if "验证" in page_text or "安全" in page_text:
            print("    [!] 可能需要验证码，等待更多时间...")
            await asyncio.sleep(15)
            await safe_screenshot(page, "02b_after_extra_wait.png")

        # ---------- 步骤 4: 访问课程页面 ----------
        print("\n[5/10] 访问课程页面...")
        await page.goto(COURSE_URL, wait_until="networkidle", timeout=60000)
        print("    课程页面加载完成，等待动态内容 (10 秒)...")
        await asyncio.sleep(10)

        print(f"    当前 URL: {page.url}")
        await safe_screenshot(page, "03_course_page.png")

        # ---------- 步骤 5: 分析课程页面结构 ----------
        print("\n[6/10] 分析课程页面结构...")

        # 查找章节树结构
        print("\n    --- 章节相关元素 ---")
        chapter_info = await page.evaluate("""
            () => {
                const results = [];
                // 查找所有包含章节相关内容的元素
                const keywords = ['chapter', 'section', 'lesson', 'chapter',
                                '章节', '节', '课', '单元', '目录', '大纲',
                                'sidebar', 'sider', 'tree', 'nav', 'menu',
                                'left-arrow', 'dian', 'activity'];
                const allEls = document.querySelectorAll('*');
                const seen = new Set();

                for (const el of allEls) {
                    const id = (el.id || '').toLowerCase();
                    const cls = typeof el.className === 'string' ? el.className.toLowerCase() : '';
                    const tag = el.tagName.toLowerCase();

                    if (['script', 'style', 'link', 'meta'].includes(tag)) continue;

                    let matched = false;
                    const reasons = [];
                    for (const kw of keywords) {
                        if (id.includes(kw)) { matched = true; reasons.push(`#id:"${kw}"`); }
                        if (cls.includes(kw)) { matched = true; reasons.push(`.class:"${kw}"`); }
                    }

                    if (matched && !seen.has(el)) {
                        seen.add(el);
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            results.push({
                                tag: tag,
                                id: (el.id || '').substring(0, 60),
                                className: (typeof el.className === 'string' ? el.className : '').substring(0, 80),
                                text: (el.innerText || '').trim().substring(0, 60),
                                match: reasons.join(', '),
                                rect: `${Math.round(rect.width)}x${Math.round(rect.height)}`
                            });
                        }
                    }
                }
                return results.slice(0, 60);
            }
        """)

        if chapter_info:
            print(f"    找到 {len(chapter_info)} 个相关元素:")
            for i, item in enumerate(chapter_info):
                print(f"    [{i+1}] <{item['tag']}> {item['match']}")
                print(f"          id='{item['id']}'")
                print(f"          class='{item['className']}'")
                print(f"          text='{item['text']}' size={item['rect']}")
        else:
            print("    未找到章节相关元素")

        # 查找所有 left-arrow 箭头（章节展开/折叠按钮）
        print("\n    --- left-arrow 箭头元素 ---")
        arrows = await page.query_selector_all('.left-arrow')
        print(f"    找到 {len(arrows)} 个 .left-arrow 元素")
        for i, arrow in enumerate(arrows):
            cls = await arrow.get_attribute("class")
            parent_text = await arrow.evaluate("""
                el => {
                    let p = el.parentElement;
                    return p ? (p.innerText || '').trim().substring(0, 50) : '';
                }
            """)
            print(f"    [{i+1}] class='{cls}' parent_text='{parent_text}'")

        # 查找所有活动列表项
        print("\n    --- activity-list-item 元素 ---")
        activity_items = await page.query_selector_all('.activity-list-item')
        print(f"    找到 {len(activity_items)} 个 .activity-list-item")
        for i, item in enumerate(activity_items):
            text = await item.inner_text()
            cls = await item.get_attribute("class")
            html = await item.evaluate("el => el.outerHTML.substring(0, 400)")
            print(f"\n    [{i+1}] class='{cls}'")
            print(f"         text='{text[:100]}'")
            print(f"         html={html}")

        # 如果没有 activity-list-item，搜索所有可能包含「自适应练习」的元素
        print("\n    --- 搜索包含「自适应练习」的元素 ---")
        adaptive_elements = await page.evaluate("""
            () => {
                const results = [];
                const allEls = document.querySelectorAll('*');
                for (const el of allEls) {
                    const text = (el.innerText || '').trim();
                    if (text.includes('自适应练习') || text.includes('自适应训练')) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            results.push({
                                tag: el.tagName.toLowerCase(),
                                id: el.id || '',
                                className: (typeof el.className === 'string' ? el.className : '').substring(0, 100),
                                text: text.substring(0, 120),
                                rect: `${Math.round(rect.width)}x${Math.round(rect.height)}`,
                                html: el.outerHTML.substring(0, 500)
                            });
                        }
                    }
                }
                return results;
            }
        """)

        if adaptive_elements:
            print(f"    找到 {len(adaptive_elements)} 个包含「自适应练习」的元素:")
            for i, item in enumerate(adaptive_elements):
                print(f"\n    [{i+1}] <{item['tag']}> id='{item['id']}'")
                print(f"          class='{item['className']}'")
                print(f"          text='{item['text']}'")
                print(f"          html={item['html']}")
        else:
            print("    未找到包含「自适应练习」的元素")

        # ---------- 步骤 6: 展开所有章节 ----------
        print("\n[7/10] 展开所有章节...")
        expand_count = 0
        for attempt in range(5):
            arrows = await page.query_selector_all('.left-arrow:not(.is-open):not(.dian)')
            if len(arrows) == 0:
                print(f"    所有章节已展开 (尝试 {attempt+1} 次)")
                break
            print(f"    第 {attempt+1} 轮: 发现 {len(arrows)} 个未展开箭头")
            for arrow in arrows:
                try:
                    await arrow.click()
                    expand_count += 1
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"      点击箭头失败: {e}")
            await asyncio.sleep(2)

        print(f"    共展开 {expand_count} 个章节")
        await safe_screenshot(page, "04_chapters_expanded.png")

        # ---------- 步骤 7: 查找并点击包含「自适应练习」的章节 ----------
        print("\n[8/10] 查找包含「自适应练习」的叶子章节...")

        # 先用 JavaScript 查找
        chapter_targets = await page.evaluate("""
            () => {
                const results = [];
                // 查找所有可能包含「自适应练习」的列表项
                const items = document.querySelectorAll('.activity-list-item, ' +
                    '[class*="chapter"]:not([class*="arrow"]), ' +
                    '[class*="section"], [class*="lesson"], ' +
                    '.el-tree-node__content, li, ' +
                    '.chapter-item, .chapter-wrap');

                for (const item of items) {
                    const text = (item.innerText || '').trim();
                    if (text.includes('自适应练习') || text.includes('自适应训练')) {
                        const rect = item.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            // 检查是否可点击
                            const isClickable = item.tagName === 'A' ||
                                item.querySelector('a') ||
                                item.getAttribute('role') === 'button' ||
                                item.style.cursor === 'pointer';

                            results.push({
                                tag: item.tagName.toLowerCase(),
                                id: item.id || '',
                                className: (typeof item.className === 'string' ? item.className : '').substring(0, 120),
                                text: text.substring(0, 150),
                                clickable: isClickable,
                                rect: `${Math.round(rect.width)}x${Math.round(rect.height)}`,
                                position: { top: Math.round(rect.top), left: Math.round(rect.left) },
                                html: item.outerHTML.substring(0, 600)
                            });
                        }
                    }
                }
                return results;
            }
        """)

        if chapter_targets:
            print(f"    找到 {len(chapter_targets)} 个可能的章节目标:")
            for i, item in enumerate(chapter_targets):
                print(f"\n    [{i+1}] <{item['tag']}> clickable={item['clickable']}")
                print(f"          id='{item['id']}'")
                print(f"          class='{item['className']}'")
                print(f"          text='{item['text']}'")
                print(f"          position=({item['position']['left']},{item['position']['top']})")
                print(f"          html={item['html']}")
        else:
            print("    未通过文本找到目标，尝试查找已知章节名称...")
            # 尝试查找包含「常见数据挖掘算法」的章节
            known_targets = await page.evaluate("""
                () => {
                    const results = [];
                    const keywords = ['常见数据挖掘算法', '数据挖掘', '算法', '自适应'];
                    const allEls = document.querySelectorAll('*');
                    const seen = new Set();

                    for (const el of allEls) {
                        const text = (el.innerText || '').trim();
                        for (const kw of keywords) {
                            if (text.includes(kw) && text.length < 200) {
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0 && !seen.has(el)) {
                                    seen.add(el);
                                    results.push({
                                        tag: el.tagName.toLowerCase(),
                                        id: el.id || '',
                                        className: (typeof el.className === 'string' ? el.className : '').substring(0, 100),
                                        text: text.substring(0, 200),
                                        rect: `${Math.round(rect.width)}x${Math.round(rect.height)}`,
                                        html: el.outerHTML.substring(0, 500)
                                    });
                                    break;
                                }
                            }
                        }
                    }
                    return results;
                }
            """)

            if known_targets:
                print(f"    找到 {len(known_targets)} 个匹配元素:")
                for i, item in enumerate(known_targets):
                    print(f"\n    [{i+1}] <{item['tag']}> id='{item['id']}'")
                    print(f"          class='{item['className']}'")
                    print(f"          text='{item['text']}'")
                    print(f"          html={item['html']}")

        # 尝试点击最具体的章节目标
        clicked_chapter = False
        for target in chapter_targets:
            try:
                print(f"\n    尝试点击: {target['text'][:60]}")
                # 构建选择器
                if target['id']:
                    selector = f"#{target['id']}"
                else:
                    # 用 XPath 更精确地定位
                    selector = f"text={target['text'][:50]}"

                el = await page.query_selector(selector) if target['id'] else None
                if not el:
                    # 用 XPath
                    xpath = f"//*[contains(text(), '{target['text'][:30]}')]"
                    els = await page.query_selector_all(f":has-text('{target['text'][:30]}')")
                    if els:
                        # 找最具体的那个（最深、父级有章节类名的）
                        for e in els:
                            cls = await e.get_attribute("class") or ""
                            parent_cls = await e.evaluate("el => el.parentElement ? el.parentElement.className : ''")
                            if 'chapter' in cls.lower() or 'section' in cls.lower() or 'activity' in cls.lower():
                                el = e
                                break
                        if not el and els:
                            el = els[-1]  # 取最后一个（最深）

                if el:
                    await el.scroll_into_view_if_needed()
                    await asyncio.sleep(1)
                    await el.click()
                    print(f"      点击成功!")
                    clicked_chapter = True
                    await safe_screenshot(page, "05_chapter_clicked.png")
                    break
            except Exception as e:
                print(f"      点击失败: {e}")

        if not clicked_chapter:
            print("\n    [!] 未找到可点击的章节，尝试用 JavaScript 点击...")
            # 尝试用 JS 查找并点击最可能的目标
            clicked = await page.evaluate("""
                () => {
                    // 查找所有包含「自适应练习」的叶子节点
                    const items = document.querySelectorAll('.activity-list-item');
                    for (const item of items) {
                        if (item.innerText.includes('自适应练习')) {
                            item.click();
                            return '点击了 activity-list-item: ' + item.innerText.trim();
                        }
                    }
                    // 查找包含特定文本的 a 标签
                    const links = document.querySelectorAll('a, span, div, p');
                    for (const el of links) {
                        if (el.innerText.includes('常见数据挖掘算法') ||
                            el.innerText.includes('自适应练习')) {
                            if (el.children.length === 0 || el.tagName === 'A') {
                                el.click();
                                return '点击了: ' + el.innerText.trim();
                            }
                        }
                    }
                    return '未找到可点击元素';
                }
            """)
            print(f"    JS 点击结果: {clicked}")
            await asyncio.sleep(3)
            await safe_screenshot(page, "05b_js_click_result.png")

        # ---------- 等待内容页加载 ----------
        print("\n    等待内容页加载 (5 秒)...")
        await asyncio.sleep(5)
        print(f"    当前 URL: {page.url}")
        await safe_screenshot(page, "06_content_page.png")

        # ---------- 步骤 8: 查找资源列表中的「自适应练习」 ----------
        print("\n[9/10] 在资源列表中查找类型为「自适应练习」的 .activity-list-item...")

        # 分析资源列表
        resource_info = await page.evaluate("""
            () => {
                const results = [];
                // 查找所有活动列表项
                const items = document.querySelectorAll('.activity-list-item, ' +
                    '[class*="resource"], [class*="activity"], ' +
                    '.resource-item, .el-row, .el-col');

                items.forEach(item => {
                    const text = (item.innerText || '').trim();
                    const rect = item.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && text.length > 0) {
                        // 找类型标签
                        const typeEl = item.querySelector('.resource-type, [class*="type"], ' +
                            '.tag, .el-tag, .activity-type');
                        const typeText = typeEl ? (typeEl.innerText || '').trim() : '';

                        results.push({
                            tag: item.tagName.toLowerCase(),
                            id: item.id || '',
                            className: (typeof item.className === 'string' ? item.className : '').substring(0, 100),
                            text: text.substring(0, 200),
                            typeText: typeText,
                            html: item.outerHTML.substring(0, 400)
                        });
                    }
                });
                return results.slice(0, 40);
            }
        """)

        if resource_info:
            print(f"    找到 {len(resource_info)} 个资源相关项:")
            for i, item in enumerate(resource_info):
                print(f"\n    [{i+1}] <{item['tag']}> type='{item['typeText']}'")
                print(f"          id='{item['id']}'")
                print(f"          class='{item['className']}'")
                print(f"          text='{item['text']}'")
                print(f"          html={item['html']}")
        else:
            print("    未找到资源列表，搜索所有可见元素中的相关文本...")
            all_visible = await page.evaluate("""
                () => {
                    const results = [];
                    const keywords = ['自适应练习', '自适应训练', 'PPT', '视频', '文档', 'PDF',
                                    'adaptive', 'exercise', 'training'];
                    const allEls = document.querySelectorAll('body *');
                    const seen = new Set();

                    for (const el of allEls) {
                        const text = (el.innerText || '').trim();
                        if (text.length > 0 && text.length < 300) {
                            for (const kw of keywords) {
                                if (text.includes(kw) && !seen.has(el)) {
                                    const rect = el.getBoundingClientRect();
                                    if (rect.width > 0 && rect.height > 0) {
                                        seen.add(el);
                                        results.push({
                                            tag: el.tagName.toLowerCase(),
                                            id: el.id || '',
                                            className: (typeof el.className === 'string' ? el.className : '').substring(0, 80),
                                            text: text.substring(0, 200),
                                            rect: `${Math.round(rect.width)}x${Math.round(rect.height)}`
                                        });
                                        break;
                                    }
                                }
                            }
                        }
                    }
                    return results.slice(0, 40);
                }
            """)

            if all_visible:
                print(f"    找到 {len(all_visible)} 个包含关键词的元素:")
                for i, item in enumerate(all_visible):
                    print(f"\n    [{i+1}] <{item['tag']}> id='{item['id']}'")
                    print(f"          class='{item['className']}'")
                    print(f"          text='{item['text']}'")

        # 查找具体的"自适应练习"条目并点击
        print("\n    --- 尝试点击「自适应练习」 ---")
        adaptive_clicked = False

        # 方法1: 精确查找 activity-list-item 包含「自适应练习」
        adaptive_items = await page.query_selector_all('.activity-list-item')
        for item in adaptive_items:
            text = await item.inner_text()
            if '自适应练习' in text:
                print(f"    找到 .activity-list-item: text='{text[:80]}'")
                cls = await item.get_attribute("class")
                print(f"    class='{cls}'")
                await item.scroll_into_view_if_needed()
                await asyncio.sleep(1)
                await item.click()
                print("    点击了 activity-list-item")
                adaptive_clicked = True
                break

        # 方法2: 查找包含「自适应练习」的任何可点击元素
        if not adaptive_clicked:
            print("    方法1 未成功，尝试查找其他元素...")
            adaptive_els = await page.evaluate("""
                () => {
                    const results = [];
                    const allEls = document.querySelectorAll('*');
                    for (const el of allEls) {
                        if (el.innerText && el.innerText.includes('自适应练习')) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                const tag = el.tagName.toLowerCase();
                                // 看看是否有可点击的父元素
                                let clickable = el;
                                while (clickable && clickable !== document.body) {
                                    const cTag = clickable.tagName.toLowerCase();
                                    if (cTag === 'a' || cTag === 'button' ||
                                        clickable.getAttribute('role') === 'button' ||
                                        clickable.style.cursor === 'pointer' ||
                                        clickable.onclick) {
                                        results.push({
                                            tag: cTag,
                                            id: clickable.id || '',
                                            className: typeof clickable.className === 'string' ?
                                                clickable.className.substring(0, 100) : '',
                                            text: clickable.innerText.trim().substring(0, 100),
                                            clickable: true
                                        });
                                        break;
                                    }
                                    clickable = clickable.parentElement;
                                }
                                if (!clickable || clickable === document.body) {
                                    results.push({
                                        tag: tag,
                                        id: el.id || '',
                                        className: (typeof el.className === 'string' ? el.className : '').substring(0, 100),
                                        text: el.innerText.trim().substring(0, 100),
                                        clickable: false
                                    });
                                }
                                break; // 只取第一个
                            }
                        }
                    }
                    return results;
                }
            """)

            if adaptive_els:
                print(f"    找到 {len(adaptive_els)} 个包含「自适应练习」的元素:")
                for i, item in enumerate(adaptive_els):
                    print(f"\n    [{i+1}] <{item['tag']}> clickable={item['clickable']}")
                    print(f"          id='{item['id']}'")
                    print(f"          class='{item['className']}'")
                    print(f"          text='{item['text']}'")

                    if not adaptive_clicked:
                        try:
                            # 尝试点击
                            if item['id']:
                                await page.click(f"#{item['id']}")
                            else:
                                # 用 XPath
                                xpath = f"//*[contains(text(), '自适应练习')]"
                                el = await page.query_selector(f"text=自适应练习")
                                if el:
                                    await el.click()
                                else:
                                    # 用 JS
                                    await page.evaluate("""
                                        () => {
                                            const all = document.querySelectorAll('*');
                                            for (const el of all) {
                                                if (el.innerText && el.innerText.includes('自适应练习') &&
                                                    el.getBoundingClientRect().width > 0) {
                                                    el.click();
                                                    break;
                                                }
                                            }
                                        }
                                    """)
                            print("    已尝试点击")
                            adaptive_clicked = True
                        except Exception as e:
                            print(f"    点击失败: {e}")

        if not adaptive_clicked:
            print("\n    [!] 未能点击「自适应练习」，请检查页面结构")
            await safe_screenshot(page, "07_no_adaptive_found.png")

            # 保存完整页面文本和 HTML 供调试
            debug_text = await page.evaluate("() => document.body.innerText")
            with open(os.path.join(OUTPUT_DIR, "debug_page_text.txt"), "w", encoding="utf-8") as f:
                f.write(debug_text)
            print("    页面文本已保存到 debug_page_text.txt")

            debug_html = await page.evaluate("""
                () => {
                    const clone = document.documentElement.cloneNode(true);
                    clone.querySelectorAll('script').forEach(s => s.remove());
                    return clone.outerHTML;
                }
            """)
            with open(os.path.join(OUTPUT_DIR, "debug_page.html"), "w", encoding="utf-8") as f:
                f.write(debug_html)
            print("    页面 HTML 已保存到 debug_page.html")
            await browser.close()
            return

        # ---------- 步骤 9: 等待自适应练习页面加载 ----------
        print("\n[10/10] 等待自适应练习页面加载 (10 秒)...")
        await asyncio.sleep(10)

        print(f"\n    当前 URL: {page.url}")
        print(f"    打开的新标签页数: {len(new_pages)}")
        for i, np in enumerate(new_pages):
            print(f"      新标签页 [{i}]: {np.url}")
        print(f"    出现的对话框数: {len(dialogs)}")
        for i, d in enumerate(dialogs):
            print(f"      对话框 [{i}]: type={d.type} message='{d.message[:100]}'")

        await safe_screenshot(page, "07_adaptive_loaded.png")

        # ============================================================
        # 详细分析 A: 点击自适应练习后的行为
        # ============================================================
        print("\n" + "=" * 80)
        print("=== [分析 A] 点击自适应练习后的页面行为 ===")
        print("=" * 80)

        print(f"  [A1] 是否打开新标签页: {'是' if new_pages else '否'}")
        print(f"  [A2] 是否弹出对话框: {'是' if dialogs else '否'}")
        print(f"  [A3] 当前 URL: {page.url}")
        print(f"  [A4] 打开的所有标签页: {len(context.pages)}")

        for i, p in enumerate(context.pages):
            print(f"      标签页 [{i}]: url='{p.url}' title='{await p.title()}")

        # 如果有新标签页，切换到新标签页
        if len(context.pages) > 1:
            print("\n    --> 切换到新标签页")
            page = context.pages[-1]
            await asyncio.sleep(3)
            print(f"    新标签页 URL: {page.url}")
            await safe_screenshot(page, "08_new_tab.png")

        # ============================================================
        # 详细分析 B: 是否有"继续训练""开始训练"等按钮
        # ============================================================
        print("\n" + "=" * 80)
        print("=== [分析 B] 查找「继续训练/开始训练/开始学习」按钮 ===")
        print("=" * 80)

        # 获取页面文本看看有什么内容
        page_text = await page.evaluate("() => document.body.innerText")
        print(f"\n  页面可见文本 (前 1500 字):\n{page_text[:1500]}")

        # 查找各种按钮
        button_keywords = [
            '继续训练', '开始训练', '开始学习', '继续学习',
            '开始答题', '开始练习', '进入训练', '进入练习',
            'start', 'continue', 'begin', 'begin training',
            '开始', '继续', '进入', '答题'
        ]

        action_buttons = await page.evaluate(f"""
            () => {{
                const results = [];
                const keywords = {json.dumps(button_keywords)};
                const allEls = document.querySelectorAll('button, a, span, div, p, ' +
                    '[class*="btn"], [class*="button"], [role="button"]');

                for (const el of allEls) {{
                    const text = (el.innerText || el.textContent || '').trim();
                    if (text.length > 0 && text.length < 60) {{
                        for (const kw of keywords) {{
                            if (text.includes(kw)) {{
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {{
                                    results.push({{
                                        tag: el.tagName.toLowerCase(),
                                        id: el.id || '',
                                        className: (typeof el.className === 'string' ? el.className : '').substring(0, 100),
                                        text: text,
                                        rect: `${{Math.round(rect.width)}}x${{Math.round(rect.height)}}`,
                                        position: `(${{Math.round(rect.left)}},${{Math.round(rect.top)}})`
                                    }});
                                }}
                                break;
                            }}
                        }}
                    }}
                }}
                return results;
            }}
        """)

        if action_buttons:
            print(f"\n  找到 {len(action_buttons)} 个操作按钮:")
            for i, btn in enumerate(action_buttons):
                print(f"\n    [{i+1}] <{btn['tag']}> text='{btn['text']}'")
                print(f"          id='{btn['id']}'")
                print(f"          class='{btn['className']}'")
                print(f"          size={btn['rect']} pos={btn['position']}")

            # 如果有"继续训练"等按钮，点击它
            for btn_info in action_buttons:
                target_kws = ['继续训练', '开始训练', '开始学习', '继续学习', '开始答题', '开始练习']
                if any(kw in btn_info['text'] for kw in target_kws):
                    print(f"\n    --> 点击按钮: {btn_info['text']}")
                    try:
                        # 使用 JavaScript 点击，避免 CSS 选择器换行问题
                        clicked = await page.evaluate(f"""
                            () => {{
                                const allEls = document.querySelectorAll('button');
                                for (const el of allEls) {{
                                    const text = (el.innerText || '').trim().substring(0, 20);
                                    const targetKws = {json.dumps(target_kws)};
                                    for (const kw of targetKws) {{
                                        if (text.includes(kw)) {{
                                            el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                                            setTimeout(() => el.click(), 300);
                                            return '已点击: ' + text;
                                        }}
                                    }}
                                }}
                                return '未找到匹配按钮';
                            }}
                        """)
                        print(f"      {clicked}")
                        await asyncio.sleep(5)
                        await safe_screenshot(page, "09_after_start_button.png")
                    except Exception as e:
                        print(f"      点击失败: {e}")
                    break
        else:
            print("\n  未找到操作按钮")

        # 在 iframe 中查找
        print("\n  --- 检查 iframe 中的按钮 ---")
        frames = page.frames
        print(f"  页面框架数: {len(frames)}")
        for i, frame in enumerate(frames):
            try:
                frame_text = await frame.evaluate("() => document.body.innerText.substring(0, 300)")
                if any(kw in frame_text for kw in ['继续训练', '开始训练', '自适应']):
                    print(f"  Frame [{i}]: url='{frame.url}'")
                    print(f"    文本: {frame_text[:300]}")
            except Exception:
                pass

        # ============================================================
        # 详细分析 C: 答题界面结构
        # ============================================================
        print("\n" + "=" * 80)
        print("=== [分析 C] 答题界面结构分析 ===")
        print("=" * 80)

        # 分析题目相关元素
        question_analysis = await page.evaluate("""
            () => {
                function visible(el) {
                    const r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                }
                function info(el, maxText=100) {
                    return {
                        tag: el.tagName.toLowerCase(),
                        id: el.id || '',
                        className: (typeof el.className === 'string' ? el.className : '').substring(0, 80),
                        text: (el.innerText || '').trim().substring(0, maxText),
                        rect: Math.round(el.getBoundingClientRect().width) + 'x' + Math.round(el.getBoundingClientRect().height)
                    };
                }

                const results = {};

                // 1. 查找题目容器
                const containers = document.querySelectorAll(
                    '.question, .topic, .exam-item, [class*="question"], ' +
                    '[class*="topic"], [class*="exam"], ' +
                    '.el-main, .content, .answer-wrap, ' +
                    '#app > div, #root > div'
                );
                results.containers = Array.from(containers)
                    .filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 100; })
                    .slice(0, 10)
                    .map(el => info(el));

                // 2. 查找题目文本元素
                const questionTexts = document.querySelectorAll(
                    '.question-title, .topic-title, .exam-title, ' +
                    '[class*="question-title"], [class*="topic-title"], ' +
                    '[class*="exam-title"], [class*="title"]:not(.chapter-title), ' +
                    'h1, h2, h3, h4, .el-card, .card'
                );
                results.questionTexts = Array.from(questionTexts)
                    .filter(el => visible(el))
                    .slice(0, 20)
                    .map(el => info(el, 120));

                // 3. 查找选项结构
                const options = document.querySelectorAll(
                    '.el-radio, .el-radio-group, ' +
                    '.el-checkbox, .el-checkbox-group, ' +
                    '.option, .answer-option, .select-option, ' +
                    '[class*="option"], [class*="choice"], ' +
                    'input[type="radio"], input[type="checkbox"], ' +
                    'label, .el-radio__label, .el-checkbox__label'
                );
                results.options = Array.from(options)
                    .filter(el => visible(el))
                    .slice(0, 30)
                    .map(el => ({
                        ...info(el, 80),
                        type: el.type || '',
                        html: el.outerHTML.substring(0, 200)
                    }));

                // 4. 查找「下一题」按钮 (不用 :has-text, 用 filter)
                const allButtons = document.querySelectorAll('button, .next-btn, .next, [class*="next"], [aria-label*="next"]');
                const nextKeywords = ['下一题', '下一', 'next'];
                results.nextButtons = Array.from(allButtons)
                    .filter(el => {
                        if (!visible(el)) return false;
                        const text = (el.innerText || '').trim().toLowerCase();
                        return nextKeywords.some(kw => text.includes(kw));
                    })
                    .slice(0, 5)
                    .map(el => info(el, 40));

                // 5. 查找「交卷/提交」按钮
                const submitEls = document.querySelectorAll('button, .submit-btn, .submit, [class*="submit"], [class*="hand"]');
                const submitKeywords = ['交卷', '提交', '完成', 'submit', 'hand in'];
                results.submitButtons = Array.from(submitEls)
                    .filter(el => {
                        if (!visible(el)) return false;
                        const text = (el.innerText || '').trim().toLowerCase();
                        return submitKeywords.some(kw => text.includes(kw));
                    })
                    .slice(0, 5)
                    .map(el => info(el, 40));

                // 6. 查找题号/进度指示器
                const progressIndicators = document.querySelectorAll(
                    '.progress, [class*="progress"], ' +
                    '.step, [class*="step"], ' +
                    '.pagination, [class*="pagination"], ' +
                    '.index, [class*="index"], ' +
                    '.count, [class*="count"], ' +
                    '.el-pagination, .page-info'
                );
                results.progressIndicators = Array.from(progressIndicators)
                    .filter(el => visible(el))
                    .slice(0, 10)
                    .map(el => info(el, 60));

                return results;
            }
        """)

        for section, items in question_analysis.items():
            print(f"\n  [{section}]:")
            if items:
                for i, item in enumerate(items):
                    print(f"    [{i+1}] <{item['tag']}> id='{item['id']}'")
                    print(f"          class='{item['className']}'")
                    print(f"          text='{item['text']}'")
                    if 'html' in item:
                        print(f"          html={item['html']}")
                    if 'type' in item:
                        print(f"          type={item['type']}")
                    print(f"          size={item['rect']}")
            else:
                print("    未找到")

        # 如果还没进入答题界面，检查是否有 iframe
        print("\n  --- 检查 iframe 内容 ---")
        for i, frame in enumerate(page.frames):
            try:
                frame_title = await frame.title()
                frame_url = frame.url
                print(f"  Frame [{i}]: title='{frame_title}' url='{frame_url[:100]}'")

                # 只在非空 iframe 中查找
                if frame_url and 'about:blank' not in frame_url:
                    frame_text = await frame.evaluate("() => document.body.innerText.substring(0, 500)")
                    if frame_text.strip():
                        print(f"    文本: {frame_text[:300]}")

                    frame_buttons = await frame.evaluate("""
                        () => {
                            const btns = document.querySelectorAll('button, a[class*="btn"], [class*="button"]');
                            return Array.from(btns)
                                .filter(b => {
                                    const r = b.getBoundingClientRect();
                                    return r.width > 0 && r.height > 0;
                                })
                                .slice(0, 10)
                                .map(b => ({
                                    tag: b.tagName,
                                    text: (b.innerText || '').trim().substring(0, 40),
                                    id: b.id || '',
                                    className: (typeof b.className === 'string' ? b.className : '').substring(0, 60)
                                }));
                        }
                    """)
                    if frame_buttons:
                        print(f"    包含按钮: {json.dumps(frame_buttons, ensure_ascii=False)}")
            except Exception as e:
                print(f"  Frame [{i}]: 错误 {e}")

        # 特别分析 Frame[2] 如果存在（可能是自适应练习的 iframe）
        if len(page.frames) > 2:
            print("\n  --- 重点分析可能包含自适应练习的 iframe ---")
            target_frame = page.frames[2]
            try:
                frame_html = await target_frame.evaluate("""
                    () => document.documentElement.outerHTML.substring(0, 5000)
                """)
                print(f"  Frame[2] HTML 结构:\n{frame_html}")
            except Exception as e:
                print(f"  Frame[2] 分析失败: {e}")

        # ============================================================
        # 详细分析 D: 交卷确认弹窗
        # ============================================================
        print("\n" + "=" * 80)
        print("=== [分析 D] 交卷确认弹窗结构 ===")
        print("=" * 80)

        # 检查当前是否有弹窗可见
        modal_analysis = await page.evaluate("""
            () => {
                const results = {};

                // el-message-box
                const msgBox = document.querySelector('.el-message-box, .el-dialog, ' +
                    '.dialog, [class*="modal"], [class*="dialog"], ' +
                    '[class*="message-box"], [class*="confirm"], ' +
                    '.v-modal, .mask, .overlay');
                if (msgBox) {
                    results.messageBox = {
                        tag: msgBox.tagName.toLowerCase(),
                        id: msgBox.id || '',
                        className: (typeof msgBox.className === 'string' ? msgBox.className : '').substring(0, 100),
                        text: (msgBox.innerText || '').trim().substring(0, 200),
                        visible: msgBox.style.display !== 'none' && msgBox.style.visibility !== 'hidden',
                        html: msgBox.outerHTML.substring(0, 800)
                    };

                    // 查找确认按钮 (用 innerText 过滤，避免 :has-text)
                    const allBtnsInMsg = msgBox.querySelectorAll(
                        '.el-button--primary, .confirm-btn, .sure, button'
                    );
                    const confirmTexts = ['确定', '确认', '是', 'Yes'];
                    results.confirmButtons = Array.from(allBtnsInMsg)
                        .filter(b => {
                            const t = (b.innerText || '').trim();
                            return confirmTexts.some(k => t.includes(k));
                        })
                        .map(b => ({
                            tag: b.tagName.toLowerCase(),
                            text: (b.innerText || '').trim().substring(0, 40),
                            className: (typeof b.className === 'string' ? b.className : '').substring(0, 60)
                        }));

                    // 查找取消按钮
                    const cancelTexts = ['取消', '否', 'No', 'Close'];
                    results.cancelButtons = Array.from(allBtnsInMsg)
                        .filter(b => {
                            const t = (b.innerText || '').trim();
                            return cancelTexts.some(k => t.includes(k));
                        })
                        .map(b => ({
                            tag: b.tagName.toLowerCase(),
                            text: (b.innerText || '').trim().substring(0, 40),
                            className: (typeof b.className === 'string' ? b.className : '').substring(0, 60)
                        }));
                } else {
                    results.messageBox = null;
                }

                return results;
            }
        """)

        if modal_analysis.get('messageBox'):
            print(f"\n  发现弹窗:")
            print(f"    <{modal_analysis['messageBox']['tag']}> class='{modal_analysis['messageBox']['className']}'")
            print(f"    text='{modal_analysis['messageBox']['text']}'")
            print(f"    visible={modal_analysis['messageBox']['visible']}")
            print(f"    html={modal_analysis['messageBox']['html']}")
            if modal_analysis.get('confirmButtons'):
                print(f"\n  确认按钮:")
                for btn in modal_analysis['confirmButtons']:
                    print(f"    [{btn['text']}] <{btn['tag']}> class='{btn['className']}'")
            if modal_analysis.get('cancelButtons'):
                print(f"\n  取消按钮:")
                for btn in modal_analysis['cancelButtons']:
                    print(f"    [{btn['text']}] <{btn['tag']}> class='{btn['className']}'")
        else:
            print("\n  当前没有弹窗")

        # ============================================================
        # 详细分析 E: 完成后的关闭/返回按钮
        # ============================================================
        print("\n" + "=" * 80)
        print("=== [分析 E] 完成后关闭/返回按钮 ===")
        print("=" * 80)

        close_analysis = await page.evaluate("""
            () => {
                const results = [];

                // 通过 class 选择器查找
                const classSelectors = [
                    '.close-btn', '.back-btn', '.return-btn',
                    '[class*="close"]', '[class*="back"]', '[class*="return"]',
                    '[aria-label="Close"]', '[aria-label="close"]',
                    '.el-dialog__close', '.el-dialog__headerbtn',
                    '.icon-close', '.fa-times', '.fa-close'
                ];

                for (const sel of classSelectors) {
                    try {
                        const els = document.querySelectorAll(sel);
                        els.forEach(el => {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                results.push({
                                    tag: el.tagName.toLowerCase(),
                                    id: el.id || '',
                                    className: (typeof el.className === 'string' ? el.className : '').substring(0, 80),
                                    text: (el.innerText || el.title || '').trim().substring(0, 40),
                                    selector: sel,
                                    rect: `${Math.round(rect.width)}x${Math.round(rect.height)}`
                                });
                            }
                        });
                    } catch(e) {}
                }

                // 通过文本内容查找按钮
                const allButtons = document.querySelectorAll('button');
                const closeTexts = ['关闭', '返回', 'Close', 'Back', '退出', 'exit'];
                allButtons.forEach(btn => {
                    const text = (btn.innerText || '').trim();
                    if (closeTexts.some(k => text.includes(k))) {
                        const rect = btn.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            results.push({
                                tag: 'button',
                                id: btn.id || '',
                                className: (typeof btn.className === 'string' ? btn.className : '').substring(0, 80),
                                text: text.substring(0, 40),
                                selector: 'button[text~="' + text.substring(0, 10) + '"]',
                                rect: `${Math.round(rect.width)}x${Math.round(rect.height)}`
                            });
                        }
                    }
                });

                return results.slice(0, 15);
            }
        """)

        if close_analysis:
            print(f"\n  找到 {len(close_analysis)} 个关闭/返回相关元素:")
            for i, item in enumerate(close_analysis):
                print(f"\n    [{i+1}] <{item['tag']}> selector='{item['selector']}'")
                print(f"          id='{item['id']}'")
                print(f"          class='{item['className']}'")
                print(f"          text='{item['text']}'")
                print(f"          size={item['rect']}")
        else:
            print("\n  未找到关闭/返回按钮")

        # ============================================================
        # 获取完整的答题页面 HTML 结构
        # ============================================================
        print("\n" + "=" * 80)
        print("=== [补充] 当前页面完整 HTML 结构 ===")
        print("=" * 80)

        # 获取页面 body 结构树
        body_structure = await page.evaluate("""
            () => {
                function getStructure(el, depth) {
                    if (depth > 5) return '';
                    const children = Array.from(el.children);
                    if (children.length === 0) return '';

                    let result = '';
                    const tag = el.tagName.toLowerCase();
                    const id = el.id ? ` id="${el.id}"` : '';
                    const cls = el.className && typeof el.className === 'string'
                        ? ` class="${el.className.substring(0, 80)}"` : '';

                    result += `${'  '.repeat(depth)}<${tag}${id}${cls}>\\n`;

                    for (const child of children.slice(0, 10)) {
                        if (child.children.length > 0) {
                            result += getStructure(child, depth + 1);
                        } else {
                            const cTag = child.tagName.toLowerCase();
                            const cId = child.id ? ` id="${child.id}"` : '';
                            const cCls = child.className && typeof child.className === 'string'
                                ? ` class="${child.className.substring(0, 60)}"` : '';
                            const cText = (child.innerText || '').trim().substring(0, 40);
                            result += `${'  '.repeat(depth + 1)}<${cTag}${cId}${cCls}>`;
                            if (cText) result += ` "${cText}"`;
                            result += '\\n';
                        }
                    }

                    if (el.children.length > 10) {
                        result += `${'  '.repeat(depth + 1)}... ${el.children.length - 10} more\\n`;
                    }

                    return result;
                }

                const container = document.querySelector('.question, .topic, .el-main, ' +
                    '.content, .answer-wrap, main, #app, .app') || document.body;
                return getStructure(container, 0);
            }
        """)

        print(f"\n{body_structure}")

        # 保存完整 HTML
        full_html = await page.evaluate("""
            () => {
                const clone = document.documentElement.cloneNode(true);
                clone.querySelectorAll('script').forEach(s => s.remove());
                return clone.outerHTML.substring(0, 100000);
            }
        """)
        html_path = os.path.join(OUTPUT_DIR, "adaptive_page.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(full_html)
        print(f"\n  页面 HTML 已保存到: {html_path}")

        # ============================================================
        # 汇总输出选择器
        # ============================================================
        print("\n" + "=" * 80)
        print("=== 🔍 关键元素 CSS 选择器汇总 ===")
        print("=" * 80)

        # 汇总所有关键选择器
        summary_selectors = await page.evaluate("""
            () => {
                function countVisible(sel) {
                    try { return document.querySelectorAll(sel).length; } catch(e) { return -1; }
                }

                const result = {};

                // 章节展开箭头
                const arrows = document.querySelectorAll('.left-arrow');
                result.chapterExpandArrow = {
                    selector: '.left-arrow:not(.is-open):not(.dian)',
                    count: arrows.length
                };

                // 活动列表项
                const items = document.querySelectorAll('.activity-list-item');
                result.activityListItem = {
                    selector: '.activity-list-item',
                    count: items.length
                };

                // 各种按钮 - 通过 innerText 过滤
                result.buttons = {};

                const allBtns = document.querySelectorAll('button');
                const nextTexts = ['下一题', '下一', 'next'];
                const nextCount = Array.from(allBtns).filter(b => {
                    const t = (b.innerText || '').trim().toLowerCase();
                    return b.getBoundingClientRect().width > 0 && nextTexts.some(k => t.includes(k));
                }).length;
                result.buttons.nextQuestion = {
                    selectors: ['button:包含文本"下一题"'],
                    count: nextCount
                };

                const submitTexts = ['交卷', '提交', '完成', 'submit'];
                const submitCount = Array.from(allBtns).filter(b => {
                    const t = (b.innerText || '').trim().toLowerCase();
                    return b.getBoundingClientRect().width > 0 && submitTexts.some(k => t.includes(k));
                }).length;
                result.buttons.submit = {
                    selectors: ['button:包含文本"交卷/提交"'],
                    count: submitCount
                };

                // 选项
                const radios = document.querySelectorAll('.el-radio');
                const checks = document.querySelectorAll('.el-checkbox');
                result.options = {
                    el_radio: { selector: '.el-radio', count: radios.length },
                    el_checkbox: { selector: '.el-checkbox', count: checks.length }
                };

                // 弹窗
                const dialogs = document.querySelectorAll('.el-message-box, .el-dialog, .dialog, [class*="modal"]');
                result.dialogs = {
                    selectors: ['.el-message-box', '.el-dialog', '.v-modal'],
                    count: dialogs.length
                };

                // 确认按钮
                const confirmTexts = ['确定', '确认', '是'];
                const confirmCount = Array.from(allBtns).filter(b => {
                    const t = (b.innerText || '').trim();
                    return b.getBoundingClientRect().width > 0 && confirmTexts.some(k => t.includes(k));
                }).length;
                result.confirmButton = {
                    selectors: ['button:包含文本"确定/确认"'],
                    count: confirmCount
                };

                // 关闭按钮
                const closeTexts = ['关闭', '关闭'];
                const closeCount = Array.from(allBtns).filter(b => {
                    const t = (b.innerText || '').trim();
                    return b.getBoundingClientRect().width > 0 && closeTexts.some(k => t.includes(k));
                }).length +
                    document.querySelectorAll('.close-btn, .el-dialog__close, [aria-label="Close"]').length;
                result.closeButton = {
                    selectors: ['button:包含文本"关闭"', '.close-btn', '.el-dialog__close'],
                    count: closeCount
                };

                return result;
            }
        """)

        for key, val in summary_selectors.items():
            if isinstance(val, dict) and 'count' in val:
                print(f"\n  {key}:")
                if 'selector' in val:
                    print(f"    选择器: {val['selector']}")
                if 'selectors' in val:
                    for s in val['selectors']:
                        print(f"    选择器: {s}")
                print(f"    数量: {val['count']}")
            elif isinstance(val, dict):
                print(f"\n  {key}:")
                for sub_key, sub_val in val.items():
                    if isinstance(sub_val, dict):
                        print(f"    {sub_key}: count={sub_val.get('count', '?')}")
                        if 'selector' in sub_val:
                            print(f"      选择器: {sub_val['selector']}")
                        if 'selectors' in sub_val:
                            for s in sub_val['selectors']:
                                print(f"      选择器: {s}")

        # 保存 JSON 格式的结构分析
        json_output = await page.evaluate("""
            () => {
                const result = {};

                // 所有按钮
                const allBtns = document.querySelectorAll('button, a.btn, [class*="btn"], [role="button"]');
                result.allButtons = Array.from(allBtns)
                    .filter(b => {
                        const r = b.getBoundingClientRect();
                        return r.width > 0 && r.height > 0;
                    })
                    .map(b => ({
                        text: (b.innerText || '').trim().substring(0, 40),
                        tag: b.tagName.toLowerCase(),
                        cssSelector: (b.id ? '#' + b.id : '') ||
                            (b.className && typeof b.className === 'string' ? '.' + b.className.trim().split(/\\s+/).join('.') : ''),
                        rect: `${Math.round(b.getBoundingClientRect().width)}x${Math.round(b.getBoundingClientRect().height)}`
                    }));

                // 所有 iframe
                result.allFrames = Array.from(document.querySelectorAll('iframe, frame')).map(f => ({
                    src: (f.src || '').substring(0, 200),
                    id: f.id || '',
                    className: (typeof f.className === 'string' ? f.className : '').substring(0, 60)
                }));

                return result;
            }
        """)

        json_path = os.path.join(OUTPUT_DIR, "adaptive_structure.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_output, f, ensure_ascii=False, indent=2)
        print(f"\n  JSON 结构分析已保存到: {json_path}")

        # 最终截图
        await safe_screenshot(page, "99_final_state.png")

        # ============================================================
        print("\n" + "=" * 80)
        print("✅ 自适应练习页面结构分析完成!")
        print(f"   输出目录: {OUTPUT_DIR}")
        print(f"   截图文件: 共 10+ 张截图")
        print(f"   HTML 文件: adaptive_page.html")
        print(f"   JSON 文件: adaptive_structure.json")
        print("=" * 80)

        # 保持浏览器打开 60 秒供手动查看
        print("\n浏览器将保持打开状态 60 秒供手动查看...")
        await asyncio.sleep(60)

        await browser.close()
        print("浏览器已关闭。")


if __name__ == "__main__":
    asyncio.run(main())
