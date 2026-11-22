-- Etapa 20 (D85): "entregue/lida" vindo do WhatsApp (evento message.ack).
-- Mensagens automáticas já tinham status entregue/lida (outbound_messages); a conversa ganha o mesmo para as
-- respostas da Ísis e da equipe. null = sem informação (mensagem antiga, chat do site ou recebida do paciente).
alter table messages
  add column if not exists entrega text check (entrega in ('enviada', 'entregue', 'lida'));

-- o aviso chega só com o id da mensagem no WhatsApp: busca rápida por ele, sempre dentro da clínica
create index if not exists outbound_external on outbound_messages (clinic_id, external_id) where external_id is not null;
