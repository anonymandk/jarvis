"""Central configuration for JARVIS.

Loads from (in order of precedence):
1) Environment variables (prefixed with JARVIS_)
2) config/api_keys.json (legacy)
3) Defaults defined in code
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional, Literal

from pydantic import Field, validator
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class LLMSettings(BaseSettings):
    provider: Literal["gemini", "openai", "ollama"] = "gemini"

    # API keys
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Ollama (stub until Phase 8)
    ollama_host: Optional[str] = None
    ollama_model: Optional[str] = None

    class Config:
        env_prefix = "JARVIS_LLM_"


class VoiceSettings(BaseSettings):
    name: str = "puck"

    class Config:
        env_prefix = "JARVIS_VOICE_"


class AudioSettings(BaseSettings):
    channels: int = 1
    send_sample_rate: int = 16000
    receive_sample_rate: int = 24000
    chunk_size: int = 1024
    vad_silence_ms: int = 200

    class Config:
        env_prefix = "JARVIS_AUDIO_"


class FeaturesSettings(BaseSettings):
    # empty => enabled tools default is "all built-in tools"
    enabled_tools: List[str] = []
    enabled_plugins: List[str] = []

    class Config:
        env_prefix = "JARVIS_FEATURES_"


class RuntimeSettings(BaseSettings):
    runtime_limit_seconds: Optional[int] = None
    required_unlock_path: Optional[str] = None
    required_unlock_secret: Optional[str] = None

    class Config:
        env_prefix = "JARVIS_RUNTIME_"


class Settings(BaseSettings):
    llm: LLMSettings = Field(default_factory=LLMSettings)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    features: FeaturesSettings = Field(default_factory=FeaturesSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

    @validator("llm", pre=True, always=True)
    def load_llm_legacy_config(cls, v):  # noqa: N805
        api_keys_path = BASE_DIR / "config" / "api_keys.json"
        legacy: dict = {}
        if api_keys_path.exists():
            try:
                legacy = json.loads(api_keys_path.read_text(encoding="utf-8"))
            except Exception:
                legacy = {}

        if not isinstance(v, dict):
            v = {}

        # GEMINI_API_KEY legacy key
        env_gemini_key = os.environ.get("GEMINI_API_KEY")
        if env_gemini_key:
            v.setdefault("gemini_api_key", env_gemini_key)
        elif v.get("gemini_api_key") is None and legacy.get("api_key"):
            v.setdefault("gemini_api_key", legacy["api_key"])

        return v

    @validator("voice", pre=True, always=True)
    def load_voice_legacy_config(cls, v):  # noqa: N805
        api_keys_path = BASE_DIR / "config" / "api_keys.json"
        legacy: dict = {}
        if api_keys_path.exists():
            try:
                legacy = json.loads(api_keys_path.read_text(encoding="utf-8"))
            except Exception:
                legacy = {}

        if not isinstance(v, dict):
            v = {}

        env_voice = os.environ.get("GEMINI_VOICE_NAME")
        if env_voice:
            v.setdefault("name", env_voice)
        elif v.get("name") in (None, "") and legacy.get("voice_name"):
            v.setdefault("name", legacy["voice_name"])

        return v

    @validator("runtime", pre=True, always=True)
    def load_runtime_env(cls, v):  # noqa: N805
        # main.py reads these env vars directly today; this bridges that.
        if not isinstance(v, dict):
            v = {}

        runtime_kw = os.environ.get("JARVIS_TRIAL_KEYWORD")
        if runtime_kw:
            runtime_seconds = os.environ.get("JARVIS_RUNTIME_SECONDS", "3600")
            try:
                v.setdefault("runtime_limit_seconds", int(runtime_seconds))
            except Exception:
                pass

        locked_secret = os.environ.get("JARVIS_LOCKED_KEY_SECRET")
        if locked_secret:
            v.setdefault("required_unlock_secret", locked_secret.strip())

        locked_vol = os.environ.get("JARVIS_LOCKED_VOLUME")
        if locked_vol:
            mount_path = f"/Volumes/{locked_vol}/unlock.key"
            v.setdefault("required_unlock_path", mount_path)

        return v


def get_settings() -> Settings:
    return Settings()


# Backwards compatible helpers (used by existing code we refactor later)
def get_api_key() -> str:
    settings = get_settings()
    if not settings.llm.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY not set. Set via environment GEMINI_API_KEY "
            "or config/api_keys.json"
        )
    return settings.llm.gemini_api_key


def get_voice_name() -> str:
    return get_settings().voice.name