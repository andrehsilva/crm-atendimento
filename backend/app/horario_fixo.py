"""Etapa 26 — sessões do tratamento marcadas ao abrir, e horário fixo sem data para terminar (D105–D107).

- RN-TR-12: com horário fixo, o sistema mantém sempre as próximas JANELA sessões marcadas; a cada rodada do agendador
  acrescenta as que faltam, enquanto o tratamento estiver em andamento. A renovação continua da última data TENTADA
  (`serie_ate`): uma sessão que o paciente cancelou não volta sozinha.
- RN-TR-13: tratamento com avisos desligados não gera confirmação nem lembrete (o filtro fica em painel/avisos.py).
- Encerrar um tratamento com horário fixo cancela as sessões futuras dele, sem mensagem ao paciente.
Cada data passa por todas as regras da agenda (servico.marcar); a que não couber fica de fora com o motivo.
"""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from psycopg.rows import dict_row

from app import tratamentos as T
from app.agenda import servico as S
from app.agenda.erros import AgendaError
from app.core import relogio
from app.painel import avisos

log = logging.getLogger("isis.horario_fixo")

JANELA = 8  # sessões sempre marcadas à frente (8 semanas no semanal)


def _datas(primeira: datetime, intervalo_dias: int, n: int) -> list[datetime]:
    # datetime com ZoneInfo: somar dias mantém o horário de parede (09:00 continua 09:00)
    return [primeira + timedelta(days=intervalo_dias * i) for i in range(n)]


def _ate(clinica: dict, agora: datetime) -> datetime:
    """Último instante em que a agenda aceita marcação (horizonte da clínica, RN-AG-05)."""
    return agora + timedelta(days=clinica["regras"].horizonte_dias)


def _marcar_datas(conn, clinic_id: UUID, t: dict, telefone: str, datas: list[datetime], agora: datetime):
    marcadas, falhas = [], []
    for quando in datas:
        try:
            marcadas.append(S.marcar(conn, clinic_id, telefone=telefone, nome=None, professional_id=t["professional_id"],
                                     service_id=t["service_id"], inicio=quando, ator="recepcao", agora=agora,
                                     avisar_paciente=False))
        except AgendaError as e:  # cada sessão é independente (como na série, RN-TR-07)
            falhas.append({"inicio": quando, "codigo": e.codigo, "motivo": e.mensagem})
    return marcadas, falhas


def marcar_ao_abrir(conn, clinic_id: UUID, tratamento_id: UUID, *, inicio: datetime, sessoes: int | None,
                    agora: datetime | None = None) -> dict:
    """Ao abrir o tratamento: `sessoes` = N (2 a 20) marca N datas; None = horário fixo, sem data para terminar.
    Nada coube → erro (quem chama desfaz tudo, inclusive o tratamento recém-aberto)."""
    clinica = S.carregar_clinica(conn, clinic_id)
    tz = clinica["tz"]
    agora = agora or relogio.agora()
    t = T.obter(conn, clinic_id, tratamento_id)
    if not t["professional_id"]:
        raise AgendaError("DADOS_INVALIDOS", "Escolha o profissional das sessões.")
    intervalo = t["intervalo_dias"] or 7
    if not 1 <= intervalo <= 60:
        raise AgendaError("DADOS_INVALIDOS", "O intervalo entre sessões vai de 1 a 60 dias.")
    if sessoes is not None and not 2 <= sessoes <= S.SERIE_MAX:
        raise AgendaError("DADOS_INVALIDOS", f"Uma série tem de 2 a {S.SERIE_MAX} sessões.")
    primeira = (inicio if inicio.tzinfo else inicio.replace(tzinfo=tz)).astimezone(tz)
    datas = _datas(primeira, intervalo, sessoes or JANELA)
    if sessoes is None:  # sem fim: só até onde a agenda está aberta (RN-AG-05); o resto a renovação marca depois
        datas = [d for d in datas if d <= _ate(clinica, agora)] or datas[:1]
    telefone = conn.execute("select phone from patients where id = %s", (t["patient_id"],)).fetchone()[0]
    marcadas, falhas = _marcar_datas(conn, clinic_id, t, telefone, datas, agora)
    if not marcadas:
        motivo = falhas[0]["motivo"] if falhas else ""
        raise AgendaError("SERIE_VAZIA", f"Nenhuma das datas coube na agenda. {motivo}".strip())
    if sessoes is None:
        conn.execute("update treatments set horario_fixo = true, intervalo_dias = %s, serie_ate = %s, updated_at = now() "
                     "where id = %s", (intervalo, datas[-1], tratamento_id))
    elif not t["sessoes_previstas"]:
        conn.execute("update treatments set sessoes_previstas = %s, intervalo_dias = %s where id = %s",
                     (sessoes, intervalo, tratamento_id))
    avisos.enfileirar_serie(conn, clinica, marcadas, agora)  # uma confirmação só (ou nada, se avisos desligados)
    return {"marcadas": marcadas, "falhas": falhas}


