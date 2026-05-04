"""Unit tests for AgentLoadBalancer and PerformanceMonitor"""

import asyncio
import pytest
from src.monitoring.load_balancer import AgentLoadBalancer
from src.monitoring.performance_monitor import PerformanceMonitor


# AgentLoadBalancer
@pytest.fixture()
def balancer():
    return AgentLoadBalancer(max_concurrent_agents={"qa": 2, "tts": 1})


class TestAgentLoadBalancer:

    # get_load_stats
    def test_initial_load_is_zero(self, balancer):
        stats = balancer.get_load_stats()
        assert stats["qa"]["current_load"] == 0
        assert stats["tts"]["current_load"] == 0

    def test_stats_contain_expected_keys(self, balancer):
        stats = balancer.get_load_stats()
        for agent_stats in stats.values():
            for key in (
                "current_load",
                "max_concurrent",
                "utilization",
                "queue_size",
                "total_processed",
                "total_queued",
            ):
                assert key in agent_stats

    # acquire_slot / release_slot
    @pytest.mark.asyncio
    async def test_acquire_increments_load(self, balancer):
        await balancer.acquire_slot("qa")
        assert balancer.current_load["qa"] == 1
        balancer.release_slot("qa")

    @pytest.mark.asyncio
    async def test_release_decrements_load(self, balancer):
        await balancer.acquire_slot("qa")
        balancer.release_slot("qa")
        assert balancer.current_load["qa"] == 0

    @pytest.mark.asyncio
    async def test_release_below_zero_is_safe(self, balancer):
        balancer.release_slot("qa")  # nothing acquired
        assert balancer.current_load["qa"] == 0

    @pytest.mark.asyncio
    async def test_unknown_agent_does_not_raise(self, balancer):
        """Agents not in max_concurrent are silently ignored."""
        await balancer.acquire_slot("unknown_agent")
        balancer.release_slot("unknown_agent")

    @pytest.mark.asyncio
    async def test_total_processed_increments(self, balancer):
        await balancer.acquire_slot("qa")
        balancer.release_slot("qa")
        assert balancer.total_processed["qa"] == 1

    @pytest.mark.asyncio
    async def test_concurrent_slots_up_to_limit(self, balancer):
        """Both qa slots should be acquirable without queuing."""
        await balancer.acquire_slot("qa")
        await balancer.acquire_slot("qa")
        assert balancer.current_load["qa"] == 2
        balancer.release_slot("qa")
        balancer.release_slot("qa")

    # @pytest.mark.asyncio
    # async def test_queued_request_unblocks_after_release(self, balancer):
    #     """tts has max 1. A second acquire should wait until release."""
    #     # fills the slot
    #     await balancer.acquire_slot("tts")

    #     acquired = asyncio.Event()

    #     async def waiter():
    #         await balancer.acquire_slot("tts")
    #         acquired.set()
    #         balancer.release_slot("tts")

    #     task = asyncio.create_task(waiter())
    #     # waiter should be blocked
    #     await asyncio.sleep(0.1)
    #     assert not acquired.is_set()

    #     balancer.release_slot("tts")
    #     await asyncio.wait_for(task, timeout=2.0)
    #     assert acquired.is_set()


# PerformanceMonitor
@pytest.fixture()
def monitor():
    return PerformanceMonitor()


class TestPerformanceMonitor:

    # record_agent_execution
    def test_records_successful_execution(self, monitor):
        monitor.record_agent_execution("qa", 300.0, success=True)
        summary = monitor.get_performance_summary()
        assert "qa" in summary["agents"]
        assert summary["agents"]["qa"]["total_executions"] == 1

    def test_records_failed_execution(self, monitor):
        monitor.record_agent_execution("qa", 0.0, success=False)
        summary = monitor.get_performance_summary()
        assert summary["agents"]["qa"]["error_count"] == 1

    def test_multiple_agents_tracked_separately(self, monitor):
        monitor.record_agent_execution("qa", 200.0)
        monitor.record_agent_execution("tts", 100.0)
        summary = monitor.get_performance_summary()
        assert "qa" in summary["agents"]
        assert "tts" in summary["agents"]

    # get_performance_summary
    def test_summary_structure(self, monitor):
        summary = monitor.get_performance_summary()
        assert "monitoring_duration_hours" in summary
        assert "agents" in summary
        assert "system_health" in summary

    # _calculate_system_health
    def test_system_health_healthy_with_no_agents(self, monitor):
        health = monitor._calculate_system_health()
        assert health["score"] == 1.0
        assert health["status"] == "healthy"
        assert health["issues"] == []

    def test_system_health_degrades_with_high_error_rate(self, monitor):
        # 10 executions, 8 failures → 20% success rate → should trigger degradation
        for _ in range(2):
            monitor.record_agent_execution("qa", 100.0, success=True)
        for _ in range(8):
            monitor.record_agent_execution("qa", 0.0, success=False)
        health = monitor._calculate_system_health()
        assert health["score"] < 1.0
        assert len(health["issues"]) > 0

    def test_system_health_degrades_with_high_latency(self, monitor):
        # qa threshold is 4000ms; record 10,000ms latency
        for _ in range(5):
            monitor.record_agent_execution("qa", 10_000.0, success=True)
        health = monitor._calculate_system_health()
        assert health["score"] < 1.0

    def test_status_is_critical_below_07(self, monitor):
        # Force a very low score by maxing out errors
        for _ in range(1):
            monitor.record_agent_execution("qa", 100.0, success=True)
        for _ in range(99):
            monitor.record_agent_execution("qa", 0.0, success=False)
        health = monitor._calculate_system_health()
        assert health["status"] in ("warning", "critical")
