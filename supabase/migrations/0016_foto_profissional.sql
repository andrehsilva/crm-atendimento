-- Etapa 11 (D63): foto e bio curta de cada profissional, para o site de apresentação.
create table if not exists professional_photos (
  professional_id uuid primary key references professionals(id) on delete cascade,
  clinic_id       uuid not null references clinics(id) on delete cascade,
  mime            text not null check (mime in ('image/png', 'image/jpeg', 'image/webp')),
  data            bytea not null check (octet_length(data) <= 524288),
  updated_at      timestamptz not null default now()
);
create index if not exists professional_photos_clinic_idx on professional_photos (clinic_id);
alter table professional_photos enable row level security;

alter table professionals add column if not exists bio text check (bio is null or char_length(bio) <= 400);
