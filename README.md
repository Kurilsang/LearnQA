# LearnQA

使用 Playwright 实现教育平台页面自动化遍历与功能校验的 UI 自动化测试框架。

## 项目结构

```
LearnQA/
├── config.py              # 配置管理
├── run_tests.py           # 一键运行入口
├── pages/                 # Page Object Model
│   ├── login_page.py      # 登录页
│   ├── course_page.py     # 课程页
│   └── content_page.py    # 内容页
├── tests/                 # 测试用例
│   ├── test_login.py
│   ├── test_course_navigation.py
│   └── test_content_playback.py
└── utils/
    ├── logger.py           # 日志
    └── reporter.py         # HTML 测试报告 + AI 分析输出
```

## 快速开始

```bash
pip install -r requirements.txt
```

在 `.env` 中配置账号密码：

```ini
FIF_USERNAME=your_username
FIF_PASSWORD=your_password
```

运行测试：

```bash
python run_tests.py
# 或
pytest tests/ -v
```

## 运行方式

- **`python run_tests.py`** - 全量执行并生成 HTML 报告（含 AI 智能分析）
- **`pytest tests/ -v`** - 按需执行单个测试文件

测试报告输出至 `reports/latest.html`。

## 功能特性

- 登录、课程导航、内容播放全链路校验
- 自动捕获页面异常与接口报错
- HTML 测试报告，失败自动截图
- AI 智能分析测试结果（接入 DeepSeek）
