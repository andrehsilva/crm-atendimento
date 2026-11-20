"""Regras de horário das mensagens automáticas, em funções puras (sem banco)."""

import calendar
import unicodedata
from datetime import date, time, timedelta


def hora(texto: str) -> time:
    h, m = texto.split(":")
    return time(int(h), int(m))


def dia_do_lembrete(dia_consulta: date, dias_abertos: set[int], feriados: set[date], dias_uteis: int = 1) -> date:
    """RN-MS-02: dia útil anterior à consulta (pula dias em que a clínica não abre e feriados).
    Ex.: consulta na segunda → lembrete na sexta (ou no sábado, se a clínica abre sábado)."""
    dia = dia_consulta
    contados = 0
    for _ in range(30):  # proteção: nunca procura mais de 30 dias para trás
        dia -= timedelta(days=1)
        if dia.weekday() in dias_abertos and dia not in feriados:
            contados += 1
            if contados >= max(1, dias_uteis):
                return dia
    return dia_consulta - timedelta(days=1)


def em_silencio(agora: time, inicio: time, fim: time) -> bool:
    """RN-MS-09: janela sem mensagens automáticas (padrão 21h–08h; pode passar da meia-noite)."""
    if inicio <= fim:
        return inicio <= agora < fim
    return agora >= inicio or agora < fim


def faz_aniversario(nascimento: date, hoje: date) -> bool:
    """RN-DP-03: quem nasceu em 29/02 comemora em 28/02 nos anos não bissextos."""
    if (nascimento.month, nascimento.day) == (hoje.month, hoje.day):
        return True
    return (nascimento.month, nascimento.day) == (2, 29) and (hoje.month, hoje.day) == (2, 28) and not calendar.isleap(hoje.year)


def _simples(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "".join(c for c in sem_acento.upper() if c.isalnum())


def resposta_ao_lembrete(texto: str) -> str | None:
    """Entende a resposta ao lembrete: '1'/'confirmo' → confirmar, '2' → remarcar, '3' → cancelar (RN-MS-04)."""
    t = _simples(texto)
    if t in ("1", "CONFIRMAR", "CONFIRMO", "CONFIRMADO"):
        return "confirmar"
    if t in ("2", "REMARCAR"):
        return "remarcar"
    if t in ("3", "CANCELAR"):
        return "cancelar"
    return None


def pediu_para_sair(texto: str) -> bool:
    """RN-DP-04: 'PARAR' ou 'SAIR' (sozinhos na mensagem) desligam os disparos."""
    return _simples(texto) in ("PARAR", "SAIR", "PARE")
