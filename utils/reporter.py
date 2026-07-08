import os
from datetime import datetime


AI_SECTION_TEMPLATE = """
<div class="ai-analysis">
<div class="ai-header" onclick="const b=this.nextElementSibling;b.style.display=b.style.display==='none'?'':'none'">
<span class="ai-icon">AI</span>
<span class="ai-title">AI 智能分析报告</span>
<span class="ai-toggle">收起</span>
</div>
<div class="ai-body">
{content}
</div>
</div>"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; color: #333; padding: 20px; }}
.header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; padding: 30px; border-radius: 12px; margin-bottom: 24px; }}
.header h1 {{ font-size: 24px; margin-bottom: 8px; }}
.header .meta {{ font-size: 14px; opacity: 0.9; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 24px; }}
.summary-item {{ background: #fff; border-radius: 10px; padding: 20px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
.summary-item .num {{ font-size: 36px; font-weight: 700; }}
.summary-item .label {{ font-size: 13px; color: #888; margin-top: 4px; }}
.summary-item.pass .num {{ color: #52c41a; }}
.summary-item.fail .num {{ color: #ff4d4f; }}
.summary-item.skip .num {{ color: #faad14; }}
.summary-item.total .num {{ color: #667eea; }}
.ai-analysis {{ background: #fff; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); overflow: hidden; border: 1px solid #e8e8e8; }}
.ai-header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #e0e0e0; padding: 16px 20px; cursor: pointer; display: flex; align-items: center; gap: 12px; user-select: none; }}
.ai-header:hover {{ opacity: 0.95; }}
.ai-icon {{ background: #0f3460; color: #e94560; font-weight: 700; font-size: 13px; padding: 4px 10px; border-radius: 6px; letter-spacing: 1px; }}
.ai-title {{ font-size: 16px; font-weight: 600; color: #fff; flex: 1; }}
.ai-toggle {{ font-size: 12px; color: #888; }}
.ai-body {{ padding: 20px; line-height: 1.8; font-size: 14px; }}
.ai-body h3 {{ font-size: 15px; color: #1a1a2e; margin: 16px 0 8px; padding-left: 12px; border-left: 3px solid #667eea; }}
.ai-body h3:first-child {{ margin-top: 0; }}
.ai-body p {{ margin: 6px 0; color: #444; }}
.ai-body ul {{ margin: 6px 0 6px 20px; color: #555; }}
.ai-body li {{ margin: 4px 0; }}
.ai-body .highlight {{ background: #f0f5ff; border-left: 3px solid #667eea; padding: 10px 16px; margin: 10px 0; border-radius: 4px; font-size: 13px; }}
.ai-body .risk-low {{ color: #52c41a; font-weight: 600; }}
.ai-body .risk-mid {{ color: #faad14; font-weight: 600; }}
.ai-body .risk-high {{ color: #ff4d4f; font-weight: 600; }}
.test-suite {{ background: #fff; border-radius: 10px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); overflow: hidden; }}
.suite-header {{ padding: 16px 20px; cursor: pointer; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #f0f0f0; }}
.suite-header:hover {{ background: #fafafa; }}
.suite-name {{ font-size: 16px; font-weight: 600; }}
.suite-status {{ font-size: 12px; padding: 2px 10px; border-radius: 10px; }}
.suite-status.pass {{ background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }}
.suite-status.fail {{ background: #fff2f0; color: #ff4d4f; border: 1px solid #ffccc7; }}
.suite-status.error {{ background: #fff7e6; color: #fa8c16; border: 1px solid #ffd591; }}
.suite-body {{ padding: 0 20px 16px; }}
.test-case {{ padding: 12px 0; border-bottom: 1px solid #f5f5f5; }}
.test-case:last-child {{ border-bottom: none; }}
.test-case .case-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }}
.test-case .case-name {{ font-size: 14px; font-weight: 500; }}
.test-case .case-status {{ font-size: 11px; padding: 1px 8px; border-radius: 8px; }}
.test-case .case-status.PASS {{ background: #f6ffed; color: #52c41a; }}
.test-case .case-status.FAIL {{ background: #fff2f0; color: #ff4d4f; }}
.test-case .case-status.ERROR {{ background: #fff7e6; color: #fa8c16; }}
.test-case .case-status.SKIP {{ background: #fffbe6; color: #faad14; }}
.test-case .case-time {{ font-size: 12px; color: #aaa; margin-left: auto; }}
.test-case .case-detail {{ font-size: 13px; color: #666; margin-left: 20px; padding: 4px 0; }}
.test-case .case-detail.error {{ color: #ff4d4f; }}
.test-case .case-screenshot {{ margin: 8px 0 8px 20px; }}
.test-case .case-screenshot img {{ max-width: 100%; max-height: 300px; border: 1px solid #e8e8e8; border-radius: 6px; }}
.steps {{ margin-top: 8px; margin-left: 20px; }}
.step {{ font-size: 12px; padding: 2px 0; color: #888; }}
.step.INFO {{ color: #1890ff; }}
.step.WARN {{ color: #faad14; }}
.step.ERROR {{ color: #ff4d4f; }}
.step.ASSERT {{ color: #333; }}
.step.PASS {{ color: #52c41a; }}
.step.FAIL {{ color: #ff4d4f; }}
.footer {{ text-align: center; padding: 20px; color: #aaa; font-size: 13px; }}
</style>
</head>
<body>
<div class="header">
<h1>{title}</h1>
<div class="meta">测试时间: {start_time} | 运行环境: {environment}</div>
</div>
<div class="summary">
<div class="summary-item total"><div class="num">{total}</div><div class="label">总用例</div></div>
<div class="summary-item pass"><div class="num">{passed}</div><div class="label">通过</div></div>
<div class="summary-item fail"><div class="num">{failed}</div><div class="label">失败</div></div>
<div class="summary-item skip"><div class="num">{skipped}</div><div class="label">跳过</div></div>
</div>
{ai_section}
{suites}
<div class="footer">报告生成时间: {report_time}</div>
</body>
</html>"""


