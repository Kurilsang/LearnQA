import asyncio
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass, field

import httpx


@dataclass
class ApiResponse:
    status_code: int
    headers: dict
    json_body: any
    text: str
    elapsed: float
    request_method: str
    request_url: str
    request_body: any


class ApiClient:
    def __init__(
        self,
        base_url: str = "",
        timeout: float = 30.0,
        max_retries: int = 0,
        retry_interval: float = 1.0,
        token_provider: Optional[Callable[[], Awaitable[Optional[str]]]] = None,
        logger=None,
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_interval = retry_interval
        self._token_provider = token_provider
        self._log = logger
        self._token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def start(self):
        if self._client is not None:
            return
        timeout = httpx.Timeout(self._timeout)
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
        )
        if self._token_provider:
            self._token = await self._token_provider()
        if self._log:
            self._log.info(f"API 客户端启动，基础地址: {self._base_url or '未设置'}")

    async def stop(self):
        if self._client is None:
            return
        await self._client.aclose()
        self._client = None
        if self._log:
            self._log.info("API 客户端已关闭")

    async def _refresh_token(self):
        if self._token_provider:
            self._token = await self._token_provider()

    def _log_request(self, method: str, url: str, kwargs: dict):
        if not self._log:
            return
        body = kwargs.get("json") or kwargs.get("data") or ""
        self._log.info(f"[API] {method.upper()} {url}")
        if body:
            self._log.debug(f"[API] 请求体: {body}")

    def _log_response(self, resp: ApiResponse):
        if not self._log:
            return
        self._log.info(
            f"[API] {resp.request_method} {resp.request_url} "
            f"-> {resp.status_code} ({resp.elapsed:.2f}s)"
        )

    async def request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> ApiResponse:
        if self._client is None:
            raise RuntimeError("客户端未启动，请先调用 start()")

        url = path if path.startswith("http") else f"{self._base_url}{path}"
        self._log_request(method, url, kwargs)

        headers = kwargs.pop("headers", {})
        if self._token:
            headers.setdefault("Authorization", f"Bearer {self._token}")
        kwargs["headers"] = headers

        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.request(method, url, **kwargs)
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                if attempt < self._max_retries:
                    wait = self._retry_interval * (attempt + 1)
                    if self._log:
                        self._log.warn(
                            f"[API] 请求失败 ({type(e).__name__})，"
                            f"{wait:.0f}s 后重试 ({attempt + 1}/{self._max_retries})"
                        )
                    await asyncio.sleep(wait)
                    continue
                raise

            if response.status_code == 401 and self._token_provider:
                if self._log:
                    self._log.info("[API] Token 过期，尝试刷新")
                await self._refresh_token()
                headers["Authorization"] = f"Bearer {self._token}"
                kwargs["headers"] = headers
                response = await self._client.request(method, url, **kwargs)

            try:
                json_body = response.json()
            except Exception:
                json_body = None

            result = ApiResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                json_body=json_body,
                text=response.text,
                elapsed=response.elapsed.total_seconds(),
                request_method=method.upper(),
                request_url=str(response.url),
                request_body=kwargs.get("json") or kwargs.get("data"),
            )
            self._log_response(result)
            return result

        raise last_error

    async def get(self, path: str, **kwargs) -> ApiResponse:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> ApiResponse:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs) -> ApiResponse:
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> ApiResponse:
        return await self.request("DELETE", path, **kwargs)
