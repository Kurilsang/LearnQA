from core.base_api import BaseApi
from core.api_client import ApiResponse


class ContentAPI(BaseApi):
    async def submit_progress(self, resource_id: str, progress: float = 100) -> ApiResponse:
        return await self.request(
            "progress",
            path_params={"resource_id": resource_id},
            json={"progress": progress},
        )

    async def get_status(self, resource_id: str) -> ApiResponse:
        return await self.request(
            "status",
            path_params={"resource_id": resource_id},
        )
