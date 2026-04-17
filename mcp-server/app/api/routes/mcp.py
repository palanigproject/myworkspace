import logging

from fastapi import APIRouter, HTTPException

from app.models.tool import ToolRequest, ToolResponse
from app.services.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])
registry = ToolRegistry()


@router.post("/tools", response_model=ToolResponse)
async def execute_tool(request: ToolRequest) -> ToolResponse:
    try:
        data = await registry.execute(request.name, request.input)
        return ToolResponse(success=True, name=request.name, data=data)
    except ValueError as exc:
        logger.warning("Tool validation error: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to execute tool: %s", request.name)
        return ToolResponse(success=False, name=request.name, error=str(exc))
