from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "prepare_message_reply", "description": "Creates an approval-gated message draft, approves the current pending draft, or cancels it. Never approve unless the user explicitly confirms the exact pending draft.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING", "enum": ["prepare", "approve", "cancel"], "description": "Draft lifecycle action."}, "platform": {"type": "STRING", "description": "Instagram, iMessage, WhatsApp, Telegram, or another supported platform."}, "receiver": {"type": "STRING", "description": "Recipient name. Optional for the currently open chat."}, "message_text": {"type": "STRING", "description": "Exact draft text, required for prepare."}}, "required": ["action"]}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "prepare_message_reply", args)
