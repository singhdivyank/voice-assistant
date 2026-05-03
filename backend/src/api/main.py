"""FastAPI application entry point"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import sessions, diagnosis, prescription
from src.api.routes.workflow_routes import router as crewai_router
from src.api.routes.monitoring import router as monitoring_router
from src.api.routes.health_checks import router as health_router
from src.api.middleware.logging import RequestLoggingMiddleWare
from src.core.crew_ai.medical_crew import MedicalCrew
from src.config import get_settings, setup_monitoring, telemetry
from src.monitoring.dashboard import MonitoringDashboard
from src.utils.exceptions import DocJarvisError

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s  - %(message)s"
)
logger = logging.getLogger(__name__)
settings = get_settings()
monitoring_dashboard = MonitoringDashboard()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator:
    """Application lifespan manager"""

    logger.info("Starting DocJatrvis API...")
    setup_monitoring()
    telemetry.instrument_fastapi(application)
    settings.setup_dir()
    logger.info("Initialising multi-agent workflow ...")

    try:
        # Pre-initialize the crew to validate configuration
        _ = MedicalCrew()
        logger.info("CrewAI medical crew initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize CrewAI system: %s", str(e))
        # Don't fail startup, but log the issue

    logger.info("DocJarvis API started on %s:%d", settings.host, settings.port)
    yield
    logger.info("Shutting down DocJarvis API...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered medical consultation assistant API",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleWare)


@app.exception_handler(DocJarvisError)
async def docjarvis_exception_handler(exc: DocJarvisError):
    """Handle application-specific exceptions"""

    return JSONResponse(
        status_code=400, content={"error": str(exc), "type": exc.__class__.__name__}
    )


@app.exception_handler(Exception)
async def general_exception_handler(exc: Exception):
    """Handle unexpected exceptions"""

    logger.exception("Unexpected error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occured", "type": "InternalError"},
    )


app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(diagnosis.router, prefix="/api/v1/diagnosis", tags=["diagnosis"])
app.include_router(
    prescription.router, prefix="/api/v1/prescription", tags=["prescription"]
)
# app.include_router(
#   sessions_v2.router,
#   prefix="/api/v2/sessions",
#   tags=["multi-agent-sessions-v2"]
# )
# app.include_router(
#   monitoring.router,
#   prefix="/api/v2/monitoring",
#   tags=["multi-agent-monitoring-v2"]
# )
# app.include_router(
#   health_checks.router,
#   prefix="/api/v2/health",
#   tags=["multi-agent-health-v2"]
# )

# V2 API - CrewAI multi-agent routes
app.include_router(crewai_router, prefix="/api/v2", tags=["crewai-v2"])
app.include_router(
    monitoring_router, prefix="/api/v2/monitoring", tags=["monitoring-v2"]
)
app.include_router(health_router, prefix="/api/v2/health", tags=["health-v2"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    base_health = {"status": "healthy", "version": settings.app_version}

    try:
        dashboard_data = await monitoring_dashboard.get_dashboard_data()
        system_health = dashboard_data.get("performance", {}).get("system_health", {})
        base_health.update(
            {
                "multi_agent_status": system_health.get("status", "unknown"),
                "agents_health_score": system_health.get("score", 1.0),
            }
        )

        if system_health.get("status") == "critical":
            base_health["status"] = "degraded"
    except Exception as e:
        logger.error("Failed to get agent health: %s", e)
        base_health["multi_agent_status"] = "error"
        base_health["status"] = "degraded"

    return base_health


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    base_rediness = {
        "status": "ready",
        "environment": settings.environment.value,
        "monitoring": {
            "otel_enabled": settings.otel_enabled,
            "langsmith_enabled": bool(settings.langsmith_api_key),
        },
    }

    try:
        load_stats = monitoring_dashboard.load_balancer.get_load_stats()
        base_rediness["agents"] = {
            agent: {
                "ready": stats["current_load"] < stats["max_concurrent"],
                "load": f"{stats['current_load']}/{stats['max_concurrent']}",
            }
            for agent, stats in load_stats.items()
        }
    except Exception as e:
        logger.error("Failed to get agent readiness: %s", e)
        base_rediness["agents"] = {"error": str(e)}

    return base_rediness


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else None,
        "api_versions": {
            "v1": "Legacy single-agent API",
            "v2": "Multi-agent system API",
        },
        "monitoring": "/monitoring/dashboard",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
    )
