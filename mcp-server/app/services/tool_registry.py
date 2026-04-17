import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.clients.project_client import ProjectClient
from app.clients.slack_client import SlackClient

logger = logging.getLogger(__name__)

ToolHandler = Callable[[dict[str, Any]], Awaitable[Any]]


class ToolRegistry:
    def __init__(self) -> None:
        self.project_client = ProjectClient()
        self.slack_client = SlackClient()
        self.tools: dict[str, ToolHandler] = {
            "get_projects": self._get_projects,
            "slack_send_message": self._slack_send_message,
        }

    async def execute(self, name: str, input_payload: dict[str, Any]) -> Any:
        handler = self.tools.get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")
        logger.info("Executing tool: %s", name)
        return await handler(input_payload)

    async def _get_projects(self, _: dict[str, Any]) -> Any:
        return await self.project_client.get_projects()

    async def _slack_send_message(self, payload: dict[str, Any]) -> Any:
        return await self.slack_client.send_message(payload)
