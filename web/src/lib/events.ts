export type Envelope = {
  v: 1;
  type: string;
  ts: string;
  session_id: string;
  seq: number;
  payload: Record<string, unknown>;
};

export type EnvelopeContext = { sessionId: string; sequence: number; turnId?: string };

type RawEvent = Record<string, unknown>;

const STATE_ALIASES: Record<string, string> = {
  IDLE: "idle",
  STANDBY: "idle",
  "STANDING BY": "idle",
  LISTENING: "listening",
  HEARING: "listening",
  THINKING: "processing",
  PROCESSING: "processing",
  EXECUTING: "processing",
  SPEAKING: "speaking",
  RECONNECTING: "reconnecting",
  RECONNECT: "reconnecting",
  ERROR: "error",
  FAILED: "error",
  MUTED: "muted",
  SILENCED: "muted",
  "MICROPHONE MUTED": "muted",
};

function object(value: unknown): RawEvent | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as RawEvent
    : null;
}

function timestamp(value: unknown): string {
  if (typeof value === "string" && Number.isFinite(Date.parse(value))) {
    return new Date(value).toISOString();
  }
  return new Date().toISOString();
}

function makeEnvelope(
  context: EnvelopeContext,
  type: string,
  payload: Record<string, unknown>,
  at?: unknown,
): Envelope {
  context.sequence += 1;
  return {
    v: 1,
    type,
    ts: timestamp(at),
    session_id: context.sessionId,
    seq: context.sequence,
    payload,
  };
}

function currentTurn(context: EnvelopeContext, startNew = false): string {
  if (startNew || !context.turnId) {
    context.turnId = `${context.sessionId}-${context.sequence + 1}`;
  }
  return context.turnId;
}

export function normalizeJarvisState(value: unknown): string | null {
  return typeof value === "string"
    ? STATE_ALIASES[value.trim().toUpperCase()] ?? null
    : null;
}

/** Translate the current API frames to the shared UI v1 envelope. */
export function mapSocketEvent(value: unknown, context: EnvelopeContext): Envelope | null {
  const raw = object(value);
  if (!raw) return null;

  if (raw.v === 1) {
    if (
      typeof raw.type !== "string"
      || typeof raw.ts !== "string"
      || typeof raw.session_id !== "string"
      || typeof raw.seq !== "number"
      || !object(raw.payload)
    ) return null;
    context.sequence = Math.max(context.sequence, raw.seq);
    return raw as Envelope;
  }

  const at = raw.timestamp;
  switch (raw.type) {
    case "status": {
      const state = normalizeJarvisState(raw.state);
      return state ? makeEnvelope(context, "state", { state, source: "websocket_adapter" }, at) : null;
    }
    case "message": {
      const speaker = raw.role === "assistant" || raw.role === "user" ? raw.role : "system";
      const turnId = currentTurn(context, speaker === "user");
      return makeEnvelope(context, "transcript", {
        speaker,
        text: String(raw.content ?? ""),
        final: true,
        turn_id: turnId,
      }, at);
    }
    case "transcript":
      return makeEnvelope(context, "transcript", {
        speaker: "assistant",
        text: String(raw.content ?? ""),
        final: raw.final === true,
        turn_id: currentTurn(context),
      }, at);
    case "transcript_clear":
      return makeEnvelope(context, "transcript", {
        speaker: "assistant",
        text: "",
        final: true,
        clear: true,
        turn_id: currentTurn(context, true),
      }, at);
    case "progress":
      return makeEnvelope(context, "progress", {
        kind: String(raw.kind ?? "task"),
        label: String(raw.label ?? "Atividade em andamento"),
        percent: typeof raw.percent === "number" && Number.isFinite(raw.percent) ? raw.percent : null,
        phase: String(raw.phase ?? ""),
        visible: raw.visible !== false,
      }, at);
    case "progress_end":
      return makeEnvelope(context, "progress", {
        kind: String(raw.kind ?? "task"),
        completed: true,
        state: String(raw.state ?? ""),
        detail: String(raw.detail ?? ""),
      }, at);
    case "progress_hide":
      return makeEnvelope(context, "progress", { visible: false }, at);
    case "error": {
      const payload: Record<string, unknown> = {
        code: typeof raw.code === "string" ? raw.code : "unspecified",
        message: String(raw.message ?? "O cliente sinalizou um erro."),
      };
      if (typeof raw.recoverable === "boolean") payload.recoverable = raw.recoverable;
      if (typeof raw.retry_after_ms === "number") payload.retry_after_ms = raw.retry_after_ms;
      return makeEnvelope(context, "error", payload, at);
    }
    case "audio":
      return makeEnvelope(context, "audio", {
        data: String(raw.data ?? ""),
        mime_type: String(raw.mime_type ?? "audio/pcm;rate=24000"),
      }, at);
    case "ready": {
      const state = normalizeJarvisState(raw.state);
      return makeEnvelope(context, "ready", state ? { state } : {}, at);
    }
    default:
      return null;
  }
}
