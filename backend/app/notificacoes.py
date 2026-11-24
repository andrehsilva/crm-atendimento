"""Etapa 19 — sino de notificações (D81–D83).

Nada aqui é gravado como "notificação": a lista sai do que o sistema já registra.
- **Situação** (D82): existe enquanto o problema existe e some sozinha — conversa aguardando atendimento humano e
  WhatsApp desconectado. Não dá para marcar como lida.
- **Acontecimento**: o que a Ísis fez na agenda, confirmação do paciente, mensagem que não saiu, gasto da IA.
  Cada pessoa marca como lida (tabela notification_reads).
"""

from datetime import datetime, timedelta
from uuid import UUID

from psycopg.rows import dict_row

from app import segmentos, uso_ia
from app.agenda import servico
from app.core import relogio
from app.painel.avisos import quando

DIAS_ACONTECIMENTOS = 7
LIMITE = 100
WHATSAPP_CAIU = ("SCAN_QR_CODE", "STOPPED", "FAILED")
NOME_MENSAGEM = {"tratamento": "Convite para seguir o tratamento", "pos_consulta": "Pós-consulta", "retorno": "Convite de retorno", "confirmacao": "Confirmação", "remarcacao": "Aviso de remarcação", "cancelamento": "Aviso de cancelamento",
                 "lembrete": "Lembrete", "aniversario": "Mensagem de aniversário", "campanha": "Campanha"}

_SQL = """
with eventos as (
  -- situação: conversas esperando a equipe
  select 'humano:' || cv.id as chave, 'humano' as tipo, cv.last_message_at as quando,
         p.id as paciente_id, p.name as nome, p.phone as telefone, null::text as extra, null::timestamptz as inicio,
         null::uuid as consulta_id, null::timestamptz as inicio_alvo,
         (select m.content from messages m where m.conversation_id = cv.id and m.clinic_id = cv.clinic_id
           and m.direction = 'in' order by m.created_at desc limit 1) as detalhe
    from conversations cv join patients p on p.id = cv.patient_id and p.clinic_id = cv.clinic_id
   where cv.clinic_id = %(c)s and cv.status = 'humano'
  union all
  -- o que a Ísis fez na agenda e as confirmações do paciente
  -- na remarcação, o que interessa é a consulta NOVA (é ela que a agenda abre)
  select 'ag:' || e.id, e.action, e.created_at, p.id, p.name, p.phone, s.name, a.starts_at,
         coalesce(n.id, a.id), coalesce(n.starts_at, a.starts_at), null
    from appointment_events e
    join appointments a on a.id = e.appointment_id and a.clinic_id = e.clinic_id
    left join appointments n on e.action = 'remarcada' and n.clinic_id = e.clinic_id and n.id = (e.after ->> 'nova_consulta')::uuid
    join patients p on p.id = a.patient_id and p.clinic_id = a.clinic_id
    join services s on s.id = a.service_id
   where e.clinic_id = %(c)s and e.created_at >= %(desde)s
     and ((e.actor_type = 'isis' and e.action in ('cancelada', 'remarcada'))
          or (e.actor_type = 'isis' and e.action = 'marcada' and a.rescheduled_from_id is null)
          or (e.actor_type in ('paciente', 'isis') and e.action = 'confirmada'))
  union all
  -- mensagens automáticas que não saíram
  select 'msg:' || o.id, 'falhou', o.scheduled_for, p.id, p.name, p.phone, o.kind, null, null, null, o.error
    from outbound_messages o join patients p on p.id = o.patient_id and p.clinic_id = o.clinic_id
   where o.clinic_id = %(c)s and o.status = 'falhou' and o.scheduled_for >= %(desde)s
  union all
  -- respostas que não chegaram ao WhatsApp do paciente
  select 'resp:' || m.id, 'resposta_falhou', m.created_at, p.id, p.name, p.phone, null, null, null, null, null
    from messages m
    join conversations cv on cv.id = m.conversation_id and cv.clinic_id = m.clinic_id
    join patients p on p.id = cv.patient_id and p.clinic_id = cv.clinic_id
   where m.clinic_id = %(c)s and m.author = 'sistema' and m.content like '⚠️ Não consegui enviar%%' and m.created_at >= %(desde)s
  union all
  -- Etapa 21: paciente pediu para marcar enquanto o tratamento aguardava (a chave muda a cada novo pedido)
  select 'trp:' || t.id || ':' || extract(epoch from t.perguntou_em)::bigint, 'tratamento_pedido', t.perguntou_em,
         p.id, p.name, p.phone, s.name, null, null, null, case t.motivo_espera when 'protetico' then 'protético' when 'exame' then 'exame'
                                      when 'cicatrizacao' then 'cicatrização' else coalesce(t.motivo_texto, 'outro motivo') end || '|' || coalesce(to_char(t.previsao, 'DD/MM'), '')
    from treatments t join patients p on p.id = t.patient_id and p.clinic_id = t.clinic_id join services s on s.id = t.service_id
   where t.clinic_id = %(c)s and t.status = 'aguardando' and t.perguntou_em >= %(desde)s
  union all
  -- Etapa 21: previsão da espera passou e o tratamento continua aguardando
  select 'trv:' || t.id || ':' || t.previsao, 'tratamento_previsao', (t.previsao + 1)::timestamp at time zone %(tz)s,
         p.id, p.name, p.phone, s.name, null, null, null, case t.motivo_espera when 'protetico' then 'protético' when 'exame' then 'exame'
                                      when 'cicatrizacao' then 'cicatrização' else coalesce(t.motivo_texto, 'outro motivo') end || '|' || to_char(t.previsao, 'DD/MM')
    from treatments t join patients p on p.id = t.patient_id and p.clinic_id = t.clinic_id join services s on s.id = t.service_id
   where t.clinic_id = %(c)s and t.status = 'aguardando' and t.previsao < %(hoje)s
  union all
  -- Etapa 21: falta numa sessão de tratamento
  select 'ag:' || e.id, 'faltou_sessao', e.created_at, p.id, p.name, p.phone, s.name, a.starts_at, a.id, a.starts_at,
         (select count(*) from appointments x where x.treatment_id = a.treatment_id and x.status in ('realizada', 'faltou')
            and x.starts_at <= a.starts_at) || '|' || coalesce(t.sessoes_previstas::text, '')
    from appointment_events e
    join appointments a on a.id = e.appointment_id and a.clinic_id = e.clinic_id
    join treatments t on t.id = a.treatment_id
    join patients p on p.id = a.patient_id and p.clinic_id = a.clinic_id
    join services s on s.id = a.service_id
   where e.clinic_id = %(c)s and e.created_at >= %(desde)s and e.action = 'faltou'
)
select e.*, (r.chave is not null) as lida
  from eventos e
  left join notification_reads r on r.clinic_id = %(c)s and r.user_id = %(u)s and r.chave = e.chave
 order by e.quando desc
 limit %(limite)s
"""


