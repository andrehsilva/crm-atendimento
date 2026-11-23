"""Relógio do sistema de mensagens automáticas, com "relógio simulado" para testes (spec 05).

Em desenvolvimento dá para adiantar o relógio (ex.: até o horário do próximo lembrete) sem esperar um dia.
O deslocamento vale só para o envio de lembretes e aniversários, e some quando o backend reinicia.
"""

from datetime import UTC, datetime, timedelta

_deslocamento = timedelta(0)
_fixo: datetime | None = None  # só nos testes: "agora" parado num instante (pode ser no passado)


def agora() -> datetime:
    if _fixo is not None:
        return _fixo
    return datetime.now(UTC) + _deslocamento


def fixar(momento: datetime | None) -> None:
    """Testes: congela o relógio em `momento` (None solta). Assim o código que compara com "agora" não
    depende do dia em que a bateria roda."""
    global _fixo
    _fixo = momento


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
    global _deslocamento, _fixo
    _deslocamento = timedelta(0)
    _fixo = None
