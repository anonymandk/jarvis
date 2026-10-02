"use client";

import { FormEvent, useState } from "react";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, type Session } from "@/lib/api";

export function AuthScreen({ onSession }: { onSession: (session: Session) => void }) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      const session = await api<Session>(`/auth/${mode}`, {
        method: "POST",
        body: JSON.stringify({
          email: data.get("email"),
          password: data.get("password"),
          ...(mode === "signup" ? { display_name: data.get("display_name") } : {}),
        }),
      });
      onSession(session);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Authentication failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="entry-shell">
      <section className="entry-identity" aria-labelledby="entry-title">
        <div className="wordmark"><span className="wordmark-mark">J</span> JARVIS</div>
        <div className="entry-reactor" aria-hidden="true"><span /></div>
        <p className="eyebrow">Sistema pessoal de inteligência</p>
        <h1 id="entry-title">Comande sem atrito.</h1>
        <p className="entry-copy">
          Voz, texto, pesquisa e criação compartilham o mesmo contexto de trabalho.
        </p>
        <div className="trust-line"><ShieldCheck size={16} /> Sua chave do Gemini é criptografada antes do armazenamento.</div>
      </section>

      <section className="auth-panel" aria-labelledby="auth-title" lang="pt-BR">
        <div className="mode-switch" role="tablist" aria-label="Acesso à conta">
          <button role="tab" aria-selected={mode === "login"} onClick={() => setMode("login")}>Entrar</button>
          <button role="tab" aria-selected={mode === "signup"} onClick={() => setMode("signup")}>Criar conta</button>
        </div>
        <div>
          <p className="section-index">ACESSO / 01</p>
          <h2 id="auth-title">{mode === "login" ? "Retomar sessão" : "Criar identidade"}</h2>
        </div>
        <form onSubmit={submit} className="auth-form">
          {mode === "signup" && (
            <label>Como devo chamar você?<Input name="display_name" autoComplete="name" required placeholder="Nome de exibição" /></label>
          )}
          <label>E-mail<Input name="email" type="email" autoComplete="email" required placeholder="voce@exemplo.com" /></label>
          <label>Senha<Input name="password" type="password" minLength={10} autoComplete={mode === "login" ? "current-password" : "new-password"} required placeholder="Pelo menos 10 caracteres" /></label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <Button type="submit" disabled={pending} className="w-full">
            {pending ? "Autorizando" : mode === "login" ? "Entrar no JARVIS" : "Criar conta segura"}
            {!pending && <ArrowRight size={16} />}
          </Button>
        </form>
      </section>
    </main>
  );
}
