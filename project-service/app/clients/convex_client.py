import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ConvexClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def fetch_projects(self) -> dict:
        timeout = httpx.Timeout(self.settings.http_timeout)
        headers: dict[str, str] = {}
        if self.settings.convex_bearer_token:
            headers["Authorization"] = f"Bearer {self.settings.convex_bearer_token}"

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.get(self.settings.convex_projects_url, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as exc:
                logger.error("Timeout while fetching projects from Convex API")
                raise RuntimeError("Convex API request timed out") from exc
            except httpx.HTTPStatusError as exc:
                logger.error("Convex API returned HTTP %s", exc.response.status_code)
                raise RuntimeError(f"Convex API returned HTTP {exc.response.status_code}") from exc
            except httpx.HTTPError as exc:
                logger.error("Unexpected HTTP error while calling Convex API: %s", exc)
                raise RuntimeError("Failed to connect to Convex API") from exc
