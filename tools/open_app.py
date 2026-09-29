from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "open_app", "description": "Opens any application on the computer. Use this whenever the user asks to open, launch, or start any app, website, or program. Always call this tool — never just say you opened it.", "parameters": {"type": "OBJECT", "properties": {"app_name": {"type": "STRING", "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"}}, "required": ["app_name"]}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "open_app", args)
