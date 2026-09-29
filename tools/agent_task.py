from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "agent_task", "description": "Executes complex multi-step tasks requiring multiple different tools. Examples: 'research X and save to file', 'find and organize files'. DO NOT use for single commands. NEVER use for Steam/Epic — use game_updater.", "parameters": {"type": "OBJECT", "properties": {"goal": {"type": "STRING", "description": "Complete description of what to accomplish"}, "priority": {"type": "STRING", "description": "low | normal | high (default: normal)"}}, "required": ["goal"]}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "agent_task", args)
