"""Regras de horário em funções puras (sem banco) — fáceis de testar.

Intervalos são pares (início, fim) de datetime com fuso, fechados no início e abertos no fim: [início, fim).
"""

from dataclasses import dataclass, fields
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

Intervalo = tuple[datetime, datetime]


@dataclass(frozen=True)
class RegrasClinica:
    """Valores padrão das regras "Config" (docs/REGRAS-DE-NEGOCIO.md). A clínica sobrescreve em clinics.settings."""

    antecedencia_min_horas: float = 2  # RN-AG-04
    horizonte_dias: int = 60  # RN-AG-05
    aviso_cancelamento_horas: float = 24  # RN-AG-07
    limite_consultas_futuras: int = 2  # RN-AG-08
    confirmar_automatico_horas: float = 24  # RN-AG-19 (D129): marcada para menos que isso já entra confirmada (0 = desliga)
    faltas_limite: int = 2  # RN-AG-16 (D91): com tantas faltas na janela, a assistente passa para a recepção (0 = desliga)
    faltas_janela_dias: int = 45
    passo_slot_min: int = 30  # grade de horários oferecidos
    # Mensagens automáticas (Etapa 6)
    lembrete_hora: str = "09:00"  # RN-MS-02
    lembrete_dias_uteis: int = 1  # RN-MS-02: quantos dias úteis antes
    silencio_inicio: str = "21:00"  # RN-MS-09
    silencio_fim: str = "08:00"
    aniversario_hora: str = "09:00"  # RN-DP-01
    envio_por_minuto: int = 20  # RN-DP-07
    envio_por_dia: int = 300

    @classmethod
    def de_settings(cls, settings: dict | None) -> "RegrasClinica":
        settings = settings or {}
        validos = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in settings.items() if k in validos})


@dataclass(frozen=True)
class Faixa:
    """Faixa de horário num dia da semana (0 = segunda ... 6 = domingo)."""

    weekday: int
    inicio: time
    fim: time


def _no_dia(dia: date, h: time, tz: ZoneInfo) -> datetime:
    return datetime.combine(dia, h, tzinfo=tz)


def janelas_do_dia(
    dia: date,
    tz: ZoneInfo,
    horario_clinica: dict[int, Faixa],
    pausas: list[Faixa],
    excecoes_profissional: list[Faixa],
) -> list[Intervalo]:
    """Faixas em que o profissional atende no dia (RN-AG-01).

    - horário da clínica do dia (sem linha ou desligado = fechado);
    - se o profissional tem exceções cadastradas, atende só nelas (e sempre dentro do horário da clínica);
    - menos as pausas do dia.
    """
    wd = dia.weekday()
    faixa = horario_clinica.get(wd)
    if faixa is None:
        return []
    janelas = [(_no_dia(dia, faixa.inicio, tz), _no_dia(dia, faixa.fim, tz))]

    if excecoes_profissional:
        proprias = [(_no_dia(dia, f.inicio, tz), _no_dia(dia, f.fim, tz)) for f in excecoes_profissional if f.weekday == wd]
        janelas = intersectar(janelas, proprias)

    pausas_dia = [(_no_dia(dia, p.inicio, tz), _no_dia(dia, p.fim, tz)) for p in pausas if p.weekday == wd]
    return subtrair(janelas, pausas_dia)


def intersectar(a: list[Intervalo], b: list[Intervalo]) -> list[Intervalo]:
    saida = []
    for ai, af in a:
        for bi, bf in b:
            ini, fim = max(ai, bi), min(af, bf)
            if ini < fim:
                saida.append((ini, fim))
    return sorted(saida)


def subtrair(janelas: list[Intervalo], ocupados: list[Intervalo]) -> list[Intervalo]:
    """Remove das janelas os trechos ocupados (consultas, pausas, bloqueios)."""
    resultado = list(janelas)
    for oi, of in ocupados:
        novo = []
        for ji, jf in resultado:
            if of <= ji or oi >= jf:  # não encosta
                novo.append((ji, jf))
                continue
            if ji < oi:
                novo.append((ji, oi))
            if of < jf:
                novo.append((of, jf))
        resultado = novo
    return sorted(resultado)


def fatiar(janelas: list[Intervalo], duracao: timedelta, passo: timedelta) -> list[datetime]:
    """Inícios possíveis de consulta: a cada `passo`, desde que a consulta inteira caiba na janela."""
    inicios = []
    for ji, jf in janelas:
        t = ji
        while t + duracao <= jf:
            inicios.append(t)
            t += passo
    return inicios


def cabe(inicio: datetime, fim: datetime, janelas: list[Intervalo]) -> bool:
    return any(ji <= inicio and fim <= jf for ji, jf in janelas)


def limites_de_tempo(agora: datetime, regras: RegrasClinica) -> tuple[datetime, datetime]:
    """(mais cedo, mais tarde) em que uma consulta pode começar (RN-AG-04 e RN-AG-05)."""
    return (
        agora + timedelta(hours=regras.antecedencia_min_horas),
        agora + timedelta(days=regras.horizonte_dias),
    )
