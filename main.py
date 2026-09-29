import asyncio
import os
import re
import threading
import json
import sys
import traceback
import logging
import random

from observability.logging import setup_logging
from observability.metrics import metrics, Timer
from pathlib import Path

import sounddevice as sd
from google import genai
from google.genai import types
from api import status as jarvis_status
from core.jarvis_client import JarvisClient
from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
)
from config.settings import get_settings
import importlib
import time

from core.live_model import pick_live_model

logger = logging.getLogger("jarvis")


def _lazy_action(module_name: str, attribute: str):
    """Keep desktop-only dependencies out of headless API process startup."""

    def invoke(*args, **kwargs):
        action = getattr(importlib.import_module(module_name), attribute)
        return action(*args, **kwargs)

    invoke.__name__ = attribute
    return invoke


# Preserve the historical module-level action surface for patches/plugins while
# deferring platform-specific imports until a declared action actually runs.
file_processor = _lazy_action("actions.file_processor", "file_processor")
flight_finder = _lazy_action("actions.flight_finder", "flight_finder")
open_app = _lazy_action("actions.open_app", "open_app")
weather_action = _lazy_action("actions.weather_report", "weather_action")
send_message = _lazy_action("actions.send_message", "send_message")
prepare_message_reply = _lazy_action("actions.send_message", "prepare_message_reply")
email_control = _lazy_action("actions.email_control", "email_control")
check_messages = _lazy_action("actions.message_monitor", "check_messages")
reminder = _lazy_action("actions.reminder", "reminder")
computer_settings = _lazy_action("actions.computer_settings", "computer_settings")
screen_process = _lazy_action("actions.screen_processor", "screen_process")
youtube_video = _lazy_action("actions.youtube_video", "youtube_video")
media_control = _lazy_action("actions.media_control", "media_control")
desktop_control = _lazy_action("actions.desktop", "desktop_control")
browser_control = _lazy_action("actions.browser_control", "browser_control")
file_controller = _lazy_action("actions.file_controller", "file_controller")
code_helper = _lazy_action("actions.code_helper", "code_helper")
dev_agent = _lazy_action("actions.dev_agent", "dev_agent")
web_search_action = _lazy_action("actions.web_search", "web_search")
computer_control = _lazy_action("actions.computer_control", "computer_control")
game_updater = _lazy_action("actions.game_updater", "game_updater")
request_presentation = _lazy_action("actions.presentation_maker", "request_presentation")
request_deep_research = _lazy_action("actions.deep_research", "request_deep_research")


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def _load_dotenv():
    """Load .env file if it exists. Silently skip if not found."""
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE_DIR / ".env")
    except ImportError:
        # python-dotenv not installed — rely on already-set env vars
        pass


BASE_DIR        = get_base_dir()
_load_dotenv()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
get_settings().audio.channels            = 1
get_settings().audio.send_sample_rate    = 16000
SUPPORTED_VOICE_NAMES = {
    "puck", "charon", "kore", "fenrir", "aoede",
    "leda", "orus", "schedar", "zubenelgenubi"
}
DEFAULT_VOICE_NAME   = "puck"

get_settings().audio.receive_sample_rate = 24000
get_settings().audio.chunk_size          = 1024
get_settings().audio.vad_silence_ms = 200
STARTUP_CLAPS_REQUIRED = 2
STARTUP_CLAP_MAX_GAP_SECONDS = 4.0
STARTUP_CLAP_COOLDOWN_SECONDS = 0.22
SELF_QUIT_GOODBYE = (
    "Certainly, sir. It has been a privilege. JARVIS is going offline now. "
    "Until next time."
)

_SELF_QUIT_PATTERNS = tuple(re.compile(pattern, re.IGNORECASE) for pattern in (
    r"\b(?:quit|close|exit)\s+(?:jarvis|yourself)\b",
    r"\b(?:shut|turn)\s+(?:jarvis|yourself)\s+(?:down|off)\b",
    r"\b(?:shut\s+down|turn\s+off|power\s+down)\s+(?:jarvis|yourself)\b",
    r"\bjarvis\b.{0,36}\b(?:quit|close|exit|shut\s+down|turn\s+off|go\s+offline)\b",
    r"\b(?:go|take\s+yourself)\s+offline(?:\s+jarvis)?\b",
))


def _exception_leaves(exc: BaseException):
    nested = getattr(exc, "exceptions", None)
    if nested:
        for child in nested:
            yield from _exception_leaves(child)
    else:
        yield exc


def _is_normal_live_close_error(exc: BaseException) -> bool:
    for leaf in _exception_leaves(exc):
        name = leaf.__class__.__name__.lower()
        message = str(leaf).lower()
        if name == "connectionclosedok" or "1000 (ok)" in message:
            return True
        if isinstance(leaf, genai.errors.APIError) and "1000" in message:
            return True
    return False


def _is_transient_live_connection_error(exc: BaseException) -> bool:
    transient_markers = (
        "connection reset", "connection aborted", "temporarily unavailable",
        "timed out", "timeout", "network is unreachable", "broken pipe",
    )
    return any(
        isinstance(leaf, (ConnectionResetError, ConnectionAbortedError, TimeoutError))
        or any(marker in str(leaf).lower() for marker in transient_markers)
        for leaf in _exception_leaves(exc)
    )


def _live_reconnect_delay(attempt: int) -> float:
    return min(30.0, float(2 ** max(0, int(attempt) - 1)))


def _compute_jitter_delay(
    base_delay_s: float,
    jitter_ratio: float,
    *,
    rand_fn=None,
) -> float:
    """Apply jitter to a base delay.

    rand_fn is injectable for tests; if omitted it uses random.random.
    """
    if jitter_ratio <= 0:
        return float(base_delay_s)
    if rand_fn is None:
        rand_fn = random.random
    # Convert [0,1) to (-1, +1)
    jitter = (float(rand_fn()) * 2.0 - 1.0) * float(jitter_ratio) * float(base_delay_s)
    return max(0.0, float(base_delay_s) + jitter)


def _live_response_audio_bytes(response) -> bytes | None:
    server_content = getattr(response, "server_content", None)
    model_turn = getattr(server_content, "model_turn", None)
    for part in getattr(model_turn, "parts", None) or []:
        inline_data = getattr(part, "inline_data", None)
        data = getattr(inline_data, "data", None)
        mime_type = str(getattr(inline_data, "mime_type", "") or "").lower()
        if data and mime_type.startswith("audio/"):
            return bytes(data)
    return None


