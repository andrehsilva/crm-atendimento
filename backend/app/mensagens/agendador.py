"""Roda em segundo plano dentro do backend: a cada 30 s gera os aniversários do dia, envia a fila vencida e os
resumos do dia dos profissionais (Etapa 23)."""

import logging
import threading

from app.core import relogio
from app.db import pool
from app.mensagens.envio import enviar_pendentes
from app.mensagens.lembretes import gerar_aniversarios
from app.mensagens.resumo_dia import enviar_resumos

log = logging.getLogger("isis.agendador")
INTERVALO_S = 30

_rodando = threading.Lock()


def rodada() -> dict:
    """Uma passada completa. Se outra já está rodando (ex.: botão do relógio de teste), não roda junto."""
    if not _rodando.acquire(blocking=False):
        return {"ok": False, "motivo": "já existe uma rodada em andamento"}
    try:
        agora = relogio.agora()
        with pool().connection() as conn:
            aniversarios = gerar_aniversarios(conn, agora)
            conn.commit()
            enviadas = enviar_pendentes(conn, agora)
            resumos = enviar_resumos(conn, agora)  # Etapa 23: resumo do dia do profissional
        return {"ok": True, "aniversarios_na_fila": aniversarios, "enviadas": enviadas, "resumos": resumos}
    finally:
        _rodando.release()


class Agendador:
    def __init__(self) -> None:
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    def iniciar(self) -> None:
        if self._thread:
            return
        self._parar.clear()
        self._thread = threading.Thread(target=self._loop, name="isis-agendador", daemon=True)
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._thread = None

    def _loop(self) -> None:
        while not self._parar.wait(INTERVALO_S):
            try:
                r = rodada()
                if r.get("enviadas") or r.get("aniversarios_na_fila") or r.get("resumos"):
                    log.info("mensagens automáticas: %s", r)
            except Exception:  # noqa: BLE001 — o agendador nunca pode morrer
                log.exception("falha na rodada de mensagens automáticas")


agendador = Agendador()
