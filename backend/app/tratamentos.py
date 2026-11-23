"""Etapa 21 — Tratamentos em andamento (RN-TR, D87–D90).

O tratamento diz à Ísis o que ela pode fazer com um paciente recorrente. Tudo o que não pode falhar fica aqui,
no código: bloqueio enquanto aguarda (RN-TR-04), exceção do limite (RN-TR-08), tags (RN-TR-11).
"""

from datetime import date, datetime
from uuid import UUID

from psycopg.rows import dict_row

from app.agenda.erros import AgendaError
from app.core import relogio

ABERTOS = ("em_andamento", "aguardando")
ATIVOS_CONSULTA = ("agendada", "confirmada")
MOTIVOS = {"protetico": "protético", "exame": "exame", "cicatrizacao": "cicatrização", "outro": "outro motivo"}

TEXTO_RETOMAR = ("Olá, {nome}! Boa notícia da {clinica}: já podemos seguir com o seu tratamento de {procedimento}. "
                 "Quer marcar a próxima sessão? É só responder aqui. 😊")


def _cur(conn):
    return conn.cursor(row_factory=dict_row)


def motivo(t: dict) -> str:
    """'protético', 'exame'… ou o texto livre quando é 'outro'."""
    if t.get("motivo_espera") == "outro" and t.get("motivo_texto"):
        return t["motivo_texto"]
    return MOTIVOS.get(t.get("motivo_espera") or "", "outro motivo")


_SELECT = """
select t.*, s.name as procedimento, pr.name as profissional,
       (select count(*) from appointments a where a.treatment_id = t.id and a.status = 'realizada') as realizadas,
       (select count(*) from appointments a where a.treatment_id = t.id and a.status = any(%(ativos)s)
          and a.starts_at > %(agora)s) as marcadas,
       (select max(a.starts_at) from appointments a where a.treatment_id = t.id and a.status = 'realizada') as ultima_sessao,
       (select p2.name from appointments a join professionals p2 on p2.id = a.professional_id
         where a.treatment_id = t.id and a.status in ('realizada', 'agendada', 'confirmada')
         order by a.starts_at desc limit 1) as profissional_das_sessoes,
       (select min(a.starts_at) from appointments a where a.treatment_id = t.id and a.status = any(%(ativos)s)
          and a.starts_at > %(agora)s) as proxima_sessao,
       (select a.starts_at from appointments a where a.treatment_id = t.id and a.status = 'faltou'
          order by a.starts_at desc limit 1) as ultima_falta
  from treatments t join services s on s.id = t.service_id
  left join professionals pr on pr.id = t.professional_id
 where t.clinic_id = %(c)s
"""


def do_paciente(conn, clinic_id: UUID, patient_id: UUID, so_abertos: bool = False) -> list[dict]:
    sql = _SELECT + " and t.patient_id = %(p)s" + (" and t.status = any(%(abertos)s)" if so_abertos else "")
    return _cur(conn).execute(
        sql + " order by (t.status = any(%(abertos)s)) desc, t.created_at desc",
        {"c": clinic_id, "p": patient_id, "ativos": list(ATIVOS_CONSULTA), "abertos": list(ABERTOS),
         "agora": relogio.agora()},
    ).fetchall()


def obter(conn, clinic_id: UUID, tratamento_id: UUID) -> dict:
    t = _cur(conn).execute(_SELECT + " and t.id = %(t)s",
                           {"c": clinic_id, "t": tratamento_id, "ativos": list(ATIVOS_CONSULTA),
                            "agora": relogio.agora()}).fetchone()
    if not t:
        raise AgendaError("DADOS_INVALIDOS", "Tratamento não encontrado.")
    return t


def aberto(conn, clinic_id: UUID, patient_id: UUID, service_id: UUID) -> dict | None:
    return _cur(conn).execute(
        "select * from treatments where clinic_id = %s and patient_id = %s and service_id = %s and status = any(%s)",
        (clinic_id, patient_id, service_id, list(ABERTOS)),
    ).fetchone()


