-- Etapa 14A (D69–D72): campanhas (Natal, Ano novo, férias…) e envio espaçado das mensagens em massa.
create table if not exists campaigns (
  id          uuid primary key default gen_random_uuid(),
  clinic_id   uuid not null references clinics(id) on delete cascade,
  titulo      text not null check (char_length(titulo) between 1 and 80),
  texto       text not null check (char_length(texto) between 1 and 1000),
  publico     text not null check (publico in ('todos', 'ativos12m', 'com_consulta')),
  enviar_em   timestamptz not null,
  status      text not null default 'agendada' check (status in ('agendada', 'cancelada')),
  total       integer not null default 0,
  criada_por  uuid references app_users(user_id) on delete set null,
  created_at  timestamptz not null default now()
);
create index if not exists campaigns_clinic_idx on campaigns (clinic_id, enviar_em desc);
alter table campaigns enable row level security;

alter table outbound_messages add column if not exists campaign_id uuid references campaigns(id) on delete set null;
alter table outbound_messages drop constraint if exists outbound_messages_kind_check;
alter table outbound_messages add constraint outbound_messages_kind_check
  check (kind in ('confirmacao', 'remarcacao', 'cancelamento', 'lembrete', 'aniversario', 'campanha'));
