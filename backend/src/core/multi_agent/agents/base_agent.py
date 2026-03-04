import logging
import time
from typing import Any

from src.core.multi_agent.llm_manager import llm_manager
from src.monitoring import (
    cache_manager, 
    load_balancer, 
    performance_monitor
)

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all agents with performance monitoring, caching, and load balancing"""

    def __init__(self, agent_name):
        self.agent_name = agent_name
        self.llm_manager = llm_manager
    
    async def execute_with_monitoring(self, state: Any) -> Any:
        """Execute agent with full monitoring and optimization"""

        cached_result = cache_manager.get(self.agent_name, state)
        if cached_result is not None:
            logger.debug("Using cached result for agent %s", self.agent_name)
            return cached_result
        
        await load_balancer.acquire_slot(self.agent_name)

        start_time = time.perf_counter()
        success = False
        try:
            result = await self._execute_logic(state)
            success = True
            cache_manager.set(self.agent_name, state, result)
            return result
        except Exception as e:
            logger.error("Agent %s execution failed: %s", self.agent_name, e)
            raise
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            performance_monitor.record_agent_execution(self.agent_name, duration_ms, success)
            load_balancer.release_slot(self.agent_name)
        
    async def _execute_logic(self, state: Any) -> Any:
        """Override in subclasses"""
        raise NotImplementedError
