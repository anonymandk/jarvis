"""Platform reduced-motion preference detection and preference resolution."""

from __future__ import annotations

import os
import platform
import subprocess


def system_prefers_reduced_motion() -> bool | None:
    """Return the OS setting when available; otherwise leave the choice to the user."""
    system = platform.system()
    try:
        if system == "Windows":
            import ctypes

            enabled = ctypes.c_int()
            ok = ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0)
            return not bool(enabled.value) if ok else None
        if system == "Darwin":
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleReduceMotion"],
                capture_output=True, text=True, timeout=1, check=False,
            )
            return result.stdout.strip() == "1" if result.returncode == 0 else None
        if system == "Linux":
            env_setting = os.environ.get("GTK_ENABLE_ANIMATIONS")
            if env_setting is not None:
                return env_setting.strip().lower() in {"0", "false", "no"}
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "enable-animations"],
                capture_output=True, text=True, timeout=1, check=False,
            )
            if result.returncode == 0:
                value = result.stdout.strip().lower()
                return value in {"false", "0"}
    except (OSError, subprocess.SubprocessError, AttributeError, ValueError):
        return None
    return None


def resolve_reduced_motion(preference: str, system_value: bool | None = None) -> bool:
    value = str(preference or "system").strip().lower()
    if value in {"reduced", "on", "true"}:
        return True
    if value in {"full", "off", "false"}:
        return False
    return bool(system_prefers_reduced_motion() if system_value is None else system_value)
