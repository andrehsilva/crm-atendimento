-- Etapa 30 (D117–D120): "Pergunte à assistente" — chat interno da equipe, SÓ LEITURA, só a clínica de quem pergunta.
--
-- A IA escreve um SELECT livre, mas quem garante a segurança é o banco:
--   1. visões no esquema "leitura" que só mostram a clínica gravada pelo backend (sem ela = nada);
--   2. papel isis_leitura, que só pode ler essas visões (nada do esquema public, nada de escrever);
--   3. o backend roda cada consulta numa transação só-leitura, com tempo máximo (app/consulta_equipe/leitura.py).
-- Ficam de fora: chaves de IA, usuários, tokens, WhatsApp, mensagens das conversas e observações internas.

do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'isis_leitura') then
    create role isis_leitura nologin;
  end if;
end $$;
grant isis_leitura to postgres;

create schema if not exists leitura;
revoke all on schema leitura from public;

-- A clínica vem de uma tabela temporária da conexão, gravada pelo backend ANTES de assumir o papel isis_leitura.
-- (Não usamos configuração de sessão: qualquer papel poderia trocá-la com set_config() no meio do SELECT.)
-- isis_leitura não lê nem escreve essa tabela; sem ela (ou vazia) as visões não mostram nada.
create or replace function leitura.clinica() returns uuid
  language plpgsql stable security definer
  set search_path = pg_catalog
  as $fn$
begin
  return (select id from pg_temp._isis_clinica limit 1);
exception when undefined_table then
  return null;
end $fn$;
revoke all on function leitura.clinica() from public;

create or replace view leitura.pacientes with (security_barrier) as
  select p.id, p.name as nome, p.phone as telefone, p.birth_date as nascimento,
         p.origin as origem, p.crm_stage as etapa_crm, p.last_event as ultimo_evento,
         p.last_activity_at as ultima_atividade_em, p.convenio as tipo_pagamento,
         ci.name as convenio, pr.name as profissional_preferido,
         p.archived_at is not null as arquivado, p.optout_disparos as nao_quer_campanhas,
         p.created_at as criado_em
    from patients p
    left join clinic_insurances ci on ci.id = p.insurance_id
    left join professionals pr on pr.id = p.preferred_professional_id
   where p.clinic_id = (select leitura.clinica());

create or replace view leitura.consultas with (security_barrier) as
  select a.id, a.patient_id as paciente_id, p.name as paciente, p.phone as telefone_paciente,
         a.professional_id as profissional_id, pr.name as profissional,
         a.service_id as procedimento_id, s.name as procedimento,
         a.starts_at as inicio, a.ends_at as fim, a.status as situacao,
         a.source as marcada_por, a.cancel_reason as motivo_cancelamento,
         a.treatment_id as tratamento_id, a.rescheduled_from_id is not null as foi_remarcada,
         s.price_cents / 100.0 as preco_reais, a.created_at as criada_em
    from appointments a
    join patients p on p.id = a.patient_id
    join professionals pr on pr.id = a.professional_id
    join services s on s.id = a.service_id
   where a.clinic_id = (select leitura.clinica());

create or replace view leitura.tratamentos with (security_barrier) as
  select t.id, t.patient_id as paciente_id, p.name as paciente, s.name as procedimento,
         pr.name as profissional, t.status as situacao, t.sessoes_previstas, t.intervalo_dias,
         t.motivo_espera, t.previsao, t.volta_em, t.horario_fixo, t.avisos_paciente as assistente_manda_lembrete,
         t.status_desde as situacao_desde, t.created_at as aberto_em
    from treatments t
    join patients p on p.id = t.patient_id
    left join services s on s.id = t.service_id
    left join professionals pr on pr.id = t.professional_id
   where t.clinic_id = (select leitura.clinica());

create or replace view leitura.profissionais with (security_barrier) as
  select id, name as nome, specialty as especialidade, active as ativo,
         archived_at is not null as arquivado, created_at as criado_em
    from professionals
   where clinic_id = (select leitura.clinica());

create or replace view leitura.procedimentos with (security_barrier) as
  select id, name as nome, description as descricao, duration_min as duracao_min,
         price_cents / 100.0 as preco_reais, active as ativo, bookable_by_ai as assistente_pode_marcar
    from services
   where clinic_id = (select leitura.clinica());

create or replace view leitura.convenios with (security_barrier) as
  select id, name as nome, active as ativo
    from clinic_insurances
   where clinic_id = (select leitura.clinica());

create or replace view leitura.eventos_crm with (security_barrier) as
  select e.patient_id as paciente_id, p.name as paciente, e.from_stage as de_etapa, e.to_stage as para_etapa,
         e.event as evento, e.actor_type as quem, e.created_at as quando
    from crm_events e
    join patients p on p.id = e.patient_id
   where e.clinic_id = (select leitura.clinica());

create or replace view leitura.campanhas with (security_barrier) as
  select id, titulo, publico, enviar_em, status as situacao, total as destinatarios, created_at as criada_em
    from campaigns
   where clinic_id = (select leitura.clinica());

grant usage on schema leitura to isis_leitura;
grant execute on function leitura.clinica() to isis_leitura;
grant select on all tables in schema leitura to isis_leitura;

-- Gasto do chat interno entra no teto da clínica (D120): agent_runs sem conversa, tipo 'equipe'.
alter table agent_runs alter column conversation_id drop not null;
alter table agent_runs drop constraint if exists agent_runs_tipo_check;
alter table agent_runs add constraint agent_runs_tipo_check check (tipo in ('resposta', 'transcricao', 'equipe'));
