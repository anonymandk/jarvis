# JARVIS — UI Display

## Links

- Repositório: [anonymandk/jarvis](https://github.com/anonymandk/jarvis)
- Notion: [JARVIS — UI Display](https://app.notion.com/p/3ea9a662a0c5817fa9deed59994abbde?pvs=204)
- Figma: sem link de arquivo. A conta conectada está no assento **View**; nenhum arquivo foi criado nem alterado.
- PR: [docs: add JARVIS UI display specification](https://github.com/anonymandk/jarvis/pull/1).

## Entrega

- [Especificação completa para Figma](figma-spec.md)
- [Assets e previews conceituais](assets/README.md)
- [Preview desktop 1440×900](assets/desktop-preview.svg)
- [Preview overlay 420×640](assets/compact-preview.svg)
- [Fluxo de estados Mermaid](assets/state-flow.mmd)
- [Arquitetura UI ↔ núcleo Mermaid](assets/architecture.mmd)

Os SVGs são ilustrações vetoriais da especificação, não exports ou screenshots do Figma.

## Resumo das telas

- **Desktop, 1440×900**: trilho de navegação, conversa e entrada, orb central com estado e visualizador, painel de tools, conexão/RTT, logs e barra de atalhos.
- **Overlay, 420×640**: status/conexão, orb, transcrição curta, tool atual e entrada de texto/voz.
- **Estados cobertos**: vazio/em espera, ouvindo, processando, falando, carregando/reconectando e erro.

## Contrato de eventos

Envelope v1 comum:

    {"v":1,"type":"state|transcript|tool_call|metric|log|error","ts":"ISO-8601 UTC","session_id":"...","seq":1,"payload":{}}

JarvisLive já depende do protocolo JarvisClient; a UI deve continuar sendo um adapter de apresentação. O contrato detalhado e o mapeamento dos eventos atuais estão em [figma-spec.md](figma-spec.md). Esta entrega não altera main.py ou o núcleo, não adiciona persistência e não cria schema Supabase.