def renovar(conn, clinica: dict, t: dict, agora: datetime) -> int:
    """Acrescenta as sessões que faltam para manter JANELA à frente. Devolve quantas marcou."""
    from app.mensagens.lembretes import agendar_lembrete  # import aqui para evitar import circular

    tz, intervalo = clinica["tz"], t["intervalo_dias"]
    limite = min(agora + timedelta(days=intervalo * JANELA), _ate(clinica, agora))
    prox = t["serie_ate"].astimezone(tz) + timedelta(days=intervalo)
    while prox <= agora:  # voltou de uma espera: não tenta datas que já passaram
        prox += timedelta(days=intervalo)
    datas = []
    while prox <= limite:
        datas.append(prox)
        prox += timedelta(days=intervalo)
    if not datas:
        return 0
    telefone = conn.execute("select phone from patients where id = %s", (t["patient_id"],)).fetchone()[0]
    marcadas, falhas = _marcar_datas(conn, clinica["id"], t, telefone, datas, agora)
    for c in marcadas:
        agendar_lembrete(conn, clinica, c, agora)  # não faz nada se os avisos estiverem desligados
    for f in falhas:
        log.info("horário fixo %s: %s ficou de fora (%s)", t["id"], f["inicio"], f["codigo"])
    conn.execute("update treatments set serie_ate = %s where id = %s", (datas[-1], t["id"]))
    return len(marcadas)


def renovar_todos(conn, agora: datetime, so_clinica: UUID | None = None) -> int:
    """Chamado pelo agendador. Só tratamentos em andamento (aguardando = pausa a renovação)."""
    linhas = conn.cursor(row_factory=dict_row).execute(
        """select t.* from treatments t join clinics c on c.id = t.clinic_id
           where t.horario_fixo and t.status = 'em_andamento' and t.professional_id is not null
             and c.status = 'ativa' and (%s::uuid is null or t.clinic_id = %s::uuid)
             and t.serie_ate + make_interval(days => t.intervalo_dias) <= %s + make_interval(days => t.intervalo_dias * %s)
           order by t.clinic_id""",
        (so_clinica, so_clinica, agora, JANELA),
    ).fetchall()
    total, clinicas = 0, {}
    for t in linhas:
        if t["clinic_id"] not in clinicas:
            clinicas[t["clinic_id"]] = S.carregar_clinica(conn, t["clinic_id"])
        with conn.transaction():
            total += renovar(conn, clinicas[t["clinic_id"]], t, agora)
    return total


def cancelar_futuras(conn, clinic_id: UUID, tratamento_id: UUID, agora: datetime) -> int:
    """Encerrou o tratamento com horário fixo: as sessões futuras saem da agenda, sem mensagem ao paciente."""
    ids = [r[0] for r in conn.execute(
        """update appointments set status = 'cancelada', cancel_reason = 'Tratamento encerrado'
           where clinic_id = %s and treatment_id = %s and status = any(%s) and starts_at > %s returning id""",
        (clinic_id, tratamento_id, list(T.ATIVOS_CONSULTA), agora)).fetchall()]
    if ids:
        conn.execute(
            """update outbound_messages set status = 'cancelada'
               where clinic_id = %s and appointment_id = any(%s) and status = 'agendada'""", (clinic_id, ids))
        for aid in ids:
            S._registrar(conn, clinic_id, aid, "recepcao", "cancelada", depois={"motivo": "Tratamento encerrado"})
    return len(ids)


def sincronizar_lembretes(conn, clinic_id: UUID, tratamento_id: UUID, agora: datetime | None = None) -> None:
    """Avisos desligados → cancela os lembretes pendentes das sessões; ligados → agenda os que faltam."""
    from app.mensagens.lembretes import agendar_lembrete  # import aqui para evitar import circular

    clinica = S.carregar_clinica(conn, clinic_id)
    agora = agora or relogio.agora()
    ligado = conn.execute("select avisos_paciente from treatments where id = %s", (tratamento_id,)).fetchone()[0]
    if not ligado:
        conn.execute(
            """update outbound_messages o set status = 'cancelada' from appointments a
               where a.id = o.appointment_id and a.treatment_id = %s and o.clinic_id = %s
                 and o.status = 'agendada' and o.kind = 'lembrete'""", (tratamento_id, clinic_id))
        return
    sem_lembrete = [r[0] for r in conn.execute(
        """select a.id from appointments a
           where a.clinic_id = %s and a.treatment_id = %s and a.status = any(%s) and a.starts_at > %s
             and not exists (select 1 from outbound_messages o where o.appointment_id = a.id and o.kind = 'lembrete'
                             and o.status <> 'cancelada')""",
        (clinic_id, tratamento_id, list(T.ATIVOS_CONSULTA), agora)).fetchall()]
    for aid in sem_lembrete:
        agendar_lembrete(conn, clinica, S.detalhar(conn, clinic_id, aid), agora)
