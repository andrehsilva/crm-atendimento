"""Observações do cliente (Etapa 9C, D48) e link da pasta do Google Drive (D49).

- Histórico: cada nota guarda data/hora e quem escreveu. Texto com formatação simples em Markdown
  (**negrito**, *itálico*, "- " lista, [link](https://...)); o painel desenha sem HTML cru.
- Quem escreveu edita e apaga a sua; o admin da clínica (ou o super admin) apaga qualquer uma.
- Notas são internas da equipe: a assistente não lê.
- Drive: só o link (sem integração); aceita apenas https://drive.google.com/...
"""

import re
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from app.agenda.erros import AgendaError
from app.auth.acesso import acesso, usuario_da_requisicao
from app.db import get_conn
from app.eventos import avisar

router = APIRouter(prefix="/api/clinics/{clinic_id}/patients/{patient_id}", tags=["observações"],
                   dependencies=[Depends(acesso)])

DRIVE_RE = re.compile(r"^https://drive\.google\.com/\S*$")
ADMINS = ("clinic_admin", "super_admin")


class Nota(BaseModel):
    texto: str = Field(max_length=5000)


class Drive(BaseModel):
    url: str | None = Field(None, max_length=500)


def _paciente(conn, clinic_id: UUID, patient_id: UUID) -> None:
    if not conn.execute("select 1 from patients where clinic_id = %s and id = %s", (clinic_id, patient_id)).fetchone():
        raise AgendaError("DADOS_INVALIDOS", "Paciente não encontrado.")


def _texto(t: str) -> str:
    t = t.strip()
    if not t:
        raise AgendaError("DADOS_INVALIDOS", "Escreva a observação antes de salvar.")
    return t


def _nota(conn, clinic_id: UUID, patient_id: UUID, nota_id: UUID) -> dict:
    n = conn.cursor(row_factory=dict_row).execute(
        "select id, author_id from patient_notes where id = %s and clinic_id = %s and patient_id = %s",
        (nota_id, clinic_id, patient_id)).fetchone()
    if not n:
        raise AgendaError("DADOS_INVALIDOS", "Observação não encontrada.")
    return n


@router.get("/observacoes", summary="Histórico de observações e pasta do Drive")
def listar(clinic_id: UUID, patient_id: UUID, request: Request, conn=Depends(get_conn)):
    _paciente(conn, clinic_id, patient_id)
    u = usuario_da_requisicao(request)
    admin = u.papel(clinic_id) in ADMINS
    notas = conn.cursor(row_factory=dict_row).execute(
        """select id, body as texto, author_name as autor, author_id, created_at as criado_em,
                  case when updated_at > created_at + interval '1 second' then updated_at end as editado_em
           from patient_notes where clinic_id = %s and patient_id = %s order by created_at desc""",
        (clinic_id, patient_id)).fetchall()
    for n in notas:
        minha = n.pop("author_id") == u.id
        n["pode_editar"] = minha
        n["pode_apagar"] = minha or admin
    drive = conn.execute("select drive_url from patients where id = %s", (patient_id,)).fetchone()[0]
    return {"drive_url": drive, "notas": notas}


@router.post("/observacoes", summary="Nova observação", status_code=201)
def criar(clinic_id: UUID, patient_id: UUID, body: Nota, request: Request, conn=Depends(get_conn)):
    _paciente(conn, clinic_id, patient_id)
    u = usuario_da_requisicao(request)
    conn.execute(
        """insert into patient_notes (clinic_id, patient_id, author_id, author_name, body, created_at, updated_at)
           values (%s, %s, %s, %s, %s, clock_timestamp(), clock_timestamp())""",
        (clinic_id, patient_id, u.id, u.nome or u.email, _texto(body.texto)))
    avisar(conn, clinic_id, "crm", patient_id)
    return listar(clinic_id, patient_id, request, conn)


@router.patch("/observacoes/{nota_id}", summary="Corrigir a própria observação")
def editar(clinic_id: UUID, patient_id: UUID, nota_id: UUID, body: Nota, request: Request, conn=Depends(get_conn)):
    n = _nota(conn, clinic_id, patient_id, nota_id)
    if n["author_id"] != usuario_da_requisicao(request).id:
        raise AgendaError("SEM_ACESSO", "Só quem escreveu pode corrigir esta observação.")
    conn.execute("update patient_notes set body = %s, updated_at = clock_timestamp() where id = %s", (_texto(body.texto), nota_id))
    return listar(clinic_id, patient_id, request, conn)


@router.delete("/observacoes/{nota_id}", summary="Apagar observação (a própria; o admin apaga qualquer uma)")
def apagar(clinic_id: UUID, patient_id: UUID, nota_id: UUID, request: Request, conn=Depends(get_conn)):
    n = _nota(conn, clinic_id, patient_id, nota_id)
    u = usuario_da_requisicao(request)
    if n["author_id"] != u.id and u.papel(clinic_id) not in ADMINS:
        raise AgendaError("SEM_ACESSO", "Só quem escreveu ou o administrador da clínica pode apagar esta observação.")
    conn.execute("delete from patient_notes where id = %s", (nota_id,))
    avisar(conn, clinic_id, "crm", patient_id)
    return listar(clinic_id, patient_id, request, conn)


@router.put("/drive", summary="Link da pasta do Google Drive (vazio remove)")
def salvar_drive(clinic_id: UUID, patient_id: UUID, body: Drive, request: Request, conn=Depends(get_conn)):
    _paciente(conn, clinic_id, patient_id)
    url = (body.url or "").strip() or None
    if url and not DRIVE_RE.match(url):
        raise AgendaError("DADOS_INVALIDOS", "Cole um link do Google Drive (começa com https://drive.google.com/).")
    conn.execute("update patients set drive_url = %s where clinic_id = %s and id = %s", (url, clinic_id, patient_id))
    avisar(conn, clinic_id, "crm", patient_id)
    return listar(clinic_id, patient_id, request, conn)
