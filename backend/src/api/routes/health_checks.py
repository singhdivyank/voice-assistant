import logging
from datetime import datetime

from fastapi import APIRouter

from src.config.settings import get_settings
from src.monitoring.dashboard import MonitoringDashboard

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
    from src.integration.muti_agent_service import MultiAgentService

    status = {
        "status": "ready",
        **_base_status("docjarvis-multi-agent"),
        "environment": settings.environment.value,
        "components": {}
    }
    all_ready = True

    try:
        llm_manager = LLMManager()
        resp = await llm_manager.call_llm("Hello")
        comp, ok = _component_ok(
            "llm_manager",
            model=settings.gemini_model,
            test_response_length=len(resp) if resp else 0,
        )
    except Exception as e:
        logger.error("LLM Manager not ready: %s", e)
        comp, ok = _component_fail("llm_manager", e)
    status["components"].update(comp)
    all_ready &= ok

    try:
        service = MultiAgentService()
        comp, ok = _component_ok(
            "multi_agent_service",
            workflow_initialized=hasattr(service, "workflow"),
        )
    except Exception as e:
        logger.error("Multi-Agent Service not ready: %s", e)
        comp, ok = _component_fail("multi_agent_service", e)
    status["components"].update(comp)
    all_ready &= ok

    try:
        cache_stats = dashboard.cache_manager.get_stats()
        comp, ok = _component_ok(
            "cache_system",
            total_entries=cache_stats.get("total_entries", 0),
            hit_rate=cache_stats.get("hit_rate", 0.0),
        )
    except Exception as e:
        logger.error("Cache System not ready: %s", e)
        comp, ok = _component_fail("cache_system", e)
    status["components"].update(comp)
    all_ready &= ok

    try:
        load_stats = dashboard.load_balancer.get_load_stats()
        comp, ok = _component_ok(
            "load_balancer",
            agents_configured=len(load_stats),
            total_capacity=sum(
                stats["max_concurrent"] for stats in load_stats.values()
            ),
        )
    except Exception as e:
        logger.error("Load Balancer not ready: %s", e)
        comp, ok = _component_fail("load_balancer", e)
    status["components"].update(comp)
    all_ready &= ok

    try:
        monitoring_data = await dashboard.get_dashboard_data()
        comp, _ = _component_ok(
            "monitoring_system",
            dashboard_data_available=bool(monitoring_data),
        )
    except Exception as e:
        logger.error("Monitoring System not ready: %s", e)
        comp, _ = _component_fail("monitoring_system", e)
    status["components"].update(comp)

    if not all_ready:
        status["status"] = "not_ready"

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

    from src.core.multi_agent.agents.base_agent import AgentExecutionState
    from src.utils.consts import PatientInfo, Gender, Language
    from src.core.multi_agent.agents.qa_agent import QuestionAnswerAgent

    try:
        logger.info("Running deep health check - workflow integration test")
        _ = AgentExecutionState(
            patient=PatientInfo(
                name="Health Check",
                email="test@test.com",
                age=30,
                gender=Gender.MALE,
            ),
            session_id="health-check-test",
            source_language=Language.ENGLISH,
            transcribed_texts=["Test health check"],
            questions=[],
            answers=[],
            conversation_complete=False,
            translated_content={},
            tts_files=[],
            response_audio=None,
            symptoms_analysis=None,
            differential_diagnosis=None,
            final_diagnosis=None,
            medication_recommendations=None,
            prescription_path=None,
            current_step="test",
            errors=[],
            metadata={"test": True},
        )

        agent_tests = {}
        try:
            _ = QuestionAnswerAgent()
            agent_tests["qa"] = {"status": "healthy", "initialized": True}
        except Exception as e:
            agent_tests["qa"] = {"status": "unhealthy", "error": str(e)}
            overall_ok = False

        health["deep_checks"]["workflow_integration"] = {
            "status": "healthy" if overall_ok else "unhealthy",
            "agent_tests": agent_tests,
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

        if cpu > 90:
            res_status = "degraded"
            issues.append(f"High CPU usage: {cpu}%")
        if mem > 90:
            res_status = "degraded"
            issues.append(f"High memory usage: {mem}%")
        if disk > 90:
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
        health["deep_checks"]["resources"] = {
            "status": "unhealthy",
            "error": str(e),
        }

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