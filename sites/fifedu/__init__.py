from core.registry import registry
from .config import site_config

from . import handlers

registry.register("process_pptx", handlers.process_pptx)
registry.register("process_html_pdf", handlers.process_html_pdf)
registry.register("process_video", handlers.process_video)
registry.register("process_adaptive", handlers.process_adaptive)
registry.register("handle_adaptive_questions", handlers.handle_adaptive_questions)
registry.register("handle_adaptive_in_iframe", handlers.handle_adaptive_in_iframe)
registry.register("ai_ask", handlers.ai_ask)
