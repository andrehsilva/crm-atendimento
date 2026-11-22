-- Etapa 21 (D87–D90, RN-TR): tratamentos em andamento (pacientes recorrentes).
create table if not exists treatments (
  id                 uuid primary key default gen_random_uuid(),
  clinic_id          uuid not null references clinics(id) on delete cascade,
  patient_id         uuid not null,
  service_id         uuid not null references services(id),
  professional_id    uuid references professionals(id) on delete set null,
  sessoes_previstas  integer check (sessoes_previstas is null or sessoes_previstas between 1 and 100),
  intervalo_dias     integer check (intervalo_dias is null or intervalo_dias between 1 and 365),
  orientacao         text check (orientacao is null or length(orientacao) <= 300),  -- lida pela assistente
  status             text not null default 'em_andamento'
                     check (status in ('em_andamento', 'aguardando', 'concluido', 'interrompido')),
  motivo_espera      text check (motivo_espera is null or motivo_espera in ('protetico', 'exame', 'cicatrizacao', 'outro')),
  motivo_texto       text check (motivo_texto is null or length(motivo_texto) <= 120),
  previsao           date,               -- quando a espera deve acabar (só aviso à equipe)
  volta_em           date,               -- concluído: quando chamar de volta (recall)
  perguntou_em       timestamptz,        -- paciente pediu para marcar enquanto aguardava (sino)
  status_desde       timestamptz not null default now(),
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  foreign key (clinic_id, patient_id) references patients(clinic_id, id) on delete cascade,
  check (status = 'aguardando' or (motivo_espera is null and previsao is null))
);

-- RN-TR-01: só um tratamento ABERTO por procedimento para o mesmo paciente
create unique index if not exists treatments_um_aberto
  on treatments (clinic_id, patient_id, service_id) where status in ('em_andamento', 'aguardando');
create index if not exists treatments_paciente on treatments (clinic_id, patient_id);

alter table treatments enable row level security;

-- sessão marcada fica ligada ao tratamento
alter table appointments add column if not exists treatment_id uuid references treatments(id) on delete set null;
create index if not exists appointments_tratamento on appointments (treatment_id) where treatment_id is not null;

-- mensagem de "pode marcar a próxima sessão" (Retomar, D88)
alter table outbound_messages drop constraint if exists outbound_messages_kind_check;
alter table outbound_messages add constraint outbound_messages_kind_check
  check (kind in ('confirmacao', 'remarcacao', 'cancelamento', 'lembrete', 'aniversario', 'campanha', 'tratamento'));
