"""Transcrição de áudio do WhatsApp (Etapa 13B — D67).

- Usa a chave de transcrição da plataforma (TRANSCRICAO_* no .env; API compatível com OpenAI, padrão Whisper).
  Nem todo provedor das clínicas transcreve áudio, por isso a chave é da plataforma.
- Até TRANSCRICAO_MAX_S (2 min). O custo (US$ por minuto) entra no "Uso da IA" e no teto da clínica.
- Falhou ou não está configurada: devolve None e o WhatsApp pede para a pessoa escrever.
"""

import logging
import math
import time
from decimal import Decimal
from uuid import UUID

from openai import OpenAI
from psycopg.types.json import Jsonb

from app.config import get_settings
from app.ia import USER_AGENT, explicar_erro

log = logging.getLogger("isis.transcricao")


def configurada() -> bool:
    return bool(get_settings().transcricao_api_key)


def custo(segundos: int) -> Decimal:
    """Cobrança por minuto, arredondada para cima por segundo (como a maioria dos provedores)."""
    minutos = Decimal(max(1, segundos)) / Decimal(60)
    return (minutos * Decimal(str(get_settings().transcricao_usd_minuto))).quantize(Decimal("0.000001"))


def _segundos(dados: bytes, informado: int | None) -> int:
    # Sem a duração no aviso do WhatsApp: estima pelo tamanho (áudio do WhatsApp ≈ 2 KB por segundo)
    return informado if informado and informado > 0 else max(1, math.ceil(len(dados) / 2000))


def transcrever(conn, clinic_id: UUID, conversa_id: UUID, dados: bytes, mime: str | None, duracao_s: int | None) -> str | None:
    s = get_settings()
    if not s.transcricao_api_key:
        return None
    segundos = _segundos(dados, duracao_s)
    inicio = time.perf_counter()
    texto, erro = None, None
    try:
        cliente = OpenAI(api_key=s.transcricao_api_key, base_url=s.transcricao_base_url, timeout=60, max_retries=1,
                         default_headers={"User-Agent": USER_AGENT})
        r = cliente.audio.transcriptions.create(model=s.transcricao_modelo, language="pt",
                                                file=("audio.ogg", dados, mime or "audio/ogg"))
        texto = (getattr(r, "text", "") or "").strip() or None
    except Exception as e:  # noqa: BLE001 — nunca derruba o atendimento
        erro = explicar_erro(e)
        log.warning("falha na transcrição: %s", erro)
    conn.execute(
        """insert into agent_runs (clinic_id, conversation_id, input, tools, output, latency_ms, error,
                                   provider, model, origem, tipo, audio_segundos, custo_usd)
           values (%s, %s, '[áudio]', %s, %s, %s, %s, 'transcricao', %s, 'plataforma', 'transcricao', %s, %s)""",
        (clinic_id, conversa_id, Jsonb([]), texto or "", round((time.perf_counter() - inicio) * 1000), erro,
         s.transcricao_modelo, segundos, custo(segundos) if texto else None))
    return texto
