-- Etapa 19 (D81–D83): sino de notificações.
-- As notificações em si NÃO são gravadas: saem do que o sistema já registra (histórico da agenda, fila de
-- mensagens, conversas, uso da IA). Aqui fica só quem já leu o quê — cada pessoa tem a sua leitura (D82).
create table if not exists notification_reads (
  clinic_id  uuid not null references clinics(id) on delete cascade,
  user_id    uuid not null,
  chave      text not null,             -- ex.: "ag:<id do evento>", "msg:<id da mensagem>", "ia:2026-11:aviso"
  read_at    timestamptz not null default now(),
  primary key (clinic_id, user_id, chave)
);

alter table notification_reads enable row level security;

-- leitura rápida dos eventos recentes da agenda (o sino olha só os últimos dias)
create index if not exists appointment_events_recentes on appointment_events (clinic_id, created_at desc);
