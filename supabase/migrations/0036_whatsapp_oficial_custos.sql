-- Etapa 36E (D131): WhatsApp oficial — campanhas como modelo de marketing e custo das mensagens.
-- Só acrescenta: nada muda para clínicas no WAHA.

-- Campanha de clínica na Meta vira um modelo próprio, que a Meta aprova antes do envio.
alter table campaigns
  add column if not exists meta_modelo       text,
  add column if not exists meta_situacao     text,
  add column if not exists meta_motivo       text,
  add column if not exists meta_conferido_em timestamptz;

-- Cada mensagem que a Meta disse que cobra (vem no aviso de enviada/entregue: categoria e se é cobrável).
create table if not exists meta_cobrancas (
  id          uuid primary key default gen_random_uuid(),
  clinic_id   uuid not null references clinics(id) on delete cascade,
  wamid       text not null,
  categoria   text not null,  -- service | utility | marketing | authentication | ...
  cobravel    boolean not null default true,
  criado_em   timestamptz not null default now(),
  unique (clinic_id, wamid)
);
create index if not exists meta_cobrancas_mes on meta_cobrancas (clinic_id, criado_em);
alter table meta_cobrancas enable row level security;

-- Preços da Meta (US$ por mensagem entregue, Brasil) — editáveis pelo dono da plataforma; mudam por trimestre.
alter table platform_settings
  add column if not exists meta_precos_usd jsonb not null
    default '{"marketing": 0.0625, "utility": 0.0068, "authentication": 0.0068, "service": 0.0068}'::jsonb,
  add column if not exists meta_servico_gratis integer not null default 1000 check (meta_servico_gratis >= 0);
