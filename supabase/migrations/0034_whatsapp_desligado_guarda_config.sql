-- Etapa 31 (D122–D124): desligar o WhatsApp da clínica não apaga mais o servidor próprio nem o webhook exclusivo.
-- A linha da clínica fica com session = null e enabled = false; o servidor pode ser configurado antes de ligar.
alter table whatsapp_instances alter column session drop not null;
alter table whatsapp_instances add constraint whatsapp_ligado_tem_sessao check (not enabled or session is not null);
