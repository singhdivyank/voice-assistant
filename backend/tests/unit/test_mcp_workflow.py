"""Unit tests for src/core/crew_ai/workflows/mcp_workflow.py"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.crew_ai.workflows.mcp_workflow import MCPWorkflowManager


@pytest.fixture()
def manager():
    mgr = MCPWorkflowManager()
    mgr.client = MagicMock()
    mgr.client.connect = AsyncMock()
    mgr.client.send_email = AsyncMock(
        return_value={"success": True, "message_id": "msg_001"}
    )
    mgr.client.read_emails = AsyncMock(return_value=[])
    return mgr


# _parse_action (and helpers)
class TestParseAction:
    def test_approve_detected(self, manager):
        result = manager._parse_action("APPROVE #rev-001", "rev-001")
        assert result["action"] == "APPROVED"
        assert result["review_id"] == "rev-001"

    def test_approve_case_insensitive(self, manager):
        result = manager._parse_action("approve #rev-001", "rev-001")
        assert result["action"] == "APPROVED"

    def test_modify_detected_with_changes(self, manager):
        result = manager._parse_action(
            "MODIFY #rev-002 - reduce dosage by half", "rev-002"
        )
        assert result["action"] == "MODIFIED"
        assert "reduce dosage" in result["modifications"]

    def test_reject_detected_with_reason(self, manager):
        result = manager._parse_action(
            "REJECT #rev-003 - patient allergy to penicillin", "rev-003"
        )
        assert result["action"] == "REJECTED"
        assert "allergy" in result["reason"]

    def test_no_action_defaults_to_rejected(self, manager):
        result = manager._parse_action("Thanks for sending this.", "rev-004")
        assert result["action"] == "REJECTED"
        assert "No valid action" in result["reason"]

    def test_wrong_review_id_does_not_match(self, manager):
        result = manager._parse_action("APPROVE #rev-999", "rev-001")
        # rev-999 ≠ rev-001 → no approve match → defaults to REJECTED
        assert result["action"] == "REJECTED"

    def test_modify_without_dash_separator(self, manager):
        result = manager._parse_action("MODIFY #r1 change medication to aspirin", "r1")
        assert result["action"] == "MODIFIED"
        assert "aspirin" in result["modifications"]


# _build_review_email_body
class TestBuildReviewEmailBody:
    def test_contains_review_id(self, manager):
        data = {
            "review_id": "rev-007",
            "patient_age": 45,
            "patient_gender": "male",
            "prescription_content": "Amoxicillin 500mg",
        }
        body = manager._build_review_email_body(data)
        assert "rev-007" in body
        assert "45" in body
        assert "Amoxicillin" in body

    def test_contains_action_instructions(self, manager):
        data = {
            "review_id": "r1",
            "patient_age": 30,
            "patient_gender": "female",
            "prescription_content": "Test",
        }
        body = manager._build_review_email_body(data)
        assert "APPROVE" in body
        assert "MODIFY" in body
        assert "REJECT" in body


# get_mcp_metrics
class TestGetMcpMetrics:
    @pytest.mark.asyncio
    async def test_empty_pending_returns_zeros(self, manager):
        metrics = await manager.get_mcp_metrics()
        assert metrics["total_pending_reviews"] == 0
        assert metrics["total_completed_reviews"] == 0
        assert metrics["sla_compliance_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_counts_pending_reviews(self, manager):
        manager.pending_reviews["rev-1"] = {"status": "PENDING"}
        manager.pending_reviews["rev-2"] = {"status": "SENT"}
        metrics = await manager.get_mcp_metrics()
        assert metrics["total_pending_reviews"] == 2

    @pytest.mark.asyncio
    async def test_counts_completed_reviews(self, manager):
        manager.pending_reviews["rev-3"] = {"status": "APPROVED"}
        manager.pending_reviews["rev-4"] = {"status": "REJECTED"}
        metrics = await manager.get_mcp_metrics()
        assert metrics["total_completed_reviews"] == 2


# send_for_review
class TestSendForReview:
    @pytest.mark.asyncio
    async def test_raises_if_no_review_id(self, manager):
        with pytest.raises(ValueError, match="review_id"):
            await manager.send_for_review({})

    @pytest.mark.asyncio
    async def test_adds_to_pending_reviews_on_success(self, manager):
        manager.client.send_email = AsyncMock(
            return_value={"success": True, "message_id": "msg_xyz"}
        )
        with patch("src.config.settings.get_settings") as mock_settings:
            mock_settings.return_value.doc_email = "doc@hospital.com"
            manager.client.connected = True
            await manager.send_for_review(
                {
                    "review_id": "rev-010",
                    "patient_age": 30,
                    "patient_gender": "female",
                    "prescription_content": "Aspirin",
                }
            )
        assert "rev-010" in manager.pending_reviews

    @pytest.mark.asyncio
    async def test_raises_on_send_failure(self, manager):
        manager.client.send_email = AsyncMock(
            return_value={"success": False, "error": "SMTP error"}
        )
        with pytest.raises(RuntimeError, match="Gmail MCP send failed"):
            await manager.send_for_review(
                {
                    "review_id": "rev-fail",
                    "patient_age": 25,
                    "patient_gender": "male",
                    "prescription_content": "Test",
                }
            )


# await_review_result (timeout path)
class TestAwaitReviewResult:
    @pytest.mark.asyncio
    async def test_times_out_and_returns_timeout_dict(self, manager):
        """With TIMEOUT=0 the while-loop exits immediately."""
        with patch("src.core.crew_ai.workflows.mcp_workflow.TIMEOUT", 0):
            result = await manager.await_review_result("rev-missing")
        assert result["action"] == "TIMEOUT"
        assert result["review_id"] == "rev-missing"

    @pytest.mark.asyncio
    async def test_returns_response_when_completed(self, manager):
        manager.pending_reviews["rev-done"] = {
            "status": "COMPLETED",
            "doctor_response": {"action": "APPROVED"},
        }
        result = await manager.await_review_result("rev-done")
        assert result["action"] == "APPROVED"
