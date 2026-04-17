import httpx

from app.core.config import get_settings


class SlackApiClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def fetch_channel_history(self, channel_id: str | None = None, limit: int | None = None) -> dict:
        token = self.settings.slack_bot_token.strip()
        if not token:
            return {"ok": False, "error": "SLACK_BOT_TOKEN is not configured"}

        target_channel = (channel_id or self.settings.slack_history_channel_id).strip()
        if not target_channel:
            return {"ok": False, "error": "Channel id is required (payload.channel_id or SLACK_HISTORY_CHANNEL_ID)"}

        if not target_channel.upper().startswith(("C", "G", "D")):
            resolved_channel_id = await self._resolve_channel_id(target_channel, token)
            if not resolved_channel_id:
                return {"ok": False, "error": f'Channel "{target_channel}" was not found'}
            target_channel = resolved_channel_id

        target_limit = limit if isinstance(limit, int) and limit > 0 else self.settings.slack_history_limit
        timeout = httpx.Timeout(self.settings.http_timeout)
        headers = {"Authorization": f"Bearer {token}"}
        params = {"channel": target_channel, "limit": target_limit}

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                f"{self.settings.slack_api_base_url}/conversations.history",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def list_channels(self, limit: int | None = None) -> dict:
        token = self.settings.slack_bot_token.strip()
        if not token:
            return {"ok": False, "error": "SLACK_BOT_TOKEN is not configured"}

        target_limit = limit if isinstance(limit, int) and limit > 0 else 200
        timeout = httpx.Timeout(self.settings.http_timeout)
        headers = {"Authorization": f"Bearer {token}"}
        params = {"exclude_archived": "true", "limit": target_limit}

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                f"{self.settings.slack_api_base_url}/conversations.list",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def _resolve_channel_id(self, channel_name_or_id: str, token: str) -> str | None:
        normalized = channel_name_or_id.strip().lower().lstrip("#")
        timeout = httpx.Timeout(self.settings.http_timeout)
        headers = {"Authorization": f"Bearer {token}"}
        params = {"exclude_archived": "true", "limit": 1000}

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                f"{self.settings.slack_api_base_url}/conversations.list",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        channels = data.get("channels", [])
        for channel in channels:
            if not isinstance(channel, dict):
                continue
            if channel.get("id", "").lower() == normalized:
                return channel.get("id")
            if channel.get("name", "").lower() == normalized:
                return channel.get("id")
        return None
