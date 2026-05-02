"""Gmail MCP server integration tools"""

import asyncio
import json
import logging
from pydantic import BaseModel

from crewai_tools import BaseTool

from .mcp_client import GMailMCPClient
from src.utils.consts import GmailSendInput, GmailReadInput

logger = logging.getLogger(__name__)
gmail_client = GMailMCPClient()


class GMailMCPSendTool(BaseTool):
    name: str = "gmail_mcp_send"
    description: str = "Send emails via Gmail MCP server for review"
    args_schema: type[BaseModel] = GmailSendInput

    def _run(self, to: str, subject: str, body: str, review_id: str) -> str:
        """Send email via GMail MCP server"""

        try:
            if not gmail_client.connected:
                asyncio.run(gmail_client.connect())
            
            result = asyncio.run(gmail_client.send_email(
                to=to,
                subject=subject,
                body=body
            ))

            is_success = result.get('success', False)
            if not is_success:
                return json.dumps({
                    "status": "EMAIL_FAILED",
                    "error": result.get('error')
                })
            
            return json.dumps({
                "status": "EMAIL_SENT",
                "review_id": review_id,
                "message_id": result.get('message_id'),
                "timestamp": result.get('timestamp'),
                "recipient": to
            })
        except Exception as e:
            logger.error(f"GMail MCP send tool failed: {e}")
            return json.dumps({
                "status": "ERROR",
                "message": f"Gmail MCP integration failed: {str(e)}"
            })


class GMailMCPReadTool(BaseTool):
    name: str = "gmail_mcp_read"
    description: str = "Read emails via Gmail MCP server to check for doctor responses"
    args_schema: type[BaseModel] = GmailReadInput

    def _run(self, search_query: str, max_results: int = 2) -> str:
        """Read emails via Gmail MCP server"""

        try:
            if not gmail_client.connected:
                asyncio.run(gmail_client.connect())
            
            emails = asyncio.run(gmail_client.read_emails(search_query, max_results))
            return json.dumps({
                "status": "EMAIL_READ",
                "count": len(emails),
                "emails": emails
            })
        except Exception as e:
            logger.error(f"Gmail MCP read tool failed: {e}")
            return json.dumps({
                "status": "ERROR",
                "message": f"Gmail MCP read failed: {str(e)}"
            })
