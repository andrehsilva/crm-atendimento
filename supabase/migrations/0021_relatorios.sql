-- Etapa 15A (D73): cada download de relatório fica registrado (LGPD).
create table if not exists report_exports (
  id          uuid primary key default gen_random_uuid(),
  clinic_id   uuid not null references clinics(id) on delete cascade,
  user_id     uuid references app_users(user_id) on delete set null,
  tipo        text not null,
  filtros     jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);
create index if not exists report_exports_clinic_idx on report_exports (clinic_id, created_at desc);
alter table report_exports enable row level security;
