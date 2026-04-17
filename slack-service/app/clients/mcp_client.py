import httpx

from app.core.config import get_settings


class MCPClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def execute_tool(self, name: str, tool_input: dict) -> dict:
        timeout = httpx.Timeout(self.settings.http_timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.settings.mcp_server_url}/mcp/tools",
                json={
                    "name": name,
                    "input": tool_input,
                },
            )
            response.raise_for_status()
            return response.json()