def wait_for_startup_claps(
    required: int = STARTUP_CLAPS_REQUIRED,
    *,
    timeout: float | None = None,
    stream_factory=None,
) -> bool:
    """Hold startup until two distinct claps are heard by the default microphone."""
    if os.environ.get("JARVIS_SKIP_CLAP_GATE", "").strip().lower() in {"1", "true", "yes", "on"}:
        logger.info("[JARVIS] 👏 Startup clap gate bypassed (JARVIS_SKIP_CLAP_GATE).")
        return True
    # Some macOS/AUHAL configurations expose a nominal input device but reject
    # every PortAudio operation (PaErrorCode -9986). Avoid repeatedly starting
    # a failing Core Audio stream; users with a working mic can opt in.
    if sys.platform == "darwin" and stream_factory is None and os.environ.get("JARVIS_ENABLE_CLAP_GATE", "").strip().lower() not in {"1", "true", "yes", "on"}:
        logger.info("[JARVIS] ⚠️ macOS microphone gate disabled for this audio configuration.")
        logger.info("[JARVIS] Continuing without clap startup. Set JARVIS_ENABLE_CLAP_GATE=1 to force it.")
        return True

    required = max(1, int(required))
    stream_factory = stream_factory or sd.InputStream
    try:
        import numpy as np
    except ImportError:
        logger.info("[JARVIS] ❌ Startup clap gate needs numpy. Set JARVIS_SKIP_CLAP_GATE=1 to bypass.")
        return False

    clap_times: list[float] = []
    last_clap_at = 0.0
    # Microphone input levels vary considerably between Mac models.  The old
    # fixed 0.12 RMS / 0.32 peak gates rejected quiet real claps, while laptop
    # fan noise could sometimes trip them.  Track the room floor and use both
    # transient shape (crest factor) and energy to identify a clap.
    noise_floor = 0.008
    finished = threading.Event()
    started_at = time.monotonic()

    def callback(indata, frames, time_info, status):
        nonlocal last_clap_at, noise_floor, clap_times
        if status:
            logger.info(f"[JARVIS] ⚠️ Clap mic: {status}")
        samples = np.asarray(indata, dtype=np.float32).reshape(-1)
        if samples.size == 0:
            return
        magnitude = np.abs(samples)
        rms = float(np.sqrt(np.mean(samples * samples)))
        peak = float(np.max(magnitude))
        # Only let low-energy frames teach the noise floor; otherwise a clap
        # would raise the threshold immediately and make the second clap hard
        # to detect.
        if rms < max(0.08, noise_floor * 6.0):
            noise_floor = (noise_floor * 0.96) + (rms * 0.04)
        threshold = max(0.100, noise_floor * 6.5)
        peak_threshold = max(0.35, noise_floor * 15.0)
        crest_factor = peak / max(rms, 1e-6)
        now = time.monotonic()
        # A valid clap must be either a sharp transient with meaningful energy
        # or a genuinely loud impact. This rejects speech, fan noise, and most
        # desk/keyboard taps that only have a brief peak.
        is_transient = crest_factor >= 2.20 and rms >= threshold
        is_loud = rms >= max(0.28, noise_floor * 15.0)
        if (
            peak < peak_threshold
            or not (is_transient or is_loud)
            or now - last_clap_at < STARTUP_CLAP_COOLDOWN_SECONDS
        ):
            return
        if clap_times and now - clap_times[-1] > STARTUP_CLAP_MAX_GAP_SECONDS:
            clap_times = []
        clap_times.append(now)
        last_clap_at = now
        logger.info(f"[JARVIS] 👏 Clap {len(clap_times)}/{required} detected")
        if len(clap_times) >= required:
            finished.set()

    logger.info(f"[JARVIS] 👏 Waiting for {required} claps to power up...")
    # PortAudio on macOS commonly rejects 16 kHz even when the microphone is
    # available (PaErrorCode -9986). Prefer the device's native rate, then
    # retry standard rates before reporting that the microphone is unavailable.
    sample_rates = [get_settings().audio.send_sample_rate, 44100, 48000]
    input_device = None
    try:
        if stream_factory is sd.InputStream:
            try:
                default_device = sd.default.device
                try:
                    input_index = int(default_device[0])
                except (TypeError, IndexError, ValueError):
                    input_index = -1
                if input_index < 0:
                    logger.info("[JARVIS] ⚠️ macOS reports no default microphone device.")
                    if os.environ.get("JARVIS_REQUIRE_CLAP_GATE", "").strip().lower() not in {"1", "true", "yes", "on"}:
                        logger.info("[JARVIS] ⚠️ Continuing without the clap gate; microphone input is unavailable.")
                        return True
                    raise RuntimeError("no default microphone device")
                input_device = input_index
                device = sd.query_devices(input_device if input_device is not None else None, "input")
                if int(device.get("max_input_channels", 0)) < 1:
                    raise RuntimeError("no input channels are available")
                native_rate = int(float(device.get("default_samplerate", 0)))
                if native_rate > 0:
                    sample_rates.insert(0, native_rate)
            except Exception:
                pass
        sample_rates = list(dict.fromkeys(sample_rates))
        last_error = None
        for sample_rate in sample_rates:
            try:
                if stream_factory is sd.InputStream:
                    # Validate the format before constructing a live AUHAL
                    # stream; macOS can report a device but reject it with
                    # PaErrorCode -9986 during stream startup.
                    sd.check_input_settings(
                        device=input_device,
                        samplerate=sample_rate,
                        channels=get_settings().audio.channels,
                        dtype="float32",
                    )
                with stream_factory(
                    samplerate=sample_rate,
                    device=input_device,
                    channels=get_settings().audio.channels,
                    dtype="float32",
                    blocksize=0,
                    latency="high",
                    callback=callback,
                ):
                    while not finished.wait(0.05):
                        if timeout is not None and time.monotonic() - started_at >= timeout:
                            logger.info("[JARVIS] ⏱️ Startup clap gate timed out.")
                            return False
                break
            except Exception as exc:
                last_error = exc
                if finished.is_set():
                    break
        else:
            raise last_error or RuntimeError("no compatible microphone sample rate")
    except KeyboardInterrupt:
        logger.info("\n[JARVIS] Startup cancelled.")
        return False
    except Exception as exc:
        logger.info(f"[JARVIS] ❌ Startup clap microphone unavailable: {exc}")
        if os.environ.get("JARVIS_REQUIRE_CLAP_GATE", "").strip().lower() not in {"1", "true", "yes", "on"}:
            logger.info("[JARVIS] ⚠️ Continuing without the clap gate; microphone input is unavailable.")
            logger.info("[JARVIS] Restore microphone access to use voice input.")
            return True
        logger.info("[JARVIS] Clap gate required. Set JARVIS_SKIP_CLAP_GATE=1 to bypass it.")
        return False

    logger.info("[JARVIS] ⚡ Two claps detected. Powering up...")
    return True

