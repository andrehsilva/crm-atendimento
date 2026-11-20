"""Aparência de cada clínica (Etapa 9B, D40): cor principal e logo.

- Cor: hex "#RRGGBB" em clinics.settings->>'cor'. Precisa de contraste mínimo de 3:1 com o branco,
  senão botões e textos na cor da clínica ficam ilegíveis.
- Logo: PNG, JPG ou WebP até 512 KB, guardada na tabela clinic_logos. O tipo é conferido pelos
  primeiros bytes do arquivo (não pelo nome nem pelo que o navegador diz). SVG não entra: pode carregar script.
"""

import re

from app.agenda.erros import AgendaError

COR_PADRAO = "#b85c74"
COR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
CONTRASTE_MINIMO = 3.0
LOGO_MAX = 512 * 1024


def _luminancia(cor: str) -> float:
    def canal(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)


def contraste_com_branco(cor: str) -> float:
    return 1.05 / (_luminancia(cor) + 0.05)


def validar_cor(cor: str) -> str:
    if not COR_RE.match(cor):
        raise AgendaError("DADOS_INVALIDOS", "Cor inválida: use o formato #RRGGBB.")
    if contraste_com_branco(cor) < CONTRASTE_MINIMO:
        raise AgendaError("DADOS_INVALIDOS", "Essa cor é clara demais: textos e botões ficariam difíceis de ler. "
                                             "Escolha um tom mais escuro.")
    return cor.lower()


def cor_da_clinica(settings: dict | None) -> str:
    cor = (settings or {}).get("cor")
    return cor if isinstance(cor, str) and COR_RE.match(cor) else COR_PADRAO


def tipo_da_imagem(dados: bytes) -> str:
    """Devolve o tipo pela assinatura do arquivo; recusa o que não for PNG, JPG ou WebP."""
    if len(dados) > LOGO_MAX:
        raise AgendaError("LOGO_GRANDE", "A imagem pode ter no máximo 512 KB.")
    if dados.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if dados.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(dados) >= 12 and dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        return "image/webp"
    raise AgendaError("LOGO_INVALIDA", "A imagem precisa ser PNG, JPG ou WebP.")


async def ler_imagem(request) -> tuple[bytes, str]:
    """Lê o corpo da requisição (a própria imagem) aos poucos, parando se passar de 512 KB."""
    dados = bytearray()
    async for parte in request.stream():
        dados += parte
        if len(dados) > LOGO_MAX:
            raise AgendaError("LOGO_GRANDE", "A imagem pode ter no máximo 512 KB.")
    return bytes(dados), tipo_da_imagem(bytes(dados))


def resposta_imagem(mime: str, dados: bytes):
    from fastapi.responses import Response

    # A URL leva ?v=<versão>: pode guardar em cache; nosniff impede o navegador de tratar como outra coisa
    return Response(dados, media_type=mime, headers={
        "Cache-Control": "private, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff"})


def versao_da_logo(conn, clinic_id) -> int | None:
    """Número que muda a cada nova logo: vai na URL da imagem para o navegador não mostrar a antiga."""
    r = conn.execute("select (extract(epoch from updated_at) * 1000)::bigint from clinic_logos where clinic_id = %s",
                     (clinic_id,)).fetchone()
    return r[0] if r else None


def versao_da_foto_paciente(conn, patient_id) -> int | None:
    r = conn.execute("select (extract(epoch from updated_at) * 1000)::bigint from patient_photos where patient_id = %s",
                     (patient_id,)).fetchone()
    return r[0] if r else None
