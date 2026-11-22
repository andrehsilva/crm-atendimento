-- Etapa 16 (D76): WhatsApp próprio de cada clínica — número, servidor WAHA (opcional) e webhook exclusivo.
alter table whatsapp_instances
  add column if not exists numero                text check (numero is null or numero ~ '^\+[1-9][0-9]{9,14}$'),
  add column if not exists waha_url              text check (waha_url is null or waha_url ~ '^https?://'),
  add column if not exists waha_key_cipher       bytea,
  add column if not exists waha_key_last4        text,
  add column if not exists webhook_token         text unique,
  add column if not exists webhook_secret_cipher bytea;
