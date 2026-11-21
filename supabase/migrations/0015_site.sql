-- Etapa 11A (D57 revista, D58, D61, D62): site de apresentação de cada clínica.

-- D61: o endereço curto da clínica de apresentação deixa de ser "demo" (vira "rodrigues").
-- A demonstração passa a ser a clínica marcada como apresentação (D55), não um endereço fixo.
update clinics set slug = 'rodrigues'
where slug = 'demo' and apresentacao and name ilike '%rodrigues%'
  and not exists (select 1 from clinics where slug = 'rodrigues');

-- Um site por clínica. Começa como rascunho; publica pelo painel (só com a configuração inicial concluída).
create table if not exists clinic_sites (
  clinic_id    uuid primary key references clinics(id) on delete cascade,
  template     text not null default 'classico' check (template in ('classico', 'moderno', 'acolhedor')),
  publicado    boolean not null default false,
  publicado_em timestamptz,
  secoes       jsonb not null default '{}'::jsonb,   -- 11B: liga/desliga e ordem das seções
  textos       jsonb not null default '{}'::jsonb,   -- 11B: título, chamada e textos próprios
  updated_at   timestamptz not null default now()
);
alter table clinic_sites enable row level security;
