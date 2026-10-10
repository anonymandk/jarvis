from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "screen_process", "description": "Captures and analyzes the screen or webcam image. MUST be called when user asks what is on screen, what you see, analyze my screen, look at camera, etc. You have NO visual ability without this tool. After calling this tool, stay SILENT — the vision module speaks directly.", "parameters": {"type": "OBJECT", "properties": {"angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"}, "text": {"type": "STRING", "description": "The question or instruction about the captured image"}}, "required": ["text"]}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "screen_process", args)
