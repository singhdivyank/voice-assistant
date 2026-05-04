"""
Integration tests for:
  - /api/v2/monitoring/*   (monitoring routes)
  - /api/v2/health/*       (health check routes)
  - /health and /ready     (root health endpoints)

All heavy dependencies (psutil, LLM, crews) are mocked.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# Shared mock for MonitoringDashboard
@pytest.fixture(autouse=True)
def mock_dashboard(client):
    """Patch monitoring_dashboard at every location it's imported."""
    dashboard = MagicMock()

    # Performance monitor
    dashboard.performance_monitor.get_performance_summary.return_value = {
        "monitoring_duration_hours": 1.0,
        "agents": {
            "qa": {
                "total_executions": 10,
                "average_duration_ms": 200.0,
                "success_rate": 0.95,
                "p95_ms": 400.0,
                "error_count": 0,
            }
        },
        "system_health": {"score": 0.98, "status": "healthy", "issues": []},
    }

    # Cache manager
    dashboard.cache_manager.get_stats.return_value = {
        "total_entries": 5,
        "hits": 8,
        "misses": 2,
        "hit_rate": 0.8,
        "evictions": 0,
        "memory_usage": {"cache_size": 5, "max_size": 1000, "utilization": 0.005},
    }
    dashboard.cache_manager.agent_cache_config = {
        "translation": {"ttl": 7200, "enabled": True},
        "qa": {"ttl": 3600, "enabled": True},
    }
    dashboard.cache_manager._cache = {}
    dashboard.cache_manager.clear_agent_cache = MagicMock()

    # Load balancer
    dashboard.load_balancer.get_load_stats.return_value = {
        "qa": {
            "current_load": 0,
            "max_concurrent": 2,
            "utilization": 0.0,
            "queue_size": 0,
            "total_processed": 5,
            "total_queued": 0,
        },
        "tts": {
            "current_load": 1,
            "max_concurrent": 4,
            "utilization": 0.25,
            "queue_size": 0,
            "total_processed": 3,
            "total_queued": 0,
        },
    }

    # Dashboard data
    dashboard.get_dashboard_data = AsyncMock(
        return_value={
            "performance": {
                "system_health": {"score": 0.98, "status": "healthy", "issues": []}
            },
            "cache": {"hit_rate": 0.8},
            "load_balancing": {},
            "system_metrics": {"cpu_usage_percent": 20.0},
        }
    )

    with (
        patch("src.api.routes.monitoring.monitoring_dashboard", dashboard),
        patch("src.api.routes.health_checks.monitoring_dashboard", dashboard),
        patch("src.api.main.monitoring_dashboard", dashboard),
    ):
        yield dashboard


# Monitoring routes
class TestMonitoringDashboard:
    def test_dashboard_returns_200(self, client):
        resp = client.get("/api/v2/monitoring/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "dashboard_version" in data
        assert "last_updated" in data

    def test_dashboard_contains_monitoring_endpoints(self, client):
        resp = client.get("/api/v2/monitoring/dashboard")
        assert "monitoring_endpoints" in resp.json()


class TestPerformanceMetrics:
    def test_returns_all_agents(self, client):
        resp = client.get("/api/v2/monitoring/performance")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert "system_health" in data

    def test_filter_by_known_agent(self, client):
        resp = client.get("/api/v2/monitoring/performance?agent_name=qa")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent"] == "qa"
        assert "metrics" in data

    def test_filter_by_unknown_agent_returns_404(self, client):
        resp = client.get("/api/v2/monitoring/performance?agent_name=ghost_agent")
        assert resp.status_code == 404


class TestCacheStats:
    def test_returns_cache_stats(self, client):
        resp = client.get("/api/v2/monitoring/cache")
        assert resp.status_code == 200
        data = resp.json()
        assert "hit_rate" in data
        assert "total_entries" in data
        assert "recommendations" in data

    def test_low_hit_rate_adds_recommendation(self, client, mock_dashboard):
        mock_dashboard.cache_manager.get_stats.return_value = {
            "total_entries": 0,
            "hits": 0,
            "misses": 10,
            "hit_rate": 0.1,
            "evictions": 0,
            "memory_usage": {"utilization": 0.0},
        }
        resp = client.get("/api/v2/monitoring/cache")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["recommendations"]) > 0


