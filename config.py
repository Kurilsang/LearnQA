import os
from dotenv import load_dotenv

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_env_path = os.path.join(_SCRIPT_DIR, ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)


def env(key: str, default=None):
    return os.environ.get(key, default)


class Config:
    BASE_URL = env("LOGIN_URL", "https://www.fifedu.com/iplat/fifLogin/index.html?v=5.4.4")
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

    PPTX_PAGE_INTERVAL = float(env("PPTX_PAGE_INTERVAL", "1.5"))
    SCROLL_STEP_DELAY = float(env("SCROLL_STEP_DELAY", "0.5"))
    VIDEO_MAX_WAIT = int(env("VIDEO_MAX_WAIT", "2000"))

    SCREENSHOT_DIR = os.path.join(_SCRIPT_DIR, "screenshots")
    REPORT_DIR = os.path.join(_SCRIPT_DIR, "reports")


config = Config()
