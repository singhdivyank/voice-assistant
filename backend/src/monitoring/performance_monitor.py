import logging
from datetime import datetime
from collections import defaultdict
from typing import Any, Dict, List

from src.utils.consts import AgentPerformanceMetrics
from src.config.monitoring import telemetry

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Advanced performance monitoring for multi-agent system"""

    def __init__(self):
        self.agent_metrics: Dict[str, AgentPerformanceMetrics] = {}
        self.workflow_metrics: Dict[str, List[float]] = defaultdict(list)
        self.start_time = datetime.now()
        self.latency_threshold = 5000
        self.error_rate_threshold = 0.05
        self.consecutive_error_threshold = 3
        self.agent_thresholds = {
            "stt": {"latency_ms": 3000, "error_rate": 0.03},
            "translation": {"latency_ms": 2000, "error_rate": 0.02},
            "qa": {"latency_ms": 4000, "error_rate": 0.05},
            "diagnosis": {"latency_ms": 6000, "error_rate": 0.05},
            "prescription": {"latency_ms": 5000, "error_rate": 0.05},
            "tts": {"latency_ms": 4000, "error_rate": 0.03}
        }
    
    def record_agent_execution(self, agent_name: str, duration_ms: float, success: bool = True):
        """Record agent execution metrics"""

        self.agent_name = agent_name
        if self.agent_name not in self.agent_metrics:
            self.agent_metrics[self.agent_name] = AgentPerformanceMetrics(self.agent_name)
        
        self.agent_metrics[self.agent_name].update(duration_ms, success)
        telemetry.record_histogram(
            "agent_execution_duration",
            duration_ms,
            attributes={
                "agent": self.agent_name,
                "success": success
            }
        )

        self._check_performance_alerts()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""

        summary = {
            "monitoring_duration_hours": (datetime.now() - self.start_time).total_seconds() / 3600,
            "agents": {},
            "workflows": {},
            "system_health": self._calculate_system_health()
        }

        for agent_name, metrics in self.agent_metrics.items():
            summary["agents"][agent_name] = metrics.to_dict()

        for workflow_name, durations in self.workflow_metrics.items():
            if durations:
                summary["workflows"][workflow_name] = {
                    "total_executions": len(durations),
                    "average_duration_ms": round(sum(durations) / len(durations), 2),
                    "min_duration_ms": round(min(durations), 2),
                    "max_duration_ms": round(max(durations), 2),
                }
        
        return summary
    
    def _check_performance_alerts(self):
        """Check if agent performance exceeds thresholds"""

        metrics = self.agent_metrics[self.agent_name]
        thresholds = self.agent_metrics.get(self.agent_name, {})

        latency_threshold = thresholds.get("latency_ms", self.latency_threshold)
        if metrics.p95_ms > latency_threshold:
            logger.warning(
                "High latency alert: Agent %s P95 latency %.2fms exceeds threshold %.2fms",
                self.agent_name, metrics.p95_ms, latency_threshold
            )
            telemetry.increment_counter(
                "performance_alerts",
                attributes={"agent": self.agent_name, "type": "high_latency"}
            )
        
        error_threshold = thresholds.get("error_rate", self.error_rate_threshold)
        if metrics.success_rate < (1 - error_threshold):
            logger.warning(
                "High error rate alert: Agent %s error rate %.2f%% exceeds threshold %.2f%%",
                self.agent_name, (1 - metrics.success_rate) * 100, error_threshold * 100
            )
            telemetry.increment_counter(
                "performance_alerts",
                attributes={"agent": self.agent_name, "type": "high_error_rate"}
            )
    
    def _calculate_system_health(self) -> Dict[str, Any]:
        """Calculate overall system health score"""

        if not self.agent_metrics:
            return {"score": 1.0, "status": "healthy", "issues": []}
        
        issues = []
        total_score = 0
        num_agents = len(self.agent_metrics)

        for agent_name, metrics in self.agent_metrics.items():
            agent_score = 1.0

            if metrics.success_rate - 0.95 < 0:
                agent_score -= (0.95 - metrics.success_rate) * 2
                issues.append(f"Agent {agent_name} has high error rate: {(1-metrics.success_rate)*100:.1f}%")
            
            threshold = self.agent_thresholds.get(agent_name, {}).get("latency_ms", self.latency_threshold)
            if metrics.p95_ms > threshold:
                agent_score -= min(0.3, (metrics.p95_ms - threshold) / threshold * 0.5)
                issues.append(f"Agent {agent_name} has high latency: {metrics.p95_ms:.0f}ms")
            
            total_score += max(0, agent_score)
        
        overall_score = total_score / num_agents if num_agents > 0 else 1.0
        if overall_score >= 0.9:
            status = "healthy"
        elif overall_score >= 0.7:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "score": round(overall_score, 3),
            "status": status,
            "issues": issues
        }

performance_monitor = PerformanceMonitor()
