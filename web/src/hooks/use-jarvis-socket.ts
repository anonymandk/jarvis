"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getToken, WS_URL } from "@/lib/api";
import { mapSocketEvent, normalizeJarvisState, type EnvelopeContext } from "@/lib/events";

export type JarvisState = "idle" | "listening" | "processing" | "speaking" | "reconnecting" | "error" | "muted";
export type ConnectionState = "offline" | "connecting" | "connected" | "reconnecting";
export type Message = { id: string; role: "user" | "assistant" | "system"; content: string; at: string };
export type LogEntry = { id: string; level: string; source: string; message: string; at: string };
export type Progress = { kind: string; label: string; percent: number | null; phase: string } | null;

type Capture = {
  context: AudioContext;
  stream: MediaStream;
  source: MediaStreamAudioSourceNode;
  processor: ScriptProcessorNode;
  sink: GainNode;
};

function pcm16(input: Float32Array, sourceRate: number, targetRate = 16000) {
  const ratio = sourceRate / targetRate;
  const length = Math.max(1, Math.floor(input.length / ratio));
  const output = new Int16Array(length);
  for (let i = 0; i < length; i += 1) {
    const start = Math.floor(i * ratio);
    const end = Math.min(input.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = start; j < end; j += 1) sum += input[j];
    const value = Math.max(-1, Math.min(1, sum / Math.max(1, end - start)));
    output[i] = value < 0 ? value * 32768 : value * 32767;
  }
  return output;
}

function messageRole(value: unknown): Message["role"] {
  return value === "user" || value === "assistant" ? value : "system";
}

