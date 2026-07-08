import asyncio
import os
from datetime import datetime

import pytest_asyncio
from playwright.async_api import async_playwright

from config import config
from pages.login_page import LoginPage
from pages.course_page import CoursePage
from pages.content_page import ContentPage
from utils.logger import TestLogger
from core.api_client import ApiClient
from apis.auth_api import AuthAPI
from apis.course_api import CourseAPI
from apis.content_api import ContentAPI

site_config = config.SITE_CONFIG

logger = TestLogger()


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def browser_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=config.HEADLESS,
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
            yield page
        finally:
            await browser.close()


@pytest_asyncio.fixture(scope="function")
async def login_page(browser_page):
    return LoginPage(browser_page, site_config)


@pytest_asyncio.fixture(scope="function")
async def course_page(browser_page):
    return CoursePage(browser_page, site_config)


@pytest_asyncio.fixture(scope="function")
async def content_page(browser_page):
    return ContentPage(browser_page, site_config)


@pytest_asyncio.fixture(scope="function")
async def authenticated_page(browser_page, login_page):
    logger.step("前置条件: 登录系统")
    await login_page.navigate(config.BASE_URL)
    success = await login_page.do_login(config.USERNAME, config.PASSWORD, config.COURSE_URL)
    assert success, "登录失败，无法继续后续测试"
    logger.assertion("用户登录", success)
    return browser_page


@pytest_asyncio.fixture(scope="session")
async def api_client():
    base_url = site_config.get_api_base_url()
    client = ApiClient(base_url=base_url, timeout=30.0, max_retries=2, logger=logger)
    await client.start()
    yield client
    await client.stop()


@pytest_asyncio.fixture(scope="function")
async def auth_api(api_client):
    return AuthAPI(api_client, site_config)


@pytest_asyncio.fixture(scope="function")
async def course_api(api_client):
    return CourseAPI(api_client, site_config)


@pytest_asyncio.fixture(scope="function")
async def content_api(api_client):
    return ContentAPI(api_client, site_config)
