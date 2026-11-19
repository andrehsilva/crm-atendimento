# Spec 09 — API (rascunho)

Prefixo `/api`. Rotas do painel exigem login e checam papel + clínica.

## Paciente (web)
| Método | Rota | Uso |
|---|---|---|
| GET | `/web/{slug}` | Config pública (nome, logo, cores, boas-vindas) |
| POST | `/web/{slug}/session` | Inicia sessão com telefone (+ nome) → token de sessão |
| POST | `/web/{slug}/messages` | Envia mensagem |
| GET | `/web/{slug}/stream` | SSE com respostas da Ísis |

## Painel
| Método | Rota | Uso |
|---|---|---|
| GET | `/clinics/{id}/appointments?from&to&professional` | Agenda |
| POST/PATCH | `/clinics/{id}/appointments[/{aid}]` | Marcar/remarcar/cancelar/status |
| GET | `/clinics/{id}/availability?service&from&to` | Horários livres |
| GET | `/clinics/{id}/kanban` | Cards por coluna |
| GET | `/clinics/{id}/conversations[/{cid}]` | Conversas e histórico |
| POST | `/clinics/{id}/conversations/{cid}/takeover` · `/release` | Handoff |
| GET | `/clinics/{id}/outbound?kind&status` | Mensagens enviadas |
| GET | `/clinics/{id}/events` | SSE |

## Admin
CRUD em `/admin/clinics`, `/clinics/{id}/professionals|services|working-hours|blocks|settings|channels|users`.

## Webhooks
`POST /webhooks/waha` · `GET/POST /webhooks/whatsapp`

## Dev
`POST /dev/clock` (relógio simulado) · `POST /dev/reset-demo` — só com `ENV=dev`.
