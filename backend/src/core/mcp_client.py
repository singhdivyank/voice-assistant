import logging
import uuid
from datetime import datetime
from typing import Any, List, Dict

from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GMailMCPClient:
    """Client for GMail MCP server integration"""

    def __init__(self):
        # TODO- update once in production
        self.mcp_endpoint = settings.mcp_server
        self.connected = False
    
    async def connect(self):
        """Connect to Gmail MCP server"""

        try:
            import mcp_client
            self.client = await mcp_client.connect(self.mcp_endpoint)
            self.connected = True
            logger.info("Connected to GMail MCP server")
        except Exception as e:
            logger.error(f"Failed to connect to server")
            raise
    
    async def send_email(self, to_email: str, subject: str, body: str) -> Dict[str, Any]:
        """send email via GMail MCP server"""

        mcp_request = {
            "method": "gmail/send",
            "params": {
                "to_email": to_email,
                "subject": subject,
                "body": body,
                "format": "html"
            }
        }

        try:
            await self.client.call(mcp_request)
            message_id = f"msg_{uuid.uuid4().hex[:12]}"
            return {
                "success": True,
                "message_id": message_id,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Gmail MCP send failed")
            return {"success": False, "error": str(e)}
    
    async def read_emails(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Read emails via GMail MCP server"""

        mcp_request = {
            "method": "gmail/search",
            "params": {
                "query": query,
                "maxResults": max_results,
                "includeSpamTrash": False
            }
        }

        results = []

        try:
            result = await self.client.call(mcp_request)
            results.append(result)
        except Exception as e:
            logger.error(f"GMail MCP read failed: {e}")
            return []
    
    async def get_thread(self, thread_id: str) -> Dict[str, Any]:
        """Get email thread via GMail MCP"""

        mcp_request = {
            "method": "gmail/thread/get",
            "params": {
                "id": thread_id,
                "format": "full"
            }
        }
        
        try:
            await self.client.call(mcp_request)
            return {}
        except Exception as e:
            logger.error(f"Gmail MCP get thread failed: {e}")
            return {}
