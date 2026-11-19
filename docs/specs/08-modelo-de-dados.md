# Spec 08 — Modelo de dados (Postgres)

Todas as tabelas de negócio têm `id uuid`, `clinic_id uuid`, `created_at`, `updated_at`.

```
clinics            id, name, phone (E.164, UNIQUE), slug (UNIQUE), timezone, address, status, settings jsonb
clinic_users       clinic_id, user_id (Supabase Auth), role (clinic_admin|reception)
platform_admins    user_id
professionals      clinic_id, name, specialty, color, active
services           clinic_id, name, duration_min (default 60), price_cents?, description, active, bookable_by_ai bool
professional_services  professional_id, service_id
professional_hours professional_id, weekday (0-6), start_time, end_time   -- só exceções; sem linhas = herda clinic_hours
schedule_blocks    clinic_id, professional_id?, starts_at, ends_at, reason
clinic_hours       clinic_id, weekday (0-6), enabled, start_time, end_time   -- tela "Horários de Funcionamento"
clinic_breaks      clinic_id, weekday (0-6), start_time, end_time              -- pausas (ex.: almoço)
patients           clinic_id, phone (E.164), name, birth_date?, notes, origin (web|whatsapp|manual), preferred_professional_id?,
                   marketing_opt_out bool, crm_stage (novo_contato|agendado|confirmado|cancelado),
                   stage_changed_at, last_event, last_activity_at, UNIQUE(clinic_id, phone)
crm_events         clinic_id, patient_id, from_stage, to_stage, event, actor_type, actor_id
message_templates  clinic_id, kind (aniversario|confirmacao|lembrete|cancelamento|remarcacao), enabled, body, send_time
birthday_sends     clinic_id, patient_id, year, UNIQUE(patient_id, year)          -- garante 1× por ano
appointments       clinic_id, patient_id, professional_id, service_id, starts_at, ends_at,
                   status (agendada|confirmada|cancelada|realizada|faltou),
                   rescheduled_from_id?, source (isis|recepcao|paciente_botao), cancel_reason
                   EXCLUDE gist (professional_id =, tstzrange(starts_at, ends_at) &&) WHERE status IN (agendada, confirmada)
appointment_events appointment_id, actor_type, actor_id, action, before jsonb, after jsonb
conversations      clinic_id, patient_id, channel, status (ativa|humano|encerrada), kanban_stage, last_message_at
messages           conversation_id, direction (in|out), author (paciente|isis|recepcao|sistema), content, external_id, meta jsonb
outbound_messages  clinic_id, appointment_id?, patient_id, kind (confirmacao|lembrete|cancelamento|remarcacao|aniversario|programada), channel, scheduled_for, status, attempts, payload jsonb, external_id, error
channel_connections clinic_id, type (web|waha|cloud_api), status, config jsonb (segredos criptografados), external_ref (sessão WAHA / phone_number_id) UNIQUE
action_tokens      clinic_id, patient_id, action, payload jsonb, expires_at, used_at   -- dois passos do agente
agent_runs         conversation_id, input, tools jsonb, output, latency_ms, error      -- depuração
```

Índices principais: `appointments(clinic_id, starts_at)`, `outbound_messages(status, scheduled_for)`, `messages(conversation_id, created_at)`, `patients(clinic_id, phone)`.

Futuro (fora da 1ª versão): `campaigns`/`campaign_recipients` (mensagens programadas, D24), tags de cliente (D20), convênio (Q10).

Extensão necessária: `btree_gist` (para a restrição de sobreposição).