def _texto(linha: dict, clinica: dict, t: dict, ia: str) -> tuple[str, str]:
    nome = linha["nome"] or "Paciente sem nome"
    tz = clinica["tz"]
    at = t["atendimento"]
    tipo = linha["tipo"]
    if tipo == "humano":
        return f"{nome} aguardando atendimento humano", (linha["detalhe"] or "").strip()[:120]
    if tipo == "marcada":
        return f"{ia} marcou {t['uma']} {at}", f"{nome} · {linha['extra']} · {quando(linha['inicio'], tz)}"
    if tipo == "remarcada":
        return f"{ia} remarcou {t['uma']} {at}", (f"{nome} · {linha['extra']} · agora {quando(linha['inicio_alvo'], tz)}"
                                                  f" (era {quando(linha['inicio'], tz)})")
    if tipo == "cancelada":
        return f"{ia} cancelou {t['uma']} {at}", f"{nome} · {linha['extra']} · {quando(linha['inicio'], tz)}"
    if tipo == "confirmada":
        return f"{nome} confirmou {t['o']} {at}", f"{linha['extra']} · {quando(linha['inicio'], tz)}"
    if tipo == "falhou":
        return "Mensagem não enviada", f"{NOME_MENSAGEM.get(linha['extra'], 'Mensagem')} para {nome}" + (
            f" · {linha['detalhe']}" if linha["detalhe"] else "")
    if tipo in ("tratamento_pedido", "tratamento_previsao"):
        motivo, previsao = (linha["detalhe"] or "|").split("|", 1)
        if tipo == "tratamento_pedido":
            return (f"{nome} quer marcar {linha['extra']}",
                    f"O tratamento está aguardando {motivo}" + (f" (previsão {previsao})" if previsao else "")
                    + ". Clique em Retomar quando puder seguir.")
        return (f"{linha['extra']} de {nome}: a previsão era {previsao}",
                f"Ainda aguardando {motivo}. Já chegou? Retome o tratamento ou ajuste a previsão.")
    if tipo == "faltou_sessao":
        n, total = (linha["detalhe"] or "|").split("|", 1)
        return (f"{nome} faltou à sessão {n}" + (f" de {total}" if total else ""),
                f"{linha['extra']} · {quando(linha['inicio'], tz)}")
    return "Resposta não enviada pelo WhatsApp", f"A resposta para {nome} não chegou. Veja a conversa."


