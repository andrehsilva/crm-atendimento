"""Uso e custo da IA, teto mensal (Etapa 10B — D44, D45, D46).

- Cada resposta guarda tokens e o custo calculado com a tabela de preços do admin geral (preço da época).
- O valor é uma ESTIMATIVA: o oficial é o da conta da clínica no provedor.
- Teto mensal em US$ por clínica: aviso aos 80%; aos 100% a assistente pausa e a equipe assume (D45).
  Sem preço cadastrado para o modelo, o custo não é calculado — e o teto não consegue agir (a tela avisa).
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from psycopg.rows import dict_row

from app.ia import PROVEDORES, ConfigIA

AVISO_PCT = 80


def provedor_de_preco(provedor: str) -> str:
    """A IA da plataforma chama o provedor de "opencode-go"; na tabela de preços vale "opencode"."""
    return next((p for p in PROVEDORES if provedor == p or provedor.startswith(f"{p}-")), provedor)


def calcular_custo(conn, cfg: ConfigIA, entrada: int, saida: int, cache: int) -> Decimal | None:
    p = conn.execute("select entrada_usd, saida_usd, cache_usd from ai_prices where provider = %s and model = %s",
                     (provedor_de_preco(cfg.provedor), cfg.modelo)).fetchone()
    if not p:
        return None
    pe, ps, pc = p
    cache = min(cache, entrada)  # os tokens de cache já vêm dentro dos de entrada
    total = (entrada - cache) * pe + cache * (pc if pc is not None else pe) + saida * ps
    return (Decimal(total) / Decimal(1_000_000)).quantize(Decimal("0.000001"))


def tokens_da_resposta(r) -> tuple[int, int, int]:
    m = getattr(r, "metrics", None)
    if not m:
        return 0, 0, 0
    return int(m.input_tokens or 0), int(m.output_tokens or 0), int(m.cache_read_tokens or 0)


def _inicio_do_mes(conn, clinic_id: UUID) -> datetime:
    tz = conn.execute("select timezone from clinics where id = %s", (clinic_id,)).fetchone()[0]
    agora = datetime.now(ZoneInfo(tz))
    return agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def cotacao(conn) -> Decimal | None:
    return conn.execute("select cotacao_brl from platform_settings where id = 1").fetchone()[0]


def situacao(conn, clinic_id: UUID) -> dict:
    """Gasto do mês x teto. nivel: "ok", "aviso" (≥ 80%) ou "pausada" (≥ 100%)."""
    gasto = conn.execute("select coalesce(sum(custo_usd), 0) from agent_runs where clinic_id = %s and created_at >= %s",
                         (clinic_id, _inicio_do_mes(conn, clinic_id))).fetchone()[0]
    r = conn.execute("select teto_mensal_usd from clinic_ai where clinic_id = %s", (clinic_id,)).fetchone()
    teto = r[0] if r else None
    pct = float(gasto / teto * 100) if teto else None
    nivel = "ok" if pct is None or pct < AVISO_PCT else ("aviso" if pct < 100 else "pausada")
    return {"gasto_usd": float(gasto), "teto_usd": float(teto) if teto else None,
            "pct": round(pct, 1) if pct is not None else None, "nivel": nivel}


def pausada(conn, clinic_id: UUID) -> bool:
    return situacao(conn, clinic_id)["nivel"] == "pausada"


def salvar_teto(conn, clinic_id: UUID, teto: float | None) -> None:
    conn.execute(
        """insert into clinic_ai (clinic_id, teto_mensal_usd) values (%s, %s)
           on conflict (clinic_id) do update set teto_mensal_usd = excluded.teto_mensal_usd, updated_at = now()""",
        (clinic_id, teto))


def relatorio(conn, clinic_id: UUID) -> dict:
    """Tela "Uso da IA" da clínica: mês atual por dia, últimos 6 meses e modelos sem preço."""
    cur = conn.cursor(row_factory=dict_row)
    tz = conn.execute("select timezone from clinics where id = %s", (clinic_id,)).fetchone()[0]
    inicio = _inicio_do_mes(conn, clinic_id)
    dias = cur.execute(
        """select (created_at at time zone %s)::date as dia, count(*) filter (where tipo = 'resposta') as respostas,
                  coalesce(sum(audio_segundos), 0) as audio_segundos,
                  coalesce(sum(tokens_entrada), 0) as tokens_entrada, coalesce(sum(tokens_saida), 0) as tokens_saida,
                  coalesce(sum(custo_usd), 0)::float as custo_usd
           from agent_runs where clinic_id = %s and created_at >= %s group by 1 order by 1 desc""",
        (tz, clinic_id, inicio)).fetchall()
    meses = cur.execute(
        """select to_char(date_trunc('month', created_at at time zone %s), 'YYYY-MM') as mes, count(*) filter (where tipo = 'resposta') as respostas,
                  coalesce(sum(tokens_entrada), 0) + coalesce(sum(tokens_saida), 0) as tokens,
                  coalesce(sum(custo_usd), 0)::float as custo_usd
           from agent_runs where clinic_id = %s and created_at >= %s - interval '5 months'
           group by 1 order by 1 desc""",
        (tz, clinic_id, inicio)).fetchall()
    sem_preco = cur.execute(
        """select distinct provider, model from agent_runs
           where clinic_id = %s and created_at >= %s and model is not null and custo_usd is null and error is null""",
        (clinic_id, inicio)).fetchall()
    c = cotacao(conn)
    return {"situacao": situacao(conn, clinic_id), "cotacao_brl": float(c) if c else None,
            "dias": dias, "meses": meses, "sem_preco": sem_preco}


# ---------------------------------------------------------------------------
# Admin geral: preços, cotação e uso de todas as clínicas
# ---------------------------------------------------------------------------
def precos(conn) -> list[dict]:
    return conn.cursor(row_factory=dict_row).execute(
        """select provider, model, entrada_usd::float, saida_usd::float, cache_usd::float, updated_at
           from ai_prices order by provider, model""").fetchall()


def salvar_preco(conn, provedor: str, modelo: str, entrada: float, saida: float, cache: float | None) -> None:
    conn.execute(
        """insert into ai_prices (provider, model, entrada_usd, saida_usd, cache_usd) values (%s, %s, %s, %s, %s)
           on conflict (provider, model) do update set entrada_usd = excluded.entrada_usd, saida_usd = excluded.saida_usd,
             cache_usd = excluded.cache_usd, updated_at = now()""",
        (provedor, modelo.strip(), entrada, saida, cache))


def apagar_preco(conn, provedor: str, modelo: str) -> None:
    conn.execute("delete from ai_prices where provider = %s and model = %s", (provedor, modelo))


def salvar_cotacao(conn, valor: float | None) -> None:
    conn.execute("update platform_settings set cotacao_brl = %s, updated_at = now() where id = 1", (valor,))
