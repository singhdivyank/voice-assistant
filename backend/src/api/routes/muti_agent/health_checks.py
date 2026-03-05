import logging
from datetime import datetime

from fastapi import APIRouter

from src.config.settings import get_settings
from src.monitoring.dashboard import MonitoringDashboard
from .sessions_v2 import coordinator

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()
dashboard = MonitoringDashboard()

def _base_status(service: str) -> dict:
    """helper function for liveness check"""

    return {
        "service": service,
        "version": settings.app_version,
        "timestep": datetime.now().isoformat()
    }

def _component_ok(name: str, **extra) -> tuple[dict, bool]:
    return {name: {"status": "ready", **extra}}, True

def _component_fail(name: str, exc: Exception) -> tuple[dict, bool]:
    return {name: {"status": "not_ready", "error": str(exc)}}, False

@router.get("/ready")
async def readiness_check():
    """readiness check for Kubernetes / load balancers"""

    from src.core.multi_agent import LLMManager

    status = {
        "status": "ready",
        **_base_status("docjarvis-multi-agent"),
        "environment": settings.environment.value,
        "components": {}
    }
    all_ready = True

    try:
        llm_manager = LLMManager()
        comp, ok = _component_ok(
            "llm_manager",
            model=settings.gemini_model,
        )
        status["components"].update(comp)
    except Exception as e:
        logger.error("LLM Manager not ready: %s", e)
        comp, ok = _component_fail("llm_manager", e)
        status["components"].update(comp)
        all_ready = False

    try:
        has_tools = len(coordinator.tools) > 0
        comp, ok = _component_ok(
            "agent_coordinator", 
            tools_count=len(coordinator.tools),
            status="active" if has_tools else "degraded"
        )
        status["components"].update(comp)
        if not has_tools: all_ready = False
    except Exception as e:
        comp, ok = _component_fail("agent_coordinator", e)
        status["components"].update(comp)
        all_ready = False

    if not all_ready:
        status["status"] = "partially_ready"

    return status

@router.get("/deep")
async def deep_health_check():
    """comprehensive health diagnostic"""

    health = {
        "status": "healthy",
        **_base_status("docjarvis-multi-agent"),
        "deep_checks": {},
    }
    overall_ok = True

    try:
        logger.info("Running deep health check - workflow integration test")

        graph_info = coordinator.app.get_graph().nodes

        health["deep_checks"]["workflow_integration"] = {
            "status": "healthy",
            "nodes_detected": list(graph_info.keys()),
            "checkpointer_active": True
        }
    except Exception as e:
        logger.error("Deep health workflow test failed: %s", e)
        health["deep_checks"]["workflow_integration"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        overall_ok = False

    try:
        perf_data = dashboard.performance_monitor.get_performance_summary()
        system_health = perf_data.get("system_health", {})
        # TODO- make chanegs here
        health["deep_checks"]["performance"] = {
            "status": system_health.get("status", "unknown"),
            "score": system_health.get("score", 1.0),
            "issues": system_health.get("issues", []),
            "agent_count": len(perf_data.get("agents", {})),
        }

        if system_health.get("status") in {"critical", "warning"}:
            overall_ok = False
    except Exception as e:
        logger.error("Deep health performance test failed: %s", e)
        health["deep_checks"]["performance"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        overall_ok = False

    try:
        import psutil

        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent

        res_status = "healthy"
        issues: list[str] = []

        if cpu > 85:
            res_status = "degraded"
            issues.append(f"High CPU usage: {cpu}%")
        if mem > 85:
            res_status = "degraded"
            issues.append(f"High memory usage: {mem}%")
        if disk > 85:
            res_status = "degraded"
            issues.append(f"High disk usage: {disk}%")

        health["deep_checks"]["resources"] = {
            "status": res_status,
            "cpu_percent": cpu,
            "memory_percent": mem,
            "disk_percent": disk,
            "issues": issues,
        }

        if res_status != "healthy":
            overall_ok = False
    except Exception as e:
        logger.error("Deep health resource test failed: %s", e)

    health["status"] = "healthy" if overall_ok else "unhealthy"
    return health

@router.get("/startup")
async def startup_check():
    """startup health check after initialization"""
    
    status = {
        "status": "initialized",
        **_base_status("docjarvis-multi-agent"),
        "startup_checks": {},
    }

    try:
        status["startup_checks"]["configuration"] = {
            "status": "loaded",
            "environment": settings.environment.value,
            "debug_mode": settings.debug,
            "monitoring_enabled": {
                "otel": settings.otel_enabled,
                "langsmith": bool(settings.langsmith_api_key),
            },
        }
    except Exception as e:
        status["startup_checks"]["configuration"] = {
            "status": "failed",
            "error": str(e),
        }
        status["status"] = "failed"

    try:
        dirs_exist = all(
            [
                settings.output_dir.exists(),
                settings.audio_dir.exists(),
                settings.prescription_dir.exists(),
            ]
        )

        status["startup_checks"]["directories"] = {
            "status": "created" if dirs_exist else "failed",
            "paths": {
                "output_dir": str(settings.output_dir),
                "audio_dir": str(settings.audio_dir),
                "prescription_dir": str(settings.prescription_dir),
            },
        }
        if not dirs_exist:
            status["status"] = "failed"
    except Exception as e:
        status["startup_checks"]["directories"] = {
            "status": "failed",
            "error": str(e),
        }
        status["status"] = "failed"

    return status
