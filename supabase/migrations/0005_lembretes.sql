-- Etapa 6: lembretes, avisos e aniversário

-- RN-DP-04: paciente que pediu "PARAR"/"SAIR" não recebe mais disparos (aniversário).
-- Confirmações e lembretes de consulta continuam.
alter table patients add column optout_disparos boolean not null default false;

-- Evita mensagem repetida: ex. aniversário = 1× por ano por paciente (RN-DP-01).
alter table outbound_messages add column dedupe_key text;
create unique index outbound_dedupe on outbound_messages (clinic_id, kind, dedupe_key) where dedupe_key is not null;

-- Busca rápida do último lembrete enviado ao paciente (para entender a resposta "1", "2" ou "3").
create index outbound_paciente on outbound_messages (clinic_id, patient_id, kind, sent_at desc);
