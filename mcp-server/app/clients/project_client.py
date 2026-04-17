import httpx

from app.core.config import get_settings


class ProjectClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def get_projects(self) -> dict:
        timeout = httpx.Timeout(self.settings.http_timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{self.settings.project_service_url}/projects")
            response.raise_for_status()
            return response.json()
