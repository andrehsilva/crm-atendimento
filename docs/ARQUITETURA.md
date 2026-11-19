# Arquitetura

## Visão em uma figura

```
 Paciente                    Canais (adaptadores)            Backend FastAPI                     Banco (Supabase/Postgres)
 ────────                    ────────────────────            ───────────────                     ─────────────────────────
 Página web  ──HTTP──►  WebChannel   ─┐
 WhatsApp    ──webhook► WahaChannel  ─┼─► Roteador ─► Ísis (Agno) ─► Ferramentas ─► Serviço de Agenda ─► appointments, ...
 WhatsApp    ──webhook► CloudChannel ─┘   (clínica +        │                         (valida TUDO)
 oficial                                  paciente)          └─► memória da conversa ──────────────► conversations, messages
                                                                                                                  │
 Equipe da clínica ◄──SSE (tempo real)── Barramento de eventos ◄── eventos: consulta marcada, msg enviada ◄───────┘
 (painel React)                                                                                                    │
                                          Agendador (lembretes) ──► fila de saída (outbound_messages) ──► Canal ─► Paciente
```

## Peças

| Peça | Responsabilidade | Observação |
|---|---|---|
| **Adaptador de canal** | Traduz Web/WAHA/Cloud API para um formato único (`MensagemEntrada`) e envia respostas | Trocar de canal não mexe na Ísis |
| **Roteador** | Descobre a **clínica** (pelo telefone/número que recebeu) e o **paciente** (pelo telefone de quem enviou) | Chave da conversa = `clinica_tel + paciente_tel` |
| **Ísis (Agno)** | Entende o pedido, conversa, chama ferramentas | Não grava nada sozinha; só via ferramentas |
| **Ferramentas** | Funções Python expostas ao agente | Recebem `clinic_id`/`patient_id` do contexto, nunca do modelo |
| **Serviço de Agenda** | Regras de horário, conflito, antecedência, status | Mesmo serviço usado pela API do painel |
| **Barramento de eventos** | Publica mudanças para as telas | SSE (Server-Sent Events) — simples e suficiente |
| **Agendador** | Gera e envia confirmações/lembretes | APScheduler dentro do backend; fila no banco (sobrevive a reinício) |
| **Painel React** | Chat, agenda, kanban, mensagens, admin | Uma app Vite com rotas |

## Escolhas e porquês

| Tema | Escolha | Por quê | Alternativa |
|---|---|---|---|
| Frontend | React + Vite + TS | Seu pedido; rápido; ecossistema grande | — |
| UI | Tailwind + shadcn/ui; calendário com FullCalendar ou grade própria | Layout configurável por clínica via variáveis CSS | — |
| Backend | FastAPI | Seu pedido; Python é a língua do Agno | — |
| Agente | Agno | Seu pedido; ferramentas, memória e sessão prontas | LangGraph, OpenAI Agents SDK |
| Modelo | **OpenCode Go + `gpt-6-luna`** (Responses API), configurável no `.env` | Escolha do usuário; trocar de modelo/provedor não mexe no código | OpenCode Zen, OpenAI direto |
| Banco | Postgres (Supabase) | Seu pedido; Auth e Storage (logos) de brinde | Postgres local em Docker no dev |
| Tempo real | SSE pelo FastAPI | Funciona igual local e em produção, sem depender de RLS | Supabase Realtime |
| Migrations | SQL versionado em `supabase/migrations` | Banco é a fonte da verdade | Alembic |
| Lembretes | Tabela `outbound_messages` + APScheduler | Se o servidor cair, nada se perde | Celery/Redis (exagero agora) |
| Conflito de horário | **Restrição no banco** (exclusion constraint) | Duas mensagens ao mesmo tempo nunca geram dupla marcação | — |

## Segurança e LGPD (resumo)
- Dados de saúde são **dados sensíveis** (LGPD art. 11). Guardar o mínimo: nome, telefone, consultas. Sem anamnese pelo chat.
- Todas as consultas SQL filtram por `clinic_id`. Testes automatizados de isolamento entre clínicas.
- Webhooks com segredo/assinatura. Admin com login (Supabase Auth).
- Mensagens ao modelo: evitar mandar dados de outros pacientes; só o necessário da conversa.
