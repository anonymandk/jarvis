"use client";

import type { ArgusState } from "@/hooks/use-argus-socket";

const STATE_LABELS: Record<ArgusState, string> = {
  idle: "Em espera",
  listening: "Ouvindo",
  processing: "Processando",
  speaking: "Falando",
  reconnecting: "Reconectando",
  error: "Erro",
  muted: "Microfone silenciado",
};

export function Reactor({ state }: { state: ArgusState }) {
  return (
    <div
      key={state}
      className={`reactor reactor-${state} is-transitioning`}
      aria-label={`Núcleo ARGUS. Estado: ${STATE_LABELS[state]}`}
      role="img"
    >
      <div className="reactor-orbit orbit-a" aria-hidden="true" />
      <div className="reactor-orbit orbit-b" aria-hidden="true" />
      <div className="reactor-spokes" aria-hidden="true" />
      <div className="reactor-core" aria-hidden="true"><span>J</span></div>
    </div>
  );
}
