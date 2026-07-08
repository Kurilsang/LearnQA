from typing import Optional

from core.api_client import ApiClient, ApiResponse


class BaseApi:
    def __init__(self, client: ApiClient, site_config):
        self.client = client
        self.site = site_config

    @property
    def api_key(self) -> str:
        name = type(self).__name__
        if name.endswith("API"):
            name = name[:-3]
        parts = []
        for i, c in enumerate(name):
            if c.isupper() and i > 0:
                parts.append("_")
            parts.append(c.lower())
        return "".join(parts)

    def endpoint(self, name: str) -> dict:
        ep = self.site.get_api_endpoint(self.api_key, name)
        if ep is None:
            raise KeyError(f"端点 '{name}' 未定义（{self.api_key}）")
        return ep

    async def request(self, endpoint_name: str, path_params: dict = None, **kwargs) -> ApiResponse:
        ep = self.endpoint(endpoint_name)
        method = ep.get("method", "GET").lower()
        path = ep.get("path", "")
        if path_params:
            path = path.format(**path_params)
        headers = {**ep.get("headers", {}), **kwargs.pop("headers", {})}
        return await self.client.request(method, path, headers=headers, **kwargs)
