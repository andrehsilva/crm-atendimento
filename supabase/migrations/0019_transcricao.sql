-- Etapa 13B (D67): transcrição de áudio do WhatsApp entra no uso e no teto da IA.
alter table agent_runs add column if not exists tipo text not null default 'resposta'
  check (tipo in ('resposta', 'transcricao'));
alter table agent_runs add column if not exists audio_segundos integer;
