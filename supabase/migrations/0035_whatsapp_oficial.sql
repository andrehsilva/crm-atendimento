-- Etapa 36A (D131): WhatsApp oficial (Cloud API da Meta) como 2ª opção por clínica.
-- Só acrescenta: toda clínica continua em 'waha' (padrão), nada muda para quem já usa.
-- Dados da Meta (docs/conexao_meta.md): IDs do número e da conta; token e chave secreta do app cifrados (Fernet,
-- IA_CHAVE_MESTRA), só os 4 últimos caracteres do token ficam visíveis; token de verificação do webhook gerado por nós.
alter table whatsapp_instances drop constraint if exists whatsapp_instances_provider_check;
alter table whatsapp_instances add constraint whatsapp_instances_provider_check check (provider in ('waha', 'meta'));

alter table whatsapp_instances
  add column if not exists meta_phone_number_id   text check (meta_phone_number_id is null or meta_phone_number_id ~ '^[0-9]{5,30}$'),
  add column if not exists meta_waba_id           text check (meta_waba_id is null or meta_waba_id ~ '^[0-9]{5,30}$'),
  add column if not exists meta_token_cipher      bytea,
  add column if not exists meta_token_last4       text,
  add column if not exists meta_app_secret_cipher bytea,
  add column if not exists meta_verify_token      text unique;
