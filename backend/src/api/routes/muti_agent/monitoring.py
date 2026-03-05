import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query
from fastapi.exceptions import HTTPException

from src.monitoring.dashboard import MonitoringDashboard

logger = logging.getLogger(__name__)
router = APIRouter()
dashboard = MonitoringDashboard()

TOOLS = [
    "transcribe_audio", 
    "analyze_symptoms_and_diagnose", 
    "recommend_medications", 
    "create_prescription_document",
    "generate_voice_response"
]

@router.get("/dashboard")
async def get_dashboard():
    """get monitoring dashboard for with all metrics"""

    try:
        dashboard_data = await dashboard.get_dashboard_data()
        return dashboard_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get dashboard data: %s", e)
        raise HTTPException(status_code=500, detail="Dashboard data unavailable")

@router.get("/agents")
async def get_agent_metrics():
    """get tool-specific performance"""

    metrics = {}
    for tool_name in TOOLS:
        metrics[tool_name] = await dashboard.get_agent_performance(tool_name)
    
    return metrics

@router.get("/performance")
async def get_performance_metrics(
    agent_name: Optional[str] = Query(None, description="Filter by specific agent"),
    hours: int = Query(24, description="Hours of data to return", ge=1, le=168)
):
    """get detailed performance metrics for agents"""

    try:
        performance_data = dashboard.performance_monitor.get_performance_summary()
        if agent_name:
            perfomance = performance_data.get("agents", {})
            if perfomance and agent_name in perfomance:
                metrics = perfomance.get(agent_name, {})
                filtered_data = {
                   "agent": agent_name,
                    "metrics": metrics,
                    "system_health": performance_data.get("system_health", {}),
                    "query_params": {"agent_name": agent_name, "hours": hours}
                }
                
                return filtered_data
        else:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
        
        performance_data["query_params"] = {"hours": hours}
        performance_data["available_agents"] = list(performance_data.get("agents", {}).keys())
        return performance_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get performance metrics: %s", e)
        raise HTTPException(status_code=500, detail="Performance metrics unavailable")

@router.get("/health")
async def get_system_health():
    """get overall system health score and status"""

    try:
        performance_data = dashboard.performance_monitor.get_performance_summary()
        cache_stats = dashboard.cache_manager.get_stats()
        load_stats = dashboard.load_balancer.get_load_stats()
        system_health = performance_data.get("system_health", {})

        health_components = {
            "agents": {
                "status": system_health.get("status", "unknown"),
                "score": system_health.get("score", 1.0)
            },
            "cache": {
                "status": "healthy" if cache_stats.get("hit_rate", 0) > 0.3 else "degraded",
                "hit_rate": cache_stats.get("hit_rate", 0)
            },
            "load_balancer": {
                "status": "healthy",
                "total_queued": sum(stats["queue_size"] for stats in load_stats.values())
            }
        }

        health_data = {
            **system_health,
            "components": health_components,
            "recommendation": [],
            "timestamp": datetime.now().isoformat()
        }

        if system_health.get("score", 1.0) < 0.9:
            health_issues = system_health.get("issues", [])
            health_data["recommendations"].extend(health_issues)
        
        if cache_stats.get("hit_rate", 0) < 0.3:
            health_data["recommendations"].append("Consider optimizing cache configuration for better performance")
        
        return health_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get system health: %s", e)
        raise HTTPException(status_code=500, detail="System health unavailable")

def get_health_status(agent_perf: Dict[str, Any], agent_load: Dict[str, Any]) -> str:
    """initialise health status from obtained performance stats"""
    
    health_status = "healthy"
    
    success_rate = agent_perf.get("success_rate", 1.0)
    p95_latency = agent_perf.get("p95_ms", 0)
    current_load = agent_load.get("current_load", 0)
    max_load = agent_load.get("max_concurrent", 1)
    
    if success_rate < 0.9 or p95_latency > 10000 or current_load >= max_load:
        health_status = "unhealthy"
    elif success_rate < 0.95 or p95_latency > 5000 or current_load / max_load > 0.8:
        health_status = "degraded"
    
    return health_status
