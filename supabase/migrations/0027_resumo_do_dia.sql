-- Etapa 23 (D96–D98, RN-RS): resumo do dia no WhatsApp pessoal do profissional.
alter table professionals
  add column if not exists whatsapp_pessoal text check (whatsapp_pessoal is null or whatsapp_pessoal ~ '^\+[1-9][0-9]{9,14}$'),
  add column if not exists resumo_ativo     boolean not null default false,  -- D97: só recebe quem pediu
  add column if not exists resumo_hora      text not null default '07:00' check (resumo_hora ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$');

-- Um registro por profissional e dia: garante "uma vez por dia" (D98) e guarda o que foi mandado.
create table if not exists professional_digests (
  id               uuid primary key default gen_random_uuid(),
  clinic_id        uuid not null references clinics(id) on delete cascade,
  professional_id  uuid not null references professionals(id) on delete cascade,
  dia              date not null,
  status           text not null check (status in ('enviado', 'falhou', 'sem_consulta', 'pulado')),
  body             text,
  attempts         integer not null default 0,
  error            text,
  sent_at          timestamptz,
  created_at       timestamptz not null default now(),
  unique (professional_id, dia)
);
alter table professional_digests enable row level security;
