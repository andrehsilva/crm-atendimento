"""Etapa 22 — Convênios (RN-CV, D92–D95).

O que não pode falhar fica aqui: quem precisa ser perguntado (RN-CV-02), conferência do nome contra a lista da
clínica (RN-CV-03) e o registro no cadastro (RN-CV-05). A Ísis só pergunta e repassa a resposta.
"""

import unicodedata
from uuid import UUID

from psycopg.rows import dict_row

from app.agenda.erros import AgendaError


def _norm(t: str) -> str:
    t = "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")
    return " ".join(t.replace("-", " ").split())


def listar(conn, clinic_id: UUID, so_ativos: bool = False) -> list[dict]:
    return conn.cursor(row_factory=dict_row).execute(
        "select id, name, active from clinic_insurances where clinic_id = %s" + (" and active" if so_ativos else "")
        + " order by lower(name)", (clinic_id,)).fetchall()


def perguntar_ligado(clinica: dict) -> bool:
    """A clínica pode desligar a pergunta (só atende particular). Padrão: ligada."""
    return (clinica.get("settings") or {}).get("perguntar_convenio", True) is not False


def precisa_perguntar(conn, clinica: dict, paciente: dict) -> bool:
    """RN-CV-02: só no primeiro contato — sem atendimento realizado e sem convênio registrado."""
    if not perguntar_ligado(clinica) or paciente.get("convenio"):
        return False
    return not conn.execute(
        "select exists(select 1 from appointments where clinic_id = %s and patient_id = %s and status = 'realizada')",
        (clinica["id"], paciente["id"])).fetchone()[0]


def achar(conn, clinic_id: UUID, nome: str) -> list[dict]:
    """Convênios ativos que batem com o nome dito (sem acento/maiúscula; "unimed" acha "Unimed Nacional")."""
    alvo = _norm(nome)
    if not alvo:
        return []
    ativos = listar(conn, clinic_id, so_ativos=True)
    exatos = [c for c in ativos if _norm(c["name"]) == alvo]
    if exatos:
        return exatos
    return [c for c in ativos if alvo in _norm(c["name"]) or _norm(c["name"]) in alvo]


def registrar(conn, clinic_id: UUID, patient_id: UUID, tipo: str, nome: str | None = None) -> dict:
    """Grava no cadastro. Com lista, o convênio precisa estar nela (RN-CV-03); sem lista, só "convênio" (RN-CV-04).
    Devolve {"ok": True, "rotulo": ...} ou {"ok": False, "motivo": ..., "aceitos": [...]}, sem gravar."""
    if tipo == "particular":
        conn.execute("update patients set convenio = 'particular', insurance_id = null where clinic_id = %s and id = %s",
                     (clinic_id, patient_id))
        return {"ok": True, "rotulo": "Particular"}
    if tipo != "convenio":
        raise AgendaError("DADOS_INVALIDOS", "Tipo deve ser 'particular' ou 'convenio'.")
    ativos = listar(conn, clinic_id, so_ativos=True)
    if not ativos:  # RN-CV-04: a clínica não tem lista → só "convênio"
        conn.execute("update patients set convenio = 'convenio', insurance_id = null where clinic_id = %s and id = %s",
                     (clinic_id, patient_id))
        return {"ok": True, "rotulo": "Convênio"}
    if not (nome or "").strip():
        return {"ok": False, "motivo": "qual_convenio", "aceitos": [c["name"] for c in ativos]}
    achados = achar(conn, clinic_id, nome)
    if len(achados) == 1:
        conn.execute("update patients set convenio = 'convenio', insurance_id = %s where clinic_id = %s and id = %s",
                     (achados[0]["id"], clinic_id, patient_id))
        return {"ok": True, "rotulo": achados[0]["name"]}
    if len(achados) > 1:
        return {"ok": False, "motivo": "mais_de_um", "aceitos": [c["name"] for c in achados]}
    return {"ok": False, "motivo": "nao_atende", "aceitos": [c["name"] for c in ativos]}


def rotulo(conn, paciente: dict) -> str | None:
    """Particular · nome do convênio · Convênio · None (não perguntado)."""
    if paciente.get("convenio") == "particular":
        return "Particular"
    if paciente.get("convenio") == "convenio":
        if paciente.get("insurance_id"):
            r = conn.execute("select name from clinic_insurances where id = %s", (paciente["insurance_id"],)).fetchone()
            if r:
                return r[0]
        return "Convênio"
    return None


# ---------------------------------------------------------------------------
# Configuração (administrador da clínica)
# ---------------------------------------------------------------------------
def criar(conn, clinic_id: UUID, nome: str) -> None:
    nome = " ".join((nome or "").split())
    if not nome:
        raise AgendaError("DADOS_INVALIDOS", "Escreva o nome do convênio.")
    existe = conn.execute("select id, active from clinic_insurances where clinic_id = %s and lower(trim(name)) = lower(%s)",
                          (clinic_id, nome)).fetchone()
    if existe and existe[1]:
        raise AgendaError("DADOS_INVALIDOS", "Esse convênio já está na lista.")
    if existe:  # estava desligado: religa
        conn.execute("update clinic_insurances set active = true, name = %s where id = %s", (nome, existe[0]))
        return
    conn.execute("insert into clinic_insurances (clinic_id, name) values (%s, %s)", (clinic_id, nome))


def mudar(conn, clinic_id: UUID, insurance_id: UUID, *, nome: str | None = None, ativo: bool | None = None) -> None:
    if not conn.execute("select 1 from clinic_insurances where clinic_id = %s and id = %s", (clinic_id, insurance_id)).fetchone():
        raise AgendaError("DADOS_INVALIDOS", "Convênio não encontrado.")
    if nome is not None:
        nome = " ".join(nome.split())
        if not nome:
            raise AgendaError("DADOS_INVALIDOS", "Escreva o nome do convênio.")
        if conn.execute("select 1 from clinic_insurances where clinic_id = %s and lower(trim(name)) = lower(%s) and id <> %s",
                        (clinic_id, nome, insurance_id)).fetchone():
            raise AgendaError("DADOS_INVALIDOS", "Esse convênio já está na lista.")
        conn.execute("update clinic_insurances set name = %s where id = %s", (nome, insurance_id))
    if ativo is not None:  # desligar não apaga: quem já tem esse convênio no cadastro continua com ele
        conn.execute("update clinic_insurances set active = %s where id = %s", (ativo, insurance_id))


def editar_paciente(conn, clinic_id: UUID, patient_id: UUID, convenio: str | None, insurance_id: UUID | None) -> None:
    """Recepção edita no cadastro (D94). convenio=None limpa (volta a "não perguntado")."""
    if convenio not in (None, "particular", "convenio"):
        raise AgendaError("DADOS_INVALIDOS", "Convênio inválido.")
    if insurance_id and (convenio != "convenio" or not conn.execute(
            "select 1 from clinic_insurances where clinic_id = %s and id = %s", (clinic_id, insurance_id)).fetchone()):
        raise AgendaError("DADOS_INVALIDOS", "Convênio não encontrado.")
    conn.execute("update patients set convenio = %s, insurance_id = %s where clinic_id = %s and id = %s",
                 (convenio, insurance_id, clinic_id, patient_id))