def _get_api_key() -> str:
    """Get Gemini API key from settings (env or config)."""
    settings = get_settings()
    key = settings.llm.gemini_api_key
    if not key:
        raise ValueError("GEMINI_API_KEY environment variable not set. Please set it to your Gemini API key.")
    return key

def _normalize_voice_name(voice_name: str | None) -> str:
    if not voice_name:
        return DEFAULT_VOICE_NAME
    candidate = voice_name.strip().lower()
    return candidate if candidate in SUPPORTED_VOICE_NAMES else DEFAULT_VOICE_NAME


def _is_unsupported_voice_error(exc: Exception) -> bool:
    if not isinstance(exc, genai.errors.APIError):
        return False
    code = getattr(exc, "code", None)
    msg = str(exc).lower()
    if code == 1007:
        return "requested voice api_name" in msg and "not available for model" in msg
    return "requested voice api_name" in msg and "not available for model" in msg


def _load_voice_name() -> str:
    """Get voice name from settings (env or config)."""
    return get_settings().voice.name or DEFAULT_VOICE_NAME

def _load_system_prompt() -> str:
    try:
        prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
        return (
            prompt
            + "\n\nAlways address the user respectfully as 'Sir' or 'Madam' where appropriate, while remaining efficient and direct."
        )
    except Exception:
        return (
            "You are JARVIS, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool. "
            "Always address the user respectfully as 'Sir' or 'Madam' where appropriate, while remaining efficient and direct."
        )

_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

def _clean_transcript(text: str) -> str:    
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()

# Tool names exposed by hosted clients. The names here are Gemini function
# declaration names (which differ from a few implementation module names).
CLOUD_SAFE_ACTIONS = frozenset({
    "web_search",
    "deep_research",
    "create_presentation",
    "flight_finder",
    "email_control",
    "code_helper",
    "youtube_video",
})



def get_tool_declarations(*, cloud_safe: bool = False) -> list[dict]:
    """Return the Gemini tools available for the requested runtime."""
    from tools.registry import registry as tool_registry

    if not cloud_safe:
        return tool_registry.declarations(cloud_safe=False)

    return tool_registry.declarations(
        cloud_safe=True,
        cloud_safe_action_names=set(CLOUD_SAFE_ACTIONS),
    )


