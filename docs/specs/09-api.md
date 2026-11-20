# Spec 09 — API (rascunho)

Prefixo `/api`. Rotas do painel exigem login e checam papel + clínica.

## Paciente (web)
| Método | Rota | Uso |
|---|---|---|
| GET | `/web/{slug}` | Config pública (nome, logo, cores, boas-vindas) |
| POST | `/web/{slug}/session` | Inicia sessão com telefone (+ nome) → token de sessão |
| POST | `/web/{slug}/messages` | Envia mensagem |
| GET | `/web/{slug}/stream` | SSE com respostas da Ísis |

## Implementado na Etapa 2 (sem login — só localhost)
| Método | Rota | Uso |
|---|---|---|
| GET | `/api/clinics` | Lista clínicas (achar o id da demo) |
| GET | `/api/clinics/{id}/cadastros` | Dentistas e procedimentos |
| GET | `/api/clinics/{id}/availability?service_id&de&ate&professional_id&telefone` | Horários livres |
| GET | `/api/clinics/{id}/appointments?de&ate` | Consultas no período |
| GET | `/api/clinics/{id}/patients/{telefone}/appointments` | Próximas consultas do paciente |
| POST | `/api/clinics/{id}/appointments` | Marcar (recepção) |
| POST | `/api/clinics/{id}/appointments/{aid}/reschedule` | Remarcar (recepção) |
| POST | `/api/clinics/{id}/appointments/{aid}/cancel` | Cancelar (recepção) |
| POST | `/api/clinics/{id}/appointments/{aid}/status` | confirmada / realizada / faltou |
| POST | `/api/clinics/{id}/simular-paciente/{aid}/cancel` | Paciente cancela (telefone precisa bater) |

Erros de regra: HTTP 4xx com `{"codigo": "HORARIO_OCUPADO", "mensagem": "..."}` (códigos em `backend/app/agenda/erros.py`).

## Painel (planejado)
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
