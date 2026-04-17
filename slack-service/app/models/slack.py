from typing import Any

from pydantic import BaseModel, Field


class SlackEventRequest(BaseModel):
    event_type: str = Field(..., description="Type of slack event")
    payload: dict[str, Any] = Field(default_factory=dict, description="Slack event payload")
