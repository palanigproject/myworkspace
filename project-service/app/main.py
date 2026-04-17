from fastapi import FastAPI

from app.api.routes.projects import router as projects_router
from app.core.config import get_settings
from app.core.logging_config import setup_logging

settings = get_settings()
setup_logging(settings.log_level)

app = FastAPI(title=settings.app_name)
app.include_router(projects_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "project-service"}
