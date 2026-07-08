from core.base_api import BaseApi
from core.api_client import ApiResponse


class CourseAPI(BaseApi):
    async def get_detail(self, course_id: str) -> ApiResponse:
        return await self.request("detail", path_params={"course_id": course_id})

    async def get_chapters(self, course_id: str) -> ApiResponse:
        return await self.request("chapters", path_params={"course_id": course_id})

    async def get_resources(self, course_id: str, chapter_id: str) -> ApiResponse:
        return await self.request(
            "resource_list",
            path_params={"course_id": course_id, "chapter_id": chapter_id},
        )
