"""Custo do WhatsApp oficial (Etapa 36E, D131).

A Meta diz, no aviso de enviada/entregue de cada mensagem, a categoria cobrada (marketing, utility, service…) e se é
cobrável. Guardamos uma linha por mensagem (meta_cobrancas) e mostramos o gasto **estimado** do mês: preço da tabela
(platform_settings, editável pelo dono da plataforma) × mensagens, descontando as grátis de atendimento do mês.
Quem paga é a clínica, direto para a Meta; aqui é só para ela acompanhar.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.db import pool

log = logging.getLogger("isis.meta")

ROTULO = {"service": "Atendimento", "utility": "Utilidade", "marketing": "Marketing", "authentication": "Autenticação"}


def registrar(conn, clinic_id: UUID, cobrancas: list[tuple[str, str, bool]]) -> int:
    """Uma linha por mensagem (o mesmo aviso pode chegar duas vezes: enviada e entregue)."""
    n = 0
    for wamid, categoria, cobravel in cobrancas:
        n += conn.execute(
            """insert into meta_cobrancas (clinic_id, wamid, categoria, cobravel) values (%s, %s, %s, %s)
               on conflict (clinic_id, wamid) do nothing""", (clinic_id, wamid, categoria[:40], cobravel)).rowcount
    return n


def processar(clinic_id: UUID, cobrancas: list[tuple[str, str, bool]]) -> None:
    """Chamado em segundo plano pelo webhook. Nunca levanta erro."""
    try:
        with pool().connection() as conn:
            registrar(conn, clinic_id, cobrancas)
            conn.commit()
    except Exception:  # noqa: BLE001
        log.exception("falha ao registrar cobrança da Meta")


def precos(conn) -> tuple[dict, int, Decimal | None]:
    r = conn.execute("select meta_precos_usd, meta_servico_gratis, cotacao_brl from platform_settings where id = 1").fetchone()
    return (r[0] or {}), int(r[1] or 0), r[2]


def salvar_precos(conn, valores: dict[str, float], gratis: int) -> None:
    conn.execute("update platform_settings set meta_precos_usd = %s::jsonb, meta_servico_gratis = %s, updated_at = now() where id = 1",
                 (json.dumps(valores), gratis))


def do_mes(conn, clinic_id: UUID, agora: datetime) -> dict:
    """Mensagens cobráveis do mês (no fuso da clínica) por categoria e o gasto estimado."""
    tz = conn.execute("select timezone from clinics where id = %s", (clinic_id,)).fetchone()[0]
    inicio = conn.execute("select date_trunc('month', %s::timestamptz at time zone %s) at time zone %s",
                          (agora, tz, tz)).fetchone()[0]
    contagem = dict(conn.execute(
        """select categoria, count(*) from meta_cobrancas
           where clinic_id = %s and cobravel and criado_em >= %s group by 1""", (clinic_id, inicio)).fetchall())
    tabela, gratis, cotacao = precos(conn)
    linhas, total = [], Decimal(0)
    for cat in sorted(set(contagem) | {"service", "utility", "marketing"}, key=lambda c: list(ROTULO).index(c) if c in ROTULO else 9):
        n = int(contagem.get(cat, 0))
        cobradas = max(0, n - gratis) if cat == "service" else n
        preco = Decimal(str(tabela.get(cat, tabela.get("utility", 0))))
        custo = preco * cobradas
        total += custo
        linhas.append({"categoria": cat, "rotulo": ROTULO.get(cat, cat), "mensagens": n, "cobradas": cobradas,
                       "preco_usd": float(preco), "custo_usd": float(round(custo, 4))})
    return {"inicio": inicio, "linhas": linhas, "gratis_atendimento": gratis, "total_usd": float(round(total, 4)),
            "total_brl": float(round(total * cotacao, 2)) if cotacao else None, "cotacao_brl": float(cotacao) if cotacao else None}
