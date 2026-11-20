"""Etapas do CRM (RN-PN-02, RN-PN-05, RN-PN-09)."""

from uuid import UUID

from app.eventos import avisar

ETAPAS = ("novo_contato", "agendado", "confirmado", "cancelado")


def registrar(conn, clinic_id: UUID, patient_id: UUID, evento: str, ator: str, etapa: str | None = None) -> None:
    """Grava o último evento do paciente e, se `etapa` vier, move o card de coluna."""
    atual = conn.execute(
        "select crm_stage from patients where clinic_id = %s and id = %s for update", (clinic_id, patient_id)
    ).fetchone()
    if atual is None:
        return
    if etapa and etapa != atual[0]:
        conn.execute(
            """update patients set crm_stage = %s, stage_changed_at = now(), last_event = %s, last_activity_at = now()
               where id = %s""",
            (etapa, evento, patient_id),
        )
        conn.execute(
            """insert into crm_events (clinic_id, patient_id, from_stage, to_stage, event, actor_type)
               values (%s, %s, %s, %s, %s, %s)""",
            (clinic_id, patient_id, atual[0], etapa, evento, ator),
        )
    else:
        conn.execute("update patients set last_event = %s, last_activity_at = now() where id = %s", (evento, patient_id))
    avisar(conn, clinic_id, "crm", patient_id)


def etapa_apos_cancelar(conn, clinic_id: UUID, patient_id: UUID, agora) -> str:
    """Se o paciente ainda tem outra consulta ativa, ele continua em Agendados/Confirmado."""
    r = conn.execute(
        """select bool_or(status = 'confirmada'), count(*) from appointments
           where clinic_id = %s and patient_id = %s and status in ('agendada', 'confirmada') and starts_at > %s""",
        (clinic_id, patient_id, agora),
    ).fetchone()
    if r[1]:
        return "confirmado" if r[0] else "agendado"
    return "cancelado"
