# Ísis — Atendente virtual para clínicas odontológicas

Ísis conversa com pacientes por chat, consulta a agenda, **marca, remarca e cancela**
consultas e **dispara confirmações e lembretes**. A plataforma é **multi-tenant**: uma
mesma instalação atende várias clínicas, cada uma com layout, regras e canais próprios.

> Status: **Etapa 4 em teste** — Ísis conversando com IA (Agno + gpt-6-luna) no chat de teste, com ações em dois passos e atendimento humano. Próximo: **Etapa 5** — WhatsApp (WAHA).
>
> Teste das conexões: `cd backend; uv run python scripts/teste_conexoes.py`

## Como rodar (Windows)

Pré-requisitos: `uv` (Python), Node 20+. Na pasta do projeto:

```powershell
.\dev.ps1
```

- Painel: http://localhost:5173
- Backend: http://localhost:8000/health · documentação da API: http://localhost:8000/docs
- Testes do backend: `cd backend; uv run pytest`
- Conversas de teste com a IA: `cd backend; uv run python scripts/conversa_teste.py` (gasta um pouco do plano)
- Banco: `cd backend; uv run python scripts/migrar.py` (cria/atualiza tabelas) e `uv run python scripts/seed_demo.py --reset` (recria a clínica demo)

## O que vamos ver na tela (resultado final)

| Tela | O que mostra |
|---|---|
| **Chat** | Página em `localhost` onde o "paciente" conversa com a Ísis |
| **Agenda da semana** | Grade semanal que muda **em tempo real** quando a Ísis marca/remarca/cancela |
| **CRM (kanban)** | 5 colunas: Novo Contato · Orçamento em Negociação · Agendados · Confirmado · Cancelados |
| **Mensagens enviadas** | Confirmações, lembretes e disparos, com status |
| **Disparos** | Felicitação de aniversário automática e mensagens programadas |
| **Configurações / Admin** | Perfil, horários, procedimentos, mensagens, usuários; criação de clínicas (instâncias) |

Layout de referência aprovado: [docs/layouts/](docs/layouts/) (temas claro e escuro).

## Stack proposta (detalhes em [docs/ARQUITETURA.md](docs/ARQUITETURA.md))

- **Frontend:** React + Vite + TypeScript
- **Backend:** FastAPI (Python 3.12)
- **Banco:** PostgreSQL no Supabase
- **Agente:** Agno + modelo **GPT 6 Luna** via **OpenCode Go**
- **Canais:** Web (informa telefone) · WhatsApp não oficial (WAHA) · WhatsApp oficial (Cloud API)
- **Sem n8n.** Toda a lógica fica no nosso código.

## Mapa da documentação

| Documento | Para que serve |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Como trabalhamos (etapas, pausas, idioma) — lido pelo agente de código |
| [docs/PLANO.md](docs/PLANO.md) | Etapas de construção e o que testar em cada uma |
| [docs/ARQUITETURA.md](docs/ARQUITETURA.md) | Peças do sistema e como conversam |
| [docs/REGRAS-DE-NEGOCIO.md](docs/REGRAS-DE-NEGOCIO.md) | **Catálogo único de regras** (RN-xxx) — onde mais vamos refinar |
| [docs/PERGUNTAS.md](docs/PERGUNTAS.md) | ✔️ **Checklist das perguntas que você precisa responder** |
| [docs/DECISOES.md](docs/DECISOES.md) | Decisões tomadas |
| [docs/GLOSSARIO.md](docs/GLOSSARIO.md) | Termos usados no projeto |
| [docs/CENARIOS-DE-TESTE.md](docs/CENARIOS-DE-TESTE.md) | Conversas de teste que a Ísis precisa acertar |
| [docs/specs/](docs/specs/) | Especificação de cada parte (multi-tenant, agente, agenda, canais...) |
| [docs/layouts/](docs/layouts/) | Telas de referência de layout (aprovadas) |
| [docs/specs/10-disparos.md](docs/specs/10-disparos.md) | Aniversário e mensagens programadas |
| [docs/specs/11-design-visual.md](docs/specs/11-design-visual.md) | Cores, fontes, componentes, temas |
| [comandos.md](comandos.md) | Anotações do vídeo de referência (agente "Ísis") |
