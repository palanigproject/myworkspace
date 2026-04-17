from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.mcp import router as mcp_router
from app.core.config import get_settings
from app.core.logging_config import setup_logging

settings = get_settings()
setup_logging(settings.log_level)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mcp_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "mcp-server"}