class TestReport:
    def __init__(self):
        self.suites = []
        self.ai_analysis = ""
        self.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def add_suite(self, suite_name: str):
        suite = TestSuite(suite_name)
        self.suites.append(suite)
        return suite

    def set_ai_analysis(self, analysis: str):
        self.ai_analysis = analysis

    def generate(self, report_dir: str, title: str = "自动化测试报告") -> str:
        total = sum(s.total for s in self.suites)
        passed = sum(s.passed for s in self.suites)
        failed = sum(s.failed for s in self.suites)
        skipped = sum(s.skipped for s in self.suites)

        suites_html = "\n".join(s.to_html() for s in self.suites)

        ai_html = ""
        if self.ai_analysis:
            content = self.ai_analysis.replace("\n", "<br>")
            content = content.replace("### ", "<h3>").replace("\n\n", "</p><p>").replace("<br><br>", "</p><p>")
            content = content.replace("<h3>", "</p><h3>")
            content = f"<p>{content}</p>"
            content = content.replace("</p><p>", "\n")
            ai_html = AI_SECTION_TEMPLATE.format(content=content)

        html = HTML_TEMPLATE.format(
            title=title,
            start_time=self.start_time,
            environment=f"Python | Playwright | {os.name}",
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            ai_section=ai_html,
            suites=suites_html,
            report_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        os.makedirs(report_dir, exist_ok=True)
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(report_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        latest = os.path.join(report_dir, "latest.html")
        with open(latest, "w", encoding="utf-8") as f:
            f.write(html)

        return filepath


class TestSuite:
    def __init__(self, name: str):
        self.name = name
        self.cases = []

    def add_case(self, case_name: str, status: str, duration: float = 0,
                 error: str = "", screenshot: str = "", steps: list = None):
        self.cases.append({
            "name": case_name, "status": status, "duration": duration,
            "error": error, "screenshot": screenshot, "steps": steps or [],
        })

    @property
    def total(self):
        return len(self.cases)

    @property
    def passed(self):
        return sum(1 for c in self.cases if c["status"] == "PASS")

    @property
    def failed(self):
        return sum(1 for c in self.cases if c["status"] == "FAIL")

    @property
    def skipped(self):
        return sum(1 for c in self.cases if c["status"] == "SKIP")

    @property
    def status(self):
        if self.failed > 0:
            return "fail"
        if self.skipped > 0:
            return "error"
        return "pass"

    def to_html(self) -> str:
        cases_html = ""
        for c in self.cases:
            steps_html = ""
            for s in c["steps"]:
                if len(s) == 2:
                    level, msg = s
                    steps_html += f'<div class="step {level}">[{level}] {msg}</div>'
                elif len(s) == 3:
                    level, msg, result = s
                    cls = "PASS" if result else "FAIL"
                    steps_html += f'<div class="step {cls}">[{"✓" if result else "✗"}] {msg}</div>'

            screenshot_html = ""
            if c["screenshot"]:
                rel = os.path.relpath(c["screenshot"], start=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                screenshot_html = f'<div class="case-screenshot"><img src="../{rel}" alt="screenshot"></div>'

            error_html = ""
            if c["error"]:
                error_html = f'<div class="case-detail error">{c["error"]}</div>'

            cases_html += f"""
<div class="test-case">
<div class="case-header">
<span class="case-status {c['status']}">{c['status']}</span>
<span class="case-name">{c['name']}</span>
<span class="case-time">{c['duration']:.1f}s</span>
</div>
{error_html}
{screenshot_html}
<div class="steps">{steps_html}</div>
</div>"""

        return f"""
<div class="test-suite">
<div class="suite-header" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'':'none'">
<span class="suite-name">{self.name}</span>
<span class="suite-status {self.status}">{self.passed}/{self.total} 通过</span>
</div>
<div class="suite-body">{cases_html}</div>
</div>"""
