"""Relatórios em Excel (Etapa 15A). Só o administrador da clínica baixa; cada download fica registrado (D73)."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from psycopg.types.json import Jsonb

from app import relatorios as R
from app.agenda.erros import AgendaError
from app.auth.acesso import acesso, exigir_admin_clinica
from app.db import get_conn

router = APIRouter(prefix="/api/clinics/{clinic_id}/relatorios", tags=["relatórios"], dependencies=[Depends(acesso)])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/{tipo}.xlsx", summary="Baixar relatório em Excel")
def baixar(clinic_id: UUID, tipo: str, request: Request, de: date | None = None, ate: date | None = None,
           profissional: UUID | None = None, meses: int = Query(6, ge=3, le=24), conn=Depends(get_conn)):
    u = exigir_admin_clinica(request, clinic_id)
    if tipo not in R.TIPOS:
        raise AgendaError("DADOS_INVALIDOS", "Relatório desconhecido.")
    hoje = date.today()
    de, ate = de or hoje.replace(day=1), ate or hoje
    if ate < de or (ate - de).days > 731:
        raise AgendaError("DADOS_INVALIDOS", "Escolha um período de até 2 anos, com o fim depois do início.")
    if profissional and not conn.execute("select 1 from professionals where clinic_id = %s and id = %s",
                                         (clinic_id, profissional)).fetchone():
        raise AgendaError("PROFISSIONAL_NAO_ENCONTRADO", "Profissional não encontrado.")
    dados, nome = R.gerar(conn, clinic_id, tipo, de=de, ate=ate, prof=profissional, meses=meses)
    filtros = {"de": str(de), "ate": str(ate), "profissional": str(profissional) if profissional else None, "meses": meses}
    conn.execute("insert into report_exports (clinic_id, user_id, tipo, filtros) values (%s, %s, %s, %s)",
                 (clinic_id, u.id, tipo, Jsonb(filtros)))
    return Response(dados, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{nome}"',
                                                     "Cache-Control": "no-store"})
