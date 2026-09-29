"""Gemini Live API provider implementation for JARVIS."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator

from google import genai
from google.genai import types

from llm_providers.base import (
    BaseLLM,
    LLMConfig,
    LLMEvent,
    LLMEventType,
    ToolCall,
    ToolResult,
    LLMConnectionError,
    LLMAuthenticationError,
    LLMUnsupportedVoiceError,
    LLMTransientError,
)

logger = logging.getLogger("jarvis.llm.gemini")


class GeminiLLM(BaseLLM):
    """Gemini Live API implementation of BaseLLM.

    Handles connection, audio/text I/O, tool calling, and event normalization
    for the Google Gemini Live API.
    """

    def __init__(self, api_key: str, http_options: dict = None):
        """Initialize Gemini client.

        Args:
            api_key: Gemini API key
            http_options: HTTP options for the client (e.g., api_version)
        """
        self._api_key = api_key
        self._http_options = http_options or {"api_version": "v1beta"}
        self._client: genai.Client | None = None
        self._session: Any = None
        self._connected = False
        self._model_id: str | None = None

    async def connect(self, config: LLMConfig) -> None:
        """Connect to Gemini Live API.

        Args:
            config: Session configuration including model, tools, voice, etc.

        Raises:
            LLMConnectionError: If connection fails
            LLMAuthenticationError: If API key is invalid
        """
        self._model_id = config.model
        self._client = genai.Client(
            api_key=self._api_key,
            http_options=self._http_options,
        )

        # Convert neutral tool declarations to Gemini format
        gemini_tools = self._convert_tools(config.tools)

        # Build Gemini LiveConnectConfig
        live_config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction=config.system_instruction,
            tools=[{"function_declarations": gemini_tools}] if gemini_tools else [],
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                    silence_duration_ms=config.vad_silence_ms,
                )
            ),
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            session_resumption=types.SessionResumptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=config.voice_name
                    )
                )
            ),
        )

        try:
            # Connect to Gemini Live
            self._session = await self._client.aio.live.connect(
                model=self._model_id,
                config=live_config,
            )
            self._connected = True
            logger.info(f"[JARVIS] ✅ Connected to Gemini Live: {self._model_id}")
        except genai.errors.APIError as e:
            self._connected = False
            if "API_KEY" in str(e).upper() or "UNAUTHENTICATED" in str(e):
                raise LLMAuthenticationError(f"Invalid Gemini API key: {e}") from e
            if "voice" in str(e).lower() and "not available" in str(e).lower():
                raise LLMUnsupportedVoiceError(f"Voice not supported: {e}") from e
            raise LLMConnectionError(f"Failed to connect to Gemini: {e}") from e
        except Exception as e:
            self._connected = False
            raise LLMConnectionError(f"Failed to connect to Gemini: {e}") from e

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """Convert neutral tool declarations to Gemini format.

        Args:
            tools: List of tool declarations in neutral JSON Schema format

        Returns:
            List of Gemini function declarations
        """
        if not tools:
            return []

        gemini_tools = []
        for tool in tools:
            # Ensure the tool has the required structure
            if "name" not in tool:
                continue
            gemini_tool = {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {"type": "OBJECT", "properties": {}}),
            }
            gemini_tools.append(gemini_tool)
        return gemini_tools

    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm;rate=16000") -> None:
        """Send audio to Gemini Live session."""
        if not self._connected or not self._session:
            raise LLMConnectionError("Not connected to Gemini")

        try:
            # Parse mime_type for sample rate if needed
            await self._session.send_realtime_input(
                media={"data": audio_data, "mime_type": mime_type}
            )
        except Exception as e:
            logger.error(f"[JARVIS] Failed to send audio: {e}")
            raise

    async def send_text(self, text: str) -> None:
        """Send text to Gemini Live session."""
        if not self._connected or not self._session:
            raise LLMConnectionError("Not connected to Gemini")

        try:
            await self._session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True,
            )
        except Exception as e:
            logger.error(f"[JARVIS] Failed to send text: {e}")
            raise

    async def send_tool_result(self, result: ToolResult) -> None:
        """Send tool result back to Gemini."""
        if not self._connected or not self._session:
            raise LLMConnectionError("Not connected to Gemini")

        try:
            # Convert to Gemini FunctionResponse format
            function_response = types.FunctionResponse(
                id=result.id,
                name=result.name,
                response={
                    "result": result.result if result.error is None else f"Error: {result.error}"
                },
            )
            await self._session.send_tool_response(
                function_responses=[function_response]
            )
        except Exception as e:
            logger.error(f"[JARVIS] Failed to send tool result: {e}")
            raise

    async def receive(self) -> AsyncIterator[LLMEvent]:
        """Receive and normalize events from Gemini Live session."""
        if not self._connected or not self._session:
            raise LLMConnectionError("Not connected to Gemini")

        try:
            async for response in self._session.receive():
                # Audio response
                audio_data = self._extract_audio(response)
                if audio_data:
                    yield LLMEvent(type=LLMEventType.AUDIO, data=audio_data)

                # Server content (transcriptions, turn complete)
                if response.server_content:
                    sc = response.server_content

                    # Output transcription (model's spoken response)
                    if sc.output_transcription and sc.output_transcription.text:
                        yield LLMEvent(
                            type=LLMEventType.TEXT,
                            data=sc.output_transcription.text,
                            metadata={"is_output": True}
                        )

                    # Input transcription (user's speech)
                    if sc.input_transcription and sc.input_transcription.text:
                        yield LLMEvent(
                            type=LLMEventType.TEXT,
                            data=sc.input_transcription.text,
                            metadata={"is_input": True}
                        )

                    # Turn complete
                    if sc.turn_complete:
                        yield LLMEvent(type=LLMEventType.TURN_COMPLETE)

                # Tool calls
                if response.tool_call:
                    for fc in response.tool_call.function_calls:
                        yield LLMEvent(
                            type=LLMEventType.TOOL_CALL,
                            data=ToolCall(
                                id=fc.id,
                                name=fc.name,
                                args=dict(fc.args or {}),
                            )
                        )

        except genai.errors.APIError as e:
            if "1000" in str(e):
                yield LLMEvent(type=LLMEventType.CLOSE)
                return
            logger.error(f"[JARVIS] Gemini API error: {e}")
            yield LLMEvent(type=LLMEventType.ERROR, data=e)
            raise
        except Exception as e:
            logger.error(f"[JARVIS] Error receiving from Gemini: {e}")
            yield LLMEvent(type=LLMEventType.ERROR, data=e)
            raise

    def _extract_audio(self, response) -> bytes | None:
        """Extract audio bytes from Gemini response."""
        server_content = getattr(response, "server_content", None)
        model_turn = getattr(server_content, "model_turn", None) if server_content else None
        if not model_turn:
            return None

        for part in getattr(model_turn, "parts", None) or []:
            inline_data = getattr(part, "inline_data", None)
            data = getattr(inline_data, "data", None) if inline_data else None
            mime_type = str(getattr(inline_data, "mime_type", "") or "").lower() if inline_data else ""
            if data and mime_type.startswith("audio/"):
                return bytes(data)
        return None

    async def close(self) -> None:
        """Close Gemini Live session."""
        if self._session:
            try:
                await self._session.close()
            except Exception as e:
                logger.warning(f"[JARVIS] Error closing Gemini session: {e}")
        self._connected = False
        self._session = None
        logger.info("[JARVIS] 🔌 Gemini session closed")

    def is_connected(self) -> bool:
        """Check if session is active."""
        return self._connected and self._session is not None

    def classify_error(self, error: Exception) -> str:
        """Classify Gemini error for retry policy."""
        error_str = str(error).lower()

        # Normal close (1000)
        if isinstance(error, genai.errors.APIError) and "1000" in error_str:
            return "normal_close"

        # Unsupported voice
        if isinstance(error, genai.errors.APIError):
            if "voice" in error_str and "not available" in error_str:
                return "unsupported_voice"

        # Transient connection errors
        transient_markers = (
            "connection reset", "connection aborted", "temporarily unavailable",
            "timed out", "timeout", "network is unreachable", "broken pipe",
        )
        if any(marker in error_str for marker in transient_markers):
            return "transient"
        if isinstance(error, (ConnectionResetError, ConnectionAbortedError, TimeoutError)):
            return "transient"

        return "permanent"