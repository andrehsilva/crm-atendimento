"""Campanhas: mensagens escritas pela clínica e enviadas a muitos clientes (Etapa 14A — D69–D72).

- Ao criar, já entra na fila uma mensagem por cliente do público (texto pronto, com {nome} e {clinica} trocados).
- A fila manda espaçado (D70) e respeita a janela de silêncio e os limites por minuto/dia.
- Nunca para quem pediu PARAR (RN-DP-04). Cancelar tira da fila o que ainda não saiu.
"""

from datetime import datetime, timedelta
from uuid import UUID

from psycopg.rows import dict_row

from app.agenda.erros import AgendaError
from app.eventos import avisar

PUBLICOS = {
    "todos": "Todos os clientes",
    "ativos12m": "Atendidos nos últimos 12 meses",
    "com_consulta": "Com atendimento marcado",
}
INTERVALO_MEDIO_S = 32.5  # média de 20 a 45 s (D70), para estimar o tempo do envio

MODELOS = [  # D71: prontos para a clínica só ajustar
    {"id": "natal", "titulo": "Feliz Natal",
     "texto": "Olá, {nome}! 🎄 Toda a equipe da {clinica} deseja a você e à sua família um Natal cheio de paz e alegria. Boas festas!"},
    {"id": "ano_novo", "titulo": "Feliz Ano Novo",
     "texto": "Olá, {nome}! ✨ A {clinica} deseja um Ano Novo com muita saúde e muitos sorrisos. Obrigado pela confiança!"},
    {"id": "ferias", "titulo": "Aviso de férias",
     "texto": "Olá, {nome}! A {clinica} estará em férias coletivas de DD/MM a DD/MM. Voltamos a atender em DD/MM. Se precisar marcar, é só responder esta mensagem."},
]

_PUBLICO_SQL = {
    "todos": "true",
    "ativos12m": """exists(select 1 from appointments a where a.patient_id = p.id and a.status = 'realizada'
                           and a.starts_at >= now() - interval '12 months')""",
    "com_consulta": """exists(select 1 from appointments a where a.patient_id = p.id
                              and a.status in ('agendada', 'confirmada') and a.starts_at >= now())""",
}


def _destinatarios(conn, clinic_id: UUID, publico: str) -> list[dict]:
    if publico not in _PUBLICO_SQL:
        raise AgendaError("DADOS_INVALIDOS", "Público inválido.")
    return conn.cursor(row_factory=dict_row).execute(
        f"""select p.id, p.name from patients p
            where p.clinic_id = %s and p.phone is not null and not p.optout_disparos and {_PUBLICO_SQL[publico]}
            order by p.created_at""", (clinic_id,)).fetchall()  # noqa: S608 — trecho vem do dicionário fixo acima


def previa(conn, clinic_id: UUID, publico: str) -> dict:
    total = len(_destinatarios(conn, clinic_id, publico))
    return {"total": total, "minutos": round(total * INTERVALO_MEDIO_S / 60)}


def montar_texto(texto: str, nome: str | None, clinica: str) -> str:
    primeiro = (nome or "").split()[0] if (nome or "").strip() else ""
    t = texto.replace("{clinica}", clinica)
    # sem nome cadastrado: "Olá, {nome}!" vira "Olá!"
    return (t.replace(", {nome}", "").replace(" {nome}", "") if not primeiro else t).replace("{nome}", primeiro)


def criar(conn, clinic_id: UUID, *, titulo: str, texto: str, publico: str, enviar_em: datetime, autor: UUID | None,
          agora: datetime) -> dict:
    if enviar_em < agora - timedelta(minutes=5):
        raise AgendaError("DADOS_INVALIDOS", "Escolha uma data e hora a partir de agora.")
    nome_clinica = conn.execute("select name from clinics where id = %s", (clinic_id,)).fetchone()[0]
    lista = _destinatarios(conn, clinic_id, publico)
    if not lista:
        raise AgendaError("DADOS_INVALIDOS", "Ninguém recebe com esse público. Escolha outro.")
    cid = conn.execute(
        """insert into campaigns (clinic_id, titulo, texto, publico, enviar_em, total, criada_por)
           values (%s, %s, %s, %s, %s, %s, %s) returning id""",
        (clinic_id, titulo.strip(), texto.strip(), publico, enviar_em, len(lista), autor)).fetchone()[0]
    with conn.cursor() as cur:
        cur.executemany(
            """insert into outbound_messages (clinic_id, patient_id, kind, channel, body, scheduled_for, campaign_id)
               values (%s, %s, 'campanha', 'whatsapp', %s, %s, %s)""",
            [(clinic_id, p["id"], montar_texto(texto.strip(), p["name"], nome_clinica), enviar_em, cid) for p in lista])
    avisar(conn, clinic_id, "mensagens")
    return {"id": cid, "total": len(lista)}


def cancelar(conn, clinic_id: UUID, campanha_id: UUID) -> int:
    if not conn.execute("update campaigns set status = 'cancelada' where clinic_id = %s and id = %s and status = 'agendada' "
                        "returning id", (clinic_id, campanha_id)).fetchone():
        raise AgendaError("DADOS_INVALIDOS", "Campanha não encontrada ou já cancelada.")
    n = conn.execute("""update outbound_messages set status = 'cancelada', error = 'campanha cancelada'
                        where campaign_id = %s and status = 'agendada'""", (campanha_id,)).rowcount
    avisar(conn, clinic_id, "mensagens")
    return n


def listar(conn, clinic_id: UUID) -> list[dict]:
    return conn.cursor(row_factory=dict_row).execute(
        """select c.id, c.titulo, c.texto, c.publico, c.enviar_em, c.status, c.total, c.created_at,
                  count(o.id) filter (where o.status in ('enviada', 'entregue', 'lida')) as enviadas,
                  count(o.id) filter (where o.status = 'agendada') as na_fila,
                  count(o.id) filter (where o.status in ('falhou', 'cancelada')) as nao_enviadas
           from campaigns c left join outbound_messages o on o.campaign_id = c.id
           where c.clinic_id = %s group by c.id order by c.enviar_em desc limit 50""", (clinic_id,)).fetchall()
