"""Application-owned Gemini renderer for the optional first-run narration."""

from __future__ import annotations

import asyncio
import base64
from typing import Any

from google import genai
from google.genai import types

from core.voice_catalog import PROVIDER_VOICES


MODELS = (
    "gemini-2.5-flash-preview-tts",
    "gemini-2.5-pro-preview-tts",
)
RENDER_ATTEMPTS = 2
REQUEST_TIMEOUT_SECONDS = 90.0


def _voice_label(voice_name: str) -> str:
    value = str(voice_name).strip().lower()
    return next(
        (label for label, voice_id in PROVIDER_VOICES["gemini"] if voice_id == value),
        value.title(),
    )


def _extract_audio(response: Any) -> bytes:
    for candidate in getattr(response, "candidates", ()) or ():
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", ()) or ():
            inline = getattr(part, "inline_data", None)
            data = getattr(inline, "data", None)
            mime_type = str(getattr(inline, "mime_type", "") or "")
            if data and (not mime_type or mime_type.startswith("audio/")):
                return base64.b64decode(data) if isinstance(data, str) else bytes(data)
    return b""


def _is_quota_error(error: BaseException) -> bool:
    message = str(error).lower()
    return any(marker in message for marker in (
        "429", "resource_exhausted", "quota", "rate limit",
    ))


async def _request_intro_tts(client, model: str, narration: str, voice_name: str):
    config = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=_voice_label(voice_name),
                ),
            ),
        ),
    )
    return await asyncio.wait_for(
        client.aio.models.generate_content(
            model=model,
            contents=narration,
            config=config,
        ),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


async def render_intro_with_live(
    narration: str,
    voice_name: str,
    api_key: str,
) -> bytes:
    client = genai.Client(api_key=api_key)
    try:
        last_error: BaseException | None = None
        for model in MODELS:
            for _ in range(RENDER_ATTEMPTS):
                try:
                    response = await _request_intro_tts(client, model, narration, voice_name)
                    pcm = _extract_audio(response)
                    if pcm:
                        return pcm
                    last_error = RuntimeError("Gemini TTS returned no audio.")
                except Exception as exc:
                    if _is_quota_error(exc):
                        raise
                    last_error = exc
        raise RuntimeError("Gemini TTS returned no audio.") from last_error
    finally:
        client.close()


async def render_intro_segments_with_live(
    captions: tuple[str, ...],
    voice_name: str,
    api_key: str,
) -> tuple[bytes, list[int]]:
    client = genai.Client(api_key=api_key)
    rendered: list[bytes] = []
    boundaries = [0]
    try:
        for caption in captions:
            last_error: BaseException | None = None
            pcm = b""
            for model in MODELS:
                for _ in range(RENDER_ATTEMPTS):
                    try:
                        response = await _request_intro_tts(client, model, caption, voice_name)
                        pcm = _extract_audio(response)
                        if pcm:
                            break
                        last_error = RuntimeError("Gemini TTS returned no audio.")
                    except Exception as exc:
                        if _is_quota_error(exc):
                            raise
                        last_error = exc
                if pcm:
                    break
            if not pcm:
                raise RuntimeError("Gemini TTS returned no audio.") from last_error
            rendered.append(pcm)
            boundaries.append(boundaries[-1] + len(pcm))
        return b"".join(rendered), boundaries
    finally:
        client.close()
