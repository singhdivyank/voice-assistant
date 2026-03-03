import logging
from datetime import datetime
from typing import Any, Dict

from .load_balancer import AgentLoadBalancer
from .cache_manager import CacheManager
from .performance_monitor import PerformanceMonitor

logger = logging.getLogger(__name__)


class MonitoringDashboard:
    """Provides data for monitoring dashboard"""

    def __init__(self):
        self.load_balancer = AgentLoadBalancer()
        self.cache_manager = CacheManager()
        self.performance_monitor = PerformanceMonitor()
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive monitoring dashboard data"""

        return {
            "timestamp": datetime.now().isoformat(),
            "performance": self.performance_monitor.get_performance_summary(),
            "cache": self.cache_manager.get_stats(),
            "load_balancing": self.load_balancer.get_load_stats(),
            "system_metrics": await self._get_system_metrics()
        }
    
    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics"""

        import psutil

        try:
            return {
                "cpu_usage_percent": psutil.cpu_percent(interval=1),
                "memory_usage_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                "process_count": len(psutil.pids())
            }
        except Exception as e:
            logger.error("Failed to get system metrics: %s", e)
            return {"error": str(e)}

monitoring_dashboard = MonitoringDashboard()
