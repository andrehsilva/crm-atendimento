-- =====================================================================
-- 0001 — Base multi-tenant + agenda (Etapa 2)
-- Specs: docs/specs/03-agenda.md, docs/specs/08-modelo-de-dados.md
-- Regras: RN-MT-*, RN-AG-*
-- =====================================================================

create extension if not exists btree_gist;
create extension if not exists pgcrypto;

-- Atualiza updated_at automaticamente
create or replace function set_updated_at() returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

-- ---------------------------------------------------------------------
-- Clínicas (tenant). Telefone E.164 é a chave de negócio (RN-MT-01, D4)
-- ---------------------------------------------------------------------
create table clinics (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  phone       text not null unique check (phone ~ '^\+[1-9][0-9]{9,14}$'),
  slug        text not null unique check (slug ~ '^[a-z0-9-]+$'),
  timezone    text not null default 'America/Sao_Paulo',
  address     text,
  status      text not null default 'ativa' check (status in ('ativa', 'suspensa')),
  -- regras configuráveis (RN marcadas "Config"); valores ausentes usam o padrão do código
  settings    jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- Horário de funcionamento da clínica por dia da semana (0=segunda ... 6=domingo)
create table clinic_hours (
  clinic_id   uuid not null references clinics(id) on delete cascade,
  weekday     smallint not null check (weekday between 0 and 6),
  enabled     boolean not null default true,
  start_time  time not null,
  end_time    time not null,
  primary key (clinic_id, weekday),
  check (end_time > start_time)
);

-- Pausas (ex.: almoço) por dia da semana
create table clinic_breaks (
  id          uuid primary key default gen_random_uuid(),
  clinic_id   uuid not null references clinics(id) on delete cascade,
  weekday     smallint not null check (weekday between 0 and 6),
  start_time  time not null,
  end_time    time not null,
  check (end_time > start_time)
);

-- ---------------------------------------------------------------------
-- Profissionais e procedimentos
-- ---------------------------------------------------------------------
create table professionals (
  id          uuid primary key default gen_random_uuid(),
  clinic_id   uuid not null references clinics(id) on delete cascade,
  name        text not null,
  specialty   text,
  color       text,
  active      boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (clinic_id, id)
);

-- Exceções de horário por profissional. Sem linhas para o profissional = herda clinic_hours.
-- Com linhas: só atende nos dias/faixas listados (sempre dentro do horário da clínica).
create table professional_hours (
  id               uuid primary key default gen_random_uuid(),
  clinic_id        uuid not null,
  professional_id  uuid not null,
  weekday          smallint not null check (weekday between 0 and 6),
  start_time       time not null,
  end_time         time not null,
  check (end_time > start_time),
  foreign key (clinic_id, professional_id) references professionals(clinic_id, id) on delete cascade
);

create table services (
  id              uuid primary key default gen_random_uuid(),
  clinic_id       uuid not null references clinics(id) on delete cascade,
  name            text not null,
  description     text,
  duration_min    integer not null default 60 check (duration_min between 5 and 480),
  price_cents     integer check (price_cents >= 0),
  active          boolean not null default true,
  bookable_by_ai  boolean not null default true,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (clinic_id, id),
  unique (clinic_id, name)
);

create table professional_services (
  clinic_id        uuid not null,
  professional_id  uuid not null,
  service_id       uuid not null,
  primary key (professional_id, service_id),
  foreign key (clinic_id, professional_id) references professionals(clinic_id, id) on delete cascade,
  foreign key (clinic_id, service_id) references services(clinic_id, id) on delete cascade
);

-- Bloqueios: férias, feriados, reuniões. professional_id nulo = clínica toda.
create table schedule_blocks (
  id               uuid primary key default gen_random_uuid(),
  clinic_id        uuid not null references clinics(id) on delete cascade,
  professional_id  uuid,
  starts_at        timestamptz not null,
  ends_at          timestamptz not null,
  reason           text,
  check (ends_at > starts_at),
  foreign key (clinic_id, professional_id) references professionals(clinic_id, id) on delete cascade
);

-- ---------------------------------------------------------------------
-- Pacientes (RN-MT-02: únicos por clínica + telefone)
-- ---------------------------------------------------------------------
create table patients (
  id                         uuid primary key default gen_random_uuid(),
  clinic_id                  uuid not null references clinics(id) on delete cascade,
  phone                      text not null check (phone ~ '^\+[1-9][0-9]{9,14}$'),
  name                       text,
  birth_date                 date,
  notes                      text,
  origin                     text not null default 'manual' check (origin in ('web', 'whatsapp', 'manual')),
  preferred_professional_id  uuid,
  created_at                 timestamptz not null default now(),
  updated_at                 timestamptz not null default now(),
  unique (clinic_id, phone),
  unique (clinic_id, id),
  foreign key (clinic_id, preferred_professional_id) references professionals(clinic_id, id) on delete set null (preferred_professional_id)
);

-- ---------------------------------------------------------------------
-- Consultas (RN-AG-02: sem sobreposição por profissional, garantido pelo banco)
-- ---------------------------------------------------------------------
create table appointments (
  id                   uuid primary key default gen_random_uuid(),
  clinic_id            uuid not null references clinics(id) on delete cascade,
  patient_id           uuid not null,
  professional_id      uuid not null,
  service_id           uuid not null,
  starts_at            timestamptz not null,
  ends_at              timestamptz not null,
  status               text not null default 'agendada'
                       check (status in ('agendada', 'confirmada', 'cancelada', 'realizada', 'faltou')),
  source               text not null default 'recepcao' check (source in ('isis', 'recepcao', 'paciente_botao')),
  rescheduled_from_id  uuid references appointments(id),
  cancel_reason        text,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  check (ends_at > starts_at),
  foreign key (clinic_id, patient_id) references patients(clinic_id, id),
  foreign key (clinic_id, professional_id) references professionals(clinic_id, id),
  foreign key (clinic_id, service_id) references services(clinic_id, id),
  constraint appointments_sem_sobreposicao exclude using gist (
    professional_id with =,
    tstzrange(starts_at, ends_at, '[)') with &&
  ) where (status in ('agendada', 'confirmada'))
);

create index appointments_clinica_inicio on appointments (clinic_id, starts_at);
create index appointments_paciente on appointments (clinic_id, patient_id, starts_at);

-- Histórico de toda mudança em consulta (RN-PN-04)
create table appointment_events (
  id              uuid primary key default gen_random_uuid(),
  clinic_id       uuid not null references clinics(id) on delete cascade,
  appointment_id  uuid not null references appointments(id) on delete cascade,
  actor_type      text not null check (actor_type in ('isis', 'recepcao', 'paciente', 'sistema')),
  actor_id        text,
  action          text not null,
  before          jsonb,
  after           jsonb,
  created_at      timestamptz not null default now()
);

create index appointment_events_consulta on appointment_events (appointment_id, created_at);

-- updated_at automático
create trigger t_clinics_upd       before update on clinics       for each row execute function set_updated_at();
create trigger t_professionals_upd before update on professionals for each row execute function set_updated_at();
create trigger t_services_upd      before update on services      for each row execute function set_updated_at();
create trigger t_patients_upd      before update on patients      for each row execute function set_updated_at();
create trigger t_appointments_upd  before update on appointments  for each row execute function set_updated_at();

-- ---------------------------------------------------------------------
-- Segurança: RLS ligado e SEM políticas = a API pública do Supabase (chave
-- publishable/anon) não lê nem grava nada. Só o backend (conexão postgres)
-- acessa. Políticas por clínica entram na Etapa 7, junto com o login.
-- ---------------------------------------------------------------------
alter table clinics               enable row level security;
alter table clinic_hours          enable row level security;
alter table clinic_breaks         enable row level security;
alter table professionals         enable row level security;
alter table professional_hours    enable row level security;
alter table services              enable row level security;
alter table professional_services enable row level security;
alter table schedule_blocks       enable row level security;
alter table patients              enable row level security;
alter table appointments          enable row level security;
alter table appointment_events    enable row level security;
