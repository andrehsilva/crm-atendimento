-- Etapa 26 (D105–D107): horário fixo no tratamento e lembrete ligado/desligado por tratamento.
-- avisos_paciente = false → as sessões desse tratamento não geram confirmação nem lembrete (RN-TR-13).
alter table treatments add column if not exists avisos_paciente boolean not null default true;
-- horario_fixo = true → série sem data para terminar: o sistema mantém as próximas sessões marcadas (RN-TR-12).
alter table treatments add column if not exists horario_fixo boolean not null default false;
-- última data já TENTADA da série (marcada ou não): a renovação continua dela e nunca recria o que foi cancelado.
alter table treatments add column if not exists serie_ate timestamptz;
alter table treatments drop constraint if exists treatments_horario_fixo_check;
alter table treatments add constraint treatments_horario_fixo_check
  check (not horario_fixo or (serie_ate is not null and intervalo_dias is not null));
