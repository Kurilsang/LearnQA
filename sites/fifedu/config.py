import os
from core.site import SiteConfig

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class FIFSiteConfig(SiteConfig):
    def __init__(self):
        super().__init__(_SCRIPT_DIR)

    @property
    def name(self) -> str:
        return "fifedu"

    @property
    def resource_handlers(self) -> dict:
        return {
            "PPT": "process_pptx",
            "HTML": "process_html_pdf",
            "PDF": "process_html_pdf",
            "文档": "process_html_pdf",
            "视频": "process_video",
            "video": "process_video",
            "自适应": "process_adaptive",
            "练习": "process_adaptive",
            "训练": "process_adaptive",
        }

    @property
    def default_params(self) -> dict:
        return {
            "pptx_page_interval": 1.5,
            "scroll_step_delay": 0.5,
            "video_max_wait": 2000,
            "pptx_right_click_ratio": 0.85,
            "pptx_max_pages": 200,
            "pptx_no_next_threshold": 5,
            "pdf_scroll_factor": 200,
            "pdf_scroll_min_steps": 10,
            "pdf_scroll_max_steps": 50,
            "page_scroll_factor": 200,
            "adaptive_max_questions": 100,
            "adaptive_iframe_max_rounds": 100,
            "video_stall_threshold": 4,
            "video_check_interval": 10,
            "login_max_wait": 20,
            "resource_finish_timeout": 120,
            "chapter_expand_attempts": 5,
        }


site_config = FIFSiteConfig()
