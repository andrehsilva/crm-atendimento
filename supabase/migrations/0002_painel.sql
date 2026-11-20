-- =====================================================================
-- 0002 — Painel: CRM, conversas, mensagens e fila de saída (Etapa 3)
-- Specs: 05-confirmacoes-lembretes, 06-painel-operacional, 08-modelo-de-dados
-- =====================================================================

-- CRM no paciente (RN-PN-02, RN-PN-08, RN-PN-09)
alter table patients
  add column crm_stage        text not null default 'novo_contato'
                              check (crm_stage in ('novo_contato', 'agendado', 'confirmado', 'cancelado')),
  add column stage_changed_at timestamptz not null default now(),
  add column last_event       text not null default 'iniciou_conversa',
  add column last_activity_at timestamptz not null default now();

create index patients_crm on patients (clinic_id, crm_stage);

create table crm_events (
  id          uuid primary key default gen_random_uuid(),
  clinic_id   uuid not null references clinics(id) on delete cascade,
  patient_id  uuid not null,
  from_stage  text,
  to_stage    text not null,
  event       text not null,
  actor_type  text not null check (actor_type in ('isis', 'recepcao', 'paciente', 'sistema')),
  created_at  timestamptz not null default now(),
  foreign key (clinic_id, patient_id) references patients(clinic_id, id) on delete cascade
);

-- Conversas: 1 por paciente e canal. status 'humano' = Ísis pausada (RN-AT-06)
create table conversations (
  id               uuid primary key default gen_random_uuid(),
  clinic_id        uuid not null references clinics(id) on delete cascade,
  patient_id       uuid not null,
  channel          text not null check (channel in ('web', 'whatsapp')),
  status           text not null default 'ativa' check (status in ('ativa', 'humano', 'encerrada')),
  last_message_at  timestamptz not null default now(),
  created_at       timestamptz not null default now(),
  unique (clinic_id, patient_id, channel),
  unique (clinic_id, id),
  foreign key (clinic_id, patient_id) references patients(clinic_id, id) on delete cascade
);

create table messages (
  id               uuid primary key default gen_random_uuid(),
  clinic_id        uuid not null,
  conversation_id  uuid not null,
  direction        text not null check (direction in ('in', 'out')),
  author           text not null check (author in ('paciente', 'isis', 'recepcao', 'sistema')),
  content          text not null,
  external_id      text,
  created_at       timestamptz not null default now(),
  foreign key (clinic_id, conversation_id) references conversations(clinic_id, id) on delete cascade
);

create index messages_conversa on messages (conversation_id, created_at);

-- Fila de saída: toda mensagem automática vira linha ANTES de ser enviada (spec 05).
-- O envio de verdade pelo WhatsApp entra nas Etapas 5/6; até lá ficam com status 'agendada'.
create table outbound_messages (
  id              uuid primary key default gen_random_uuid(),
  clinic_id       uuid not null references clinics(id) on delete cascade,
  patient_id      uuid not null,
  appointment_id  uuid references appointments(id) on delete set null,
  kind            text not null check (kind in ('confirmacao', 'remarcacao', 'cancelamento', 'lembrete', 'aniversario')),
  channel         text not null default 'whatsapp' check (channel in ('whatsapp', 'web')),
  body            text not null,
  scheduled_for   timestamptz not null default now(),
  status          text not null default 'agendada'
                  check (status in ('agendada', 'enviada', 'entregue', 'lida', 'falhou', 'cancelada')),
  attempts        integer not null default 0,
  sent_at         timestamptz,
  external_id     text,
  error           text,
  created_at      timestamptz not null default now(),
  foreign key (clinic_id, patient_id) references patients(clinic_id, id) on delete cascade
);

create index outbound_fila on outbound_messages (status, scheduled_for);
create index outbound_clinica on outbound_messages (clinic_id, created_at desc);

alter table crm_events        enable row level security;
alter table conversations     enable row level security;
alter table messages          enable row level security;
alter table outbound_messages enable row level security;
