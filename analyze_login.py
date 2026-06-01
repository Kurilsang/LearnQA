"""
登录页面结构分析脚本
分析 fifedu.com 登录页面的 DOM 结构，提取各元素详细信息
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def analyze_page():
    async with async_playwright() as p:
        # 启动浏览器（非无头模式，方便观察）
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("=" * 70)
        print("🌐 正在访问登录页面...")
        print("=" * 70)

        await page.goto(
            "https://www.fifedu.com/iplat/fifLogin/index.html?v=5.4.4",
            wait_until="networkidle",
            timeout=60000
        )

        # 等待页面充分加载
        print("⏳ 等待页面加载 (5秒)...")
        await page.wait_for_timeout(5000)

        # 检查是否有 iframe
        print("\n📋 检查页面框架结构...")
        frames = page.frames
        print(f"   - 检测到 {len(frames)} 个 frame")

        # 截取页面截图
        await page.screenshot(path="d:\\Develop\\Projects\\作业区\\数据挖掘\\自动刷课\\login_page.png", full_page=True)
        print("   - 已保存页面截图: login_page.png")

        # =========================================================
        # 1. 分析账号输入框
        # =========================================================
        print("\n" + "=" * 70)
        print("🔍 分析登录表单元素...")
        print("=" * 70)

        # 使用 JavaScript 获取所有输入框的详细信息
        input_analysis = await page.evaluate("""
            () => {
                const inputs = document.querySelectorAll('input');
                const results = [];
                inputs.forEach((el, index) => {
                    const rect = el.getBoundingClientRect();
                    const info = {
                        index: index,
                        tagName: el.tagName,
                        type: el.type,
                        id: el.id || '',
                        name: el.name || '',
                        className: el.className || '',
                        placeholder: el.placeholder || '',
                        autocomplete: el.autocomplete || '',
                        maxlength: el.maxLength || '',
                        // CSS 选择器
                        selectors: {
                            byId: el.id ? `#${el.id}` : null,
                            byName: el.name ? `input[name="${el.name}"]` : null,
                            byClass: el.className ? `input.${el.className.trim().split(/\\s+/).join('.')}` : null,
                            byPlaceholder: el.placeholder ? `input[placeholder="${el.placeholder}"]` : null,
                            byType: `input[type="${el.type}"]`
                        },
                        position: {
                            x: Math.round(rect.x),
                            y: Math.round(rect.y),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height)
                        },
                        isVisible: rect.width > 0 && rect.height > 0,
                        parent: {
                            tag: el.parentElement ? el.parentElement.tagName : '',
                            id: el.parentElement ? el.parentElement.id : '',
                            class: el.parentElement ? el.parentElement.className : ''
                        },
                        attributes: {}
                    };
                    // 获取所有属性
                    for (let i = 0; i < el.attributes.length; i++) {
                        const attr = el.attributes[i];
                        info.attributes[attr.name] = attr.value;
                    }
                    results.push(info);
                });
                return results;
            }
        """)

        # 2. 分析按钮
        button_analysis = await page.evaluate("""
            () => {
                const buttons = document.querySelectorAll('button, a.btn, input[type="submit"], div[class*="btn"], div[class*="login"], a[class*="login"]');
                const results = [];
                buttons.forEach((el, index) => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) return;
                    const info = {
                        index: index,
                        tagName: el.tagName,
                        id: el.id || '',
                        className: el.className || '',
                        text: (el.textContent || '').trim().substring(0, 50),
                        type: el.type || '',
                        selectors: {
                            byId: el.id ? `#${el.id}` : null,
                            byClass: el.className ? `${el.tagName.toLowerCase()}.${el.className.trim().split(/\\s+/).join('.')}` : null,
                            byText: el.textContent ? `text="${el.textContent.trim()}"` : null
                        },
                        position: {
                            x: Math.round(rect.x),
                            y: Math.round(rect.y),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height)
                        },
                        isVisible: true,
                        attributes: {}
                    };
                    for (let i = 0; i < el.attributes.length; i++) {
                        const attr = el.attributes[i];
                        info.attributes[attr.name] = attr.value;
                    }
                    results.push(info);
                });
                return results;
            }
        """)

        # 3. 检查验证码相关元素
        captcha_analysis = await page.evaluate("""
            () => {
                const results = {};
                // 查找验证码图片
                const imgs = document.querySelectorAll('img[src*="captcha"], img[src*="code"], img[src*="verify"], img[class*="captcha"], img[class*="code"], img[id*="captcha"], img[id*="code"]');
                results.captchaImages = Array.from(imgs).map(img => ({
                    src: img.src,
                    id: img.id,
                    className: img.className,
                    alt: img.alt
                }));

                // 查找验证码输入框
                const captchaInputs = document.querySelectorAll('input[placeholder*="验证"], input[placeholder*="验证码"], input[id*="captcha"], input[id*="code"], input[name*="captcha"], input[name*="code"]');
                results.captchaInputs = Array.from(captchaInputs).map(el => ({
                    id: el.id,
                    name: el.name,
                    className: el.className,
                    placeholder: el.placeholder
                }));

                // 查找所有包含"验证"的元素
                const verifyTexts = [];
                const allEls = document.querySelectorAll('*');
                allEls.forEach(el => {
                    if (el.children.length === 0 && el.textContent && 
                        (el.textContent.includes('验证') || el.textContent.includes('captcha'))) {
                        verifyTexts.push(el.textContent.trim().substring(0, 30));
                    }
                });
                results.verifyTexts = verifyTexts;

                return results;
            }
        """)

        # 4. 获取 iframe 详细信息
        iframe_analysis = await page.evaluate("""
            () => {
                const iframes = document.querySelectorAll('iframe');
                return Array.from(iframes).map(iframe => ({
                    id: iframe.id || '',
                    name: iframe.name || '',
                    className: iframe.className || '',
                    src: iframe.src || '',
                    width: iframe.width || '',
                    height: iframe.height || ''
                }));
            }
        """)

        # 5. 获取整个登录表单区域的 HTML
        form_html = await page.evaluate("""
            () => {
                // 尝试找登录表单容器
                const possibleContainers = [
                    'form', 
                    '.login-form', 
                    '#loginForm', 
                    '.login-box', 
                    '.login-container',
                    '.login-wrap',
                    '.login-main',
                    '[class*="login"]'
                ];
                
                let bestContainer = null;
                for (const sel of possibleContainers) {
                    const el = document.querySelector(sel);
                    if (el) {
                        bestContainer = {
                            selector: sel,
                            id: el.id || '',
                            class: el.className || '',
                            tag: el.tagName,
                            innerHTML: el.innerHTML.substring(0, 3000)
                        };
                        break;
                    }
                }
                return bestContainer;
            }
        """)

        # 6. 获取完整的 body HTML（不含 script）
        body_html = ""
        try:
            body_html = await page.evaluate("""
                () => {
                    const clone = document.body.cloneNode(true);
                    const scripts = clone.querySelectorAll('script');
                    scripts.forEach(s => s.remove());
                    return clone.innerHTML.substring(0, 5000);
                }
            """)
        except Exception:
            pass

        # =========================================================
        # 输出分析结果
        # =========================================================
        print("\n" + "★" * 35 + " 分析结果 " + "★" * 35)

        print("\n" + "-" * 70)
        print("📌 页面框架信息")
        print("-" * 70)
        print(f"   页面 URL: {page.url}")
        print(f"   页面标题: {await page.title()}")
        print(f"   Frame 数量: {len(frames)}")
        for i, f in enumerate(frames):
            print(f"     - Frame[{i}]: url={f.url[:80]}...")

        if iframe_analysis:
            print(f"\n   iframe 详情:")
            for ifr in iframe_analysis:
                print(f"     - id: '{ifr['id']}', name: '{ifr['name']}', src: '{ifr['src']}'")

        print("\n" + "-" * 70)
        print("📌 输入框分析")
        print("-" * 70)
        for inp in input_analysis:
            if not inp['isVisible']:
                continue
            print(f"\n   [{inp['index']}] 输入框 (type={inp['type']})")
            print(f"       id:          '{inp['id']}'")
            print(f"       name:        '{inp['name']}'")
            print(f"       className:   '{inp['className']}'")
            print(f"       placeholder: '{inp['placeholder']}'")
            print(f"       位置:        ({inp['position']['x']}, {inp['position']['y']}), 大小: {inp['position']['width']}x{inp['position']['height']}")
            print(f"       可用 CSS 选择器:")
            for sel_type, sel_value in inp['selectors'].items():
                if sel_value:
                    print(f"         - {sel_type}: {sel_value}")
            print(f"       父元素: <{inp['parent']['tag']}> id='{inp['parent']['id']}' class='{inp['parent']['class']}'")
            print(f"       所有属性: {json.dumps(inp['attributes'], ensure_ascii=False)}")

        print("\n" + "-" * 70)
        print("📌 按钮分析")
        print("-" * 70)
        for btn in button_analysis:
            print(f"\n   [{btn['index']}] 按钮 ({btn['tagName']})")
            print(f"       id:        '{btn['id']}'")
            print(f"       className: '{btn['className']}'")
            print(f"       text:      '{btn['text']}'")
            print(f"       位置:      ({btn['position']['x']}, {btn['position']['y']}), 大小: {btn['position']['width']}x{btn['position']['height']}")
            print(f"       可用 CSS 选择器:")
            for sel_type, sel_value in btn['selectors'].items():
                if sel_value:
                    print(f"         - {sel_type}: {sel_value}")
            print(f"       所有属性: {json.dumps(btn['attributes'], ensure_ascii=False)}")

        print("\n" + "-" * 70)
        print("📌 验证码检查")
        print("-" * 70)
        captcha = captcha_analysis
        if captcha['captchaImages']:
            print(f"   ⚠️ 检测到验证码图片:")
            for img in captcha['captchaImages']:
                print(f"     - id: '{img['id']}', src: '{img['src']}'")
        else:
            print(f"   ✅ 未检测到验证码图片")

        if captcha['captchaInputs']:
            print(f"   ⚠️ 检测到验证码输入框:")
            for ci in captcha['captchaInputs']:
                print(f"     - id: '{ci['id']}', placeholder: '{ci['placeholder']}'")
        else:
            print(f"   ✅ 未检测到验证码输入框")

        if captcha['verifyTexts']:
            print(f"   页面包含验证相关文本: {captcha['verifyTexts']}")

        # =========================================================
        # 尝试填入账号密码（不点击登录）
        # =========================================================
        print("\n" + "=" * 70)
        print("🔑 尝试填入账号密码（不点击登录）...")
        print("=" * 70)

        username = "gduf231543223"
        password = "gduf231543223"

        # 找到账号和密码输入框
        username_input = None
        password_input = None

        for inp in input_analysis:
            if not inp['isVisible']:
                continue
            # 判断是账号框（type=text/email/tel 或包含 user/name/account/phone）
            if inp['type'] in ['text', 'email', 'tel', 'search', 'number'] or \
               any(kw in inp['id'].lower() + inp['name'].lower() + inp['placeholder'].lower() 
                   for kw in ['user', 'name', 'account', 'phone', 'mobile', '学号', '账号', '用户名']):
                username_input = inp
                break

        for inp in input_analysis:
            if not inp['isVisible']:
                continue
            if inp['type'] == 'password' or \
               any(kw in inp['id'].lower() + inp['name'].lower() + inp['placeholder'].lower() 
                   for kw in ['pass', 'pwd', '密码', '口令']):
                password_input = inp
                break

        # 如果没找到，用更简单的方法：type=text 的是账号，type=password 的是密码
        if not username_input:
            for inp in input_analysis:
                if inp['isVisible'] and inp['type'] == 'text':
                    username_input = inp
                    break
        
        if not password_input:
            for inp in input_analysis:
                if inp['isVisible'] and inp['type'] == 'password':
                    password_input = inp
                    break

        # 根据分析结果，使用多种选择器尝试
        if username_input:
            # 构建多级备选选择器
            selectors_to_try = []
            if username_input['id']:
                selectors_to_try.append(f"#{username_input['id']}")
            if username_input['name']:
                selectors_to_try.append(f"input[name='{username_input['name']}']")
            if username_input['placeholder']:
                selectors_to_try.append(f"input[placeholder='{username_input['placeholder']}']")
            selectors_to_try.append(f"input[type='{username_input['type']}']")

            filled = False
            for sel in selectors_to_try:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        await el.fill(username)
                        print(f"   ✅ 账号已填入 (使用选择器: {sel})")
                        filled = True
                        break
                except Exception:
                    continue
            
            if not filled:
                # 尝试直接通过 evaluate 设置
                await page.evaluate(f"""
                    () => {{
                        const inputs = document.querySelectorAll('input');
                        for (const inp of inputs) {{
                            if (inp.type === 'text' || inp.type === 'email' || inp.type === 'tel') {{
                                inp.value = '{username}';
                                inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                break;
                            }}
                        }}
                    }}
                """)
                print(f"   ⚠️ 通过 JS 填入账号: {username}")
        else:
            print("   ❌ 未找到账号输入框")

        if password_input:
            selectors_to_try = []
            if password_input['id']:
                selectors_to_try.append(f"#{password_input['id']}")
            if password_input['name']:
                selectors_to_try.append(f"input[name='{password_input['name']}']")
            if password_input['placeholder']:
                selectors_to_try.append(f"input[placeholder='{password_input['placeholder']}']")
            selectors_to_try.append("input[type='password']")

            filled = False
            for sel in selectors_to_try:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        await el.fill(password)
                        print(f"   ✅ 密码已填入 (使用选择器: {sel})")
                        filled = True
                        break
                except Exception:
                    continue
            
            if not filled:
                await page.evaluate(f"""
                    () => {{
                        const inputs = document.querySelectorAll('input');
                        for (const inp of inputs) {{
                            if (inp.type === 'password') {{
                                inp.value = '{password}';
                                inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                break;
                            }}
                        }}
                    }}
                """)
                print(f"   ⚠️ 通过 JS 填入密码: {password}")
        else:
            print("   ❌ 未找到密码输入框")

        # 填入后截图
        await page.wait_for_timeout(1000)
        await page.screenshot(path="d:\\Develop\\Projects\\作业区\\数据挖掘\\自动刷课\\login_filled.png", full_page=True)
        print("\n   📸 已保存填入后的截图: login_filled.png")

        # 显示最终页面状态
        print("\n" + "=" * 70)
        print("📋 最终页面输入框状态")
        print("=" * 70)
        final_state = await page.evaluate("""
            () => {
                const inputs = document.querySelectorAll('input');
                return Array.from(inputs).map(inp => ({
                    id: inp.id,
                    type: inp.type,
                    value: inp.value.substring(0, 20),
                    placeholder: inp.placeholder
                }));
            }
        """)
        for st in final_state:
            if st['type'] != 'hidden':
                print(f"   input[type={st['type']}] id='{st['id']}': value='{st['value']}' placeholder='{st['placeholder']}'")

        print("\n" + "★" * 35 + " 分析完成 " + "★" * 35)
        print("\n⚠️  注意：未点击登录按钮，账号密码仅填入用于验证选择器是否正确")

        # 保持浏览器打开 15 秒供观察
        print("\n⏳ 浏览器将保持 15 秒供观察...")
        await page.wait_for_timeout(15000)

        await browser.close()
        print("\n✅ 浏览器已关闭")


if __name__ == "__main__":
    asyncio.run(analyze_page())
