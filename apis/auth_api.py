from core.base_api import BaseApi
from core.api_client import ApiResponse


class AuthAPI(BaseApi):
    async def login(self, username: str, password: str) -> ApiResponse:
        return await self.request("login", json={
            "username": username,
            "password": password,
        })

    async def logout(self) -> ApiResponse:
        return await self.request("logout")

    async def refresh_token(self) -> ApiResponse:
        return await self.request("refresh")
