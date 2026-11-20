"""Relógio do sistema de mensagens automáticas, com "relógio simulado" para testes (spec 05).

Em desenvolvimento dá para adiantar o relógio (ex.: até o horário do próximo lembrete) sem esperar um dia.
O deslocamento vale só para o envio de lembretes e aniversários, e some quando o backend reinicia.
"""

from datetime import UTC, datetime, timedelta

_deslocamento = timedelta(0)


def agora() -> datetime:
    return datetime.now(UTC) + _deslocamento


def deslocamento() -> timedelta:
    return _deslocamento


def avancar_para(momento: datetime) -> None:
    """Adianta o relógio até `momento` (nunca volta para antes do horário real)."""
    global _deslocamento
    _deslocamento = max(timedelta(0), momento - datetime.now(UTC))


def avancar(minutos: int) -> None:
    global _deslocamento
    _deslocamento = max(timedelta(0), _deslocamento + timedelta(minutes=minutos))


def zerar() -> None:
    global _deslocamento
    _deslocamento = timedelta(0)
