"""Etapa 30 (D117–D120): "Pergunte à assistente" — a equipe pergunta sobre os dados da clínica.

A IA tem UMA ferramenta, `consultar(sql)`, que roda um SELECT livre pelas travas de `leitura.py`
(só leitura, só esta clínica). Assim as perguntas não ficam presas a uma lista fixa.
Assunto fora da plataforma: recusa. Pedido de mudar algo: explica que aqui é só consulta.
O gasto entra no teto da clínica (agent_runs tipo 'equipe').
"""

import json
import logging
import time

from agno.agent import Agent
from agno.models.message import Message
from psycopg.types.json import Jsonb

from app import segmentos, uso_ia
from app.consulta_equipe import leitura
from app.core import relogio
from app.ia import ConfigIA, config_da_clinica, modelo_agno

log = logging.getLogger("isis.equipe")

HISTORICO = 10
DIAS = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")
MSG_SEM_IA = "A assistente está desligada nesta clínica (sem IA configurada). O administrador liga em Configurações › Assistente."
MSG_PAUSADA = "O limite de gasto de IA deste mês foi atingido, então a assistente está pausada. O administrador pode ajustar o teto."
MSG_FALHA = "Não consegui responder agora. Tente de novo em instantes ou pergunte de outro jeito."

DADOS = """\
Tabelas que você pode consultar (PostgreSQL, só SELECT; já mostram apenas esta clínica — não filtre por clínica):

pacientes(id, nome, telefone, nascimento date, origem ['web','whatsapp','manual'], etapa_crm ['novo_contato','agendado',
  'confirmado','cancelado'], ultimo_evento, ultima_atividade_em, tipo_pagamento ['particular','convenio' ou nulo],
  convenio (nome), profissional_preferido, arquivado bool, nao_quer_campanhas bool, criado_em)
consultas(id, paciente_id, paciente, telefone_paciente, profissional_id, profissional, procedimento_id, procedimento,
  inicio timestamptz, fim, situacao ['agendada','confirmada','cancelada','realizada' (compareceu),'faltou'],
  marcada_por ['isis' (assistente),'recepcao','paciente_botao'], motivo_cancelamento, tratamento_id, foi_remarcada bool,
  preco_reais (preço de tabela do procedimento), criada_em)
tratamentos(id, paciente_id, paciente, procedimento, profissional, situacao ['em_andamento','aguardando','concluido',
  'interrompido'], sessoes_previstas, intervalo_dias, motivo_espera, previsao date, volta_em date, horario_fixo bool,
  assistente_manda_lembrete bool, situacao_desde, aberto_em)
profissionais(id, nome, especialidade, ativo bool, arquivado bool, criado_em)
procedimentos(id, nome, descricao, duracao_min, preco_reais, ativo bool, assistente_pode_marcar bool)
convenios(id, nome, ativo bool)
eventos_crm(paciente_id, paciente, de_etapa, para_etapa, evento, quem ['isis','recepcao','paciente','sistema'], quando)
campanhas(id, titulo, publico, enviar_em, situacao ['agendada','cancelada'], destinatarios, criada_em)

Não existem: sexo/gênero, endereço, e-mail, CPF, valores pagos de verdade (só preço de tabela), conteúdo das conversas,
observações internas. As datas já vêm no fuso da clínica."""


