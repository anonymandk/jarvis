from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "task_status", "description": "Checks or cancels background jobs, including presentation and deep-research jobs.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING", "description": "get | all | cancel. Default: get."}, "task_id": {"type": "STRING", "description": "Background task ID for get or cancel."}}, "required": []}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "task_status", args)
