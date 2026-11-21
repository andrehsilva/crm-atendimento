"""Configuração inicial obrigatória — "Primeiros passos" (Etapa 10C, D51–D54).

As etapas são conferidas nos DADOS da clínica (não numa lista marcada à mão): se está no banco, está pronto.
- Enquanto `clinics.configurada_em` for vazio, o painel mostra só o passo a passo (D52).
- Concluída, nunca trava de novo: o que faltar depois vira aviso (D54).
"""

from dataclasses import dataclass
from uuid import UUID

from psycopg.types.json import Jsonb

from app import ia


@dataclass
class Etapa:
    codigo: str
    titulo: str
    ok: bool
    falta: str | None  # o que ainda falta, em português simples


def _settings(conn, clinic_id: UUID) -> tuple[str, str | None, dict]:
    nome, endereco, cfg = conn.execute("select name, address, settings from clinics where id = %s", (clinic_id,)).fetchone()
    return nome, endereco, cfg or {}


def _ia_ok(conn, clinic_id: UUID) -> tuple[bool, str | None]:
    atual = ia.config_da_clinica(conn, clinic_id)
    if atual is None:
        return False, "Cadastre a chave de IA da clínica."
    if atual.origem == "plataforma":
        return True, None  # liberada pelo admin geral (D46)
    testada = conn.execute("select verificada_em is not null from clinic_ai where clinic_id = %s", (clinic_id,)).fetchone()
    return (True, None) if testada and testada[0] else (False, 'Clique em "Testar conexão" com a chave salva.')


def etapas(conn, clinic_id: UUID) -> list[Etapa]:
    nome, endereco, cfg = _settings(conn, clinic_id)
    faltas_clinica = [r for r, ok in (("nome", bool((nome or "").strip())), ("endereço", bool((endereco or "").strip())),
                                      ("telefone de urgência", bool(cfg.get("telefone_urgencia"))),
                                      ("segmento", bool(cfg.get("segmento")))) if not ok]
    faltas_assist = [r for r, ok in (("nome", bool((cfg.get("nome_assistente") or "").strip())),
                                     ("forma de tratamento", bool(cfg.get("tratamento")))) if not ok]
    aparencia = bool(cfg.get("cor") or cfg.get("aparencia_confirmada"))
    horarios = conn.execute("select exists(select 1 from clinic_hours where clinic_id = %s)", (clinic_id,)).fetchone()[0]
    equipe = conn.execute(
        """select exists(select 1 from professional_services ps
                         join professionals p on p.id = ps.professional_id and p.active
                         join services s on s.id = ps.service_id and s.active
                         where ps.clinic_id = %s)""", (clinic_id,)).fetchone()[0]
    ia_ok, ia_falta = _ia_ok(conn, clinic_id)

    def falta(itens: list[str]) -> str | None:
        return f"Falta: {', '.join(itens)}." if itens else None

    return [
        Etapa("clinica", "Dados da clínica", not faltas_clinica, falta(faltas_clinica)),
        Etapa("assistente", "Assistente", not faltas_assist, falta(faltas_assist)),
        Etapa("aparencia", "Aparência", aparencia, None if aparencia else "Escolha a cor ou confirme a cor padrão."),
        Etapa("horarios", "Horários", horarios, None if horarios else "Cadastre pelo menos um dia de atendimento."),
        Etapa("equipe", "Serviços e equipe", equipe,
              None if equipe else "Cadastre um procedimento e um profissional que faça esse procedimento."),
        Etapa("ia", "Inteligência artificial", ia_ok, ia_falta),
    ]


def concluida(conn, clinic_id: UUID) -> bool:
    return conn.execute("select configurada_em is not null from clinics where id = %s", (clinic_id,)).fetchone()[0]


def estado(conn, clinic_id: UUID) -> dict:
    lista = etapas(conn, clinic_id)
    return {"concluida": concluida(conn, clinic_id), "pode_concluir": all(e.ok for e in lista),
            "etapas": [e.__dict__ for e in lista]}


def pendencias(conn, clinic_id: UUID) -> list[str]:
    return [e.titulo for e in etapas(conn, clinic_id) if not e.ok]


def confirmar_aparencia(conn, clinic_id: UUID) -> None:
    conn.execute("update clinics set settings = settings || %s where id = %s", (Jsonb({"aparencia_confirmada": True}), clinic_id))


def concluir(conn, clinic_id: UUID) -> list[str]:
    """Marca como concluída se tudo estiver pronto. Devolve o que falta (vazio = concluiu)."""
    faltando = pendencias(conn, clinic_id)
    if not faltando:
        conn.execute("update clinics set configurada_em = coalesce(configurada_em, now()) where id = %s", (clinic_id,))
    return faltando
