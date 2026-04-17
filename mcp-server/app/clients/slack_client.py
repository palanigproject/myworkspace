import httpx

from app.core.config import get_settings


class SlackClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def send_message(self, payload: dict) -> dict:
        timeout = httpx.Timeout(self.settings.http_timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.settings.slack_service_url}/slack/events",
                json={
                    "event_type": "send_message",
                    "payload": payload,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_channel_history(self, payload: dict) -> dict:
        timeout = httpx.Timeout(self.settings.http_timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.settings.slack_service_url}/slack/events",
                json={
                    "event_type": "channel_history",
                    "payload": {
                        "channel": payload.get("channel"),
                        "channel_id": payload.get("channel_id"),
                        "limit": payload.get("limit"),
                    },
                },
            )
            response.raise_for_status()
            return response.json()

    async def list_channels(self, payload: dict) -> dict:
        timeout = httpx.Timeout(self.settings.http_timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.settings.slack_service_url}/slack/events",
                json={
                    "event_type": "channel_list",
                    "payload": {
                        "limit": payload.get("limit"),
                    },
                },
            )
            response.raise_for_status()
            return response.json()
