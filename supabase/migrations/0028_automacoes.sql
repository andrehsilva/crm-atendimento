-- Etapa 25 (D100–D103, RN-AU): pós-consulta e retorno automáticos.
alter table outbound_messages drop constraint if exists outbound_messages_kind_check;
alter table outbound_messages add constraint outbound_messages_kind_check
  check (kind in ('confirmacao', 'remarcacao', 'cancelamento', 'lembrete', 'aniversario', 'campanha', 'tratamento',
                  'pos_consulta', 'retorno'));
