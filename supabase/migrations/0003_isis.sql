-- =====================================================================
-- 0003 — Ísis (Etapa 4): ações em dois passos e registro das execuções
-- Spec: docs/specs/02-agente-isis.md · Regras: RN-AG-11, RN-AT-06
-- =====================================================================

-- RN-AG-11: a Ísis "prepara" a ação (valida tudo, não grava) e recebe um token.
-- Só depois que o PACIENTE responde é que o token pode ser confirmado (checado no código).
create table action_tokens (
  id          uuid primary key default gen_random_uuid(),
  clinic_id   uuid not null references clinics(id) on delete cascade,
  patient_id  uuid not null,
  action      text not null check (action in ('marcar', 'remarcar', 'cancelar')),
  payload     jsonb not null,
  resumo      text not null,
  expires_at  timestamptz not null default now() + interval '15 minutes',
  used_at     timestamptz,
  created_at  timestamptz not null default now(),
  foreign key (clinic_id, patient_id) references patients(clinic_id, id) on delete cascade
);

create index action_tokens_paciente on action_tokens (clinic_id, patient_id, created_at desc);

-- Cada resposta da Ísis fica registrada para depuração (entrada, ferramentas, saída, tempo, erro)
create table agent_runs (
  id               uuid primary key default gen_random_uuid(),
  clinic_id        uuid not null references clinics(id) on delete cascade,
  conversation_id  uuid not null,
  input            text not null,
  tools            jsonb not null default '[]'::jsonb,
  output           text,
  latency_ms       integer,
  error            text,
  created_at       timestamptz not null default now(),
  foreign key (clinic_id, conversation_id) references conversations(clinic_id, id) on delete cascade
);

create index agent_runs_conversa on agent_runs (conversation_id, created_at desc);

alter table action_tokens enable row level security;
alter table agent_runs    enable row level security;
