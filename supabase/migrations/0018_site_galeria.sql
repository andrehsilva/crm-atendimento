-- Etapa 11B (D63): galeria de fotos do site (até 12 por clínica; mesmas regras da logo: PNG/JPG/WebP até 512 KB).
create table if not exists site_photos (
  id          uuid primary key default gen_random_uuid(),
  clinic_id   uuid not null references clinics(id) on delete cascade,
  mime        text not null check (mime in ('image/png', 'image/jpeg', 'image/webp')),
  data        bytea not null check (octet_length(data) <= 524288),
  legenda     text check (legenda is null or char_length(legenda) <= 120),
  ordem       integer not null default 0,
  created_at  timestamptz not null default now()
);
create index if not exists site_photos_clinic_idx on site_photos (clinic_id, ordem);
alter table site_photos enable row level security;
