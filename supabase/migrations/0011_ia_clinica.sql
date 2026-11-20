-- Etapa 10A (D42, D43, D46): IA de cada clínica.
-- A chave fica criptografada (a chave-mestra está só no backend/.env); a tela só vê os 4 últimos caracteres.
-- Sem chave própria e sem "usar a chave da plataforma", a assistente fica desligada.

create table if not exists clinic_ai (
  clinic_id      uuid primary key references clinics(id) on delete cascade,
  provider       text check (provider in ('google', 'openai', 'opencode', 'openrouter')),
  model          text check (model is null or char_length(model) between 1 and 120),
  key_cipher     bytea,
  key_last4      text check (key_last4 is null or char_length(key_last4) <= 4),
  usa_plataforma boolean not null default false,
  updated_at     timestamptz not null default now(),
  updated_by     uuid references app_users(user_id) on delete set null,
  -- chave própria só existe junto com provedor e modelo
  check (key_cipher is null or (provider is not null and model is not null and key_last4 is not null))
);

alter table clinic_ai enable row level security;

-- As clínicas que já existem continuam atendendo como hoje (com a IA da plataforma).
insert into clinic_ai (clinic_id, usa_plataforma)
select id, true from clinics
on conflict (clinic_id) do nothing;