class TestClearCache:
    def test_clears_all_agent_caches(self, client):
        resp = client.post("/api/v2/monitoring/cache/clear")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "all_cache_cleared"
        assert "total_cleared" in data

    def test_clears_specific_agent_cache(self, client):
        resp = client.post("/api/v2/monitoring/cache/clear/qa")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent"] == "qa"
        assert data["status"] == "cache_cleared"

    def test_invalid_agent_name_returns_400(self, client):
        resp = client.post("/api/v2/monitoring/cache/clear/nonexistent_agent")
        assert resp.status_code == 400


class TestLoadBalancingStats:
    def test_returns_agent_load_stats(self, client):
        resp = client.get("/api/v2/monitoring/load-balancing")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert "system_summary" in data
        assert "total_current_load" in data["system_summary"]

    def test_system_summary_fields(self, client):
        resp = client.get("/api/v2/monitoring/load-balancing")
        summary = resp.json()["system_summary"]
        for key in (
            "total_current_load",
            "total_max_capacity",
            "overall_utilization",
            "agents_at_capacity",
        ):
            assert key in summary


class TestAgentStatus:
    def test_returns_all_agents_status(self, client):
        resp = client.get("/api/v2/monitoring/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert "summary" in data
        for key in (
            "healthy_agents",
            "degraded_agents",
            "unhealthy_agents",
            "total_agents",
        ):
            assert key in data["summary"]


class TestMonitoringHealth:
    def test_returns_health_data(self, client):
        resp = client.get("/api/v2/monitoring/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "components" in data
        assert "recommendations" in data


# Health check routes
@pytest.fixture(autouse=True)
def mock_health_deps(client):
    """Patch crew and llm_manager for health routes."""
    mock_crew = MagicMock()
    mock_crew._initialised = True
    mock_crew.agents = {"qa": MagicMock(role="Question Generator")}
    mock_crew.initialise = AsyncMock()
    mock_crew.mcp_manager = MagicMock()
    mock_crew.mcp_manager.get_mcp_metrics = AsyncMock(
        return_value={
            "total_pending_reviews": 0,
            "total_completed_reviews": 0,
            "sla_compliance_rate": 100.0,
        }
    )

    mock_llm = MagicMock()
    mock_llm.call_llm = AsyncMock(return_value="ok")

    with (
        patch("src.api.routes.health_checks.medical_crew", mock_crew),
        patch("src.api.routes.health_checks.llm_manager", mock_llm),
    ):
        yield


class TestReadinessCheck:
    def test_returns_ready_status(self, client):
        resp = client.get("/api/v2/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "components" in data

    def test_components_present(self, client):
        resp = client.get("/api/v2/health/ready")
        data = resp.json()
        for component in (
            "llm_manager",
            "crewai_medical_service",
            "cache_system",
            "load_balancer",
        ):
            assert component in data["components"]


class TestStartupCheck:
    def test_returns_initialized_status(self, client):
        resp = client.get("/api/v2/health/startup")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "startup_checks" in data

    def test_startup_checks_include_configuration(self, client):
        resp = client.get("/api/v2/health/startup")
        data = resp.json()
        assert "configuration" in data["startup_checks"]


# Root-level health endpoints
class TestRootHealthEndpoints:
    def test_health_returns_healthy(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] in ("healthy", "degraded")

    def test_ready_returns_ready(self, client):
        resp = client.get("/ready")
        assert resp.status_code == 200
        assert "status" in resp.json()

    def test_root_returns_api_info(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert "api_versions" in data
        assert "v1" in data["api_versions"]
        assert "v2" in data["api_versions"]