def instrucoes(clinica: dict) -> str:
    seg = segmentos.segmento_de(clinica.get("settings"))
    t = segmentos.termos(clinica.get("settings"))
    agora = relogio.agora().astimezone(clinica["tz"])
    return f"""\
Você é a assistente interna da {clinica['name']} ({seg.nome}). Quem fala com você é alguém da EQUIPE da clínica,
não um {t['cliente']}. Aqui os {t['clientes']} são chamados de "{t['clientes']}" e os profissionais de "{t['profissionais']}".
Agora é {DIAS[agora.weekday()]}, {agora:%d/%m/%Y %H:%M} (fuso {clinica['timezone']}).

O que você faz: responde perguntas sobre os dados DESTA clínica na plataforma (agenda, {t['clientes']}, tratamentos,
procedimentos, profissionais, CRM, campanhas), consultando o banco com a ferramenta `consultar`.

Regras:
- Só fale da plataforma e dos dados da clínica. Qualquer outro assunto (conhecimento geral, saúde, receitas, notícias,
  programação etc.): diga com educação que aqui você só responde sobre os dados da clínica.
- Aqui é SÓ CONSULTA. Você não marca, desmarca, edita nem apaga nada. Se pedirem, explique que isso é feito nas telas
  do painel (Agenda, Clientes, CRM…).
- Nunca invente números: sempre consulte antes de responder. Se o dado não existe, diga que a plataforma não guarda isso.
- Nome de pessoa: busque com ilike e sem acento sensível (ex.: nome ilike '%andre%' or nome ilike '%andré%').
  Se achar mais de uma pessoa, liste as opções (nome e final do telefone) e pergunte qual é.
- "Quantas vezes veio" = consultas com situacao 'realizada'. Diga também se há faltas ou consultas marcadas, quando ajudar.
- Períodos como "este mês", "semana passada": calcule a partir de agora.
- Se a consulta der erro, corrija e tente de novo (no máximo algumas vezes).
- Responda em português simples, curto e direto, com os números em destaque. Listas curtas (até 10 itens; diga se há mais).
  Não mostre SQL nem nomes técnicos de colunas. Pode usar **negrito** e listas com "- ".

{DADOS}"""


def _modelo(ia: ConfigIA, clinica: dict):
    return modelo_agno(ia, f"equipe:{clinica['id']}")


def responder(conn, conn_leitura, clinica: dict, mensagens: list[dict]) -> str:
    """`mensagens` = [{autor: 'equipe'|'assistente', texto}], a última é a pergunta. `conn_leitura` = conexão limpa para os SELECTs."""
    ia = config_da_clinica(conn, clinica["id"])
    if ia is None:
        return MSG_SEM_IA
    if uso_ia.pausada(conn, clinica["id"]):
        return MSG_PAUSADA

    chamadas: list[dict] = []

    def consultar(sql: str) -> str:
        """Roda um SELECT nas tabelas descritas (só leitura, só esta clínica) e devolve as linhas em JSON.

        Args:
            sql: uma única consulta SELECT (ou WITH ... SELECT), sem ponto e vírgula.
        """
        try:
            r = leitura.executar(conn_leitura, clinica["id"], sql, clinica["timezone"])
            chamadas.append({"ferramenta": "consultar", "sql": sql[:1000], "linhas": len(r["linhas"])})
            return json.dumps(r, ensure_ascii=False, default=str)
        except leitura.ConsultaRecusada as e:
            chamadas.append({"ferramenta": "consultar", "sql": sql[:1000], "erro": str(e)})
            return json.dumps({"erro": str(e)}, ensure_ascii=False)

    historico = [m for m in mensagens if (m.get("texto") or "").strip()][-HISTORICO:]
    entrada = [Message(role="user" if m["autor"] == "equipe" else "assistant", content=m["texto"][:2000]) for m in historico]
    pergunta = historico[-1]["texto"] if historico else ""

    inicio = time.perf_counter()
    saida, erro, tokens = None, None, (0, 0, 0)
    try:
        agente = Agent(model=_modelo(ia, clinica), instructions=instrucoes(clinica), tools=[consultar],
                       tool_call_limit=6, markdown=True, telemetry=False)
        r = agente.run(entrada)
        tokens = uso_ia.tokens_da_resposta(r)
        saida = (r.content if isinstance(r.content, str) else str(r.content or "")).strip() or None
        if saida is None:
            raise RuntimeError("resposta vazia do modelo")
    except Exception as e:  # noqa: BLE001 — falha vira mensagem amigável
        erro = f"{type(e).__name__}: {e}"[:500]
        log.warning("falha no chat da equipe: %s", erro)
        saida = MSG_FALHA

    custo = uso_ia.calcular_custo(conn, ia, *tokens) if any(tokens) else None
    conn.execute(
        """insert into agent_runs (clinic_id, conversation_id, tipo, input, tools, output, latency_ms, error,
                                   provider, model, origem, tokens_entrada, tokens_saida, tokens_cache, custo_usd)
           values (%s, null, 'equipe', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (clinica["id"], pergunta[:2000], Jsonb(chamadas), saida, round((time.perf_counter() - inicio) * 1000), erro,
         ia.provedor, ia.modelo, ia.origem, *tokens, custo),
    )
    return saida
