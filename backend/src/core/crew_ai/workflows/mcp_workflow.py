"""Workflow manager with Gmail MCP integration"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

from src.core.mcp_client import GMailMCPClient
from src.config.settings import get_settings
from src.utils.consts import EMAIL_BODY, TIMEOUT

logger = logging.getLogger(__name__)
settings = get_settings()


class MCPWorkflowManager:
    """Manages workflow with Gmail MCP server integration."""

    POLL_INTERVAL_SECONDS = 10

    def __init__(self) -> None:
        self.pending_reviews: Dict[str, Dict[str, Any]] = {}
        self.review_polling: bool = False
        self.client = GMailMCPClient()

    async def initialise(self) -> None:
        """Initialise MCP connection."""
        try:
            await self.client.connect()
            logger.info("MCP workflow manager initialized")
        except Exception as e:
            logger.error("Failed to initialize MCP workflow manager: %s", e)
            raise

    async def send_for_review(self, prescription_data: Dict[str, Any]) -> str:
        """Send prescription for review via Gmail MCP."""
        review_id = prescription_data.get("review_id")
        if not review_id:
            raise ValueError("prescription_data must contain 'review_id'")

        try:
            body = self._build_review_email_body(prescription_data)
            result = await self.client.send_email(
                to_email=settings.doc_email,
                subject=f"Prescription Review #{review_id}",
                body=body,
            )

            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")
                logger.error("Failed to send prescription review: %s", error_msg)
                raise RuntimeError(f"Gmail MCP send failed: {error_msg}")

            self.pending_reviews[review_id] = {
                "prescription_data": prescription_data,
                "sent_at": datetime.now(),
                "doctor_email": settings.doc_email,
                "message_id": result["message_id"],
                "status": "PENDING",
            }

            if not self.review_polling:
                asyncio.create_task(self._poll_responses())
                logger.info("Started MCP review polling loop")

            return review_id
        except Exception as e:
            logger.error("Failed to send prescription for review: %s", e)
            raise

    async def await_review_result(self, review_id: str) -> Dict[str, Any]:
        """Wait for doctor response with timeout."""

        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < TIMEOUT:
            review = self.pending_reviews.get(review_id)

            if review and review.get("status") == "COMPLETED":
                return review.get("doctor_response", {})

            await asyncio.sleep(self.POLL_INTERVAL_SECONDS)

        return {
            "action": "TIMEOUT",
            "review_id": review_id,
            "message": "Doctor dod not respond in time",
        }

    async def get_mcp_metrics(self) -> Dict[str, Any]:
        """Return MCP workflow metrics for monitoring"""

        pending_reviews = 0
        completed_reviews = 0
        sla_compliant = 0
        total_sla_checked = 0

        try:
            reviews = getattr(self, "reviews", {})
            for _, review in reviews.items():
                status = review.get("status")
                created_at = review.get("created_at")
                completed_at = review.get("completed_at")

                if status in ["PENDING", "SENT", "IN_REVIEW"]:
                    pending_reviews += 1
                elif status in ["APPROVED", "MODIFIED", "REJECTED"]:
                    completed_reviews += 1

                    # SLA calculations
                    if created_at and completed_at:
                        total_sla_checked += 1
                        time_taken = (completed_at - created_at).total_seconds() / 60
                        if time_taken <= review.get("sla_minutes", 60):
                            sla_compliant += 1

            sla_rate = (
                (sla_compliant / total_sla_checked) * 100
                if total_sla_checked > 0
                else 100.0
            )
            return {
                "total_pending_reviews": pending_reviews,
                "total_completed_reviews": completed_reviews,
                "sla_compliance_rate": round(sla_rate, 2),
            }
        except Exception as e:
            return {
                "total_pending_reviews": 0,
                "total_completed_reviews": 0,
                "sla_compliance_rate": 0.0,
                "error": str(e),
            }

    def _build_review_email_body(self, prescription_data: Dict[str, Any]) -> str:
        """Create email body"""
        return EMAIL_BODY.format(
            review_id=prescription_data.get("review_id"),
            age=prescription_data.get("patient_age"),
            gender=prescription_data.get("patient_gender"),
            content=prescription_data.get("prescription_content", ""),
        )

    async def _poll_responses(self) -> None:
        """Poll Gmail MCP for doctor responses."""
        self.review_polling = True
        try:
            while self.pending_reviews:
                for review_id, data in list(self.pending_reviews.items()):
                    await self._check_review(review_id, data)
                await asyncio.sleep(self.POLL_INTERVAL_SECONDS)
        except Exception as e:
            logger.error("Error in response polling: %s", e)
        finally:
            self.review_polling = False
            logger.info("Stopped MCP review polling loop")

    async def _check_review(self, review_id: str, review_data: Dict[str, Any]) -> None:
        """Check for doctor response for a specific review."""
        search_query = f"subject:#{review_id} from:{review_data['doctor_email']}"

        try:
            emails = await self.client.read_emails(search_query, max_results=2)
            sent_at: datetime = review_data.get("sent_at", datetime.min)

            for email in emails:
                date_str = email.get("date") or ""
                try:
                    email_date = datetime.fromisoformat(date_str)
                except ValueError:
                    logger.warning(
                        "Invalid email date for review %s: %r", review_id, date_str
                    )
                    continue

                if email_date > sent_at:
                    await self._process_response(review_id, email)
                    break
        except Exception as e:
            logger.error("Error checking review response for %s: %s", review_id, e)

    async def _process_response(self, review_id: str, email: Dict[str, Any]) -> None:
        """Process doctor's response email."""
        try:
            email_content = email.get("body", "") or ""
            action_data = self._parse_action(email_content, review_id)

            review = self.pending_reviews.get(review_id)
            if not review:
                return

            review.update(
                {
                    "status": "COMPLETED",
                    "doctor_response": action_data,
                    "completed_at": datetime.now(),
                }
            )
            logger.info(
                "Processed doctor response for %s: %s",
                review_id,
                action_data.get("action"),
            )

            del self.pending_reviews[review_id]
            await self._handle_doctor_action(review_id, action_data)
        except Exception as e:
            logger.error("Error processing doctor response for %s: %s", review_id, e)

    async def _handle_doctor_action(
        self, review_id: str, action_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle doctor's action and return outcome"""

        action = action_data["action"]

        # approved
        if action == "APPROVED":
            outcome = {
                "action_taken": "prescription_finalized",
                "message": "Prescription approved and finalized",
                "next_steps": ["deliver_to_patient", "update_medical_records"],
            }
        # modified
        elif action == "MODIFIED":
            outcome = {
                "action_taken": "prescription_modified",
                "modifications": action_data.get("modifications", ""),
                "message": "Prescription modified per doctor's instructions",
                "next_steps": ["regenerate_prescription", "deliver_to_patient"],
            }
        # rejected
        else:
            outcome = {
                "action_taken": "prescription_rejected",
                "reason": action_data.get("reason", ""),
                "message": "Prescription rejected by doctor",
                "next_steps": [
                    "notify_patient",
                    "schedule_follow_up",
                    "restart_consultation",
                ],
            }

        # Log the outcome for tracking
        logger.info(
            "Doctor action handled for %s: $s -> %s",
            review_id,
            action,
            outcome["action_taken"],
        )
        return outcome

    def _parse_action(self, email_content: str, review_id: str) -> Dict[str, Any]:
        """
        Parse doctor's action from email content.

        Supported commands (case‑insensitive), anywhere in the body:
          - APPROVE #<id>
          - MODIFY  #<id> <free‑text>
          - REJECT  #<id> <free‑text>
        """
        email_text = email_content.strip()

        handlers = (
            self._parse_approve,
            self._parse_modify,
            self._parse_reject,
        )
        for handler in handlers:
            result = handler(email_text, review_id)
            if result is not None:
                return result

        logger.warning(
            "No explicit action found in email for review %s; defaulting to REJECTED",
            review_id,
        )
        return {
            "action": "REJECTED",
            "review_id": review_id,
            "reason": "No valid action found in email",
        }

    def _parse_approve(
        self, email_text: str, review_id: str
    ) -> Optional[Dict[str, Any]]:
        pattern = rf"\bAPPROVE\s*#\s*{re.escape(review_id)}\b"
        if not re.search(pattern, email_text, flags=re.IGNORECASE):
            return None
        return {
            "action": "APPROVED",
            "review_id": review_id,
        }

    def _parse_modify(
        self, email_text: str, review_id: str
    ) -> Optional[Dict[str, Any]]:
        pattern = rf"\bMODIFY\s*#\s*{re.escape(review_id)}\b(.*)$"
        match = re.search(pattern, email_text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None

        modifications = match.group(1).strip()
        if modifications.startswith("-"):
            modifications = modifications[1:].strip()

        return {
            "action": "MODIFIED",
            "review_id": review_id,
            "modifications": modifications,
        }

    def _parse_reject(
        self, email_text: str, review_id: str
    ) -> Optional[Dict[str, Any]]:
        pattern = rf"\bREJECT\s*#\s*{re.escape(review_id)}\b(.*)$"
        match = re.search(pattern, email_text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None

        reason = match.group(1).strip()
        if reason.startswith("-"):
            reason = reason[1:].strip()

        return {
            "action": "REJECTED",
            "review_id": review_id,
            "reason": reason,
        }
