import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.clients.chat_client import ChatClient

logger = logging.getLogger(__name__)

ToolHandler = Callable[[dict[str, Any]], Awaitable[Any]]


class ToolRegistry:
    def __init__(self) -> None:
        self.chat_client = ChatClient()
        self.tools: dict[str, ToolHandler] = {
            "get_projects": self._get_projects,
            "slack_send_message": self._slack_send_message,
            "get_slack_channel_history": self._get_slack_channel_history,
            "get_slack_channels": self._get_slack_channels,
        }

    async def execute(self, name: str, input_payload: dict[str, Any]) -> Any:
        handler = self.tools.get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")
        logger.info("Executing tool: %s", name)
        return await handler(input_payload)

    async def _get_projects(self, _: dict[str, Any]) -> Any:
        payload = {
            "query": "list out projects",
            "feature": "project",
        }
        return await self.chat_client.fetch_prompt_data(payload)

    async def _slack_send_message(self, payload: dict[str, Any]) -> Any:
        query = str(payload.get("query") or payload.get("text") or "send message in slack").strip()
        api_payload = {
            "query": query,
            "feature": str(payload.get("feature") or "slack").strip(),
        }
        return await self.chat_client.fetch_prompt_data(api_payload)

    async def _get_slack_channel_history(self, payload: dict[str, Any]) -> Any:
        channel = payload.get("channel") or payload.get("channel_id")
        query = str(payload.get("query") or "").strip()
        if not query:
            query = f"show messages in channel {channel}".strip() if channel else "show channel history"
        api_payload = {
            "query": query,
            "feature": str(payload.get("feature") or "slack").strip(),
        }
        return await self.chat_client.fetch_prompt_data(api_payload)

    async def _get_slack_channels(self, payload: dict[str, Any]) -> Any:
        api_payload = {
            "query": str(payload.get("query") or "list out channel").strip(),
            "feature": str(payload.get("feature") or "slack").strip(),
        }
        return await self.chat_client.fetch_prompt_data(api_payload)
