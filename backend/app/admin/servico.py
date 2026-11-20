"""Admin geral da plataforma (D30, spec 07-B): criar e configurar clínicas, usuários e WhatsApp."""

import re
import unicodedata
from uuid import UUID

from psycopg import errors
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.agenda.erros import AgendaError
from app.auth.usuarios import criar_ou_ligar
from app.core.telefone import TelefoneInvalido, normalizar_telefone
from app.demo import ALMOCO, HORARIO
from app.segmentos import SEGMENTOS


def _cur(conn):
    return conn.cursor(row_factory=dict_row)


def slug_de(nome: str) -> str:
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = re.sub(r"^(clinica|consultorio|odontologia|espaco|studio)-", "", s) or s
    return s[:40] or "clinica"


def _slug_livre(conn, base: str) -> str:
    slug, n = base, 2
    while conn.execute("select 1 from clinics where slug = %s", (slug,)).fetchone():
        slug, n = f"{base}-{n}", n + 1
    return slug


def listar_clinicas(conn) -> list[dict]:
    return _cur(conn).execute(
        """select c.id, c.name, c.phone, c.slug, c.status, c.timezone, c.address, c.created_at,
                  coalesce(c.settings->>'nome_assistente', 'Ísis') as nome_assistente,
                  coalesce(c.settings->>'segmento', 'odontologia') as segmento,
                  w.session as whatsapp_sessao, w.status as whatsapp_status, w.phone as whatsapp_numero,
                  (select count(distinct m.conversation_id) from messages m
                     where m.clinic_id = c.id and m.created_at >= date_trunc('month', now())) as conversas_mes,
                  (select count(*) from clinic_users cu where cu.clinic_id = c.id and cu.active) as usuarios
           from clinics c left join whatsapp_instances w on w.clinic_id = c.id
           order by c.name"""
    ).fetchall()


def criar_clinica(conn, *, nome: str, telefone: str, fuso: str, endereco: str | None, nome_assistente: str,
                  admin_email: str, admin_nome: str | None, profissional: str | None,
                  segmento: str = "odontologia") -> dict:
    """Cria a clínica já pronta para usar: horários, procedimentos do segmento e o 1º admin (senha provisória)."""
    if segmento not in SEGMENTOS:
        raise AgendaError("DADOS_INVALIDOS", "Segmento desconhecido.")
    try:
        fone = normalizar_telefone(telefone)
    except TelefoneInvalido as e:
        raise AgendaError("TELEFONE_INVALIDO", str(e)) from e
    if conn.execute("select 1 from clinics where phone = %s", (fone,)).fetchone():
        raise AgendaError("DADOS_INVALIDOS", "Já existe uma clínica com esse telefone (o telefone é a chave da clínica).")
    slug = _slug_livre(conn, slug_de(nome))
    try:
        with conn.transaction():
            cid = conn.execute(
                """insert into clinics (name, phone, slug, timezone, address, settings)
                   values (%s, %s, %s, %s, %s, %s) returning id""",
                (nome.strip(), fone, slug, fuso, (endereco or "").strip() or None,
                 Jsonb({"nome_assistente": nome_assistente.strip() or "Ísis", "segmento": segmento})),
            ).fetchone()[0]
    except errors.UniqueViolation as e:
        raise AgendaError("DADOS_INVALIDOS", "Telefone ou endereço da página já em uso.") from e

    for wd, (ini, fim) in HORARIO.items():
        conn.execute("insert into clinic_hours (clinic_id, weekday, start_time, end_time) values (%s,%s,%s,%s)", (cid, wd, ini, fim))
    for wd in range(5):
        conn.execute("insert into clinic_breaks (clinic_id, weekday, start_time, end_time) values (%s,%s,%s,%s)", (cid, wd, *ALMOCO))
    servicos = [
        conn.execute(
            """insert into services (clinic_id, name, description, duration_min, bookable_by_ai)
               values (%s,%s,%s,%s,%s) returning id""", (cid, n, d, m, ia),
        ).fetchone()[0]
        for n, d, m, ia in SEGMENTOS[segmento].procedimentos
    ]
    if profissional and profissional.strip():
        pid = conn.execute(
            "insert into professionals (clinic_id, name, color) values (%s, %s, '#B85C74') returning id", (cid, profissional.strip())
        ).fetchone()[0]
        for sid in servicos:
            conn.execute("insert into professional_services (clinic_id, professional_id, service_id) values (%s,%s,%s)", (cid, pid, sid))

    _, senha = criar_ou_ligar(conn, admin_email, admin_nome, clinic_id=cid, papel="clinic_admin")
    return {"id": cid, "slug": slug, "admin_email": admin_email.strip().lower(), "senha_provisoria": senha}


def atualizar_clinica(conn, clinic_id: UUID, dados: dict) -> None:
    campos = {"name": dados.get("nome"), "address": dados.get("endereco"), "timezone": dados.get("fuso"),
              "status": dados.get("status")}
    for coluna, valor in campos.items():
        if valor is not None:
            conn.execute(f"update clinics set {coluna} = %s, updated_at = now() where id = %s", (valor, clinic_id))  # noqa: S608 — coluna vem da lista fixa acima
    novos = {}
    if dados.get("nome_assistente"):
        novos["nome_assistente"] = dados["nome_assistente"].strip()
    if dados.get("segmento"):
        novos["segmento"] = dados["segmento"]
    if novos:
        conn.execute("update clinics set settings = settings || %s where id = %s", (Jsonb(novos), clinic_id))


def usuarios_da_clinica(conn, clinic_id: UUID) -> list[dict]:
    return _cur(conn).execute(
        """select u.user_id as id, u.email, u.name as nome, cu.role as papel, cu.active and u.active as ativo,
                  u.must_change_password as senha_provisoria, cu.created_at
           from clinic_users cu join app_users u on u.user_id = cu.user_id
           where cu.clinic_id = %s order by u.name nulls last, u.email""",
        (clinic_id,),
    ).fetchall()


def auditar(conn, user_id: UUID, acao: str, clinic_id: UUID | None = None, detalhe: dict | None = None) -> None:
    conn.execute("insert into admin_audit (user_id, clinic_id, action, detail) values (%s, %s, %s, %s)",
                 (user_id, clinic_id, acao, Jsonb(detalhe or {})))