class JarvisLive:

    def __init__(
        self,
        client: JarvisClient,
        voice_name: str = "Puck",
        *,
        cloud_safe: bool = False,
        api_key: str | None = None,
        external_audio: bool = False,
    ):
        # Keep ``ui`` as a compatibility alias for desktop integrations that
        # already inspect JarvisLive.ui. The engine contract is JarvisClient.
        self.client         = client
        self.ui             = client
        self.cloud_safe     = bool(cloud_safe)
        self.external_audio = bool(external_audio)
        self._api_key       = api_key.strip() if isinstance(api_key, str) else None
        self.tool_declarations = get_tool_declarations(cloud_safe=self.cloud_safe)
        self.session        = None
        self.audio_in_queue = None
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self.voice_name     = voice_name
        # optional runtime limit in seconds (set by main)
        self.runtime_limit_seconds: int | None = None
        # optional path that must exist (e.g. a mounted encrypted volume)
        self.required_unlock_path: str | None = None
        self.required_unlock_secret: str | None = None
        self.ui.on_text_command = self._on_text_command
        self._voice_changed  = threading.Event()
        self._turn_done_event: asyncio.Event | None = None
        self._tts_engine = None
        self._ext_tts_provider = ""
        self._ext_tts_voice_id = ""
        self._ext_tts_api_key = ""
        self._current_input_transcript = ""
        self._last_input_transcript = ""
        self._last_input_transcript_at = 0.0
        self._pending_self_quit = False
        self._pending_self_quit_farewell_received = False
        self._self_quit_timer = None
        self._shutdown_requested = threading.Event()
        self._tour_active = False

    def _on_text_command(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(self.send_text(text), self._loop)

    async def send_text(self, text: str) -> bool:
        """Send a text turn from either the desktop callback or a web client."""
        if not self.session:
            return False
        self._current_input_transcript = str(text or "").strip()
        if not self._current_input_transcript:
            return False
        self._last_input_transcript = self._current_input_transcript
        self._last_input_transcript_at = time.monotonic()
        outgoing_text = self._current_input_transcript
        if (
            not getattr(self, "_pending_self_quit", False)
            and self._is_explicit_self_quit_transcript(self._current_input_transcript)
        ):
            self._queue_self_quit_after_farewell()
            outgoing_text = (
                "[VERIFIED LOCAL SELF-SHUTDOWN] The user explicitly asked JARVIS to quit. "
                f'Say exactly: "{SELF_QUIT_GOODBYE}" Do not call a tool and say nothing else.'
            )
        await self.session.send_client_content(
            turns={"parts": [{"text": outgoing_text}]},
            turn_complete=True,
        )
        return True

    async def send_audio_chunk(
        self,
        data: bytes,
        mime_type: str = "audio/pcm;rate=16000",
    ) -> bool:
        """Queue browser-captured PCM for the active Gemini Live session."""
        if not data or self.out_queue is None or self._shutdown_requested.is_set():
            return False
        await self.out_queue.put({"data": data, "mime_type": mime_type})
        return True

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def speak(self, text: str) -> bool:
        if not self._loop or not self.session:
            return False
        try:
            asyncio.run_coroutine_threadsafe(
                self.session.send_client_content(
                    turns={"parts": [{"text": text}]},
                    turn_complete=True
                ),
                self._loop
            )
            return True
        except Exception:
            return False

    def _speak_vision_result(self, text: str) -> bool:
        """Send finished vision text through JARVIS's active voice session."""
        result = " ".join(str(text or "").split())
        if not result:
            return False
        directive = (
            "[INTERNAL VISION OUTPUT] Read the following vision result to the user "
            "verbatim. Do not add an introduction, commentary, or a tool call. "
            f"Vision result: {json.dumps(result, ensure_ascii=False)}"
        )
        return self.speak(directive)

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    @staticmethod
    def _is_explicit_self_quit_transcript(text: str) -> bool:
        """Only match commands that clearly target JARVIS, never the computer."""
        normalized = " ".join(str(text or "").lower().split())
        if not normalized:
            return False
        if re.search(r"\b(?:computer|mac|pc|system|machine)\b", normalized):
            return False
        if re.search(r"\b(?:stop talking|be quiet|cancel|never mind)\b", normalized):
            return False
        if normalized in {
            "quit", "exit", "shutdown", "shut down", "turn off", "power down",
            "go offline", "goodbye jarvis", "goodbye jarvis please",
        }:
            return True
        return any(pattern.search(normalized) for pattern in _SELF_QUIT_PATTERNS)

    def _queue_self_quit_after_farewell(self) -> None:
        """Arm shutdown without closing until the response audio is fully drained."""
        self._pending_self_quit = True
        self._pending_self_quit_farewell_received = False
        try:
            self.ui.write_log("SYS: Shutdown queued; waiting for JARVIS's farewell.")
        except Exception:
            pass
        # A voice model can occasionally omit audio/turn_complete. Do not
        # leave the user with a permanently armed shutdown in that case.
        try:
            if self._self_quit_timer is not None:
                self._self_quit_timer.cancel()
            self._self_quit_timer = threading.Timer(8.0, self._force_complete_self_quit)
            self._self_quit_timer.daemon = True
            self._self_quit_timer.start()
        except Exception:
            pass

    def _force_complete_self_quit(self) -> None:
        if not getattr(self, "_pending_self_quit", False):
            return
        self._pending_self_quit_farewell_received = True
        self._complete_self_quit_after_audio()

    def _mark_self_quit_farewell_received(self) -> None:
        if getattr(self, "_pending_self_quit", False):
            self._pending_self_quit_farewell_received = True

    def _complete_self_quit_after_audio(self) -> bool:
        """Close through the UI only after a farewell turn has actually completed."""
        if not (
            getattr(self, "_pending_self_quit", False)
            and getattr(self, "_pending_self_quit_farewell_received", False)
        ):
            return False
        self._pending_self_quit = False
        self._pending_self_quit_farewell_received = False
        if getattr(self, "_self_quit_timer", None) is not None:
            self._self_quit_timer.cancel()
            self._self_quit_timer = None
        self.request_shutdown()
        self.ui.handle_ui_command("Quit JARVIS")
        return True

    def request_shutdown(self) -> None:
        """Stop live tasks and make the process exit after the UI closes."""
        shutdown_requested = getattr(self, "_shutdown_requested", None)
        if shutdown_requested is None:
            self._shutdown_requested = threading.Event()
            shutdown_requested = self._shutdown_requested
        if shutdown_requested.is_set():
            return
        shutdown_requested.set()
        try:
            session = getattr(self, "session", None)
            loop = getattr(self, "_loop", None)
            if session is not None and loop is not None:
                asyncio.run_coroutine_threadsafe(session.close(), loop)
            out_queue = getattr(self, "out_queue", None)
            if out_queue is not None:
                out_queue.put_nowait(None)
        except Exception as exc:
            logger.info(f"[JARVIS] ⚠️ Shutdown session close failed: {exc}")

    def set_tour_active(self, active: bool) -> None:
        """Track whether the desktop introduction temporarily owns the UI."""
        self._tour_active = bool(active)

    async def _wait_before_reconnect(self, delay: float) -> None:
        deadline = time.monotonic() + max(0.0, float(delay))
        while not self._shutdown_requested.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            await asyncio.sleep(min(0.1, remaining))

    def _intercept_ui_tool_call(self, name: str, args: dict) -> str | None:
        """Safety net for stale models that attempt the removed quit tool action."""
        action = str(args.get("action") or "").strip().lower()
        if name != "shutdown_jarvis" and not (
            name == "jarvis_ui_control" and action == "quit_jarvis"
        ):
            return None

        transcript = str(getattr(self, "_current_input_transcript", "") or "")
        if not transcript:
            age = time.monotonic() - float(getattr(self, "_last_input_transcript_at", 0.0) or 0.0)
            if age <= 5.0:
                transcript = str(getattr(self, "_last_input_transcript", "") or "")

        if not self._is_explicit_self_quit_transcript(transcript):
            return "Ignored an unverified shutdown request. JARVIS remains online."

        self._queue_self_quit_after_farewell()
        return f'Shutdown queued. Say exactly: "{SELF_QUIT_GOODBYE}"'

    def update_voice(self, voice_name: str):
        self.voice_name = _normalize_voice_name(voice_name)
        self.ui.write_log(f"SYS: Voice change requested: {self.voice_name}")
        try:
            self.ui.sync_voice_display(self.voice_name)
        except Exception:
            pass
        if self.session and self._loop:
            try:
                asyncio.run_coroutine_threadsafe(self.session.close(), self._loop)
            except Exception as e:
                logger.info(f"[JARVIS] ⚠️ Could not close session after voice change: {e}")

    def _get_current_voice(self) -> str:
        if getattr(self, "voice_name", None):
            return _normalize_voice_name(self.voice_name)
        voice_combo = getattr(self.ui, "_voice_combo", None)
        if voice_combo is not None:
            idx = voice_combo.currentIndex()
            if idx >= 0:
                voice = voice_combo.itemData(idx)
                if isinstance(voice, str) and voice:
                    return _normalize_voice_name(voice)
            voice = voice_combo.currentText().strip().lower()
            if voice in SUPPORTED_VOICE_NAMES:
                return voice
        return _load_voice_name()

    async def _announce_startup(self):
        try:
            memory = load_memory()
            name_entry = memory.get("identity", {}).get("name")
            name = None
            if isinstance(name_entry, dict):
                name = name_entry.get("value")
            elif isinstance(name_entry, str):
                name = name_entry
            if name:
                greeting = f"Jarvis. At your service, {name}. What would you like to accomplish today?"
            else:
                greeting = "Jarvis. At your service, Sir or Madam. What would you like to accomplish today?"
            await self.session.send_client_content(
                turns={"parts": [{"text": greeting}]},
                turn_complete=True,
            )
        except Exception as e:
            logger.info(f"[JARVIS] ⚠️ Greeting failed: {e}")

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{
                "function_declarations": getattr(
                    self,
                    "tool_declarations",
                    [],
                )
            }],
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                    silence_duration_ms=get_settings().audio.vad_silence_ms,
                )
            ),
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            session_resumption=types.SessionResumptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self._get_current_voice()
                    )
                )
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        if getattr(self, "cloud_safe", False) and name not in CLOUD_SAFE_ACTIONS:
            return types.FunctionResponse(
                id=fc.id,
                name=name,
                response={
                    "result": (
                        f"Tool '{name}' is unavailable in cloud-safe mode."
                    )
                },
            )

        if getattr(self.ui, "operational_ready", True) is False:
            return types.FunctionResponse(
                id=fc.id,
                name=name,
                response={"result": "Startup sequence active. Try this action again when JARVIS is ready."},
            )

        from core.qa_mode import guard_tool_call, qa_block_message

        qa_decision = guard_tool_call(name, args)
        if not qa_decision.allowed:
            return types.FunctionResponse(
                id=fc.id,
                name=name,
                response={"result": qa_block_message(qa_decision)},
            )

        logger.info(f"[JARVIS] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")

        intercepted = self._intercept_ui_tool_call(name, args)
        if intercepted is not None:
            return types.FunctionResponse(
                id=fc.id, name=name, response={"result": intercepted}
            )

        # Fase 4 tool execution via registry (thin adapter modules).
        try:
            from tools.registry import ToolContext, registry

            tool_ctx = ToolContext(
                ui=self.ui,
                speak=self.speak,
                speak_vision_result=self._speak_vision_result,
            )
            tool_result = await registry.execute(name=name, ctx=tool_ctx, args=args)
            result = tool_result.get("result", "Done.")
            silent = bool(tool_result.get("silent", False))
        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            silent = False
            logger.exception("Unhandled exception")
            self.speak_error(name, str(e))

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        logger.info(f"[JARVIS] 📤 {name} → {str(result)[:80]}")
        response = {"result": result}
        if silent:
            response["silent"] = True

        return types.FunctionResponse(
            id=fc.id,
            name=name,
            response=response,
        )

        if name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                logger.info(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "ok", "silent": True}
            )

        result = "Done."

        tool_t0 = time.perf_counter()
        tool_ok = True

        try:
            if name == "open_app":
                r = await asyncio.to_thread(lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."

            elif name == "weather_report":
                r = await asyncio.to_thread(lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."

            elif name == "browser_control":
                r = await asyncio.to_thread(lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "file_controller":
                if (
                    args.get("action", "").lower() == "open"
                    and not args.get("path")
                    and not args.get("name")
                ):
                    current_file = getattr(self.ui, "current_file", None)
                    if current_file:
                        args["path"] = current_file
                r = await asyncio.to_thread(lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "check_messages":
                r = await asyncio.to_thread(
                    lambda: check_messages(parameters=args, response=None, player=self.ui, session_memory=None),
                )
                result = r or "No readable messages were found."

            elif name == "prepare_message_reply":
                r = await asyncio.to_thread(
                    lambda: prepare_message_reply(parameters=args, response=None, player=self.ui, session_memory=None),
                )
                result = r or "The message draft could not be prepared."

            elif name == "send_message":
                r = await asyncio.to_thread(lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Message sent to {args.get('receiver')}."

            elif name == "email_control":
                if args.get("action", "").lower() == "connect" and not args.get("credentials_path"):
                    current_file = getattr(self.ui, "current_file", None)
                    if current_file and Path(str(current_file)).suffix.lower() == ".json":
                        args["credentials_path"] = current_file
                r = await asyncio.to_thread(lambda: email_control(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or "Email action completed."

            elif name == "reminder":
                r = await asyncio.to_thread(lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder set."

            elif name == "youtube_video":
                r = await asyncio.to_thread(lambda: youtube_video(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "media_control":
                r = await asyncio.to_thread(lambda: media_control(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "screen_process":
                threading.Thread(
                    target=screen_process,
                    kwargs={"parameters": args, "response": None,
                            "player": self.ui, "session_memory": None,
                            "speak": self._speak_vision_result},
                    daemon=True
                ).start()
                result = "Vision module activated. Stay completely silent — vision module will speak directly."

            elif name == "computer_settings":
                r = await asyncio.to_thread(lambda: computer_settings(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "desktop_control":
                r = await asyncio.to_thread(lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "code_helper":
                r = await asyncio.to_thread(lambda: code_helper(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "dev_agent":
                r = await asyncio.to_thread(lambda: dev_agent(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "agent_task":
                from agent.task_queue import get_queue, TaskPriority
                priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
                task_id  = get_queue().submit(
                    goal=args.get("goal", ""),
                    priority=priority,
                    speak=self.speak,
                    immediate=True,
                )
                result   = f"Task started (ID: {task_id})."

            elif name == "web_search":
                r = await asyncio.to_thread(lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "file_processor":
                if not args.get("file_path") and self.ui.current_file:
                    args["file_path"] = self.ui.current_file
                r = await asyncio.to_thread(
                    lambda: file_processor(parameters=args, player=self.ui, speak=self.speak)
                )
                result = r or "Done."

            elif name == "computer_control":
                r = await asyncio.to_thread(lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "game_updater":
                r = await asyncio.to_thread(lambda: game_updater(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "flight_finder":
                r = await asyncio.to_thread(lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "graphics_quality":
                quality = str(args.get("quality") or "").strip().lower()
                if quality not in {"low", "medium", "high"}:
                    raise ValueError("Graphics quality must be low, medium, or high.")
                self.ui.set_graphics_quality(quality)
                result = f"JARVIS graphics quality changed to {quality}."

            elif name == "jarvis_ui_control":
                action = str(args.get("action") or "").strip().lower()
                if action == "change_theme":
                    theme = str(args.get("theme") or "").strip().lower()
                    allowed = {"arc_reactor", "stealth_red", "vibranium_purple", "nanotech_gold", "platinum"}
                    if theme not in allowed:
                        raise ValueError(f"Unknown JARVIS theme: {theme or 'missing'}")
                    self.ui.set_theme(theme)
                    result = f"JARVIS theme changed to {theme.replace('_', ' ')}."
                elif action == "change_graphics_quality":
                    quality = str(args.get("graphics_quality") or "").strip().lower()
                    if quality not in {"low", "medium", "high"}:
                        raise ValueError(f"Unknown graphics quality: {quality or 'missing'}")
                    self.ui.set_graphics_quality(quality)
                    result = f"JARVIS graphics quality changed to {quality}."
                else:
                    self.ui.handle_ui_command(action)
                    result = f"JARVIS interface action completed: {action.replace('_', ' ')}."

            elif name == "deep_research":
                r = request_deep_research(parameters=args, player=self.ui, speak=self.speak)
                result = r or "Deep research preference requested."

            elif name == "create_presentation":
                current_file = getattr(self.ui, "current_file", None)
                supported_sources = {
                    ".txt", ".md", ".rst", ".csv", ".json", ".jsonl", ".docx", ".pptx",
                    ".pdf", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".webp",
                    ".wav", ".mp3", ".m4a", ".mp4", ".mov", ".avi", ".webm",
                }
                if (
                    not args.get("source_file")
                    and not args.get("source_files")
                    and current_file
                    and Path(str(current_file)).suffix.lower() in supported_sources
                ):
                    args["source_files"] = [current_file]
                r = request_presentation(parameters=args, player=self.ui, speak=self.speak)
                result = r or "Presentation preference requested."

            elif name == "task_status":
                from agent.task_queue import get_queue

                queue = get_queue()
                action = str(args.get("action") or "get").lower()
                task_id = str(args.get("task_id") or "").strip()
                if action == "all" or not task_id:
                    result = json.dumps(queue.get_all_statuses(), ensure_ascii=False)
                elif action == "cancel":
                    result = f"Task {task_id} cancelled." if queue.cancel(task_id) else f"Task {task_id} could not be cancelled."
                else:
                    status = queue.get_status(task_id)
                    result = json.dumps(status, ensure_ascii=False) if status else f"Task {task_id} was not found."

            else:
                result = f"Unknown tool: {name}"

        except Exception as e:
            tool_ok = False
            result = f"Tool '{name}' failed: {e}"
            logger.exception("Unhandled exception")
            self.speak_error(name, e)

        # Record tool latency (best-effort; never break tool execution)
        try:
            metrics.record_tool_call(name=name, ok=tool_ok, latency_s=time.perf_counter() - tool_t0)
        except Exception:
            pass

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        logger.info(f"[JARVIS] 📤 {name} → {str(result)[:80]}")
        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _execute_tool_batch(self, calls):
        """Run read-only calls concurrently while preserving mutation order."""
        mutating = {
            "send_message", "prepare_message_reply", "email_control", "reminder",
            "computer_settings", "computer_control", "desktop_control", "file_controller",
            "file_processor", "code_helper", "dev_agent", "game_updater",
            "create_presentation", "save_memory", "jarvis_ui_control", "graphics_quality",
        }
        call_list = list(calls or [])
        if any(getattr(call, "name", "") in mutating for call in call_list):
            return [await self._execute_tool(call) for call in call_list]
        return list(await asyncio.gather(*(self._execute_tool(call) for call in call_list)))

    async def _send_realtime(self):
        while True:
            if self._shutdown_requested.is_set():
                return
            msg = await self.out_queue.get()
            if msg is None or self._shutdown_requested.is_set():
                return
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        logger.info("[JARVIS] 🎤 Mic started")
        loop = asyncio.get_event_loop()

        def callback(indata, frames, time_info, status):
            with self._speaking_lock:
                jarvis_speaking = self._is_speaking
            if not jarvis_speaking and not self.ui.muted:
                data = indata.tobytes()
                loop.call_soon_threadsafe(
                    self.out_queue.put_nowait,
                    {"data": data, "mime_type": "audio/pcm"}
                )

        try:
            with sd.InputStream(
                samplerate=get_settings().audio.send_sample_rate,
                channels=get_settings().audio.channels,
                dtype="int16",
                blocksize=get_settings().audio.chunk_size,
                callback=callback,
            ):
                logger.info("[JARVIS] 🎤 Mic stream open")
                while not self._shutdown_requested.is_set():
                    await asyncio.sleep(0.1)
        except Exception as e:
            logger.info(f"[JARVIS] ❌ Mic: {e}")
            raise

    async def _receive_audio(self):
        logger.info("[JARVIS] 👂 Recv started")
        out_buf, in_buf = [], []
        _new_turn = True
        turn_had_audio = False

        try:
            while True:
                if self._shutdown_requested.is_set():
                    return
                async for response in self.session.receive():

                    response_audio = _live_response_audio_bytes(response)
                    if response_audio:
                        turn_had_audio = True
                        if self._turn_done_event and self._turn_done_event.is_set():
                            self._turn_done_event.clear()
                        self.audio_in_queue.put_nowait(response_audio)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            if txt:
                                out_buf.append(txt)
                                self._interrupted_text = " ".join(out_buf)
                                if not self.ui.muted:
                                    if _new_turn:
                                        self.ui.clear_subtitle()
                                        _new_turn = False
                                    self.ui.show_subtitle(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt:
                                if not in_buf:
                                    self._current_input_transcript = ""
                                in_buf.append(txt)
                                self._current_input_transcript = " ".join(in_buf).strip()
                                if (
                                    not getattr(self, "_pending_self_quit", False)
                                    and self._is_explicit_self_quit_transcript(self._current_input_transcript)
                                ):
                                    self._queue_self_quit_after_farewell()

                        if sc.turn_complete:
                            if self._turn_done_event:
                                self._turn_done_event.set()

                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self._current_input_transcript = full_in
                                self._last_input_transcript = full_in
                                self._last_input_transcript_at = time.monotonic()
                                if (
                                    not getattr(self, "_pending_self_quit", False)
                                    and self._is_explicit_self_quit_transcript(full_in)
                                ):
                                    self._queue_self_quit_after_farewell()
                                self.ui.write_log(f"You: {full_in}")
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"Jarvis: {full_out}")
                            if (
                                getattr(self, "_pending_self_quit", False)
                                and (full_out or turn_had_audio)
                            ):
                                self._mark_self_quit_farewell_received()
                                
                            out_buf = []
                            turn_had_audio = False
                            _new_turn = True

                    if response.tool_call:
                        function_calls = list(response.tool_call.function_calls)
                        for fc in function_calls:
                            logger.info(f"[JARVIS] 📞 {fc.name}")
                        fn_responses = await self._execute_tool_batch(function_calls)
                        await self.session.send_tool_response(
                            function_responses=fn_responses
                        )
                    if self._shutdown_requested.is_set():
                        return
        except Exception as e:
            if isinstance(e, genai.errors.APIError) and "1000" in str(e):
                logger.info("[JARVIS] 🔌 Session closed normally.")
                return
            logger.info(f"[JARVIS] ❌ Recv: {e}")
            logger.exception("Unhandled exception")
            raise



    async def _play_audio(self):
        logger.info("[JARVIS] 🔊 Play started")

        stream = None
        if not self.external_audio:
            stream = sd.RawOutputStream(
                samplerate=get_settings().audio.receive_sample_rate,
                channels=get_settings().audio.channels,
                dtype="int16",
                blocksize=get_settings().audio.chunk_size,
            )
            stream.start()

        try:
            while True:
                if self._shutdown_requested.is_set():
                    return
                try:
                    _audio_get_t0 = time.perf_counter()
                    chunk = await asyncio.wait_for(
                        self.audio_in_queue.get(),
                        timeout=0.1
                    )
                    try:
                        metrics.record_audio_latency(time.perf_counter() - _audio_get_t0)
                    except Exception:
                        pass
                except asyncio.TimeoutError:
                    if (
                        self._turn_done_event
                        and self._turn_done_event.is_set()
                        and self.audio_in_queue.empty()
                    ):
                        self.set_speaking(False)
                        self._turn_done_event.clear()
                        if self._complete_self_quit_after_audio():
                            return
                    continue
                # Skip Gemini audio when external TTS is active
                if self._tts_engine and self._ext_tts_provider and self._ext_tts_provider != "gemini":
                    pass  # drain silently
                else:
                    self.set_speaking(True)
                    if self.external_audio:
                        send_audio = getattr(self.client, "send_audio", None)
                        if callable(send_audio):
                            send_audio(chunk, f"audio/pcm;rate={get_settings().audio.receive_sample_rate}")
                    elif stream is not None:
                        await asyncio.to_thread(stream.write, chunk)
        except Exception as e:
            logger.info(f"[JARVIS] ❌ Play: {e}")
            raise
        finally:
            self.set_speaking(False)
            if stream is not None:
                stream.stop()
                stream.close()

    async def run(self):
        api_key = self._api_key or _get_api_key()
        client = genai.Client(
            api_key=api_key,
            http_options={"api_version": "v1beta"}
        )
        live_model = await asyncio.to_thread(pick_live_model, client, API_CONFIG_PATH)
        live_model_id = live_model.removeprefix("models/")
        self.ui.write_log(f"SYS: Gemini Live model selected: {live_model_id}")

        start_time = time.time()
        reconnect_attempt = 0
        while True:
            if self._shutdown_requested.is_set():
                return
            # enforce runtime limit if configured
            if self.runtime_limit_seconds is not None:
                elapsed = time.time() - start_time
                if elapsed >= float(self.runtime_limit_seconds):
                    logger.info(f"[JARVIS] ⏱️ Runtime limit reached ({self.runtime_limit_seconds}s). Exiting.")
                    try:
                        jarvis_status.write_status({"state": "expired"})
                    except Exception:
                        pass
                    os._exit(0)

            # enforce presence of required unlock path (e.g. mounted encrypted volume)
            if getattr(self, "required_unlock_path", None):
                try:
                    path = Path(self.required_unlock_path)
                    if not path.exists():
                        logger.info(f"[JARVIS] 🔒 Required unlock path not present: {self.required_unlock_path}")
                        logger.info("Please mount the locked container (see scripts/create_locked_dmg.sh).")
                        time.sleep(5)
                        continue
                    if self.required_unlock_secret is not None:
                        content = path.read_text(encoding="utf-8").strip()
                        if content != self.required_unlock_secret:
                            logger.info("[JARVIS] 🔒 unlock.key content does not match expected secret.")
                            logger.info("Please mount the locked container with the correct unlock.key file.")
                            time.sleep(5)
                            continue
                except Exception as e:
                    logger.info(f"[JARVIS] 🔒 Locked path check error: {e}")
                    time.sleep(1)
                    continue
            try:
                reconnect_attempt += 1
                logger.info("[JARVIS] 🔌 Connecting...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=live_model_id, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue      = asyncio.Queue(maxsize=10)
                    self._turn_done_event = asyncio.Event()

                    logger.info("[JARVIS] ✅ Connected.")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: JARVIS online.")
                    if not self.cloud_safe:
                        try:
                            jarvis_status.write_status({
                                "state": "online",
                                "voice": self._get_current_voice(),
                                "pid": os.getpid(),
                            })
                        except Exception:
                            pass

                    tg.create_task(self._send_realtime())
                    if not self.external_audio:
                        tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())
                    tg.create_task(self._announce_startup())

            except Exception as e:
                if self._shutdown_requested.is_set():
                    return
                actual = e
                if isinstance(e, ExceptionGroup) and len(e.exceptions) == 1:
                    actual = e.exceptions[0]

                if _is_unsupported_voice_error(actual) and self.voice_name != DEFAULT_VOICE_NAME:
                    old_voice = self.voice_name
                    self.voice_name = DEFAULT_VOICE_NAME
                    self.ui.write_log(
                        f"SYS: Voice '{old_voice}' not available. Falling back to {DEFAULT_VOICE_NAME}."
                    )
                    logger.info(f"[JARVIS] ⚠️ Voice '{old_voice}' unsupported; falling back to {DEFAULT_VOICE_NAME}.")
                    self.ui.sync_voice_display(DEFAULT_VOICE_NAME)
                    if not self.cloud_safe:
                        try:
                            jarvis_status.write_status({"state": "voice_fallback", "voice": DEFAULT_VOICE_NAME})
                        except Exception:
                            pass
                elif isinstance(actual, genai.errors.APIError) and "1000" in str(actual):
                    logger.info("[JARVIS] 🔌 Session ended normally.")
                    if not self.cloud_safe:
                        try:
                            jarvis_status.write_status({"state": "offline"})
                        except Exception:
                            pass
                else:
                    # Optional provider resilience: transient connection errors can be
                    # retried with backoff/jitter. By default, backoff is disabled to
                    # preserve existing reconnect timing.
                    if _is_transient_live_connection_error(actual):
                        try:
                            if get_settings().runtime.reconnect_backoff_enabled:
                                metrics.record_reconnect_attempt()
                                delay = _live_reconnect_delay(reconnect_attempt)
                                jitter_ratio = float(get_settings().runtime.reconnect_jitter_ratio or 0.0)
                                if jitter_ratio > 0:
                                    delay = _compute_jitter_delay(
                                        delay,
                                        jitter_ratio,
                                        rand_fn=random.random,
                                    )
                                max_attempts = int(get_settings().runtime.reconnect_max_attempts or 0)
                                if max_attempts > 0 and reconnect_attempt > max_attempts:
                                    logger.info("[JARVIS] Reconnect attempts limit reached; exiting")
                                    os._exit(0)
                                logger.info(f"[JARVIS] Transient error; retrying in {delay:.2f}s (attempt {reconnect_attempt})")
                                await self._wait_before_reconnect(delay)
                                continue
                        except Exception:
                            # Never break the main loop due to metrics/backoff logic.
                            pass

                    logger.info(f"[JARVIS] ⚠️ {e}")
                    logger.exception("Unhandled exception")

def main():
    import sys

    if "--self-test" in sys.argv[1:]:
        from scripts.self_test import main as self_test_main

        return self_test_main([argument for argument in sys.argv[1:] if argument != "--self-test"])

    from ui import JarvisUI

    running_as_app = getattr(sys, "frozen", False)

    if os.environ.get("JARVIS_CLI") != "1" and not running_as_app:
        logger.info("[JARVIS] Please launch with the JARVIS CLI: jarvis")
        return
    if not wait_for_startup_claps():
        return
    logger.info("[JARVIS] ⚡ Powering up the interface...")
    try:
        ui = JarvisUI("face.png")
    except Exception as exc:
        logger.info(f"[JARVIS] ❌ Interface startup failed: {exc}")
        logger.exception("Unhandled exception")
        return

    def runner():
        ui.wait_for_api_key()
        voice_name = _load_voice_name()
        jarvis = JarvisLive(ui, voice_name)
        ui.on_quit_requested = jarvis.request_shutdown

        # Trial/keyword runtime limiting: set via env `JARVIS_TRIAL_KEYWORD`.
        # If set to any non-empty string, jarvis will run for 3600 seconds (1 hour).
        trial_kw = os.environ.get("JARVIS_TRIAL_KEYWORD")
        if trial_kw:
            jarvis.runtime_limit_seconds = int(os.environ.get("JARVIS_RUNTIME_SECONDS", "3600"))
            jarvis.ui.write_log(f"SYS: Trial keyword detected. Running for {jarvis.runtime_limit_seconds} seconds.")

        locked_secret = os.environ.get("JARVIS_LOCKED_KEY_SECRET")
        if locked_secret:
            jarvis.required_unlock_secret = locked_secret.strip()

        # Locked container check: if `JARVIS_LOCKED_VOLUME` is set, require
        # presence of `/Volumes/<name>/unlock.key` before full operation.
        locked_vol = os.environ.get("JARVIS_LOCKED_VOLUME")
        if locked_vol:
            mount_path = f"/Volumes/{locked_vol}/unlock.key"
            jarvis.required_unlock_path = mount_path
            jarvis.ui.write_log(f"SYS: Locked volume required: {mount_path}")
        ui.on_voice_change = jarvis.update_voice
        def _on_tts_change(provider, api_key, voice_id):
            if provider == "gemini":
                jarvis._tts_engine = None
                jarvis._ext_tts_provider = ""
                jarvis._ext_tts_voice_id = ""
                jarvis._ext_tts_api_key = ""
                jarvis.update_voice(voice_id)
            else:
                jarvis._ext_tts_provider = provider
                jarvis._ext_tts_voice_id = voice_id
                jarvis._ext_tts_api_key = api_key
                try:
                    from actions.tts_engine import TTSEngine
                    jarvis._tts_engine = TTSEngine(
                        provider=provider,
                        api_key=api_key,
                        voice_id=voice_id,
                    )
                    jarvis.ui.write_log(f"SYS: TTS engine ready: {provider} / {voice_id}")
                    jarvis.ui.write_log("SYS: Gemini audio muted - using external TTS")
                except Exception as e:
                    jarvis.ui.write_log(f"SYS: TTS engine error: {e}")
                # Restart session so new TTS takes effect
                if jarvis.session and jarvis._loop:
                    try:
                        asyncio.run_coroutine_threadsafe(jarvis.session.close(), jarvis._loop)
                    except Exception as e:
                        logger.info(f"[JARVIS] Could not close session: {e}")
        ui.on_tts_provider_change = _on_tts_change
        try:
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            logger.info("\n🔴 Shutting down...")
        except Exception as exc:
            message = f"Gemini startup failed: {str(exc)[:180]}"
            logger.info(f"[JARVIS] ❌ {message}")
            try:
                ui.write_log(f"ERR: {message}")
                ui.set_state("LISTENING")
            except Exception:
                pass

    threading.Thread(target=runner, daemon=True).start()
    logger.info("[JARVIS] ✅ Interface ready.")
    ui.root.mainloop()
    logger.info("[JARVIS] Interface closed.")

def cli_main():
    """Canonical console entry point installed as the `jarvis` command."""
    os.environ["JARVIS_CLI"] = "1"
    return main()


if __name__ == "__main__":
    raise SystemExit(main() or 0)
