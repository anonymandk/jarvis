from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "file_controller", "description": "Manages and opens local files and folders: open, list, create, delete, move, copy, rename, read, write, find, disk usage. Use action=open for a file path; do not use open_app for files.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING", "description": "open | list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"}, "path": {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"}, "destination": {"type": "STRING", "description": "Destination path for move/copy"}, "new_name": {"type": "STRING", "description": "New name for rename"}, "content": {"type": "STRING", "description": "Content for create_file/write"}, "name": {"type": "STRING", "description": "File name to search for"}, "extension": {"type": "STRING", "description": "File extension to search (e.g. .pdf)"}, "count": {"type": "INTEGER", "description": "Number of results for largest"}}, "required": ["action"]}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "file_controller", args)
