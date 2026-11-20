-- Etapa 5: WhatsApp pelo WAHA (D28, D29, D31)

-- Cada clínica tem no máximo 1 número/sessão de WhatsApp (D29).
-- Os dados ficam no banco, por clínica (D31); a chave de API do servidor WAHA fica no .env.
create table whatsapp_instances (
  id          uuid primary key default gen_random_uuid(),
  clinic_id   uuid not null unique references clinics(id) on delete cascade,
  provider    text not null default 'waha' check (provider in ('waha')),
  session     text not null unique,            -- nome da sessão no WAHA
  status      text not null default 'DESCONHECIDO',  -- último status recebido (WORKING, SCAN_QR_CODE...)
  phone       text,                            -- número conectado (E.164), quando o WAHA informa
  enabled     boolean not null default true,
  updated_at  timestamptz not null default now(),
  created_at  timestamptz not null default now()
);

alter table whatsapp_instances enable row level security;

-- Para onde responder no WhatsApp (o chatId pode ser @c.us ou @lid).
alter table conversations add column external_chat_id text;

-- Webhooks podem chegar duas vezes: a mesma mensagem do WhatsApp só é gravada uma vez (spec 04).
create unique index messages_external_unica on messages (clinic_id, external_id) where external_id is not null;
