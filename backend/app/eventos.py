"""Tempo real (D7): avisa as telas quando algo muda.

Como funciona:
1. Quem grava algo chama `avisar(conn, ...)` DENTRO da transação. O Postgres só entrega
   o aviso (NOTIFY) depois do COMMIT — a tela nunca vê algo que foi desfeito.
2. Uma thread fica escutando o canal (LISTEN) e repassa cada aviso para as telas
   conectadas daquela clínica, via SSE (GET /api/clinics/{id}/events).
Funciona também com outros processos (scripts, futuro worker do WhatsApp).
"""

import asyncio
import json
import logging
import threading
import time
from collections import defaultdict

import psycopg

CANAL = "isis_eventos"
log = logging.getLogger("isis.eventos")

Tipo = str  # "agenda" | "crm" | "mensagens" | "conversa"


def avisar(conn: psycopg.Connection, clinic_id, tipo: Tipo, id_=None) -> None:
    payload = json.dumps({"clinic_id": str(clinic_id), "tipo": tipo, "id": str(id_) if id_ else None})
    conn.execute("select pg_notify(%s, %s)", (CANAL, payload))


class Distribuidor:
    """Liga a thread que escuta o banco às filas das telas abertas (uma fila por tela)."""

    def __init__(self) -> None:
        self._filas: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    # --- lado das telas (asyncio) ---
    def inscrever(self, clinic_id: str) -> asyncio.Queue:
        fila: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._filas[clinic_id].add(fila)
        return fila

    def desinscrever(self, clinic_id: str, fila: asyncio.Queue) -> None:
        self._filas[clinic_id].discard(fila)

    def _entregar(self, evento: dict) -> None:
        for fila in list(self._filas.get(evento["clinic_id"], ())):
            try:
                fila.put_nowait(evento)
            except asyncio.QueueFull:  # tela travada: descarta, ela recarrega no próximo aviso
                pass

    # --- lado do banco (thread) ---
    def iniciar(self, database_url: str) -> None:
        self._loop = asyncio.get_running_loop()
        self._thread = threading.Thread(target=self._escutar, args=(database_url,), daemon=True, name="isis-listen")
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()

    def _escutar(self, url: str) -> None:
        while not self._parar.is_set():
            try:
                with psycopg.connect(url, autocommit=True, connect_timeout=10) as conn:
                    conn.execute(f"listen {CANAL}")
                    log.info("escutando eventos do banco")
                    while not self._parar.is_set():
                        for n in conn.notifies(timeout=5):
                            try:
                                evento = json.loads(n.payload)
                            except ValueError:
                                continue
                            if self._loop:
                                self._loop.call_soon_threadsafe(self._entregar, evento)
            except Exception as e:  # noqa: BLE001 — conexão caiu: tenta de novo
                log.warning("escuta de eventos caiu (%s); reconectando em 3 s", type(e).__name__)
                time.sleep(3)


distribuidor = Distribuidor()
