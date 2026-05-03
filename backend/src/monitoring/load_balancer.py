"""Load balancer for distributing agent workload"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, Dict, Optional

from src.config.monitoring import telemetry

logger = logging.getLogger(__name__)


class AgentLoadBalancer:
    """Create Load Balancer"""

    def __init__(self, max_concurrent_agents: Optional[Dict[str, int]] = None):
        self.max_concurrent = max_concurrent_agents or {
            "stt": 3,
            "translation": 5,
            "qa": 2,
            "diagnosis": 2,
            "prescription": 2,
            "tts": 4,
        }
        self.current_load: Dict[str, int] = defaultdict(int)
        self.wait_queues: Dict[str, asyncio.Queue] = {
            agent: asyncio.Queue() for agent in self.max_concurrent.keys()
        }
        self.total_processed: Dict[str, int] = defaultdict(int)
        self.total_queued: Dict[str, int] = defaultdict(int)

    async def acquire_slot(self, agent_name: str) -> None:
        """Acquire execution slot for agent"""

        if agent_name not in self.max_concurrent:
            return

        max_concurrent = self.max_concurrent[agent_name]
        if self.current_load[agent_name] >= max_concurrent:
            self.total_queued[agent_name] += 1
            logger.debug(
                "Agent %s queued, current load: %d/%d",
                agent_name,
                self.current_load[agent_name],
                max_concurrent,
            )

            telemetry.increment_counter(
                "agent_queue_operations",
                attributes={"agent": agent_name, "operation": "queued"},
            )

            await self.wait_queues[agent_name].put(None)
            await self.wait_queues[agent_name].get()

        self.current_load[agent_name] += 1
        self.total_processed[agent_name] += 1
        telemetry.record_histogram(
            "agent_concurrent_load",
            self.current_load[agent_name],
            attributes={"agent": agent_name},
        )

    def release_slot(self, agent_name: str) -> None:
        """Release execution slot for agent"""

        if agent_name not in self.max_concurrent:
            return

        if self.current_load[agent_name] > 0:
            self.current_load[agent_name] -= 1

            if not self.wait_queues[agent_name].empty():
                try:
                    self.wait_queues[agent_name].put_nowait(None)
                except asyncio.QueueFull:
                    pass

            telemetry.increment_counter(
                "agent_queue_operations",
                attributes={"agent": agent_name, "operation": "released"},
            )

    def get_load_stats(self) -> Dict[str, Any]:
        """Get current load balancing statistics"""

        stats = {}

        for agent_name in self.max_concurrent.keys():
            current = self.current_load[agent_name]
            max_concurrent = self.max_concurrent[agent_name]
            utilization = current / max_concurrent if max_concurrent > 0 else 0

            stats[agent_name] = {
                "current_load": current,
                "max_concurrent": max_concurrent,
                "utilization": round(utilization, 3),
                "queue_size": self.wait_queues[agent_name].qsize(),
                "total_processed": self.total_processed[agent_name],
                "total_queued": self.total_queued[agent_name],
            }

        return stats


load_balancer = AgentLoadBalancer()