export function useJarvisSocket() {
  const socket = useRef<WebSocket | null>(null);
  const capture = useRef<Capture | null>(null);
  const playback = useRef<AudioContext | null>(null);
  const nextPlaybackAt = useRef(0);
  const desired = useRef(true);
  const retryCount = useRef(0);
  const envelopeContext = useRef<EnvelopeContext>({
    sessionId: "",
    sequence: 0,
  });
  const [state, setState] = useState<JarvisState>("idle");
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [messages, setMessages] = useState<Message[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [transcript, setTranscript] = useState("");
  const [progress, setProgress] = useState<Progress>(null);
  const [error, setError] = useState("");
  const [micActive, setMicActive] = useState(false);

  const ensurePlayback = useCallback(async () => {
    if (!playback.current) playback.current = new AudioContext({ sampleRate: 24000 });
    if (playback.current.state === "suspended") await playback.current.resume();
    return playback.current;
  }, []);

  const playAudio = useCallback(async (encoded: string) => {
    const context = await ensurePlayback();
    const binary = window.atob(encoded);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    const view = new DataView(bytes.buffer);
    const samples = new Float32Array(Math.floor(bytes.byteLength / 2));
    for (let i = 0; i < samples.length; i += 1) samples[i] = view.getInt16(i * 2, true) / 32768;
    if (samples.length === 0) return;
    const buffer = context.createBuffer(1, samples.length, 24000);
    buffer.copyToChannel(samples, 0);
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(context.destination);
    const start = Math.max(context.currentTime + 0.02, nextPlaybackAt.current);
    source.start(start);
    nextPlaybackAt.current = start + buffer.duration;
  }, [ensurePlayback]);

  const consumeEvent = useCallback((raw: unknown) => {
    const envelope = mapSocketEvent(raw, envelopeContext.current);
    if (!envelope) return;
    const payload = envelope.payload;
    switch (envelope.type) {
      case "ready":
        setError("");
        break;
      case "state": {
        const next = normalizeJarvisState(payload.state) as JarvisState | null;
        if (!next) break;
        setState(next);
        if (next !== "error") setError("");
        break;
      }
      case "transcript": {
        if (payload.clear === true) {
          setTranscript("");
          break;
        }
        const content = String(payload.text ?? "");
        if (content) {
          setTranscript(payload.final === true ? "" : (current) => `${current} ${content}`.trim());
          if (payload.final === true) {
            const role = messageRole(payload.speaker);
            setMessages((current) => {
              const previous = current[current.length - 1];
              if (previous?.role === role && previous.content === content) return current;
              return [...current.slice(-99), { id: crypto.randomUUID(), role, content, at: envelope.ts }];
            });
          }
        }
        break;
      }
      case "log":
        setLogs((current) => [...current.slice(-99), {
          id: crypto.randomUUID(),
          level: String(payload.level ?? "info"),
          source: String(payload.source ?? "jarvis"),
          message: String(payload.message ?? ""),
          at: envelope.ts,
        }]);
        break;
      case "error":
        setState("error");
        setError(String(payload.message ?? "O cliente sinalizou um erro."));
        break;
      case "progress":
        if (payload.visible === false || payload.completed === true) {
          setProgress(null);
        } else {
          const percent = typeof payload.percent === "number" && Number.isFinite(payload.percent)
            ? Math.min(100, Math.max(0, payload.percent))
            : null;
          setProgress({
            kind: String(payload.kind ?? "task"),
            label: String(payload.label ?? "Atividade em andamento"),
            percent,
            phase: String(payload.phase ?? ""),
          });
        }
        break;
      case "audio":
        if (typeof payload.data === "string" && payload.data) {
          void playAudio(payload.data).catch(() => setError("O navegador bloqueou a reprodução de áudio. Interaja com a página e tente novamente."));
        }
        break;
      default:
        break;
    }
  }, [playAudio]);

  useEffect(() => {
    desired.current = true;
    let retry: ReturnType<typeof setTimeout> | undefined;

    function connect() {
      const token = getToken();
      if (!token || !desired.current) {
        setConnection("offline");
        return;
      }
      if (!envelopeContext.current.sessionId) {
        envelopeContext.current.sessionId = globalThis.crypto?.randomUUID?.()
          ?? `web-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
      }
      setConnection(retryCount.current > 0 ? "reconnecting" : "connecting");
      const ws = new WebSocket(`${WS_URL}/ws?token=${encodeURIComponent(token)}`);
      ws.binaryType = "arraybuffer";
      socket.current = ws;
      ws.onopen = () => {
        if (socket.current !== ws) return;
        retryCount.current = 0;
        setConnection("connected");
      };
      ws.onmessage = (message) => {
        if (socket.current !== ws || typeof message.data !== "string") return;
        try {
          consumeEvent(JSON.parse(message.data) as unknown);
        } catch {
          setError("O servidor enviou um evento que não pôde ser lido.");
        }
      };
      ws.onerror = () => {
        if (socket.current === ws) setError("Não foi possível acessar o canal ao vivo. Verifique a conexão.");
      };
      ws.onclose = (event) => {
        if (socket.current !== ws) return;
        socket.current = null;
        setConnection("offline");
        if (event.code === 4403) {
          setState("error");
          setError("A chave do Gemini precisa de atenção. Confira a configuração da conta.");
          return;
        }
        if (desired.current) {
          retryCount.current += 1;
          setConnection("reconnecting");
          retry = setTimeout(connect, 2500);
        }
      };
    }

    connect();
    return () => {
      desired.current = false;
      if (retry) clearTimeout(retry);
      socket.current?.close();
    };
  }, [consumeEvent]);

  const sendText = useCallback(async (content: string) => {
    const clean = content.trim();
    if (!clean || socket.current?.readyState !== WebSocket.OPEN) return false;
    await ensurePlayback();
    setMessages((current) => [...current.slice(-99), {
      id: crypto.randomUUID(), role: "user", content: clean, at: new Date().toISOString(),
    }]);
    socket.current.send(JSON.stringify({ type: "text", content: clean }));
    return true;
  }, [ensurePlayback]);

  const stopMic = useCallback(async () => {
    const current = capture.current;
    if (current) {
      current.processor.disconnect();
      current.source.disconnect();
      current.sink.disconnect();
      current.stream.getTracks().forEach((track) => track.stop());
      await current.context.close();
      capture.current = null;
    }
    setMicActive(false);
    if (socket.current?.readyState === WebSocket.OPEN) {
      socket.current.send(JSON.stringify({ type: "mute", muted: true }));
    }
  }, []);

  const startMic = useCallback(async () => {
    if (capture.current) return;
    try {
      await ensurePlayback();
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      const context = new AudioContext();
      const source = context.createMediaStreamSource(stream);
      const processor = context.createScriptProcessor(4096, 1, 1);
      const sink = context.createGain();
      sink.gain.value = 0;
      processor.onaudioprocess = (event) => {
        if (socket.current?.readyState !== WebSocket.OPEN) return;
        const encoded = pcm16(event.inputBuffer.getChannelData(0), context.sampleRate);
        socket.current.send(encoded.buffer);
      };
      source.connect(processor);
      processor.connect(sink);
      sink.connect(context.destination);
      capture.current = { context, stream, source, processor, sink };
      setMicActive(true);
      socket.current?.send(JSON.stringify({ type: "mute", muted: false }));
    } catch (reason) {
      setError(reason instanceof Error ? `Não foi possível iniciar o microfone: ${reason.message}` : "O acesso ao microfone foi negado.");
    }
  }, [ensurePlayback]);

  useEffect(() => () => { void stopMic(); void playback.current?.close(); }, [stopMic]);

  return { state, connection, messages, logs, transcript, progress, error, micActive, sendText, startMic, stopMic };
}