def conferir_marcacao(conn, clinic_id: UUID, patient_id: UUID, service_id: UUID, ator: str,
                      remarcando: bool = False) -> dict | None:
    """Chamada por servico.marcar. Devolve o tratamento aberto do procedimento (a sessão fica ligada a ele).
    RN-TR-04: aguardando → a Ísis (ou o paciente) não marca sessão nova; a recepção decide e pode."""
    t = aberto(conn, clinic_id, patient_id, service_id)
    if t and t["status"] == "aguardando" and ator != "recepcao" and not remarcando:
        raise AgendaError(
            "TRATAMENTO_AGUARDANDO",
            f"O tratamento está aguardando ({motivo(t)}): a próxima sessão ainda não pode ser marcada. "
            "Assim que puder seguir, a clínica entra em contato. A equipe já foi avisada.")
    return t


def futuras_que_contam(conn, clinic_id: UUID, patient_id: UUID, agora: datetime, excluir: UUID | None = None) -> int:
    """RN-AG-08 com a exceção RN-TR-08: sessões de tratamento ABERTO não contam no limite."""
    return conn.execute(
        """select count(*) from appointments a
           where a.clinic_id = %s and a.patient_id = %s and a.status = any(%s) and a.starts_at > %s
             and (%s::uuid is null or a.id <> %s::uuid)
             and not exists (select 1 from treatments t where t.id = a.treatment_id and t.status = any(%s))""",
        (clinic_id, patient_id, list(ATIVOS_CONSULTA), agora, excluir, excluir, list(ABERTOS)),
    ).fetchone()[0]


def registrar_pergunta(conn, clinic_id: UUID, patient_id: UUID, service_id: UUID) -> None:
    """Paciente pediu para marcar enquanto aguardava: vira aviso no sino (Etapa 21)."""
    conn.execute(
        """update treatments set perguntou_em = now()
           where clinic_id = %s and patient_id = %s and service_id = %s and status = 'aguardando'""",
        (clinic_id, patient_id, service_id))


# ---------------------------------------------------------------------------
# Tags automáticas (RN-TR-11, D90)
# ---------------------------------------------------------------------------
def tags(conn, clinic_id: UUID, patient_ids: list) -> dict:
    """{patient_id: [{"codigo": "novo"|"recorrente"|"em_tratamento"|"aguardando", "rotulo": "..."}]}"""
    if not patient_ids:
        return {}
    linhas = conn.execute(
        """select p.id,
                  (select count(*) from appointments a where a.patient_id = p.id and a.clinic_id = p.clinic_id
                     and a.status = 'realizada') as realizadas,
                  coalesce((select json_agg(json_build_object('status', t.status, 'procedimento', s.name,
                                                              'motivo_espera', t.motivo_espera, 'motivo_texto', t.motivo_texto)
                                            order by t.created_at)
                            from treatments t join services s on s.id = t.service_id
                            where t.patient_id = p.id and t.clinic_id = p.clinic_id and t.status = any(%s)), '[]'::json),
                  p.convenio, ci.name
           from patients p left join clinic_insurances ci on ci.id = p.insurance_id and ci.clinic_id = p.clinic_id
           where p.clinic_id = %s and p.id = any(%s)""",
        (list(ABERTOS), clinic_id, list(patient_ids)),
    ).fetchall()
    saida: dict = {}
    for pid, realizadas, abertos, convenio, nome_convenio in linhas:
        lista = []
        if realizadas == 0:
            lista.append({"codigo": "novo", "rotulo": "Novo"})
        elif realizadas >= 2:
            lista.append({"codigo": "recorrente", "rotulo": "Recorrente"})
        for t in abertos:
            if t["status"] == "aguardando":
                lista.append({"codigo": "aguardando", "rotulo": f"Aguardando {motivo(t)}", "procedimento": t["procedimento"]})
            else:
                lista.append({"codigo": "em_tratamento", "rotulo": f"Em tratamento · {t['procedimento']}",
                              "procedimento": t["procedimento"]})
        if convenio == "particular":  # Etapa 22 (D94)
            lista.append({"codigo": "particular", "rotulo": "Particular"})
        elif convenio == "convenio":
            lista.append({"codigo": "convenio", "rotulo": nome_convenio or "Convênio"})
        saida[pid] = lista
    return saida


