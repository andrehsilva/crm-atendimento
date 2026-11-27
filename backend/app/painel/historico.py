"""Etapa 35 (D130): tela Mensagens por período e por cliente, e resumo de cada disparo em massa.

- Sem cliente escolhido: a fila (o que ainda vai sair) aparece sempre; o resto só dos últimos N dias.
- Com cliente escolhido: tudo o que já foi mandado para ele, de qualquer data.
- Resumo: um cartão por campanha e um para os aniversários do período (enviadas · entregues · falharam · na fila).
"""

from datetime import datetime, timedelta
from uuid import UUID

from psycopg.rows import dict_row

PERIODOS = (7, 30, 90)
LIMITE = 500

_SELECT = """
    select o.id, o.kind, o.channel, o.body, o.status, o.scheduled_for, o.sent_at, o.created_at, o.error,
           p.name as paciente, p.phone as telefone, o.appointment_id, o.patient_id, o.campaign_id,
           c.titulo as campanha
    from outbound_messages o
    join patients p on p.id = o.patient_id
    left join campaigns c on c.id = o.campaign_id
    where o.clinic_id = %s"""

# quando a mensagem "aconteceu": saiu (sent_at) ou, se não saiu, quando estava marcada para sair
_QUANDO = "coalesce(o.sent_at, o.scheduled_for, o.created_at)"


def _desde(dias: int, agora: datetime) -> datetime:
    return agora - timedelta(days=dias if dias in PERIODOS else PERIODOS[0])


def listar(conn, clinic_id: UUID, *, agora: datetime, dias: int = 7, patient_id: UUID | None = None,
           tipo: str | None = None) -> list[dict]:
    sql, params = _SELECT, [clinic_id]
    if patient_id:
        sql += " and o.patient_id = %s"
        params.append(patient_id)
    else:
        sql += f" and (o.status = 'agendada' or {_QUANDO} >= %s)"
        params.append(_desde(dias, agora))
    if tipo:
        sql += " and o.kind = %s"
        params.append(tipo)
    sql += f" order by {_QUANDO} desc limit %s"
    params.append(LIMITE)
    return conn.cursor(row_factory=dict_row).execute(sql, params).fetchall()


def resumo(conn, clinic_id: UUID, *, agora: datetime, dias: int = 7) -> list[dict]:
    """Disparos em massa do período: cada campanha e, juntos, os aniversários."""
    linhas = conn.cursor(row_factory=dict_row).execute(
        f"""select case when o.kind = 'campanha' then 'campanha' else 'aniversario' end as tipo,
                   o.campaign_id, max(c.titulo) as titulo,
                   min({_QUANDO}) as inicio, max({_QUANDO}) as fim,
                   count(*) as total,
                   count(*) filter (where o.status in ('enviada', 'entregue', 'lida')) as enviadas,
                   count(*) filter (where o.status in ('entregue', 'lida')) as entregues,
                   count(*) filter (where o.status = 'falhou') as falharam,
                   count(*) filter (where o.status = 'agendada') as na_fila,
                   count(*) filter (where o.status = 'cancelada') as canceladas
            from outbound_messages o left join campaigns c on c.id = o.campaign_id
            where o.clinic_id = %s and o.kind in ('campanha', 'aniversario')
              and (o.status = 'agendada' or {_QUANDO} >= %s)
            group by 1, 2
            order by max({_QUANDO}) desc""",
        (clinic_id, _desde(dias, agora)),
    ).fetchall()
    for r in linhas:
        if r["tipo"] == "aniversario":
            r["titulo"] = "Aniversários"
        elif not r["titulo"]:
            r["titulo"] = "Campanha"
    return linhas
