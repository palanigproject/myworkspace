import logging

from fastapi import APIRouter, HTTPException

from app.services.project_service import ProjectService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["projects"])
service = ProjectService()


@router.get("/projects")
async def get_projects() -> dict:
    try:
        return await service.get_projects()
    except Exception as exc:
        logger.exception("Failed to fetch projects")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
