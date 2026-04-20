import asyncio
import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ChatClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _extract_complete_event(self, value: str) -> dict[str, Any] | None:
        last_event: dict[str, Any] | None = None
        for line in value.splitlines():
            text = line.strip()
            if not text.startswith("data:"):
                continue
            raw_event = text[5:].strip()
            if not raw_event or raw_event == "[DONE]":
                continue
            try:
                event = json.loads(raw_event)
            except ValueError:
                continue
            if isinstance(event, dict):
                last_event = event
                if event.get("type") == "complete":
                    return event
        return last_event

    def _normalize_payload(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            if payload.get("type") == "complete":
                return payload

            response_value = payload.get("response")
            if isinstance(response_value, str):
                sse_event = self._extract_complete_event(response_value)
                if sse_event is not None:
                    return sse_event

                try:
                    decoded = json.loads(response_value)
                except ValueError:
                    decoded = None
                if isinstance(decoded, dict):
                    return decoded

            return payload

        return {"status": "success", "response": str(payload)}

    def _service_unavailable_payload(self, detail: str) -> dict[str, Any]:
        return {
            "type": "complete",
            "status": "error",
            "response": (
                "The upstream chat API is temporarily unavailable. "
                "Please retry in a few moments."
            ),
            "error": detail,
        }

    async def fetch_prompt_data(self, payload: dict[str, str]) -> dict:
        timeout = httpx.Timeout(
            connect=10.0,
            read=self.settings.http_timeout,
            write=10.0,
            pool=10.0,
        )
        headers = {
            "Authorization": f"Bearer {self.settings.chat_api_bearer_token}",
        }
        multipart_form = {
            key: (None, str(value))
            for key, value in payload.items()
            if value is not None
        }
        transient_errors = (httpx.ReadError, httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError)
        retryable_status_codes = {429, 502, 503, 504}
        last_exception: Exception | None = None

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(1, 4):
                try:
                    response = await client.post(
                        self.settings.chat_api_url,
                        files=multipart_form,
                        headers=headers,
                    )
                    if response.status_code in retryable_status_codes:
                        detail = response.text.strip() or f"HTTP {response.status_code}"
                        last_exception = RuntimeError(
                            f"Upstream chat API temporary error ({response.status_code}): {detail}"
                        )
                        if attempt == 3:
                            break
                        await asyncio.sleep(attempt)
                        continue

                    response.raise_for_status()
                    # Upstream may return plain text/markdown even on HTTP 200.
                    body_text = response.text.strip()
                    if not body_text:
                        return {"status": "error", "response": "", "error": "Empty response from chat API."}
                    try:
                        parsed = response.json()
                        return self._normalize_payload(parsed)
                    except ValueError:
                        sse_event = self._extract_complete_event(body_text)
                        if sse_event is not None:
                            return sse_event
                        return {"status": "success", "response": body_text}
                except transient_errors as exc:
                    last_exception = exc
                    if attempt == 3:
                        break
                    await asyncio.sleep(attempt)
                except httpx.HTTPStatusError as exc:
                    detail = exc.response.text.strip() or str(exc)
                    logger.warning("Chat API non-retryable HTTP error: %s", detail)
                    return self._service_unavailable_payload(detail)

        if last_exception is not None:
            detail = str(last_exception)
            logger.warning("Chat API transient failure after retries: %s", detail)
            return self._service_unavailable_payload(detail)
        logger.warning("Chat API request failed for unknown reason.")
        return self._service_unavailable_payload("Chat API request failed for unknown reason.")
