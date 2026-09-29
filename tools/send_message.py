from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "send_message", "description": "Sends a user-authored message through iMessage, WhatsApp, Telegram, Instagram, Discord, or the current chat. For Instagram, the first call prepares a visible draft; use action=approve only after explicit user confirmation.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING", "enum": ["send", "approve", "cancel"], "description": "Default: send. Approve/cancel operates on the pending draft."}, "receiver": {"type": "STRING", "description": "Recipient contact name. Optional for current/focused chats and approval actions."}, "message_text": {"type": "STRING", "description": "Exact message content. Required for send."}, "platform": {"type": "STRING", "description": "iMessage, WhatsApp, Telegram, Instagram, Discord, or current/focused."}}, "required": ["platform"]}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "send_message", args)
