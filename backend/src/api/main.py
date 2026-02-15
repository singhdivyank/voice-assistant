"""FastAPI application entry point"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config.settings import get_settings
from src.config.monitoring import setup_monitoring, telemetry
from src.api.routes import sessions, diagnosis, prescription
from src.api.middleware.logging import RequestLoggingMiddleWare
from src.utils.exceptions import DocJarvisError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s  - %(message)s"
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager"""

    logger.info("Starting DocJatrvis API...")
    setup_monitoring()
    telemetry.instrument_fastapi(app)
    settings.setup_dir()
    logger.info(f"DocJarvis API started on {settings.host}:{settings.port}")
    yield
    logger.info("Shutting down DocJarvis API...")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered medical consultation assistant API",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.add_middleware(RequestLoggingMiddleWare)


@app.exception_handler(DocJarvisError)
async def docjarvis_exception_handler(request: Request, exc: DocJarvisError):
    """Handle application-specific exceptions"""

    return JSONResponse(
        status_code=400,
        content={"error": str(exc), "type": exc.__class__.__name__}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""

    logger.exception("Unexpected error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occured", "type": "InternalError"}
    )

app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(diagnosis.router, prefix="/api/v1/diagnosis", tags=["diagnosis"])
app.include_router(prescription.router, prefix="/api/v1/prescription", tags=["prescription"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.app_version}


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    return {
        "status": "ready",
        "environment": settings.environment.value,
        "monitoring": {
            "otel_enabled": settings.otel_enabled,
            "langsmith_enabled": bool(settings.langsmith_api_key)
        }
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers
    )
