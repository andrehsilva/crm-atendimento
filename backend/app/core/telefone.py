"""Normalização de telefones para E.164 (RN-MT-04, D5).

Aceita "+55 (21) 98765-4321", "5521987654321", "21 98765-4321", "(21) 8765-4321"...
Celular antigo sem o 9º dígito ganha o 9, para que formatos diferentes do mesmo
número virem a mesma chave.
"""

import re


class TelefoneInvalido(ValueError):
    pass


def normalizar_telefone(valor: str) -> str:
    digitos = re.sub(r"\D", "", valor or "")
    digitos = digitos.lstrip("0")  # ex.: 021987654321 (DDD com zero)

    if len(digitos) in (10, 11):  # DDD + número, sem país
        digitos = "55" + digitos

    if digitos.startswith("55"):
        local = digitos[4:]
        if len(local) == 8 and local[0] in "6789":  # celular sem o 9º dígito
            digitos = digitos[:4] + "9" + local
        if len(digitos) not in (12, 13) or digitos[2] == "0":
            raise TelefoneInvalido(f"Telefone brasileiro inválido: {valor!r}")
    elif not 10 <= len(digitos) <= 15:
        raise TelefoneInvalido(f"Telefone inválido: {valor!r}")

    return "+" + digitos
