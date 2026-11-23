"""Etapa 30 (D117–D119): roda a consulta que a IA escreveu — só leitura e só a clínica de quem pergunta.

A segurança não depende da IA obedecer. São travas independentes:
  1. aqui no código: um único SELECT/WITH, sem comentários;
  2. transação SÓ-LEITURA (o banco recusa qualquer escrita);
  3. papel isis_leitura: só enxerga as visões do esquema "leitura" (migration 0032);
  4. as visões só mostram a clínica gravada numa tabela temporária da conexão ANTES de assumir o papel
     (o papel não lê nem escreve essa tabela). A clínica vem da sessão do usuário logado, nunca do texto;
  5. tempo máximo de 5 s e no máximo LIMITE linhas.
"""

import re
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import psycopg

LIMITE = 200
TEMPO_MAX = "5s"
_TABELA = "create temp table if not exists _isis_clinica (id uuid not null)"
_INICIO = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)


class ConsultaRecusada(ValueError):
    pass


def _conferir(sql: str) -> str:
    sql = (sql or "").strip().rstrip(";").strip()
    if not sql:
        raise ConsultaRecusada("Consulta vazia.")
    if len(sql) > 4000:
        raise ConsultaRecusada("Consulta grande demais.")
    if ";" in sql:
        raise ConsultaRecusada("Só uma consulta por vez (sem ';').")
    if "--" in sql or "/*" in sql:
        raise ConsultaRecusada("Sem comentários na consulta.")
    if not _INICIO.match(sql):
        raise ConsultaRecusada("Só consultas de leitura (SELECT ou WITH).")
    return sql


def _valor(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, UUID):
        return str(v)
    return v


def executar(conn, clinic_id: UUID, sql: str, fuso: str = "America/Sao_Paulo") -> dict:
    """Devolve {colunas, linhas, truncado}. Erro de SQL vira ConsultaRecusada com texto curto (a IA corrige e tenta de novo)."""
    sql = _conferir(sql)
    # Na rota, a conexão vem limpa (separada do pool) e a transação inteira é só-leitura.
    # Nos testes ela já está numa transação com dados de teste: vira um savepoint e vale a trava do papel.
    limpa = conn.info.transaction_status == psycopg.pq.TransactionStatus.IDLE
    if limpa:
        conn.execute(_TABELA)  # criar tabela não é permitido numa transação só-leitura: cria antes
        conn.commit()
    try:
        with conn.transaction():  # sempre desfeito abaixo (papel, clínica e configurações não vazam)
            if limpa:
                conn.execute("set transaction read only")  # gravar em tabela temporária continua permitido
            else:
                conn.execute(_TABELA)
            conn.execute("insert into pg_temp._isis_clinica (id) values (%s)", (clinic_id,))
            conn.execute("set local role isis_leitura")
            conn.execute("select set_config('search_path', 'leitura', true)")
            conn.execute("select set_config('TimeZone', %s, true)", (fuso,))
            conn.execute(f"set local statement_timeout = '{TEMPO_MAX}'")
            cur = conn.execute(f"select * from ({sql}) as q limit {LIMITE + 1}")
            colunas = [d.name for d in cur.description or []]
            linhas = [[_valor(v) for v in r] for r in cur.fetchall()]
            raise _Desfazer({"colunas": colunas, "linhas": linhas[:LIMITE], "truncado": len(linhas) > LIMITE})
    except _Desfazer as d:
        return d.resultado
    except psycopg.errors.QueryCanceled as e:
        raise ConsultaRecusada("A consulta demorou demais; simplifique.") from e
    except psycopg.errors.InsufficientPrivilege as e:
        raise ConsultaRecusada("Sem permissão: use só as tabelas descritas.") from e
    except psycopg.Error as e:
        msg = (getattr(e.diag, "message_primary", None) or type(e).__name__)[:200]
        raise ConsultaRecusada(f"Erro na consulta: {msg}") from e


class _Desfazer(Exception):
    """Sai do bloco de transação desfazendo tudo (papel, configurações) e levando o resultado."""

    def __init__(self, resultado: dict):
        self.resultado = resultado
