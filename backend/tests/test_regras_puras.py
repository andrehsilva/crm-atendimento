"""Regras de horário e telefone, sem banco."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.agenda import regras as R
from app.core.telefone import TelefoneInvalido, normalizar_telefone

TZ = ZoneInfo("America/Sao_Paulo")
SEG = date(2026, 11, 23)  # segunda-feira
HORARIO = {0: R.Faixa(0, time(8), time(18)), 5: R.Faixa(5, time(9), time(13))}
ALMOCO = [R.Faixa(0, time(12), time(13))]


def h(hora: int, minuto: int = 0, dia: date = SEG) -> datetime:
    return datetime.combine(dia, time(hora, minuto), tzinfo=TZ)


# --- telefone (RN-MT-04 / cenário C20) ---------------------------------------
@pytest.mark.parametrize(
    "entrada",
    ["(21) 98765-4321", "+55 21 98765-4321", "5521987654321", "21987654321", "021 98765 4321", "(21) 8765-4321"],
)
def test_formatos_do_mesmo_celular_viram_a_mesma_chave(entrada):
    assert normalizar_telefone(entrada) == "+5521987654321"


def test_fixo_nao_ganha_nono_digito():
    assert normalizar_telefone("(11) 3456-7890") == "+551134567890"


@pytest.mark.parametrize("entrada", ["", "123", "abc", "(00) 98765-4321"])
def test_telefone_invalido(entrada):
    with pytest.raises(TelefoneInvalido):
        normalizar_telefone(entrada)


# --- janelas do dia (RN-AG-01) ------------------------------------------------
def test_dia_com_almoco_vira_duas_janelas():
    assert R.janelas_do_dia(SEG, TZ, HORARIO, ALMOCO, []) == [(h(8), h(12)), (h(13), h(18))]


def test_dia_fechado_nao_tem_janela():
    domingo = SEG + timedelta(days=6)
    assert R.janelas_do_dia(domingo, TZ, HORARIO, ALMOCO, []) == []


def test_excecao_do_profissional_restringe_ao_horario_dele():
    so_tarde = [R.Faixa(0, time(14), time(20))]  # pede até 20h, mas a clínica fecha 18h
    assert R.janelas_do_dia(SEG, TZ, HORARIO, ALMOCO, so_tarde) == [(h(14), h(18))]


def test_profissional_com_excecoes_nao_atende_em_dia_sem_excecao():
    so_sabado = [R.Faixa(5, time(9), time(13))]
    assert R.janelas_do_dia(SEG, TZ, HORARIO, ALMOCO, so_sabado) == []


# --- fatiar / subtrair --------------------------------------------------------
def test_consulta_de_60_min_nao_atravessa_o_almoco():
    janelas = R.janelas_do_dia(SEG, TZ, HORARIO, ALMOCO, [])
    inicios = R.fatiar(janelas, timedelta(minutes=60), timedelta(minutes=30))
    assert h(11) in inicios
    assert h(11, 30) not in inicios  # terminaria 12:30, dentro do almoço
    assert h(17) in inicios and h(17, 30) not in inicios


def test_consulta_ocupada_some_dos_horarios():
    janelas = R.subtrair(R.janelas_do_dia(SEG, TZ, HORARIO, ALMOCO, []), [(h(9), h(10))])
    inicios = R.fatiar(janelas, timedelta(minutes=60), timedelta(minutes=30))
    assert h(8) in inicios and h(9) not in inicios and h(8, 30) not in inicios and h(10) in inicios


def test_cabe():
    janelas = [(h(8), h(12))]
    assert R.cabe(h(11), h(12), janelas)
    assert not R.cabe(h(11, 30), h(12, 30), janelas)


def test_regras_padrao_e_sobrescrita_da_clinica():
    r = R.RegrasClinica.de_settings({"antecedencia_min_horas": 4, "campo_desconhecido": 1})
    assert r.antecedencia_min_horas == 4 and r.horizonte_dias == 60 and r.limite_consultas_futuras == 2
