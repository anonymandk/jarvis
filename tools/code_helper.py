from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "code_helper", "description": "Writes, edits, explains, runs, or builds code files.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"}, "description": {"type": "STRING", "description": "What the code should do or what change to make"}, "language": {"type": "STRING", "description": "Programming language (default: python)"}, "output_path": {"type": "STRING", "description": "Where to save the file"}, "file_path": {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"}, "code": {"type": "STRING", "description": "Raw code string for explain"}, "args": {"type": "STRING", "description": "CLI arguments for run/build"}, "timeout": {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"}}, "required": ["action"]}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "code_helper", args)
