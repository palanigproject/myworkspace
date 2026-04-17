import httpx

from app.core.config import get_settings


class SlackWebhookClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def send_message(self, text: str) -> dict:
        if not self.settings.slack_webhook_url:
            return {"delivered": False, "reason": "SLACK_WEBHOOK_URL not configured", "text": text}

        timeout = httpx.Timeout(self.settings.http_timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(self.settings.slack_webhook_url, json={"text": text})
                response.raise_for_status()
                return {"delivered": True, "text": text}
            except httpx.HTTPError as exc:
                return {
                    "delivered": False,
                    "reason": f"Slack webhook delivery failed: {exc}",
                    "text": text,
                }
