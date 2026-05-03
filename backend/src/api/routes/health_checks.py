import logging

from fastapi import APIRouter

from src.config.settings import get_settings
from src.monitoring.dashboard import monitoring_dashboard
from .helpers import _base_status, _component_ok, _component_fail

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

@router.get("/ready")
async def readiness_check():
    """readiness check for Kubernetes / load balancers"""

    from src.core.llm_manager import llm_manager
    from src.core.crew_ai.medical_crew import medical_crew

    status = {
        "status": "ready",
        **_base_status("docjarvis-crewai"),
        "environment": settings.environment.value,
        "components": {}
    }
    all_ready = True

    try:
        resp = await llm_manager.call_llm("Hello", {"test": True})
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
        initialized = hasattr(medical_crew, '_initialised') and medical_crew._initialised
        if not initialized:
            await medical_crew.initialise()
        
        comp, ok = _component_ok(
            "crewai_medical_service",
            crew_initialized=medical_crew._initialised,
            agents_available=len(medical_crew.agents),
            session_manager_ready=hasattr(medical_crew, 'session_manager'),
            mcp_manager_ready=hasattr(medical_crew, 'mcp_manager'),
        )
    except Exception as e:
        logger.error("Multi-Agent Service not ready: %s", e)
        comp, ok = _component_fail("crewai_medical_service", e)
    status["components"].update(comp)
    all_ready &= ok

    try:
        cache_stats = monitoring_dashboard.cache_manager.get_stats()
        comp, ok = _component_ok(
            "cache_system",
            total_entries=cache_stats.get("total_entries", 0),
            hit_rate=cache_stats.get("hit_rate", 0.0),
            crewai_agents_cached=len([
                agent for agent in cache_stats.get("agent_cache_status", {}).keys()
                if agent in ["speech_processor", "translator", "interviewer", "diagnostician", "pharmacist", "prescription_specialist"]
            ])
        )
    except Exception as e:
        logger.error("Cache System not ready: %s", e)
        comp, ok = _component_fail("cache_system", e)
    
    status["components"].update(comp)
    all_ready &= ok

    try:
        load_stats = monitoring_dashboard.load_balancer.get_load_stats()
        crewai_agents = ["speech_processor", "translator", "interviewer", "diagnostician", "pharmacist", "prescription_specialist"]
        crewai_configured = sum(1 for agent in load_stats.keys() if agent in crewai_agents)

        comp, ok = _component_ok(
            "load_balancer",
            agents_configured=len(load_stats),
            crewai_agents_configured=crewai_configured,
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
        monitoring_data = await monitoring_dashboard.get_dashboard_data()
        comp, _ = _component_ok(
            "monitoring_system",
            dashboard_data_available=bool(monitoring_data),
            performance_data_available=bool(monitoring_data.get("performance")),
            crewai_transition_status=monitoring_data.get("performance", {}).get("crewai_transition_status", {}),
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

    try:
        from src.core.crew_ai.medical_crew import medical_crew

        logger.info("Running deep health check - workflow integration test")

        agent_tests = {}
        try:
            if not medical_crew._initialised:
                await medical_crew.initialise()
            
            for agent_name, agent in medical_crew.agents.items():
                try:
                    # check if agent is properly initialized
                    agent_tests[agent_name] = {
                        "status": "healthy", 
                        "initialized": agent is not None,
                        "role": getattr(agent, 'role', 'unknown')
                    }
                except Exception as e:
                    agent_tests[agent_name] = {"status": "unhealthy", "error": str(e)}
                    overall_ok = False
        except Exception as e:
            agent_tests["qa"] = {"status": "unhealthy", "error": str(e)}
            overall_ok = False

        health["deep_checks"]["workflow_integration"] = {
            "status": "healthy" if overall_ok else "unhealthy",
            "agent_tests": agent_tests,
            "crew_initialized": medical_crew._initialised if hasattr(medical_crew, '_initialised') else False,
        }
    except Exception as e:
        logger.error("Deep health workflow test failed: %s", e)
        health["deep_checks"]["workflow_integration"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        overall_ok = False

    try:
        perf_data = monitoring_dashboard.performance_monitor.get_performance_summary()
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
    
    try:
        if hasattr(medical_crew, 'mcp_manager'):
            mcp_metrics = await medical_crew.mcp_manager.get_mcp_metrics()
            health["deep_checks"]["mcp_integration"] = {
                "status": "healthy",
                "pending_reviews": mcp_metrics.get("total_pending_reviews", 0),
                "completed_reviews": mcp_metrics.get("total_completed_reviews", 0),
                "sla_compliance_rate": mcp_metrics.get("sla_compliance_rate", 100.0)
            }
        else:
            health["deep_checks"]["mcp_integration"] = {
                "status": "not_configured",
                "message": "MCP manager not available"
            }
    except Exception as e:
        logger.error("Deep health MCP test failed: %s", e)
        health["deep_checks"]["mcp_integration"] = {
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
            "system_type": "crewai",
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
    
    try:
        from src.core.crew_ai.medical_crew import medical_crew
        
        crew_status = {
            "status": "initialized" if hasattr(medical_crew, '_initialised') and medical_crew._initialised else "pending",
            "agents_loaded": len(medical_crew.agents) if hasattr(medical_crew, 'agents') else 0,
            "session_manager": hasattr(medical_crew, 'session_manager'),
            "mcp_manager": hasattr(medical_crew, 'mcp_manager'),
        }
        
        status["startup_checks"]["crewai_system"] = crew_status
        
        if crew_status["status"] == "pending":
            status["status"] = "initializing"
            
    except Exception as e:
        status["startup_checks"]["crewai_system"] = {
            "status": "failed",
            "error": str(e),
        }
        status["status"] = "failed"

    return status