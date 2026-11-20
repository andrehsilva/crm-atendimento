-- Etapa 9B: foto de cada lead/cliente, enviada pela equipe em Leads / Clientes (PNG/JPG/WebP até 512 KB).

create table patient_photos (
  patient_id  uuid primary key references patients(id) on delete cascade,
  clinic_id   uuid not null references clinics(id) on delete cascade,
  mime        text not null check (mime in ('image/png', 'image/jpeg', 'image/webp')),
  data        bytea not null check (octet_length(data) <= 524288),
  updated_at  timestamptz not null default now()
);

create index patient_photos_clinica on patient_photos (clinic_id);
alter table patient_photos enable row level security;
