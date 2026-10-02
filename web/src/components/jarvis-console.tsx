"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Activity, ArrowUp, CircleDot, LogOut, MessageSquareText, Mic, MicOff, Radio, ScrollText, ShieldCheck, Wifi, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Reactor } from "@/components/reactor";
import { useJarvisSocket, type ConnectionState, type JarvisState } from "@/hooks/use-jarvis-socket";
import { api, type Action, type User } from "@/lib/api";

const STATE_LABELS: Record<JarvisState, string> = {
  idle: "Em espera",
  listening: "Ouvindo",
  processing: "Processando",
  speaking: "Falando",
  reconnecting: "Reconectando",
  error: "Erro",
  muted: "Microfone silenciado",
};

const CONNECTION_LABELS: Record<ConnectionState, string> = {
  offline: "Desconectado",
  connecting: "Conectando",
  connected: "Conectado",
  reconnecting: "Reconectando",
};

export function JarvisConsole({ user, onSignOut }: { user: User; onSignOut: () => void }) {
  const live = useJarvisSocket();
  const [actions, setActions] = useState<Action[]>([]);
  const [draft, setDraft] = useState("");
  const logEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api<{ actions: Action[] }>("/actions").then((data) => setActions(data.actions)).catch(() => undefined);
  }, []);
  useEffect(() => {
    const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
    logEnd.current?.scrollIntoView({ behavior, block: "end" });
  }, [live.messages]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (await live.sendText(draft)) setDraft("");
  }

  const connected = live.connection === "connected";
  const stateLabel = STATE_LABELS[live.state];
  const errorMessage = live.error || "O cliente sinalizou um erro. Verifique a conexão e tente novamente.";

  return (
    <main className="console-shell" lang="pt-BR">
      <header className="console-header">
        <div className="wordmark"><span className="wordmark-mark">J</span> JARVIS <small>MARK XXXIX</small></div>
        <div className={`header-state connection-${live.connection}`} aria-live="polite" aria-label={`Conexão: ${CONNECTION_LABELS[live.connection]}`}>
          {connected ? <Wifi size={16} aria-hidden="true" /> : <WifiOff size={16} aria-hidden="true" />}
          <span>{CONNECTION_LABELS[live.connection]}</span>
        </div>
        <div className="operator-menu"><span>{user.display_name}</span><Button variant="ghost" size="sm" onClick={onSignOut}><LogOut size={16} /> Sair</Button></div>
      </header>

      <div className="console-grid">
        <nav className="console-rail" aria-label="Navegação principal">
          <a href="#mission-log" aria-label="Ir para conversa" aria-current="page"><MessageSquareText size={18} aria-hidden="true" /></a>
          <a href="#command-title" aria-label="Ir para o núcleo JARVIS"><CircleDot size={18} aria-hidden="true" /></a>
          <a href="#systems-title" aria-label="Ir para estado operacional"><Activity size={18} aria-hidden="true" /></a>
          <a href="#session-logs" aria-label="Ir para registros da sessão"><ScrollText size={18} aria-hidden="true" /></a>
        </nav>

        <section className="mission-log" id="mission-log" aria-labelledby="log-title">
          <div className="panel-heading"><div><p className="section-index">CONVERSA / SESSÃO ATUAL</p><h2 id="log-title">Conversa</h2></div><Radio size={18} aria-hidden="true" /></div>
          <div className="message-stream" aria-live="polite" aria-relevant="additions text">
            {live.messages.length === 0 ? (
              <div className="empty-log"><span>Nenhuma mensagem nesta sessão.</span><p>Fale ou escreva uma instrução. A conversa mantém o contexto entre as duas formas de entrada.</p></div>
            ) : live.messages.map((message) => (
              <article key={message.id} className={`message message-${message.role}`}>
                <div><span>{message.role === "assistant" ? "JARVIS" : message.role === "user" ? "VOCÊ" : "SISTEMA"}</span><time dateTime={message.at}>{new Date(message.at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</time></div>
                <p>{message.content}</p>
              </article>
            ))}
            <div ref={logEnd} />
          </div>
        </section>

        <section className="command-stage" aria-labelledby="command-title">
          <div className={`state-caption state-${live.state}`} aria-live="polite"><span className="state-dot" aria-hidden="true" /> NÚCLEO / {stateLabel}</div>
          <Reactor state={live.state} />
          <div className="voice-caption">
            <h1 id="command-title">{stateLabel}</h1>
            <p>{live.transcript || (live.micActive ? "Microfone ativo. Pode falar." : "Canal de texto pronto. Ative o microfone para usar voz.")}</p>
          </div>
          <form className="command-composer" onSubmit={submit} aria-label="Enviar uma instrução">
            <textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder="Escreva uma instrução" aria-label="Mensagem para o JARVIS" rows={2} />
            <Button type="button" variant={live.micActive ? "danger" : "secondary"} size="icon" disabled={!connected} aria-label={live.micActive ? "Silenciar microfone" : "Ativar microfone"} onClick={() => live.micActive ? live.stopMic() : live.startMic()}>
              {live.micActive ? <MicOff size={18} aria-hidden="true" /> : <Mic size={18} aria-hidden="true" />}
            </Button>
            <Button type="submit" size="icon" aria-label="Enviar instrução" disabled={!draft.trim() || !connected}><ArrowUp size={18} aria-hidden="true" /></Button>
          </form>
          {(live.error || live.state === "error") && <p className="console-error" role="alert">{errorMessage}</p>}
        </section>

        <aside className="systems-panel" aria-labelledby="systems-title">
          <div className="panel-heading"><div><p className="section-index">SISTEMA / AO VIVO</p><h2 id="systems-title">Estado operacional</h2></div><Activity size={18} aria-hidden="true" /></div>
          <dl className="status-readout">
            <div><dt>Gemini Live</dt><dd data-on={connected}>{CONNECTION_LABELS[live.connection]}</dd></div>
            <div><dt>Latência</dt><dd aria-label="Não informada pelo cliente">—</dd></div>
            <div><dt>Entrada de voz</dt><dd data-on={live.micActive}>{live.micActive ? "Ativa" : "Silenciada"}</dd></div>
            <div><dt>Separação de conta</dt><dd data-on="true"><ShieldCheck size={14} aria-hidden="true" /> Ativa</dd></div>
          </dl>
          {live.progress && (
            <section className="real-progress" aria-label={`${live.progress.kind} em andamento`}>
              <div><span>{live.progress.label}</span><b>{live.progress.percent === null ? "—" : `${Math.round(live.progress.percent)}%`}</b></div>
              <div className="progress-track" aria-hidden="true"><span style={{ transform: `scaleX(${(live.progress.percent ?? 0) / 100})` }} /></div>
              {live.progress.phase && <p>{live.progress.phase}</p>}
            </section>
          )}
          <section className="capability-index" aria-labelledby="actions-title">
            <div className="capability-heading"><span id="actions-title">Ações disponíveis</span><b>{String(actions.length).padStart(2, "0")}</b></div>
            {actions.length === 0 ? <p className="empty-actions">A lista de ações não está disponível.</p> : (
              <ul>{actions.map((action) => <li key={action.name}><span>{action.name.replaceAll("_", " ")}</span><i aria-hidden="true" /></li>)}</ul>
            )}
          </section>
          <section className="session-logs" id="session-logs" aria-labelledby="session-logs-title">
            <div className="capability-heading"><span id="session-logs-title">Registros da sessão</span><b>{String(live.logs.length).padStart(2, "0")}</b></div>
            {live.logs.length === 0 ? <p className="empty-actions">O cliente não enviou registros nesta sessão.</p> : (
              <ul>{live.logs.slice(-8).map((entry) => <li key={entry.id} className={`log-${entry.level}`}><span>{entry.message}</span><small>{entry.source}</small></li>)}</ul>
            )}
          </section>
        </aside>
      </div>
    </main>
  );
}
