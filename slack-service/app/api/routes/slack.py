import logging

from fastapi import APIRouter, HTTPException

from app.models.slack import SlackEventRequest
from app.services.slack_service import SlackService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])
service = SlackService()


@router.post("/events")
async def slack_events(request: SlackEventRequest) -> dict:
    try:
        result = await service.process_event(request.event_type, request.payload)
        return {
            "ok": True,
            "event_type": request.event_type,
            "result": result,
        }
    except Exception as exc:
        logger.exception("Slack event processing failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
