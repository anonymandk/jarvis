# JARVIS — UI Display: especificação para Figma

> Estado: especificação pronta para handoff. O arquivo do Figma não foi criado porque a conta conectada informa assento **View**; faltam permissão de edição/criação e acesso de edição ao arquivo do projeto. Esta especificação e os SVGs conceituais não são exports do Figma.

## 1. Reconhecimento do repositório

Verificado em 2026-09-29 no repositório privado [anonymandk/jarvis](https://github.com/anonymandk/jarvis), branch padrão **main**.

- **main.py** contém a classe **JarvisLive**. Ela recebe **client: JarvisClient**; portanto, a premissa de que o núcleo é integrado diretamente à janela não descreve o contrato atual.
- **core/jarvis_client.py** define o protocolo transport-neutral **JarvisClient**, com métodos como **set_state**, **write_log**, **show_subtitle** e **clear_subtitle**.
- **ui.py** implementa a interface PyQt6: HUD animado, conversa, waveform visual, console, progresso de tool, settings, toasts e modo compacto flutuante de 80×80.
- **api/websocket_client.py** implementa outro adaptador de **JarvisClient**; **api/server.py** publica eventos via WebSocket no cliente web. Os eventos atuais usam tipos como **status**, **message**, **transcript**, **audio** e **progress**.
- O cliente web existe em **web/**; não há diretório **ui/** nem **docs/ui/** na branch padrão.
- O núcleo usa Gemini Live diretamente por **google.genai**, com seleção de modelo em **core/live_model.py**. Não há abstração de provedores LLM confirmada.
- O desktop escolhe voz, mas a seleção de dispositivos de áudio não aparece no contrato **JarvisClient**; os streams atuais usam os dispositivos padrão de **sounddevice**.
- O HUD mostra CPU, memória, rede e alguns dados de GPU/temperatura quando disponíveis. Não expõe latência do Gemini. O waveform desenhado é animado e não recebe nível real de áudio.
- O cliente web já salva mensagens finais em PostgreSQL. Este escopo mostra somente a sessão corrente no HUD e não adiciona persistência, histórico ou schema.

Fontes inspecionadas: README.md, main.py, ui.py, core/jarvis_client.py, api/websocket_client.py, api/server.py, árvore web/ e issues abertas (nenhuma encontrada).

## 2. Escopo e princípios

Projetar uma superfície de observabilidade e controle visual para estados, transcrição, tools, conexão, métricas e logs. O HUD consome eventos já produzidos pelo núcleo e envia somente comandos de interface autorizados. Não contém lógica de Gemini, tools ou regras de negócio.

Princípios: leitura rápida a 1440×900; núcleo visual central sem esconder os dados; PT-BR em toda a interface; tokens e nomes de componentes em inglês; dark mode padrão; todos os estados distinguíveis por texto/ícone além da cor; layout responsivo entre janela principal e overlay.

## 3. Estado/evento → componente de UI

| Estado/Evento | Evidência no código atual | Componente proposto | Lacuna/observação |
|---|---|---|---|
| Em espera / idle | “Standing by.” no diálogo; o núcleo não emite um estado IDLE estável | Core/Orb, Header/ConnectionStatus | Normalizar o estado inicial como idle; não inferir conexão online a partir do estado visual |
| Ouvindo | JarvisLive chama set_state("LISTENING"); UI usa HudCanvas e CompactModeWidget | Core/Orb, Audio/Visualizer, Header/StateBadge | Estado disponível; nível do microfone não é emitido |
| Processando | THINKING em conexão/tool call; UI também entende PROCESSING | Core/Orb, Tools/ExecutionPanel, StatusBar | Unificar THINKING/PROCESSING em processing, preservando subtipo |
| Falando | set_speaking() envia SPEAKING; transcrição incremental passa por show_subtitle() | Core/Orb, Audio/Visualizer, Transcript/Live | O waveform atual é animação visual, não amplitude real |
| Erro | Logs ERR: e toasts; não há estado de núcleo ERROR consistente | Toast/Error, Console/Logs, Header/StateBadge | Adicionar evento estruturado de erro no adapter futuro |
| Reconectando | O loop do engine reconecta; helper de backoff existe, mas não há evento visual RECONNECTING confirmado | Header/ConnectionStatus, Core/Orb | Normalizar conexão em evento explícito; não confundir com THINKING |
| Transcrição do usuário | Transcrição de entrada acumula e vira You: ... no fim do turno | Transcript/Live | Texto parcial do usuário não é enviado ao desktop em tempo real |
| Transcrição do JARVIS | output_transcription chama show_subtitle; mensagem final vai a write_log | Transcript/Live, Transcript/History | Mostrar incremental/final e speaker label |
| Tool call | _execute_tool entra em THINKING; UI possui ToolProgressWidget, com heurísticas baseadas em logs | Tools/ExecutionPanel, Tools/ResultCard | Não há evento tool_call estruturado no protocolo atual |
| Resultado de tool | Resultado é enviado ao Gemini; logs podem alimentar widgets quando escritos pela UI | Tools/ResultCard, Console/Logs | Adotar resumo seguro, sem argumentos secretos |
| Gemini Live / latência | /status reporta estado/conectado/voz; WebSocket tem ping/pong; sem RTT medido | Header/ConnectionStatus, Metric/Latency | Calcular RTT no cliente via ping/pong; latência ainda sem fonte |
| Áudio / waveform | HudCanvas desenha barras; captura e playback não publicam amplitude ao cliente | Audio/Visualizer | Animar por estado enquanto não houver métrica; rotular “atividade”, não dB |
| Logs | write_log() e console com prefixos SYS/ERR/You/Jarvis | Console/Logs | Futuro contrato inclui nível, origem e correlação |
| Métricas locais | CPU, RAM, rede, GPU e temperatura são amostradas pelo desktop | Metric/System | Valores indisponíveis devem exibir “—”; não usar zero |

### Vocabulário visual normalizado

- idle: Em espera
- listening: Ouvindo
- processing: Processando (subtipos: raciocinando, executando tool, carregando)
- speaking: Falando
- reconnecting: Reconectando
- error: Erro
- muted: Microfone silenciado

## 4. Contrato de eventos proposto (v1)

Um adapter de apresentação traduz chamadas existentes de JarvisClient para eventos versionados. A mesma estrutura serve para sinais Qt internos ou WebSocket local caso a UI seja separada do processo. Não alterar main.py nem o núcleo neste handoff.

Exemplo de envelope JSON (campos comuns):

    {
      "v": 1,
      "type": "state",
      "ts": "2026-09-29T15:04:05.123Z",
      "session_id": "sess-local-ephemeral",
      "seq": 42,
      "payload": {
        "state": "listening",
        "source": "jarvis_client",
        "connection": {
          "provider": "gemini_live",
          "status": "connected",
          "rtt_ms": null
        }
      }
    }

| Tipo | Payload mínimo | Uso |
|---|---|---|
| state | state, source, opcional reason e connection | Estado visual do núcleo e conexão |
| transcript | speaker, text, final, turn_id | Atualização incremental ou final |
| tool_call | id, name, status, started_at, opcional duration_ms e result_summary | Tool em execução, concluída, cancelada ou falhou |
| metric | name, value, unit | RTT, nível de áudio ou métrica local |
| log | level, source, message, opcional correlation_id | Console com filtro por severidade |
| error | code, message, recoverable, opcional retry_after_ms | Toast, banner ou recuperação |

Regras: ts sempre ISO-8601 UTC; seq crescente por sessão; session_id efêmero; texto de ferramenta deve ser resumo sanitizado; nunca emitir chaves, tokens, argumentos completos ou conteúdo de .env. Atualizações de métrica podem ser agregadas; callbacks de áudio nunca aguardam renderização de UI. O protocolo atual da WebSocketClient não corresponde a este envelope, então um mapper deve traduzir status/message/transcript/progress sem mudar o núcleo.

## 5. Foundations

### Cores (Dark, padrão)

| Token | Valor | Uso |
|---|---|---|
| color/background/950 | #050B12 | Fundo principal |
| color/surface/900 | #0A121C | Painéis |
| color/surface/800 | #101C29 | Cards elevados |
| color/surface/glass | #102332 a 72% | Vidro fosco |
| color/border/subtle | #263847 | Divisores |
| color/text/primary | #EAF5FC | Texto principal |
| color/text/secondary | #9AB0BF | Texto auxiliar |
| color/accent/cyan-500 | #00C8FF | Ação e foco |
| color/accent/blue-500 | #3B82F6 | Estado secundário |
| color/state/success | #00C98D | Conectado/sucesso |
| color/state/warning | #FFB020 | Atenção/reconexão |
| color/state/error | #FF4D6D | Erro |
| color/state/processing | #9B7BFF | Tool/raciocínio |
| color/control/disabled | #587182 | Desabilitado |

Acentos derivam do tema Arc Reactor já presente em ui.py. Validar combinações finais para WCAG AA: contraste 4.5:1 em texto normal e 3:1 em texto grande/contornos de controle. Não usar texto secundário em cinzas mais escuros sobre vidro.

### Tipografia

- font/display: Rajdhani Semibold, alternativa Orbitron para títulos curtos.
- font/body: Inter Regular/Medium/Semibold.
- font/mono: JetBrains Mono Regular/Medium para métricas, logs e timestamps.
- Escala: display 32/40; title 20/28; section 14/20; body 14/20; label 12/16; micro 11/16. Títulos em caixa alta somente para rótulos curtos.

### Espaçamento, raio e efeitos

- space/1..8: 4, 8, 12, 16, 24, 32, 48, 64 px.
- radius/sm..pill: 4, 8, 12, 16, 24, 999 px.
- Borda de painel: 1 px sólida com ciano a 18–28% de opacidade.
- shadow/panel: 0 8 24 rgba(0,0,0,0.35).
- glow/accent: 0 0 24 rgba(0,200,255,0.22); usar apenas em foco/estado ativo.
- Fundo de glass: superfície escura com opacidade entre 72–88%; texto permanece opaco.

### Motion

- motion/duration/fast: 120 ms; normal: 180 ms; emphasis: 320 ms; transition/state: 240 ms.
- motion/easing/standard: cubic-bezier(0.2, 0.8, 0.2, 1).
- Respiração do núcleo: ciclo 2.4 s em speaking/listening; nenhuma animação contínua no modo prefers-reduced-motion. Em reduced motion, trocar pulso por halo estático e waveform por barras discretas.

### Grid

- Desktop: frame 1440×900, top bar 64 px, rail 72 px, margem de conteúdo 24 px, grid 12 colunas, gutter 16 px, status bar 32 px.
- Overlay: frame 420×640, margem 16 px, grid 4 colunas, gutter 12 px, cabeçalho 48 px.
- Elevar contraste e reduzir ruído de scanline em todo estado; textura não pode competir com texto/logs.

## 6. Components e variants

Nomes de componentes em inglês. Controles interativos implementam default, hover, active, disabled, loading e error; componentes informativos expõem os mesmos estados quando semânticos e usam variants de estado próprios.

| Component set | Variants principais | Estados/uso |
|---|---|---|
| Core/Orb | State: Idle, Listening, Processing, Speaking, Reconnecting, Error; Motion: Full, Reduced | Núcleo central; texto de estado persistente ao redor do orb |
| Audio/Visualizer | Mode: Input, Output, Silent; State: Active, Muted, NoDevice, Loading, Error; Motion: Full, Reduced | Barras centradas no orb; nível real somente após evento metric |
| Transcript/Live | Speaker: User, Assistant, System; State: Empty, Streaming, Final, Paused, Error | Bolhas com timestamp; indicação “ao vivo” e foco de speaker |
| Tools/ExecutionPanel | State: Idle, Running, Success, Failed, Cancelled; Density: Full, Compact | Tool atual primeiro; elapsed time e resultado resumido |
| Connection/StatusCard | State: Offline, Connecting, Connected, Reconnecting, Error; Metric: Available, Pending | Nome Gemini Live, conectado/desconectado e RTT ou “—” |
| Console/LogPanel | Level: All, Info, Warning, Error; State: Empty, Populated, Loading, StreamError | Fonte e timestamp mono; filtro/pausa somente no painel |
| Settings/Panel | Section: Model, Voice, Audio; State: Default, Editing, Loading, Error | Gemini Live como provider atual; voz selecionável; dispositivos exibidos como padrão até suporte explícito |
| Status/ShortcutBar | Density: Desktop, Compact; State: Ready, Loading, Error | Estado da sessão, mute e atalhos confirmados na implementação |
| Toast/Notification | Type: Info, Success, Warning, Error; Action: None, Retry, Dismiss | Erro recuperável inclui ação e não depende de cor |
| Button/Primary | Size: Sm, Md, Lg; State: Default, Hover, Active, Disabled, Loading, Error | Foco por teclado com outline visível de 2 px e offset 2 px |

Cada component set deve usar Auto Layout nos agrupamentos, propriedades boolean/string para conteúdo variável e descrição de uso no componente principal. Usar exemplos PT-BR: “Ouvindo”, “Processando”, “Falando”, “Reconectar”, “Microfone silenciado”, “Nenhuma tool em execução”.

## 7. Screens

### Desktop — 1440×900

- Top bar 64 px: marca JARVIS à esquerda, provider Gemini Live + badge textual de conexão ao centro, relógio/sessão/atalhos à direita.
- Rail 72 px: ícones para Conversa, Tools, Logs e Configurações; tooltip e foco visível.
- Área principal entre x=96 e x=1416, y=88 e y=852: grid 3/6/3 com gutters 16 px. Coluna esquerda (~317 px) = transcrição + entrada; centro (~650 px) = Orb, estado legível, visualizador e controles; direita (~317 px) = tools atuais, conexão/RTT e logs recentes.
- Barra inferior 32 px: mute, provider, estado reduzido de movimento e atalhos.
- Sem dados: estado “Em espera”, placeholder de conversa e orb estático. Carregando: conectar/recuperar com texto e progresso. Erro: banner/toast com descrição, retry quando recuperável e link para log.

### Compact overlay — 420×640

- Header 48 px com botão expandir/fechar, estado de conexão e mute.
- Orb de 144–168 px, speaker/status legível e visualizador de altura máx. 32 px.
- Transcrição curta em card rolável, panel de tool atual de 56 px, input de 44 px no rodapé.
- Mostrar no máximo 3 logs recentes; configurações e lista completa de tools permanecem na janela expandida.
- Empty/loading/error devem ter as mesmas mensagens e ações do desktop em versão compacta.

Os SVGs em assets/ são previews vetoriais conceituais produzidos a partir desta especificação, não screenshots do Figma.

## 8. Prototype e diagramas

Caminho principal: idle → listening → processing → speaking → listening. Ramo de falha: qualquer estado ativo → error ou reconnecting → listening/idle. Processing pode conter tool running → success/failed. Testar variants com texto acessível e reduced motion.

- Diagrama Mermaid de estados: [assets/state-flow.mmd](assets/state-flow.mmd) e [preview SVG](assets/state-flow.svg).
- Diagrama Mermaid da arquitetura: [assets/architecture.mmd](assets/architecture.mmd) e [preview SVG](assets/architecture.svg).

## 9. Integração técnica

1. Preservar JarvisLive e o protocolo JarvisClient; criar futuramente um mapper/event adapter, sem importar Gemini ou módulos de tools na UI.
2. No desktop, entregar eventos ao thread Qt por signals/queue (o app já usa sinais Qt para estado/log/subtitle).
3. No web client, mapear os eventos existentes da WebSocketClient para o envelope v1; cliente web envia texto/áudio/mute e ping, sem executar regra de negócio.
4. Conexão deve mostrar estado real de ready/status; RTT pode usar ping/pong medido no cliente; sem RTT, exibir “—”.
5. Tools devem emitir start/end/error explícitos antes de ligar o painel novo. Não inferir estado crítico só por substring de log.
6. Não incluir lista de sessões, transcrições arquivadas ou novo banco. O cliente web atual persiste mensagens finais em PostgreSQL; esta entrega não altera essa política. Não há uso de Supabase confirmado, e nenhuma tabela/policy/migration é necessária para este design.

## 10. Acessibilidade

- Contraste AA; badge usa texto + ícone + cor; estado da conexão nunca é apenas um ponto colorido.
- Foco de teclado com 2 px; sequência lógica: rail, conversa, orb/controles, tools, logs, configurações.
- Controle de mute anuncia estado acessível e suporte a teclado; orb oferece rótulo textual.
- Redução de movimento desliga rotação, scanline e pulso infinito; transições ficam instantâneas ou em 120 ms.
- Áudio não é a única forma de consumir resposta: transcrição legível permanece disponível.
- Alvos clicáveis de pelo menos 40×40 px no overlay; texto de logs no mínimo 12 px.

## 11. Decisões e handoff

| Data | Decisão | Motivo |
|---|---|---|
| 2026-09-29 | Spec fallback em vez de criar arquivo Figma | Conta Figma conectada informa assento View; não há permissão de edição/criação |
| 2026-09-29 | Separar atividade visual de waveform medido | UI atual anima barras sem receber amplitude de áudio |
| 2026-09-29 | Não criar schema ou persistência | Tela fica na sessão atual; o repo usa PostgreSQL/Redis no serviço hospedado, sem Supabase confirmado |

Checklist:
- [x] Reconhecimento de código e tabela Estado/Evento → Componente
- [x] Contrato de evento proposto
- [x] Foundations, componentes, variants, telas, fluxo e acessibilidade especificados
- [x] SVGs conceituais e fontes Mermaid incluídos
- [ ] Criar/atualizar o arquivo Figma após conceder acesso de edição e localizar o arquivo existente
- [ ] Associar links dos frames na database Componentes após handoff no Figma
- [ ] Validar contraste final e atalhos no Figma/app durante implementação
- [ ] Integrar eventos explícitos de tool, erro, RTT e nível de áudio em tarefa posterior

## Pendências

1. Conceder ao conector Figma um assento Editor ou permissão **Can edit** no team/project e compartilhar o arquivo existente, se já existir.
2. Confirmar se a experiência final é a janela desktop PyQt6, o cliente web, ou ambas; esta spec organiza dados para ambas.
3. Confirmar disponibilidade/seleção de dispositivos de áudio e o modelo real de telemetria antes de ligar os controles.

