"""
课程页面结构分析脚本
使用 Playwright 自动化浏览器，分析 FIF 课程平台页面结构
"""

import asyncio
import json
import os
import sys
from datetime import datetime


async def main():
    print("=" * 80)
    print("FIF 课程平台 - 页面结构分析")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        # 启动浏览器
        print("[1/6] 启动浏览器...")
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

        # ---------- 步骤 1: 访问登录页面 ----------
        print("[2/6] 访问登录页面: https://www.fifedu.com/iplat/fifLogin/index.html?v=5.4.4")
        await page.goto(
            "https://www.fifedu.com/iplat/fifLogin/index.html?v=5.4.4",
            wait_until="networkidle",
            timeout=60000,
        )
        await asyncio.sleep(3)
        print("    页面加载完成")

        # 保存登录页截图
        await page.screenshot(path="01_login_page.png", full_page=True)
        print("    登录页面截图已保存: 01_login_page.png")

        # 获取登录页面的可见文本
        login_text = await page.evaluate("() => document.body.innerText")
        print(f"\n    登录页可见文本(前500字):\n    {login_text[:500]}")

        # ---------- 步骤 2: 查找输入框并登录 ----------
        print("\n[3/6] 查找输入框并填写登录信息...")

        # 尝试多种可能的账号输入框选择器
        username_selectors = [
            'input[type="text"]',
            'input[placeholder*="账号"]',
            'input[placeholder*="用户"]',
            'input[name*="user"]',
            'input[name*="account"]',
            'input[name*="login"]',
            'input[id*="user"]',
            'input[id*="account"]',
            'input[id*="login"]',
            'input[class*="user"]',
            'input[class*="account"]',
            'input[class*="login"]',
            '#username',
            '#userName',
            '#account',
            '#loginName',
            'input:not([type="hidden"])',
        ]

        password_selectors = [
            'input[type="password"]',
            'input[placeholder*="密码"]',
            'input[name*="pwd"]',
            'input[name*="pass"]',
            'input[id*="pwd"]',
            'input[id*="pass"]',
            '#password',
            '#pwd',
            '#passWord',
        ]

        username_input = None
        password_input = None

        print("    搜索账号输入框...")
        for sel in username_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    tag = await el.get_attribute("tagName")
                    type_attr = await el.get_attribute("type")
                    placeholder = await el.get_attribute("placeholder")
                    name_attr = await el.get_attribute("name")
                    id_attr = await el.get_attribute("id")
                    class_attr = await el.get_attribute("class")
                    print(f"      找到元素: <{tag} type={type_attr} placeholder={placeholder} "
                          f"name={name_attr} id={id_attr} class={class_attr}>")
                    # 检查是否为可见的文本输入框
                    if type_attr in (None, "text", "email", "tel"):
                        username_input = el
                        print(f"      -> 选择器 '{sel}' 匹配成功，将用于输入账号")
                        break
            except Exception:
                continue

        if not username_input:
            print("    [!] 未找到账号输入框，尝试查找所有 input 元素...")
            all_inputs = await page.evaluate("""
                () => {
                    const inputs = document.querySelectorAll('input');
                    return Array.from(inputs).map(i => ({
                        tag: i.tagName,
                        type: i.type,
                        placeholder: i.placeholder,
                        name: i.name,
                        id: i.id,
                        className: i.className,
                        rect: i.getBoundingClientRect()
                    }));
                }
            """)
            print(f"    所有 input 元素:")
            for inp in all_inputs:
                print(f"      <input type={inp['type']} placeholder={inp['placeholder']} "
                      f"name={inp['name']} id={inp['id']} class={inp['className']}>")

        print("\n    搜索密码输入框...")
        for sel in password_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    tag = await el.get_attribute("tagName")
                    type_attr = await el.get_attribute("type")
                    placeholder = await el.get_attribute("placeholder")
                    name_attr = await el.get_attribute("name")
                    id_attr = await el.get_attribute("id")
                    class_attr = await el.get_attribute("class")
                    print(f"      找到元素: <{tag} type={type_attr} placeholder={placeholder} "
                          f"name={name_attr} id={id_attr} class={class_attr}>")
                    if type_attr == "password":
                        password_input = el
                        print(f"      -> 选择器 '{sel}' 匹配成功，将用于输入密码")
                        break
            except Exception:
                continue

        if not password_input:
            print("    [!] 未找到密码输入框")

        # 尝试查找登录按钮
        login_button_selectors = [
            'button[type="submit"]',
            'button:has-text("登录")',
            'button:has-text("Login")',
            'button:has-text("登 录")',
            '.login-btn',
            '#loginBtn',
            '#login-btn',
            'a:has-text("登录")',
            'span:has-text("登录")',
            '.el-button--primary',
            'button',
            'a.btn',
            '.submit-btn',
            'input[type="submit"]',
            'input[value*="登录"]',
        ]

        login_button = None
        print("\n    搜索登录按钮...")
        for sel in login_button_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    text = await el.inner_text()
                    tag = await el.get_attribute("tagName")
                    class_attr = await el.get_attribute("class")
                    print(f"      找到元素: <{tag} class={class_attr}> text='{text[:30]}'")
                    if login_button is None:
                        login_button = el
                        print(f"      -> 选择器 '{sel}' 将用于登录")
            except Exception:
                continue

        if not login_button:
            print("    [!] 未找到登录按钮")

        # 如果找到输入框，填写并登录
        if username_input and password_input:
            print("\n    --- 填写登录信息 ---")
            await username_input.click()
            await username_input.fill("")
            await asyncio.sleep(0.5)
            await username_input.type("gduf231543223", delay=50)
            print("    账号已填写: gduf231543223")

            await password_input.click()
            await password_input.fill("")
            await asyncio.sleep(0.5)
            await password_input.type("gduf231543223", delay=50)
            print("    密码已填写")

            await asyncio.sleep(1)

            if login_button:
                print("    点击登录按钮...")
                await login_button.click()
            else:
                print("    未找到登录按钮，尝试按 Enter 键...")
                await page.keyboard.press("Enter")
        else:
            print("\n    [!] 未能找到输入框，尝试使用 evaluate 直接填写...")
            # 尝试更广泛的查找
            result = await page.evaluate("""
                () => {
                    const inputs = document.querySelectorAll('input');
                    let textInput = null;
                    let pwdInput = null;
                    for (const inp of inputs) {
                        if (inp.type === 'password') pwdInput = inp;
                        else if (inp.type === 'text' || !inp.type) {
                            if (!textInput) textInput = inp;
                        }
                    }
                    if (textInput) {
                        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value'
                        ).set;
                        nativeInputValueSetter.call(textInput, 'gduf231543223');
                        textInput.dispatchEvent(new Event('input', { bubbles: true }));
                        textInput.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    if (pwdInput) {
                        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value'
                        ).set;
                        nativeInputValueSetter.call(pwdInput, 'gduf231543223');
                        pwdInput.dispatchEvent(new Event('input', { bubbles: true }));
                        pwdInput.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    return { foundText: !!textInput, foundPwd: !!pwdInput };
                }
            """)
            print(f"    直接填写结果: {result}")

            if login_button:
                await login_button.click()
            else:
                await page.keyboard.press("Enter")

        # ---------- 步骤 3: 等待登录成功 ----------
        print("\n[4/6] 等待登录成功 (等待 8 秒)...")
        await asyncio.sleep(8)

        current_url = page.url
        print(f"    当前 URL: {current_url}")

        await page.screenshot(path="02_after_login.png", full_page=True)
        print("    登录后截图已保存: 02_after_login.png")

        # ---------- 步骤 4: 访问课程页面 ----------
        print("\n[5/6] 访问课程页面...")
        course_url = (
            "https://icourse.fifedu.com/istp-learning-center/"
            "index?courseId=0bbe8331f3ae41d4ade3618c31e5c0d9"
            "&classId=2811000226001709298&termId=0ebfcb74812d4e5ab9f8f1919a341d97"
        )
        print(f"    课程 URL: {course_url}")
        await page.goto(course_url, wait_until="networkidle", timeout=60000)
        print("    课程页面加载完成，等待额外 10 秒让动态内容加载...")
        await asyncio.sleep(10)

        await page.screenshot(path="03_course_page.png", full_page=True)
        print("    课程页面截图已保存: 03_course_page.png")

        # ---------- 步骤 5: 分析页面结构 ----------
        print("\n" + "=" * 80)
        print("[6/6] 开始分析页面 DOM 结构...")
        print("=" * 80)

        # 获取页面标题
        page_title = await page.title()
        print(f"\n页面标题: {page_title}")
        print(f"当前 URL: {page.url}")

        # 获取页面可见文本
        visible_text = await page.evaluate("() => document.body.innerText")
        print(f"\n--- 页面可见文本 (前 3000 字) ---")
        print(visible_text[:3000])
        print("... (截断)")

        # ---------- 分析章节相关元素 ----------
        print("\n" + "-" * 80)
        print("【章节相关元素分析】")
        print("-" * 80)

        # 查找包含章节/课程相关关键词的元素
        chapter_analysis = await page.evaluate("""
            () => {
                const keywords = ['chapter', 'section', 'lesson', 'unit', 'module', 'course',
                                'chapter', 'section', 'lesson', 'unit', 'module', 'course',
                                '章节', '节', '课', '单元', '模块', '课程'];
                const results = [];

                // 查找所有元素，获取它们的 class, id, text 中包含的关键词
                const allElements = document.querySelectorAll('*');
                const checked = new Set();

                for (const el of allElements) {
                    const id = el.id || '';
                    const className = el.className || '';
                    const tagName = el.tagName.toLowerCase();

                    // 只检查有意义的元素
                    if (['script', 'style', 'link', 'meta'].includes(tagName)) continue;

                    const text = (el.innerText || '').trim().substring(0, 100);
                    const idLower = id.toLowerCase();
                    const classLower = (typeof className === 'string' ? className : '').toLowerCase();
                    const textLower = text.toLowerCase();

                    let matched = false;
                    const matchInfo = [];

                    for (const kw of keywords) {
                        const kwLower = kw.toLowerCase();
                        if (idLower.includes(kwLower)) {
                            matched = true;
                            matchInfo.push(`id含"${kw}"`);
                        }
                        if (classLower.includes(kwLower)) {
                            matched = true;
                            matchInfo.push(`class含"${kw}"`);
                        }
                        if (textLower.includes(kwLower) && text.length > 0 && text.length < 200) {
                            matched = true;
                            matchInfo.push(`文本含"${kw}"`);
                        }
                    }

                    if (matched && !checked.has(el)) {
                        checked.add(el);
                        const rect = el.getBoundingClientRect();
                        const visible = rect.width > 0 && rect.height > 0;
                        results.push({
                            tag: tagName,
                            id: id.substring(0, 80),
                            className: (typeof className === 'string' ? className : '').substring(0, 100),
                            text: text.substring(0, 120),
                            matchReason: matchInfo.join(', '),
                            visible: visible,
                            rect: { w: Math.round(rect.width), h: Math.round(rect.height) }
                        });
                    }
                }
                return results.slice(0, 100);
            }
        """)

        if chapter_analysis:
            print(f"\n找到 {len(chapter_analysis)} 个与章节相关的元素:")
            for i, item in enumerate(chapter_analysis):
                print(f"\n  [{i + 1}] <{item['tag']}> id='{item['id']}'")
                print(f"      class='{item['className']}'")
                print(f"      text='{item['text']}'")
                print(f"      match: {item['matchReason']}")
                print(f"      可见: {item['visible']}, 尺寸: {item['rect']}")
        else:
            print("    未找到与章节相关的元素")

        # ---------- 查找导航/侧边栏/目录结构 ----------
        print("\n" + "-" * 80)
        print("【导航/侧边栏/目录结构分析】")
        print("-" * 80)

        nav_analysis = await page.evaluate("""
            () => {
                // 查找侧边栏、导航、目录等容器
                const containers = [];
                const keywords = ['sidebar', 'sider', 'nav', 'menu', 'catalog', 'tree',
                                'sidebar', 'sider', 'nav', 'menu', 'catalog', 'tree',
                                '侧边栏', '导航', '目录', '列表', '侧栏'];

                // 查找 ul, li 列表结构
                const lists = document.querySelectorAll('ul, ol, nav, aside, .sidebar, .sider, '
                    + '[class*=sidebar], [class*=sider], [class*=nav], [class*=menu], '
                    + '[class*=catalog], [class*=tree], [class*=list], [class*=chapter]');

                lists.forEach(el => {
                    const id = el.id || '';
                    const className = el.className || '';
                    const tagName = el.tagName.toLowerCase();
                    const rect = el.getBoundingClientRect();
                    const visible = rect.width > 0 && rect.height > 0;

                    if (visible) {
                        const items = el.querySelectorAll('li, a, [class*=item], [class*=node]');
                        containers.push({
                            tag: tagName,
                            id: id.substring(0, 80),
                            className: (typeof className === 'string' ? className : '').substring(0, 120),
                            childrenCount: items.length,
                            firstChildText: items.length > 0 ? (items[0].innerText || '').trim().substring(0, 80) : '',
                            rect: { w: Math.round(rect.width), h: Math.round(rect.height) },
                            position: { top: Math.round(rect.top), left: Math.round(rect.left) }
                        });
                    }
                });

                return containers.slice(0, 50);
            }
        """)

        if nav_analysis:
            print(f"\n找到 {len(nav_analysis)} 个导航/目录容器:")
            for i, item in enumerate(nav_analysis):
                print(f"\n  [{i + 1}] <{item['tag']}> id='{item['id']}'")
                print(f"      class='{item['className']}'")
                print(f"      子元素数: {item['childrenCount']}, 首个文本: '{item['firstChildText']}'")
                print(f"      位置: ({item['position']['left']}, {item['position']['top']}), "
                      f"尺寸: {item['rect']}")
        else:
            print("    未找到导航/目录容器")
            # 输出所有可见的 ul/li 结构
            all_lists = await page.evaluate("""
                () => {
                    const uls = document.querySelectorAll('ul');
                    return Array.from(uls).filter(ul => {
                        const r = ul.getBoundingClientRect();
                        return r.width > 0 && r.height > 0;
                    }).slice(0, 20).map(ul => ({
                        tag: ul.tagName,
                        id: ul.id,
                        className: ul.className.substring(0, 100),
                        children: ul.children.length,
                        firstChild: ul.children[0] ? (ul.children[0].innerText || '').trim().substring(0, 60) : ''
                    }));
                }
            """)
            if all_lists:
                print(f"\n所有可见的 <ul> 列表 ({len(all_lists)} 个):")
                for i, item in enumerate(all_lists):
                    print(f"  [{i + 1}] id='{item['id']}' class='{item['className']}' "
                          f"子项={item['children']} 首个='{item['firstChild']}'")

        # ---------- 查找进度信息 ----------
        print("\n" + "-" * 80)
        print("【学习进度相关元素】")
        print("-" * 80)

        progress_analysis = await page.evaluate("""
            () => {
                const results = [];
                const progressKeywords = ['progress', 'percent', 'rate', 'ratio',
                                        '进度', '百分比', '率', '已完成', '未完成'];
                const allElements = document.querySelectorAll('*');
                const checked = new Set();

                for (const el of allElements) {
                    const id = el.id || '';
                    const className = el.className || '';
                    const tagName = el.tagName.toLowerCase();

                    if (['script', 'style', 'link', 'meta'].includes(tagName)) continue;

                    const text = (el.innerText || '').trim().substring(0, 100);
                    const idLower = id.toLowerCase();
                    const classLower = (typeof className === 'string' ? className : '').toLowerCase();
                    const textLower = text.toLowerCase();

                    let matched = false;
                    const matchInfo = [];

                    for (const kw of progressKeywords) {
                        const kwLower = kw.toLowerCase();
                        if (idLower.includes(kwLower)) { matched = true; matchInfo.push(`id含"${kw}"`); }
                        if (classLower.includes(kwLower)) { matched = true; matchInfo.push(`class含"${kw}"`); }
                        if (textLower.includes(kwLower) && text.length > 0 && text.length < 200) {
                            matched = true; matchInfo.push(`文本含"${kw}"`);
                        }
                    }

                    if (matched && !checked.has(el)) {
                        checked.add(el);
                        const rect = el.getBoundingClientRect();
                        results.push({
                            tag: tagName,
                            id: id.substring(0, 80),
                            className: (typeof className === 'string' ? className : '').substring(0, 100),
                            text: text.substring(0, 120),
                            match: matchInfo.join(', '),
                            rect: { w: Math.round(rect.width), h: Math.round(rect.height) }
                        });
                    }
                }
                return results.slice(0, 50);
            }
        """)

        if progress_analysis:
            print(f"\n找到 {len(progress_analysis)} 个与进度相关的元素:")
            for i, item in enumerate(progress_analysis):
                print(f"\n  [{i + 1}] <{item['tag']}> id='{item['id']}'")
                print(f"      class='{item['className']}'")
                print(f"      text='{item['text']}'")
                print(f"      match: {item['match']}")
        else:
            print("    未找到进度相关元素")

        # ---------- 查找按钮 ----------
        print("\n" + "-" * 80)
        print("【按钮元素分析】")
        print("-" * 80)

        button_analysis = await page.evaluate("""
            () => {
                const buttons = document.querySelectorAll('button, a[class*=btn], [class*=button], '
                    + '[class*=btn], [role=button], input[type=button], input[type=submit]');
                return Array.from(buttons).filter(btn => {
                    const r = btn.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                }).slice(0, 50).map(btn => ({
                    tag: btn.tagName.toLowerCase(),
                    id: btn.id || '',
                    className: (btn.className || '').substring(0, 100),
                    text: (btn.innerText || btn.value || '').trim().substring(0, 60),
                    rect: { w: Math.round(btn.getBoundingClientRect().width),
                           h: Math.round(btn.getBoundingClientRect().height) },
                    position: { top: Math.round(btn.getBoundingClientRect().top),
                               left: Math.round(btn.getBoundingClientRect().left) }
                }));
            }
        """)

        if button_analysis:
            print(f"\n找到 {len(button_analysis)} 个可见按钮:")
            for i, btn in enumerate(button_analysis):
                print(f"  [{i + 1}] <{btn['tag']}> text='{btn['text']}' "
                      f"id='{btn['id']}' class='{btn['className']}' "
                      f"pos=({btn['position']['left']},{btn['position']['top']}) "
                      f"size={btn['rect']}")
        else:
            print("    未找到按钮元素")

        # ---------- 查找 iframe ----------
        print("\n" + "-" * 80)
        print("【iframe/框架分析】")
        print("-" * 80)

        iframe_analysis = await page.evaluate("""
            () => {
                const iframes = document.querySelectorAll('iframe, frame');
                return Array.from(iframes).map(f => ({
                    tag: f.tagName.toLowerCase(),
                    id: f.id || '',
                    className: (f.className || '').substring(0, 80),
                    src: (f.src || '').substring(0, 200),
                    rect: f.getBoundingClientRect() ? {
                        w: Math.round(f.getBoundingClientRect().width),
                        h: Math.round(f.getBoundingClientRect().height)
                    } : null
                }));
            }
        """)

        if iframe_analysis:
            print(f"\n找到 {len(iframe_analysis)} 个 iframe:")
            for i, f in enumerate(iframe_analysis):
                print(f"  [{i + 1}] <{f['tag']}> id='{f['id']}' src='{f['src']}' size={f['rect']}")
        else:
            print("    未找到 iframe")

        # ---------- 视频播放器相关 ----------
        print("\n" + "-" * 80)
        print("【视频播放器相关元素】")
        print("-" * 80)

        video_analysis = await page.evaluate("""
            () => {
                const results = [];
                // 查找 video 标签
                const videos = document.querySelectorAll('video');
                videos.forEach(v => {
                    results.push({
                        tag: 'video',
                        id: v.id || '',
                        className: (v.className || '').substring(0, 80),
                        src: (v.src || '').substring(0, 200),
                        rect: { w: Math.round(v.getBoundingClientRect().width),
                               h: Math.round(v.getBoundingClientRect().height) }
                    });
                });

                // 查找包含视频相关 class/id 的元素
                const videoKeywords = ['video', 'player', 'media', '播放器', '视频', 'media'];
                const allEls = document.querySelectorAll('[class*=video], [class*=player], '
                    + '[class*=media], [id*=video], [id*=player], [id*=media]');
                allEls.forEach(el => {
                    const r = el.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0 && el.tagName.toLowerCase() !== 'video') {
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            id: el.id || '',
                            className: (el.className || '').substring(0, 80),
                            text: (el.innerText || '').trim().substring(0, 80),
                            rect: { w: Math.round(r.width), h: Math.round(r.height) }
                        });
                    }
                });

                return results.slice(0, 20);
            }
        """)

        if video_analysis:
            print(f"\n找到 {len(video_analysis)} 个视频相关元素:")
            for i, v in enumerate(video_analysis):
                print(f"  [{i + 1}] <{v['tag']}> id='{v['id']}' class='{v['className']}' "
                      f"size={v['rect']}")
                if v.get('src'):
                    print(f"      src='{v['src']}'")
                if v.get('text'):
                    print(f"      text='{v['text']}'")
        else:
            print("    未找到视频播放器相关元素")

        # ---------- "开始学习" / "继续学习" 按钮 ----------
        print("\n" + "-" * 80)
        print('【"开始学习/继续学习"等操作按钮】')
        print("-" * 80)

        action_analysis = await page.evaluate("""
            () => {
                const actionKeywords = ['开始学习', '继续学习', '开始', '继续', '进入学习',
                                     '学习', '播放', '观看', '查看', 'start', 'begin',
                                     'continue', 'play', 'learn', 'study'];
                const results = [];
                const allEls = document.querySelectorAll('*');
                const checked = new Set();

                for (const el of allEls) {
                    const text = (el.innerText || el.textContent || '').trim();
                    if (text.length > 0 && text.length < 50) {
                        for (const kw of actionKeywords) {
                            if (text.includes(kw)) {
                                if (!checked.has(el)) {
                                    checked.add(el);
                                    const rect = el.getBoundingClientRect();
                                    if (rect.width > 0 && rect.height > 0) {
                                        results.push({
                                            tag: el.tagName.toLowerCase(),
                                            id: el.id || '',
                                            className: (el.className || '').substring(0, 80),
                                            text: text,
                                            rect: { w: Math.round(rect.width), h: Math.round(rect.height) },
                                            position: { top: Math.round(rect.top),
                                                       left: Math.round(rect.left) }
                                        });
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }
                return results.slice(0, 30);
            }
        """)

        if action_analysis:
            print(f"\n找到 {len(action_analysis)} 个操作按钮:")
            for i, btn in enumerate(action_analysis):
                print(f"\n  [{i + 1}] <{btn['tag']}> text='{btn['text']}'")
                print(f"      id='{btn['id']}' class='{btn['className']}'")
                print(f"      位置: ({btn['position']['left']}, {btn['position']['top']}), "
                      f"尺寸: {btn['rect']}")
        else:
            print('    未找到"开始学习/继续学习"等操作按钮')

        # ---------- 查找 "未完成" 相关元素 ----------
        print("\n" + "-" * 80)
        print('【"未完成/进行中"状态标记】')
        print("-" * 80)

        status_analysis = await page.evaluate("""
            () => {
                const statusKeywords = ['未完成', '已完成', '进行中', '待学习', '已学完',
                                      '未开始', '进行', '完成', '待完成',
                                      'incomplete', 'complete', 'progress', 'finished',
                                      'pending', 'done', 'notstart'];
                const results = [];
                const allEls = document.querySelectorAll('*');
                const checked = new Set();

                for (const el of allEls) {
                    const text = (el.innerText || el.textContent || '').trim();
                    if (text.length > 0 && text.length < 80) {
                        for (const kw of statusKeywords) {
                            if (text.includes(kw) || text.toLowerCase().includes(kw.toLowerCase())) {
                                if (!checked.has(el)) {
                                    checked.add(el);
                                    const rect = el.getBoundingClientRect();
                                    if (rect.width > 0 && rect.height > 0) {
                                        results.push({
                                            tag: el.tagName.toLowerCase(),
                                            id: el.id || '',
                                            className: (el.className || '').substring(0, 80),
                                            text: text,
                                            rect: { w: Math.round(rect.width), h: Math.round(rect.height) }
                                        });
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }
                return results.slice(0, 30);
            }
        """)

        if status_analysis:
            print(f"\n找到 {len(status_analysis)} 个状态标记元素:")
            for i, item in enumerate(status_analysis):
                print(f"\n  [{i + 1}] <{item['tag']}> text='{item['text']}'")
                print(f"      id='{item['id']}' class='{item['className']}'")
                print(f"      尺寸: {item['rect']}")
        else:
            print('    未找到"未完成/已完成"状态标记')

        # ---------- 获取完整的 HTML 结构 (约定区域) ----------
        print("\n" + "-" * 80)
        print("【主要区域 HTML 结构】")
        print("-" * 80)

        # 获取 body 的子元素结构
        body_structure = await page.evaluate("""
            () => {
                function getStructure(el, depth = 0) {
                    if (depth > 4) return '';
                    const children = Array.from(el.children);
                    if (children.length === 0) return '';

                    let result = '';
                    const tagName = el.tagName.toLowerCase();
                    const id = el.id ? ` id="${el.id}"` : '';
                    const className = el.className && typeof el.className === 'string'
                        ? ` class="${el.className.substring(0, 60)}"` : '';

                    result += `${'  '.repeat(depth)}<${tagName}${id}${className}> (${children.length} children)\\n`;

                    for (const child of children.slice(0, 8)) {
                        const childTag = child.tagName.toLowerCase();
                        const childId = child.id ? ` id="${child.id}"` : '';
                        const childClass = child.className && typeof child.className === 'string'
                            ? ` class="${child.className.substring(0, 40)}"` : '';
                        const childText = (child.innerText || '').trim().substring(0, 40);
                        const hasMore = child.children.length > 0;

                        if (hasMore) {
                            result += getStructure(child, depth + 1);
                        } else {
                            result += `${'  '.repeat(depth + 1)}<${childTag}${childId}${childClass}>`;
                            if (childText) result += ` "${childText}"`;
                            result += '\\n';
                        }
                    }

                    if (el.children.length > 8) {
                        result += `${'  '.repeat(depth + 1)}... 还有 ${el.children.length - 8} 个子元素\\n`;
                    }

                    return result;
                }

                const body = document.body;
                let output = '';
                const mainContainers = ['main', 'section', 'article', 'div.container',
                    'div.content', 'div.wrapper', 'div.app', '#app', '#root'];

                // 先显示 body 的直接子元素
                output += '=== body 直接子元素 ===\\n';
                for (const child of body.children) {
                    const tag = child.tagName.toLowerCase();
                    const id = child.id ? ` id="${child.id}"` : '';
                    const cls = child.className && typeof child.className === 'string'
                        ? ` class="${child.className.substring(0, 80)}"` : '';
                    const text = (child.innerText || '').trim().substring(0, 60);
                    output += `  <${tag}${id}${cls}> "${text}"\\n`;
                }

                return output;
            }
        """)

        print(f"\n{body_structure}")

        # ---------- 保存完整 HTML ----------
        print("\n" + "-" * 80)
        print("【保存完整页面 HTML (去除 script)】")
        print("-" * 80)

        full_html = await page.evaluate("""
            () => {
                const clone = document.documentElement.cloneNode(true);
                const scripts = clone.querySelectorAll('script');
                scripts.forEach(s => s.remove());
                return clone.outerHTML.substring(0, 50000);
            }
        """)

        with open("course_page_structure.html", "w", encoding="utf-8") as f:
            f.write(full_html)
        print(f"HTML 已保存到 course_page_structure.html (前 50000 字符)")

        # ---------- 获取所有 CSS 类名 ----------
        print("\n" + "-" * 80)
        print("【页面使用的关键 CSS 类名】")
        print("-" * 80)

        css_classes = await page.evaluate("""
            () => {
                const classes = new Set();
                const allEls = document.querySelectorAll('[class]');
                allEls.forEach(el => {
                    const cls = el.className;
                    if (typeof cls === 'string') {
                        cls.split(/\\s+/).forEach(c => {
                            if (c.length > 2) classes.add(c);
                        });
                    }
                });
                return Array.from(classes).sort().slice(0, 100);
            }
        """)

        if css_classes:
            print(f"\n共 {len(css_classes)} 个 CSS 类名:")
            # 分组显示
            for i in range(0, len(css_classes), 10):
                group = css_classes[i:i + 10]
                print(f"  {'  '.join(group)}")
        else:
            print("    未找到 CSS 类名")

        # ---------- 等待用户查看 ----------
        print("\n" + "=" * 80)
        print("页面分析完成! 请在浏览器中查看页面内容。")
        print("截图文件: 01_login_page.png, 02_after_login.png, 03_course_page.png")
        print("HTML 文件: course_page_structure.html")
        print("=" * 80)

        # 保持浏览器打开，让用户查看
        print("\n浏览器将保持打开状态 30 秒供您查看...")
        await asyncio.sleep(30)

        await browser.close()
        print("浏览器已关闭。")


if __name__ == "__main__":
    asyncio.run(main())
