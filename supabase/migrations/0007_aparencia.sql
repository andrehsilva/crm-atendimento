-- Etapa 9B: logo de cada clínica (D40). A cor principal fica em clinics.settings->>'cor'.
-- A imagem fica numa tabela própria para não pesar em toda leitura da clínica.

create table clinic_logos (
  clinic_id   uuid primary key references clinics(id) on delete cascade,
  mime        text not null check (mime in ('image/png', 'image/jpeg', 'image/webp')),
  data        bytea not null check (octet_length(data) <= 524288),  -- até 512 KB
  updated_at  timestamptz not null default now()
);

alter table clinic_logos enable row level security;