# ---------------------------------------------------------------------------
# Equipe: abrir, editar e mudar situação (RN-TR-01/02)
# ---------------------------------------------------------------------------
def _profissional_faz(conn, clinic_id: UUID, professional_id: UUID | None, service_id: UUID) -> None:
    if professional_id and not conn.execute(
            "select 1 from professional_services where clinic_id = %s and professional_id = %s and service_id = %s",
            (clinic_id, professional_id, service_id)).fetchone():
        raise AgendaError("PROFISSIONAL_NAO_FAZ", "Este profissional não realiza esse procedimento.")


def criar(conn, clinic_id: UUID, patient_id: UUID, *, service_id: UUID, professional_id: UUID | None,
          sessoes_previstas: int | None, intervalo_dias: int | None, orientacao: str | None,
          avisos_paciente: bool = True) -> dict:
    if not conn.execute("select 1 from services where clinic_id = %s and id = %s", (clinic_id, service_id)).fetchone():
        raise AgendaError("DADOS_INVALIDOS", "Procedimento não encontrado.")
    _profissional_faz(conn, clinic_id, professional_id, service_id)
    if aberto(conn, clinic_id, patient_id, service_id):
        raise AgendaError("DADOS_INVALIDOS", "Este paciente já tem um tratamento aberto desse procedimento.")
    tid = conn.execute(
        """insert into treatments (clinic_id, patient_id, service_id, professional_id, sessoes_previstas, intervalo_dias,
                                   orientacao, avisos_paciente)
           values (%s, %s, %s, %s, %s, %s, %s, %s) returning id""",
        (clinic_id, patient_id, service_id, professional_id, sessoes_previstas, intervalo_dias,
         (orientacao or "").strip() or None, avisos_paciente),
    ).fetchone()[0]
    # consultas futuras desse procedimento passam a ser sessões do tratamento
    conn.execute(
        """update appointments set treatment_id = %s where clinic_id = %s and patient_id = %s and service_id = %s
           and status = any(%s) and starts_at > %s and treatment_id is null""",
        (tid, clinic_id, patient_id, service_id, list(ATIVOS_CONSULTA), relogio.agora()))
    return obter(conn, clinic_id, tid)


def editar(conn, clinic_id: UUID, tratamento_id: UUID, dados: dict) -> dict:
    t = obter(conn, clinic_id, tratamento_id)
    if t["status"] not in ABERTOS:
        raise AgendaError("STATUS_INVALIDO", "Tratamento encerrado não pode ser editado.")
    permitidos = {k: v for k, v in dados.items()
                  if k in ("professional_id", "sessoes_previstas", "intervalo_dias", "orientacao", "avisos_paciente",
                           "horario_fixo")}
    if permitidos.get("horario_fixo"):  # só dá para DESLIGAR por aqui; ligar é com a série (horario_fixo.iniciar)
        raise AgendaError("DADOS_INVALIDOS", "Para fixar um horário, abra o tratamento com o horário fixo.")
    if "avisos_paciente" in permitidos and permitidos["avisos_paciente"] is None:
        del permitidos["avisos_paciente"]
    fixo = t["horario_fixo"] and permitidos.get("horario_fixo") is not False
    if fixo and "intervalo_dias" in permitidos and not permitidos["intervalo_dias"]:
        raise AgendaError("DADOS_INVALIDOS", "O horário fixo precisa do intervalo entre sessões.")
    if fixo and "professional_id" in permitidos and not permitidos["professional_id"]:
        raise AgendaError("DADOS_INVALIDOS", "O horário fixo precisa de um profissional.")
    if permitidos.get("professional_id"):
        _profissional_faz(conn, clinic_id, permitidos["professional_id"], t["service_id"])
    if "orientacao" in permitidos:
        permitidos["orientacao"] = (permitidos["orientacao"] or "").strip() or None
    if permitidos:
        sets = ", ".join(f"{k} = %s" for k in permitidos)  # chaves fixas acima, não vêm do usuário
        conn.execute(f"update treatments set {sets}, updated_at = now() where id = %s", [*permitidos.values(), tratamento_id])
    return obter(conn, clinic_id, tratamento_id)