def listar(conn, clinic_id: UUID, user_id: UUID, agora: datetime | None = None) -> dict:
    clinica = servico.carregar_clinica(conn, clinic_id)
    agora = agora or relogio.agora().astimezone(clinica["tz"])
    t = segmentos.termos(clinica["settings"])
    ia = (clinica["settings"] or {}).get("nome_assistente") or "Ísis"

    linhas = conn.cursor(row_factory=dict_row).execute(
        _SQL, {"c": clinic_id, "u": user_id, "desde": agora - timedelta(days=DIAS_ACONTECIMENTOS), "limite": LIMITE,
               "hoje": agora.astimezone(clinica["tz"]).date(), "tz": clinica["timezone"]},
    ).fetchall()

    situacoes: list[dict] = []
    acontecimentos: list[dict] = []
    for r in linhas:
        titulo, texto = _texto(r, clinica, t, ia)
        item = {"chave": r["chave"], "tipo": r["tipo"], "titulo": titulo, "texto": texto, "quando": r["quando"],
                "paciente": {"id": r["paciente_id"], "name": r["nome"], "phone": r["telefone"]},
                # para o sino abrir a agenda no dia certo, já com a consulta aberta
                "consulta_id": r["consulta_id"],
                "dia": r["inicio_alvo"].astimezone(clinica["tz"]).date().isoformat() if r["inicio_alvo"] else None}
        if r["tipo"] == "humano":
            situacoes.append({**item, "situacao": True, "lida": False})
        else:
            acontecimentos.append({**item, "situacao": False, "lida": r["lida"]})
    situacoes.sort(key=lambda x: x["quando"])  # quem espera há mais tempo primeiro

    # Situação: consulta que já terminou e ninguém registrou se o paciente veio (pedido do usuário, 22/11/2026).
    # Some sozinha quando marcam Compareceu / Faltou (ou cancelam). Olha os últimos 30 dias.
    tz = clinica["tz"]
    for c in conn.cursor(row_factory=dict_row).execute(
            """select a.id, a.starts_at, a.ends_at, p.id as pid, p.name, p.phone, s.name as procedimento, pr.name as profissional
               from appointments a join patients p on p.id = a.patient_id and p.clinic_id = a.clinic_id
               join services s on s.id = a.service_id join professionals pr on pr.id = a.professional_id
               where a.clinic_id = %s and a.status in ('agendada', 'confirmada')
                 and a.ends_at <= %s and a.ends_at > %s - interval '30 days'
               order by a.starts_at limit 50""", (clinic_id, agora, agora)).fetchall():
        situacoes.append({
            "chave": f"presenca:{c['id']}", "tipo": "presenca", "situacao": True, "lida": False, "quando": c["ends_at"],
            "titulo": f"Registrar presença: {c['name'] or 'Paciente sem nome'}",
            "texto": f"{c['procedimento']} com {c['profissional']} · {quando(c['starts_at'], tz)} — compareceu ou faltou?",
            "paciente": {"id": c["pid"], "name": c["name"], "phone": c["phone"]},
            "consulta_id": c["id"], "dia": c["starts_at"].astimezone(tz).date().isoformat(),
        })

    w = conn.execute("select status, updated_at from whatsapp_instances where clinic_id = %s and enabled", (clinic_id,)).fetchone()
    if w and w[0] in WHATSAPP_CAIU:
        situacoes.insert(0, {"chave": "whatsapp", "tipo": "whatsapp", "situacao": True, "lida": False, "paciente": None,
                             "titulo": "WhatsApp desconectado", "quando": w[1], "consulta_id": None, "dia": None,
                             "texto": "As mensagens não estão chegando. Reconecte em Configurações › Canais."})

    uso = uso_ia.situacao(conn, clinic_id)
    if uso["nivel"] in ("aviso", "pausada"):
        chave = f"ia:{agora:%Y-%m}:{uso['nivel']}"
        lida = conn.execute("select 1 from notification_reads where clinic_id = %s and user_id = %s and chave = %s",
                            (clinic_id, user_id, chave)).fetchone() is not None
        titulo = (f"Gasto da IA em {uso['pct']:.0f}% do teto do mês" if uso["nivel"] == "aviso"
                  else f"{ia} pausada: o teto de gasto do mês foi atingido")
        acontecimentos.insert(0, {"chave": chave, "tipo": "ia", "situacao": False, "lida": lida, "paciente": None,
                                  "titulo": titulo, "quando": agora, "texto": "Veja em Configurações › Uso da IA.",
                                  "consulta_id": None, "dia": None})

    nao_lidas = sum(1 for a in acontecimentos if not a["lida"])
    return {
        "itens": situacoes + acontecimentos,
        "contador": len(situacoes) + nao_lidas,
        "aguardando": sum(1 for s in situacoes if s["tipo"] == "humano"),  # D83: só isso toca o som
    }


def marcar_lidas(conn, clinic_id: UUID, user_id: UUID, chaves: list[str] | None) -> None:
    """chaves=None → todas as não lidas da lista atual. Situações ("humano:", "whatsapp") não se marcam: somem sozinhas."""
    if chaves is None:
        chaves = [i["chave"] for i in listar(conn, clinic_id, user_id)["itens"] if not i["situacao"] and not i["lida"]]
    chaves = [c for c in chaves if not c.startswith(("humano:", "presenca:")) and c != "whatsapp"]
    if not chaves:
        return
    with conn.cursor() as cur:
        cur.executemany(
            "insert into notification_reads (clinic_id, user_id, chave) values (%s, %s, %s) on conflict do nothing",
            [(clinic_id, user_id, c) for c in chaves],
        )
