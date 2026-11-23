-- Etapa 29 (D112–D115): contato arquivado sai do CRM e de Clientes; volta sozinho se escrever de novo.
alter table patients add column if not exists archived_at timestamptz;