def aguardar(conn, clinic_id: UUID, tratamento_id: UUID, *, motivo_espera: str, motivo_texto: str | None,
             previsao: date | None) -> dict:
    t = obter(conn, clinic_id, tratamento_id)
    if t["status"] not in ABERTOS:
        raise AgendaError("STATUS_INVALIDO", "Tratamento encerrado.")
    if motivo_espera not in MOTIVOS:
        raise AgendaError("DADOS_INVALIDOS", "Motivo inválido.")
    conn.execute(
        """update treatments set status = 'aguardando', motivo_espera = %s, motivo_texto = %s, previsao = %s,
                  perguntou_em = null, status_desde = now(), updated_at = now() where id = %s""",
        (motivo_espera, ((motivo_texto or "").strip() or None) if motivo_espera == "outro" else None, previsao, tratamento_id))
    return obter(conn, clinic_id, tratamento_id)


def texto_retomar(clinica: dict, t: dict, nome_paciente: str | None) -> str:
    return TEXTO_RETOMAR.format(nome=(nome_paciente or "").split(" ")[0] or "tudo bem",
                                clinica=clinica["name"], procedimento=t["procedimento"])


def retomar(conn, clinica: dict, tratamento_id: UUID, *, texto: str | None, avisar_paciente: bool = True) -> dict:
    """D88: volta para em_andamento e (se pedido) põe na fila a mensagem convidando a marcar."""
    t = obter(conn, clinica["id"], tratamento_id)
    if t["status"] != "aguardando":
        raise AgendaError("STATUS_INVALIDO", "Só dá para retomar um tratamento que está aguardando.")
    conn.execute(
        """update treatments set status = 'em_andamento', motivo_espera = null, motivo_texto = null, previsao = null,
                  perguntou_em = null, status_desde = now(), updated_at = now() where id = %s""", (tratamento_id,))
    if avisar_paciente:
        nome = conn.execute("select name from patients where id = %s", (t["patient_id"],)).fetchone()[0]
        corpo = (texto or "").strip() or texto_retomar(clinica, t, nome)
        if len(corpo) > 1000:
            raise AgendaError("DADOS_INVALIDOS", "A mensagem passa de 1000 caracteres.")
        corpo = corpo.replace("{nome}", (nome or "").split(" ")[0]).replace("{clinica}", clinica["name"])
        conn.execute(
            "insert into outbound_messages (clinic_id, patient_id, kind, body) values (%s, %s, 'tratamento', %s)",
            (clinica["id"], t["patient_id"], corpo))
    return obter(conn, clinica["id"], tratamento_id)


def encerrar(conn, clinic_id: UUID, tratamento_id: UUID, *, status: str, volta_em: date | None) -> dict:
    """Concluído (com "volta em", RN-TR-10) ou interrompido. Não reabre."""
    t = obter(conn, clinic_id, tratamento_id)
    if t["status"] not in ABERTOS:
        raise AgendaError("STATUS_INVALIDO", "Este tratamento já foi encerrado.")
    if status not in ("concluido", "interrompido"):
        raise AgendaError("DADOS_INVALIDOS", "Situação inválida.")
    conn.execute(
        """update treatments set status = %s, volta_em = %s, motivo_espera = null, motivo_texto = null, previsao = null,
                  status_desde = now(), updated_at = now() where id = %s""",
        (status, volta_em if status == "concluido" else None, tratamento_id))
    return obter(conn, clinic_id, tratamento_id)
