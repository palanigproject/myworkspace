from typing import Any

from pydantic import BaseModel, Field


class ToolRequest(BaseModel):
    name: str = Field(..., description="Tool name to execute")
    input: dict[str, Any] = Field(default_factory=dict, description="Tool input payload")


class ToolResponse(BaseModel):
    success: bool
    name: str
    data: Any = None
    error: str | None = None
