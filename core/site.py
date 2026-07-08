import os
import yaml
from typing import Optional


class SiteConfig:
    def __init__(self, site_dir: str):
        self.site_dir = site_dir
        self._selectors = self._load_yaml("selectors.yaml") or {}
        self._api_endpoints = self._load_yaml("api_endpoints.yaml") or {}

    def _load_yaml(self, filename: str) -> Optional[dict]:
        path = os.path.join(self.site_dir, filename)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    @property
    def name(self) -> str:
        return "unknown"

    @property
    def resource_handlers(self) -> dict:
        return {}

    @property
    def default_params(self) -> dict:
        return {}

    def get_element(self, page_name: str, element_name: str) -> Optional[str]:
        return (
            self._selectors.get("pages", {})
            .get(page_name, {})
            .get("elements", {})
            .get(element_name)
        )

    def get_group(self, page_name: str, group_name: str) -> list:
        return (
            self._selectors.get("pages", {})
            .get(page_name, {})
            .get("groups", {})
            .get(group_name, [])
        )

    def get_script(self, page_name: str, script_name: str) -> Optional[str]:
        return (
            self._selectors.get("pages", {})
            .get(page_name, {})
            .get("scripts", {})
            .get(script_name)
        )

    def get_page_url(self, page_name: str) -> Optional[str]:
        return (
            self._selectors.get("pages", {})
            .get(page_name, {})
            .get("url")
        )

    def get_api_base_url(self) -> str:
        return self._api_endpoints.get("base_url", "")

    def get_api_endpoint(self, api_name: str, endpoint_name: str) -> Optional[dict]:
        return (
            self._api_endpoints.get(api_name, {})
            .get(endpoint_name)
        )
