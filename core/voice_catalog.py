"""Vendor-neutral voice metadata shared by the UI and playback engine."""

PROVIDER_VOICES: dict[str, list[tuple[str, str]]] = {
    "gemini": [
        ("Puck", "puck"),
        ("Charon", "charon"),
        ("Kore", "kore"),
        ("Fenrir", "fenrir"),
        ("Aoede", "aoede"),
        ("Leda", "leda"),
        ("Orus", "orus"),
        ("Schedar", "schedar"),
        ("Zubenelgenubi", "zubenelgenubi"),
    ],
}

EXTERNAL_PROVIDERS: set[str] = set()
DEFAULT_PROVIDER = "gemini"
DEFAULT_VOICE_ID = "orus"
PROVIDER_TUTORIAL: dict[str, dict] = {}
