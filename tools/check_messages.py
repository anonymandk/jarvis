from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "check_messages", "description": "Reads the current Instagram or Apple Messages conversation and optionally searches Contacts. Use this before drafting a reply or when the user asks about recent messages.", "parameters": {"type": "OBJECT", "properties": {"platform": {"type": "STRING", "description": "all | Instagram | iMessage | Contacts. Default: all."}, "include_contacts": {"type": "BOOLEAN", "description": "Also search the user's Contacts."}, "contact_query": {"type": "STRING", "description": "Optional spoken contact name to match."}, "max_messages": {"type": "INTEGER", "description": "Maximum current-chat lines to inspect. Default: 30."}}, "required": []}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "check_messages", args)
