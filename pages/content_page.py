import asyncio
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from core.base_page import BasePage
from core.registry import registry
from utils.logger import TestLogger

logger = TestLogger()


def _make_params(**extra):
    params = dict(extra)
    params["log_cb"] = lambda msg: logger.step(msg)
    return params


class ContentPage(BasePage):
    page_key = "content_page"

    async def process_pptx(self) -> bool:
        logger.step("处理 PPTX 资源 - 翻页校验")
        params = _make_params(site_config=self.site)
        if self.site:
            params.update(self.site.default_params)
        return await registry.execute("process_pptx", self.page, params) if registry.has("process_pptx") else False

    async def process_html_pdf(self, resource_idx: int = None) -> bool:
        logger.step("处理 HTML/PDF 资源 - 滚动加载校验")
        params = _make_params(resource_idx=resource_idx, site_config=self.site)
        if self.site:
            params.update(self.site.default_params)
        return await registry.execute("process_html_pdf", self.page, params) if registry.has("process_html_pdf") else False

    async def process_video(self) -> bool:
        logger.step("处理视频资源 - 播放校验")
        params = _make_params(site_config=self.site)
        if self.site:
            params.update(self.site.default_params)
        return await registry.execute("process_video", self.page, params) if registry.has("process_video") else False

    async def process_adaptive(self) -> bool:
        logger.step("处理自适应训练 - 答题流程校验")
        params = _make_params(site_config=self.site)
        if self.site:
            params.update(self.site.default_params)
        return await registry.execute("process_adaptive", self.page, params) if registry.has("process_adaptive") else False

    async def get_content_type(self) -> str:
        script = self.script("get_content_type")
        if script:
            return await self.page.evaluate(script)
        return "unknown"
