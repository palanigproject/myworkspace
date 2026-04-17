from typing import Any

from app.clients.convex_client import ConvexClient


class ProjectService:
    def __init__(self) -> None:
        self.client = ConvexClient()

    async def get_projects(self) -> dict[str, Any]:
        raw_data = await self.client.fetch_projects()
        projects = self._extract_projects(raw_data)
        return {
            "count": len(projects),
            "projects": projects,
        }

    @staticmethod
    def _extract_projects(raw_data: Any) -> list[dict[str, Any]]:
        if isinstance(raw_data, list):
            source = raw_data
        elif isinstance(raw_data, dict):
            if isinstance(raw_data.get("data"), list):
                source = raw_data["data"]
            elif isinstance(raw_data.get("items"), list):
                source = raw_data["items"]
            else:
                source = [raw_data]
        else:
            source = []

        projects: list[dict[str, Any]] = []
        for item in source:
            if not isinstance(item, dict):
                continue
            projects.append(
                {
                    "id": item.get("id") or item.get("projectId"),
                    "name": item.get("name") or item.get("projectName"),
                    "status": item.get("statusName")
                    or item.get("status")
                    or ((item.get("statusId") or {}).get("name") if isinstance(item.get("statusId"), dict) else None),
                    "owner": item.get("ownerName")
                    or item.get("owner")
                    or ((item.get("ownerId") or {}).get("username") if isinstance(item.get("ownerId"), dict) else None),
                    "raw": item,
                }
            )
        return projects
