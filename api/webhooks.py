"""
OriginMark Webhook System for Slack and Discord notifications
"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import aiohttp
from pydantic import BaseModel, HttpUrl
from enum import Enum

class WebhookType(str, Enum):
    SLACK = "slack"
    DISCORD = "discord"

class WebhookEvent(str, Enum):
    SIGNATURE_CREATED = "signature.created"
    SIGNATURE_VERIFIED = "signature.verified" 
    SIGNATURE_FAILED = "signature.failed"
    BATCH_COMPLETED = "batch.completed"

class WebhookConfig(BaseModel):
    id: str
    name: str
    url: HttpUrl
    type: WebhookType
    events: List[WebhookEvent]
    is_active: bool = True
    secret: Optional[str] = None

class WebhookManager:
    def __init__(self):
        self.webhooks: Dict[str, WebhookConfig] = {}
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def trigger_event(self, event: WebhookEvent, data: Dict[str, Any]):
        """Trigger a webhook event"""
        webhooks = [w for w in self.webhooks.values() if event in w.events and w.is_active]
        
        for webhook in webhooks:
            await self.send_webhook(webhook, event, data)
    
    async def send_webhook(self, webhook: WebhookConfig, event: WebhookEvent, data: Dict[str, Any]):
        """Send webhook notification"""
        if webhook.type == WebhookType.SLACK:
            message = self.format_slack_message(event, data)
        else:  # Discord
            message = self.format_discord_message(event, data)
        
        # In a real implementation, you would send the HTTP request here
        print(f"Sending {webhook.type} webhook: {message}")
    
    def format_slack_message(self, event: WebhookEvent, data: Dict[str, Any]) -> Dict:
        """Format Slack message"""
        if event == WebhookEvent.SIGNATURE_CREATED:
            return {
                "text": f" New content signed by {data.get('author', 'Unknown')}",
                "attachments": [{
                    "color": "good",
                    "fields": [
                        {"title": "File", "value": data.get('file_name', 'Unknown'), "short": True},
                        {"title": "Model", "value": data.get('model_used', 'Unknown'), "short": True}
                    ]
                }]
            }
        return {"text": f"OriginMark event: {event}"}
    
    def format_discord_message(self, event: WebhookEvent, data: Dict[str, Any]) -> Dict:
        """Format Discord message"""
        if event == WebhookEvent.SIGNATURE_CREATED:
            return {
                "embeds": [{
                    "title": " New Content Signed",
                    "description": f"Content signed by {data.get('author', 'Unknown')}",
                    "color": 0x22c55e,
                    "fields": [
                        {"name": "File", "value": data.get('file_name', 'Unknown'), "inline": True},
                        {"name": "Model", "value": data.get('model_used', 'Unknown'), "inline": True}
                    ]
                }]
            }
        return {"content": f"OriginMark event: {event}"}

# Global webhook manager
webhook_manager = WebhookManager()

# Helper functions
async def notify_signature_created(signature_data: Dict[str, Any]):
    """Notify about signature creation"""
    metadata = signature_data.get("metadata", {})
    await webhook_manager.trigger_event(
        WebhookEvent.SIGNATURE_CREATED,
        {
            "author": metadata.get("author"),
            "file_name": metadata.get("file_name"),
            "model_used": metadata.get("model_used"),
            "content_type": metadata.get("content_type")
        }
    )