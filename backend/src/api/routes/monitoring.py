import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.exceptions import HTTPException

from src.api.routes.helpers import get_health_status
from src.config.monitoring import telemetry
from src.monitoring.dashboard import monitoring_dashboard

logger = logging.getLogger(__name__)
router = APIRouter()

AGENTS = ["stt", "translation", "qa", "diagnosis", "medication", "prescription", "tts"]

@router.get("/dashboard")
async def get_dashboard():
    """get monitoring dashboard for with all metrics"""

    try:
        dashboard_data = await monitoring_dashboard.get_dashboard_data()
        dashboard_data.update({
            "dashboard_version": "v2.0",
            "last_updated": datetime.now().isoformat(),
            "monitoring_endpoints": {
                "performance": "/monitoring/performance",
                "cache": "/monitoring/cache", 
                "load_balancing": "/monitoring/load-balancing",
                "agents": "/monitoring/agents",
                "health": "/monitoring/health"
            }
        })
        return dashboard_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get dashboard data: %s", e)
        raise HTTPException(status_code=500, detail="Dashboard data unavailable")

@router.get("/performance")
async def get_performance_metrics(
    agent_name: Optional[str] = Query(None, description="Filter by specific agent"),
    hours: int = Query(24, description="Hours of data to return", ge=1, le=168)
):
    """get detailed performance metrics for agents"""

    try:
        performance_data = monitoring_dashboard.performance_monitor.get_performance_summary()
        if agent_name:
            perfomance = performance_data.get("agents", {})
            if agent_name not in perfomance:
                raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
            
            return {
                "agent": agent_name,
                "metrics": perfomance[agent_name],
                "system_health": performance_data.get("system_health", {}),
                "query_params": {"agent_name": agent_name, "hours": hours}
            }
        
        performance_data["query_params"] = {"hours": hours}
        performance_data["available_agents"] = list(performance_data.get("agents", {}).keys())
        return performance_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get performance metrics: %s", e)
        raise HTTPException(status_code=500, detail="Performance metrics unavailable")

@router.get("/cache")
async def get_cache_statistics():
    """retrieve intelligent cache stats"""

    try:
        cache_stats = monitoring_dashboard.cache_manager.get_stats()
        cache_stats["agent_configurations"] = monitoring_dashboard.cache_manager.agent_cache_config
        cache_stats["recommendations"] = []

        hit_rate = cache_stats.get("hit_rate", 0)
        if hit_rate < 0.3:
            cache_stats["recommendations"].append("Low hit rate detected. Consider increasing cache TTL or reviewing cache keys.")
        
        utilization = cache_stats.get("memory_usage", {}).get("utilization", 0)
        if utilization > 0.9:
            cache_stats["recommendations"].append("High cache utilization. Consider increasing max_size")

        return cache_stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get cache statistics: %s", e)
        raise HTTPException(status_code=500, detail="Cache stats unavailable")

@router.post("/cache/clear")
async def clear_cache():
    """clear cache across all agents"""

    cleared_counts = {}

    try:
        for agent in AGENTS:
            initial_size = len([k for k in monitoring_dashboard.cache_manager._cache.keys() if k.startswith(f"{agent}:")])
            monitoring_dashboard.cache_manager.clear_agent_cache(agent)
            final_size = len([k for k in monitoring_dashboard.cache_manager._cache.keys() if k.startswith(f"{agent}:")])
            cleared_counts[agent] = initial_size - final_size
        
        logger.error("All cache cleared")
        telemetry.increment_counter("cache_manual_clears", attributes={"scope": "all"})

        return {
            "status": "all_cache_cleared",
            "cleared_entries_per_agent": cleared_counts,
            "total_cleared": sum(cleared_counts.values()),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to clear caches: %s", e)
        raise HTTPException(status_code=500, detail="Cache clearing failed")

@router.post("/cache/clear/{agent_name}")
async def clear_agent_cache(agent_name: str):
    """clear cache for specific agent"""
    
    if agent_name not in AGENTS:
        raise HTTPException(status_code=400, detail=f"Invalid agent name. Must be from: {AGENTS}")
    
    try:
        initial_size = len([k for k in monitoring_dashboard.cache_manager._cache.keys() if k.startswith(f"{agent_name}:")])
        monitoring_dashboard.cache_manager.clear_agent_cache(agent_name)
        final_size = len([k for k in monitoring_dashboard.cache_manager._cache.keys() if k.startswith(f"{agent_name}:")])
        cleared_count = initial_size - final_size

        logger.info("Cache cleared for agent %s: %d entries", agent_name, cleared_count)
        telemetry.increment_counter("cache_manual_clears", attributes={"agent": agent_name})

        return {
            "status": "cache_cleared",
            "agent": agent_name,
            "entries_cleared": cleared_count,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to clear cache for agent %s: %s", agent_name, e)
        raise HTTPException(status_code=500, detail=f"Cache clearing failed for {agent_name}")

@router.get("/load-balancing")
async def get_load_balancing_stats():
    """retrieve load balancing stats for all agents"""

    try:
        load_stats = monitoring_dashboard.load_balancer.get_load_stats()

        total_current_load = sum(stats["current_load"] for stats in load_stats.values())
        total_max_capacity = sum(stats["max_concurrent"] for stats in load_stats.values())
        overall_utilization = total_current_load / max(1, total_max_capacity)
        return {
            "agents": load_stats,
            "system_summary": {
                "total_current_load": total_current_load,
                "total_max_capacity": total_max_capacity,
                "overall_utilization": round(overall_utilization, 3),
                "agents_at_capacity": [
                    agent for agent, stats in load_stats.items() 
                    if stats["current_load"] >= stats["max_concurrent"]
                ],
                "total_queued_requests": sum(stats["queue_size"] for stats in load_stats.values())
            },
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get load balancing stats: %s", e)
        raise HTTPException(status_code=500, detail="Load balancing data unavailable")

@router.get("/agents")
async def get_agent_status():
    """get the status and health information of all agents"""

    agent_status = {}
    
    try:
        performance_data = monitoring_dashboard.performance_monitor.get_performance_summary()
        load_data = monitoring_dashboard.load_balancer.get_load_stats()

        for agent_name in AGENTS:
            agent_perf = performance_data.get("agents", {}).get(agent_name, {})
            agent_load = load_data.get(agent_name, {})
            health_status = get_health_status(agent_perf, agent_load)
            agent_status[agent_name] = {
                "health_status": health_status,
                "performance": agent_perf,
                "load_balancing": agent_load,
                "last_executed": agent_perf.get("total_executions", 0) > 0
            }

        return {
            "agents": agent_status,
            "summary": {
                "healthy_agents": len([a for a in agent_status.values() if a["health_status"] == "healthy"]),
                "degraded_agents": len([a for a in agent_status.values() if a["health_status"] == "degraded"]),
                "unhealthy_agents": len([a for a in agent_status.values() if a["health_status"] == "unhealthy"]),
                "total_agents": len(agent_status)
            },
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get agent status: %s", e)
        raise HTTPException(status_code=500, detail="Agent status unavailable")

@router.get("/health")
async def get_system_health():
    """get overall system health score and status"""

    try:
        performance_data = monitoring_dashboard.performance_monitor.get_performance_summary()
        cache_stats = monitoring_dashboard.cache_manager.get_stats()
        load_stats = monitoring_dashboard.load_balancer.get_load_stats()
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
            "recommendations": [],
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
