import os
import importlib
from dotenv import load_dotenv

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_env_path = os.path.join(_SCRIPT_DIR, ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)


def env(key: str, default=None):
    return os.environ.get(key, default)


# ============================================================
# 站点配置加载
# ============================================================
# 修改 SITE_NAME 即可切换目标站点（例如 "fifedu", "chaoxing" 等）
# 站点配置位于 sites/{SITE_NAME}/ 目录下
SITE_NAME = env("SITE_NAME", "fifedu")

_site_module_path = f"sites.{SITE_NAME}"
_site_module = importlib.import_module(_site_module_path)

# 站点配置实例，包含 selectors、handlers、default_params 等
SITE_CONFIG = _site_module.site_config


# ============================================================
# 通用配置（所有站点共享）
# ============================================================
class Config:
    # 站点特定值优先从站点 config 获取，fallback 到环境变量
    BASE_URL = env("LOGIN_URL", SITE_CONFIG.get_page_url("login_page") or "")
    COURSE_URL = env("COURSE_URL", (
        "https://icourse.fifedu.com/istp-learning-center/"
        "index?courseId=0bbe8331f3ae41d4ade3618c31e5c0d9"
        "&classId=2811000226001709298&termId=0ebfcb74812d4e5ab9f8f1919a341d97"
    ))
    USERNAME = env("FIF_USERNAME", "")
    PASSWORD = env("FIF_PASSWORD", "")
    HEADLESS = env("HEADLESS", "false").lower() == "true"
    TIMEOUT = int(env("TIMEOUT", "30000"))
    MAX_CHAPTERS = int(env("MAX_CHAPTERS", "100"))

    AI_API_BASE = env("AI_API_BASE", "https://api.deepseek.com")
    AI_API_KEY = env("AI_API_KEY", "")
    AI_MODEL = env("AI_MODEL", "deepseek-chat")
    AI_TEMPERATURE = float(env("AI_TEMPERATURE", "0.1"))

    PPTX_PAGE_INTERVAL = float(
        env("PPTX_PAGE_INTERVAL",
            str(SITE_CONFIG.default_params.get("pptx_page_interval", 1.5)))
    )
    SCROLL_STEP_DELAY = float(
        env("SCROLL_STEP_DELAY",
            str(SITE_CONFIG.default_params.get("scroll_step_delay", 0.5)))
    )
    VIDEO_MAX_WAIT = int(
        env("VIDEO_MAX_WAIT",
            str(SITE_CONFIG.default_params.get("video_max_wait", 2000)))
    )

    SCREENSHOT_DIR = os.path.join(_SCRIPT_DIR, "screenshots")
    REPORT_DIR = os.path.join(_SCRIPT_DIR, "reports")


config = Config()
config.SITE_CONFIG = SITE_CONFIG
