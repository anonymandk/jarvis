"use client";

import { FormEvent, useState } from "react";
import { Check, ExternalLink, KeyRound, LockKeyhole } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, type User } from "@/lib/api";

export function Onboarding({ user, onComplete, onSignOut }: { user: User; onComplete: () => void; onSignOut: () => void }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      await api("/me/gemini-key", {
        method: "POST",
        body: JSON.stringify({ api_key: data.get("api_key"), validate: true }),
      });
      onComplete();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The key could not be verified");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="onboarding-shell">
      <header className="onboarding-header">
        <div className="wordmark"><span className="wordmark-mark">J</span> JARVIS</div>
        <button className="text-button" onClick={onSignOut}>Usar outra conta</button>
      </header>
      <section className="onboarding-sequence" lang="pt-BR">
        <div className="sequence-rail" aria-label="Progresso da configuração">
          <div className="sequence-step complete"><span><Check size={14} /></span><div><b>Identidade</b><small>{user.email}</small></div></div>
          <div className="sequence-line" />
          <div className="sequence-step active"><span>02</span><div><b>Gemini Live</b><small>Acesso privado ao modelo</small></div></div>
        </div>
        <div className="key-stage">
          <p className="section-index">CONFIGURAÇÃO / 02</p>
          <KeyRound className="stage-icon" size={28} />
          <h1>Conecte sua camada de inteligência.</h1>
          <p>
            O JARVIS usa sua chave de API do Gemini para voz e raciocínio ao vivo. A chave é criptografada ao ser armazenada e nunca retorna ao navegador.
          </p>
          <form onSubmit={submit} className="key-form">
            <label>Chave de API do Gemini<Input name="api_key" type="password" autoComplete="off" required minLength={20} placeholder="Cole a chave do Google AI Studio" /></label>
            {error && <p className="form-error" role="alert">{error}</p>}
            <Button disabled={pending} type="submit" className="w-full">
              <LockKeyhole size={16} /> {pending ? "Validando com o Gemini" : "Criptografar e iniciar"}
            </Button>
          </form>
          <a className="external-link" href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer">
            Abrir o Google AI Studio <ExternalLink size={14} />
          </a>
        </div>
      </section>
    </main>
  );
}
