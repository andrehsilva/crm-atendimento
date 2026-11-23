"""Tratamentos em andamento (Etapa 21, RN-TR). Toda a equipe da clínica vê e mexe (recepção e admin)."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app import horario_fixo, segmentos
from app import tratamentos as T
from app.agenda import servico
from app.agenda.erros import AgendaError
from app.auth.acesso import acesso
from app.core import relogio
from app.db import get_conn
from app.eventos import avisar

router = APIRouter(prefix="/api/clinics/{clinic_id}", tags=["tratamentos"], dependencies=[Depends(acesso)])


def _paciente(conn, clinic_id: UUID, patient_id: UUID) -> dict:
    r = conn.execute("select id, name from patients where clinic_id = %s and id = %s", (clinic_id, patient_id)).fetchone()
    if not r:
        raise AgendaError("DADOS_INVALIDOS", "Paciente não encontrado.")
    return {"id": r[0], "name": r[1]}


def _do_paciente(conn, clinic_id: UUID, patient_id: UUID) -> dict:
    cfg = conn.execute("select settings from clinics where id = %s", (clinic_id,)).fetchone()[0]
    return {"tratamentos": T.do_paciente(conn, clinic_id, patient_id),
            "tags": T.tags(conn, clinic_id, [patient_id]).get(patient_id, []),
            "avisos_padrao": segmentos.avisos_tratamento(cfg)}  # D107: padrão do "manda lembrete" ao abrir


def _mudou(conn, clinic_id: UUID, t: dict) -> dict:
    avisar(conn, clinic_id, "crm", t["patient_id"])
    return _do_paciente(conn, clinic_id, t["patient_id"])


@router.get("/patients/{patient_id}/tratamentos", summary="Tratamentos e tags do paciente")
def listar(clinic_id: UUID, patient_id: UUID, conn=Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    _paciente(conn, clinic_id, patient_id)
    return _do_paciente(conn, clinic_id, patient_id)


class SessoesAoAbrir(BaseModel):
    """Etapa 26: já marcar as sessões ao abrir. sessoes = None → horário fixo, sem data para terminar (D105)."""
    inicio: datetime
    sessoes: int | None = Field(None, ge=2, le=servico.SERIE_MAX)


class NovoTratamento(BaseModel):
    service_id: UUID
    professional_id: UUID | None = None
    sessoes_previstas: int | None = Field(None, ge=1, le=100)
    intervalo_dias: int | None = Field(None, ge=1, le=365)
    orientacao: str | None = Field(None, max_length=300)
    avisos_paciente: bool | None = None  # None = padrão do tipo de clínica (D107)
    serie: SessoesAoAbrir | None = None


@router.post("/patients/{patient_id}/tratamentos", status_code=201, summary="Abrir tratamento (e, se pedido, marcar as sessões)")
def criar(clinic_id: UUID, patient_id: UUID, body: NovoTratamento, conn=Depends(get_conn)):
    clinica = servico.carregar_clinica(conn, clinic_id)
    _paciente(conn, clinic_id, patient_id)
    dados = body.model_dump(exclude={"serie"})
    if dados["avisos_paciente"] is None:
        dados["avisos_paciente"] = segmentos.avisos_tratamento(clinica["settings"])
    if body.serie:
        if not body.professional_id:
            raise AgendaError("DADOS_INVALIDOS", "Escolha o profissional das sessões.")
        dados["intervalo_dias"] = dados["intervalo_dias"] or 7
    resultado = None
    with conn.transaction():  # savepoint: se nenhuma data couber, o tratamento também não fica
        t = T.criar(conn, clinic_id, patient_id, **dados)
        horario_fixo.sincronizar_lembretes(conn, clinic_id, t["id"])  # consultas já marcadas que viraram sessões
        if body.serie:
            resultado = horario_fixo.marcar_ao_abrir(conn, clinic_id, t["id"], inicio=body.serie.inicio,
                                                     sessoes=body.serie.sessoes)
    if resultado:
        avisar(conn, clinic_id, "agenda")
    saida = _mudou(conn, clinic_id, t)
    if resultado:
        saida["serie"] = {"marcadas": len(resultado["marcadas"]),
                          "falhas": [{"inicio": f["inicio"], "motivo": f["motivo"]} for f in resultado["falhas"]]}
    return saida


class EdicaoTratamento(BaseModel):
    professional_id: UUID | None = None
    sessoes_previstas: int | None = Field(None, ge=1, le=100)
    intervalo_dias: int | None = Field(None, ge=1, le=365)
    orientacao: str | None = Field(None, max_length=300)
    avisos_paciente: bool | None = None
    horario_fixo: Literal[False] | None = None  # só desligar (parar de renovar)


@router.patch("/tratamentos/{tratamento_id}", summary="Editar tratamento aberto")
def editar(clinic_id: UUID, tratamento_id: UUID, body: EdicaoTratamento, conn=Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    dados = body.model_dump(exclude_unset=True)
    t = T.editar(conn, clinic_id, tratamento_id, dados)
    if "avisos_paciente" in dados:
        horario_fixo.sincronizar_lembretes(conn, clinic_id, tratamento_id)
        avisar(conn, clinic_id, "mensagens")
    return _mudou(conn, clinic_id, t)


class Espera(BaseModel):
    motivo: Literal["protetico", "exame", "cicatrizacao", "outro"]
    motivo_texto: str | None = Field(None, max_length=120)
    previsao: date | None = None


@router.post("/tratamentos/{tratamento_id}/aguardar", summary="Pôr em espera (a Ísis não marca a próxima sessão)")
def aguardar(clinic_id: UUID, tratamento_id: UUID, body: Espera, conn=Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    t = T.aguardar(conn, clinic_id, tratamento_id, motivo_espera=body.motivo, motivo_texto=body.motivo_texto,
                   previsao=body.previsao)
    return _mudou(conn, clinic_id, t)


@router.get("/tratamentos/{tratamento_id}/retomar", summary="Texto sugerido da mensagem de retomada")
def previa_retomar(clinic_id: UUID, tratamento_id: UUID, conn=Depends(get_conn)):
    clinica = servico.carregar_clinica(conn, clinic_id)
    t = T.obter(conn, clinic_id, tratamento_id)
    nome = _paciente(conn, clinic_id, t["patient_id"])["name"]
    tem_whatsapp = conn.execute("select 1 from whatsapp_instances where clinic_id = %s and enabled", (clinic_id,)).fetchone()
    return {"texto": T.texto_retomar(clinica, t, nome), "tem_whatsapp": bool(tem_whatsapp)}


class Retomada(BaseModel):
    texto: str | None = Field(None, max_length=1000)
    avisar_paciente: bool = True


@router.post("/tratamentos/{tratamento_id}/retomar", summary="Retomar (e chamar o paciente para marcar, D88)")
def retomar(clinic_id: UUID, tratamento_id: UUID, body: Retomada, conn=Depends(get_conn)):
    clinica = servico.carregar_clinica(conn, clinic_id)
    t = T.retomar(conn, clinica, tratamento_id, texto=body.texto, avisar_paciente=body.avisar_paciente)
    if body.avisar_paciente:
        avisar(conn, clinic_id, "mensagens")
    return _mudou(conn, clinic_id, t)


class Encerramento(BaseModel):
    status: Literal["concluido", "interrompido"]
    volta_em: date | None = None


@router.post("/tratamentos/{tratamento_id}/encerrar", summary="Concluir (com 'volta em') ou interromper")
def encerrar(clinic_id: UUID, tratamento_id: UUID, body: Encerramento, conn=Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    t = T.encerrar(conn, clinic_id, tratamento_id, status=body.status, volta_em=body.volta_em)
    if t["horario_fixo"]:  # Etapa 26: horário fixo encerrado → sessões futuras saem da agenda
        if horario_fixo.cancelar_futuras(conn, clinic_id, tratamento_id, relogio.agora()):
            avisar(conn, clinic_id, "agenda")
    return _mudou(conn, clinic_id, t)
