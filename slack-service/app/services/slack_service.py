import logging

from app.clients.mcp_client import MCPClient
from app.clients.slack_api_client import SlackApiClient
from app.clients.slack_webhook_client import SlackWebhookClient

logger = logging.getLogger(__name__)


class SlackService:
    def __init__(self) -> None:
        self.mcp_client = MCPClient()
        self.slack_api_client = SlackApiClient()
        self.webhook_client = SlackWebhookClient()

    async def process_event(self, event_type: str, payload: dict) -> dict:
        if event_type == "send_message":
            text = payload.get("text", "No message supplied")
            return await self.webhook_client.send_message(text)

        if event_type == "slash_command":
            command = payload.get("command", "").strip().lower()
            if command == "/projects":
                result = await self.mcp_client.execute_tool("get_projects", {})
                if not result.get("success", False):
                    error_message = result.get("error", "Unknown MCP error")
                    message = f"Failed to fetch projects via MCP: {error_message}"
                    await self.webhook_client.send_message(message)
                    return {"handled": False, "message": message, "tool_result": result}

                data = result.get("data") or {}
                project_count = data.get("count", 0)
                message = f"Projects fetched through MCP: {project_count}"
                await self.webhook_client.send_message(message)
                return {"handled": True, "message": message, "tool_result": result}

            fallback = "Unsupported slash command."
            await self.webhook_client.send_message(fallback)
            return {"handled": False, "message": fallback}

        if event_type == "channel_history":
            channel_id = payload.get("channel_id") or payload.get("channel")
            limit = payload.get("limit")
            history = await self.slack_api_client.fetch_channel_history(channel_id=channel_id, limit=limit)
            return {"handled": bool(history.get("ok")), "history": history}

        if event_type == "channel_list":
            limit = payload.get("limit")
            channels = await self.slack_api_client.list_channels(limit=limit)
            return {"handled": bool(channels.get("ok")), "channels": channels}

        logger.warning("Unknown event_type received: %s", event_type)
        return {"handled": False, "message": f"Unknown event_type: {event_type}"}
