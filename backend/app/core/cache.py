"""Etapa 32 (desempenho): cache curto em memória para o que quase não muda e é pedido em toda tela.

Por quê: com o servidor longe do banco (Helsinque × São Paulo), cada consulta custa ~0,2 s. Quem está logado,
os dados da clínica e os cadastros são pedidos a cada troca de tela e quase nunca mudam.

Regras (o que não pode falhar continua no banco):
- Só leitura de dados de configuração. Agenda, horários livres, conflitos, mensagens: NUNCA passam por aqui.
- Vale por poucos segundos (TTL) e QUALQUER gravação no painel (POST/PUT/PATCH/DELETE) limpa tudo
  (middleware em app/main.py). Desativar um usuário vale no próximo pedido.
- O backend roda num processo só (D37): não existem duas cópias do cache para ficarem diferentes.
"""

import threading
import time
from collections.abc import Callable
from typing import Any

ATIVO = True  # os testes desligam (conftest) e ligam só onde testam o cache
_dados: dict[str, tuple[float, Any]] = {}
_trava = threading.Lock()


def memo(chave: str, ttl: float, calcular: Callable[[], Any]) -> Any:
    """Devolve o valor guardado em `chave` se ainda vale; senão calcula, guarda e devolve."""
    if not ATIVO:
        return calcular()
    agora = time.monotonic()
    with _trava:
        achado = _dados.get(chave)
    if achado and achado[0] > agora:
        return achado[1]
    valor = calcular()
    with _trava:
        _dados[chave] = (agora + ttl, valor)
        if len(_dados) > 2000:  # nunca cresce sem limite: joga fora o que já venceu
            for k in [k for k, (vence, _) in _dados.items() if vence <= agora]:
                _dados.pop(k, None)
    return valor


def limpar() -> None:
    with _trava:
        _dados.clear()
