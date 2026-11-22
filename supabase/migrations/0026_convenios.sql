-- Etapa 22 (D92–D95, RN-CV): convênios.
-- Lista de convênios que a clínica atende (Configurações › Convênios).
create table if not exists clinic_insurances (
  id          uuid primary key default gen_random_uuid(),
  clinic_id   uuid not null references clinics(id) on delete cascade,
  name        text not null check (length(trim(name)) between 1 and 80),
  active      boolean not null default true,
  created_at  timestamptz not null default now(),
  unique (clinic_id, id)
);
create unique index if not exists clinic_insurances_nome on clinic_insurances (clinic_id, lower(trim(name)));
alter table clinic_insurances enable row level security;

-- No paciente (D94): particular, convênio da lista, ou só "convênio" quando a clínica não tem lista.
-- null = ainda não perguntado.
alter table patients
  add column if not exists convenio      text check (convenio is null or convenio in ('particular', 'convenio')),
  add column if not exists insurance_id  uuid references clinic_insurances(id) on delete set null;
alter table patients drop constraint if exists patients_convenio_coerente;
alter table patients add constraint patients_convenio_coerente
  check (insurance_id is null or convenio = 'convenio');
