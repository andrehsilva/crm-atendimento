-- Etapa 10B (D44, D45, D46): uso e custo da IA, tabela de preços, cotação e teto mensal.

-- Cada resposta guarda de onde veio a IA e quanto gastou. O custo é calculado na hora (preço da época).
alter table agent_runs
  add column if not exists provider      text,
  add column if not exists model         text,
  add column if not exists origem        text check (origem is null or origem in ('clinica', 'plataforma')),
  add column if not exists tokens_entrada integer,
  add column if not exists tokens_saida   integer,
  add column if not exists tokens_cache   integer,
  add column if not exists custo_usd      numeric(14, 6);

create index if not exists agent_runs_uso_idx on agent_runs (clinic_id, created_at);

-- Preços por 1 milhão de tokens, em US$, mantidos pelo admin geral. Estimativa: o valor oficial é o da conta no provedor.
create table if not exists ai_prices (
  provider       text not null,
  model          text not null check (char_length(model) between 1 and 120),
  entrada_usd    numeric(12, 4) not null check (entrada_usd >= 0),
  saida_usd      numeric(12, 4) not null check (saida_usd >= 0),
  cache_usd      numeric(12, 4) check (cache_usd is null or cache_usd >= 0),  -- vazio = cobra como entrada
  updated_at     timestamptz not null default now(),
  primary key (provider, model)
);
alter table ai_prices enable row level security;

-- Configurações da plataforma (uma linha só): cotação do dólar para mostrar R$.
create table if not exists platform_settings (
  id           integer primary key default 1 check (id = 1),
  cotacao_brl  numeric(10, 4) check (cotacao_brl is null or cotacao_brl > 0),
  updated_at   timestamptz not null default now()
);
insert into platform_settings (id) values (1) on conflict do nothing;
alter table platform_settings enable row level security;

-- Teto mensal da clínica em US$ (vazio = sem teto).
alter table clinic_ai add column if not exists teto_mensal_usd numeric(12, 2)
  check (teto_mensal_usd is null or teto_mensal_usd > 0);
