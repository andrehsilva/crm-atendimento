"""Etapa 36A (D131): WhatsApp oficial (Meta) como 2ª opção por clínica. Meta simulada; nada sai de verdade.

O ponto principal: clínica em WAHA (o padrão) continua exatamente como antes.
"""

import json

import httpx
import pytest

from app.canais import conexao
from app.canais.meta import ClienteMeta, MetaErro, numero_do_chat
from app.canais.waha import ClienteWaha, WahaErro
from app.mensagens import envio

PHONE_ID = "123456789012345"
WABA_ID = "987654321098765"
TOKEN = "EAAGtokenDeTesteMuitoLongo1234wxyz"


def _meta_simulada(chamadas: list, resposta=None, status=200):
    def tratar(req: httpx.Request) -> httpx.Response:
        chamadas.append(req)
        return httpx.Response(status, json=resposta if resposta is not None else {"messages": [{"id": "wamid.ABC"}]})
    return httpx.MockTransport(tratar)


# ---------------------------------------------------------------------------
# Cliente da Meta
# ---------------------------------------------------------------------------
def test_numero_do_chat():
    assert numero_do_chat("5511999998888@c.us") == "5511999998888"
    assert numero_do_chat("+55 (11) 99999-8888") == "5511999998888"


def test_enviar_texto_monta_o_pedido_da_meta():
    chamadas: list = []
    c = ClienteMeta(PHONE_ID, TOKEN, base_url="https://graph.test/v23.0", transport=_meta_simulada(chamadas))
    assert c.enviar_texto("qualquer-sessao", "5511999998888@c.us", "Olá!") == "wamid.ABC"
    (req,) = chamadas
    assert req.method == "POST" and req.url.path == f"/v23.0/{PHONE_ID}/messages"
    assert req.headers["authorization"] == f"Bearer {TOKEN}"
    corpo = json.loads(req.content)
    assert corpo["to"] == "5511999998888" and corpo["type"] == "text" and corpo["text"]["body"] == "Olá!"


def test_erro_da_meta_vira_metaerro_que_e_wahaerro():
    c = ClienteMeta(PHONE_ID, TOKEN, base_url="https://graph.test/v23.0",
                    transport=_meta_simulada([], {"error": {"message": "Invalid OAuth access token"}}, 401))
    with pytest.raises(MetaErro) as e:
        c.enviar_texto(None, "5511999998888", "oi")
    assert isinstance(e.value, WahaErro)  # a fila e as telas já tratam WahaErro: vale para os dois
    assert "Invalid OAuth" in str(e.value)


def test_baixar_midia_so_aceita_endereco_da_meta():
    resp = {"url": "https://servidor-estranho.com/arquivo"}
    c = ClienteMeta(PHONE_ID, TOKEN, base_url="https://graph.test/v23.0", transport=_meta_simulada([], resp))
    with pytest.raises(MetaErro, match="fora da Meta"):
        c.baixar_midia("1234567890")
    with pytest.raises(MetaErro, match="inválido"):
        c.baixar_midia("../../outra-coisa")


def test_acoes_de_sessao_do_waha_avisam_que_nao_se_aplicam():
    c = ClienteMeta(PHONE_ID, TOKEN, base_url="https://graph.test/v23.0", transport=_meta_simulada([]))
    with pytest.raises(MetaErro, match="WAHA"):
        c.qr_png("sessao")
    assert c.atualizar_eventos_do_webhook("s", "u", "k") is False


def test_testar_devolve_numero_e_nome():
    resp = {"display_phone_number": "+55 16 99112-2235", "verified_name": "Clínica Teste", "quality_rating": "GREEN"}
    c = ClienteMeta(PHONE_ID, TOKEN, base_url="https://graph.test/v23.0", transport=_meta_simulada([], resp))
    assert c.testar() == {"numero": "+55 16 99112-2235", "nome": "Clínica Teste", "qualidade": "GREEN"}


# ---------------------------------------------------------------------------
# Escolha do provedor por clínica (padrão WAHA)
# ---------------------------------------------------------------------------
def test_clinica_nova_e_as_de_hoje_ficam_no_waha(conn, clinica):
    assert conexao.provedor(conn, clinica.id) == "waha"  # sem linha nenhuma
    conn.execute("insert into whatsapp_instances (clinic_id, session) values (%s, 'sessao-x')", (clinica.id,))
    assert conexao.provedor(conn, clinica.id) == "waha"  # linha como as de hoje
    assert isinstance(conexao.cliente_da_clinica(conn, clinica.id), ClienteWaha)


def test_salvar_meta_guarda_cifrado_e_nao_devolve_segredo(conn, clinica):
    conexao.salvar_meta(conn, clinica.id, phone_number_id=PHONE_ID, waba_id=WABA_ID, token=TOKEN, app_secret="segredo-app")
    cru = conn.execute("select meta_token_cipher, meta_app_secret_cipher from whatsapp_instances where clinic_id = %s",
                       (clinica.id,)).fetchone()
    assert TOKEN.encode() not in bytes(cru[0]) and b"segredo-app" not in bytes(cru[1])
    e = conexao.estado_meta(conn, clinica.id)
    assert e["provedor"] == "waha"  # salvar os dados NÃO troca o provedor
    assert (e["phone_number_id"], e["waba_id"], e["token_final"], e["tem_app_secret"]) == (PHONE_ID, WABA_ID, "wxyz", True)
    assert e["verify_token"] and TOKEN not in json.dumps(e, default=str)


def test_salvar_meta_sem_token_mantem_o_salvo(conn, clinica):
    conexao.salvar_meta(conn, clinica.id, phone_number_id=PHONE_ID, waba_id=WABA_ID, token=TOKEN, app_secret="s")
    verif = conexao.estado_meta(conn, clinica.id)["verify_token"]
    conexao.salvar_meta(conn, clinica.id, phone_number_id="111112222233333", waba_id=WABA_ID, token=None, app_secret=None)
    e = conexao.estado_meta(conn, clinica.id)
    assert e["phone_number_id"] == "111112222233333" and e["token_final"] == "wxyz"
    assert e["verify_token"] == verif  # não troca o token de verificação já colado na Meta


def test_salvar_meta_pela_primeira_vez_exige_token_e_chave(conn, clinica):
    with pytest.raises(ValueError, match="token"):
        conexao.salvar_meta(conn, clinica.id, phone_number_id=PHONE_ID, waba_id=WABA_ID, token=None, app_secret="s")
    with pytest.raises(ValueError, match="chave secreta"):
        conexao.salvar_meta(conn, clinica.id, phone_number_id=PHONE_ID, waba_id=WABA_ID, token=TOKEN, app_secret=None)


def test_so_a_clinica_trocada_para_meta_usa_a_meta(conn, clinica, outra_clinica):
    conn.execute("insert into whatsapp_instances (clinic_id, session) values (%s, 'sessao-b')", (outra_clinica.id,))
    conexao.salvar_meta(conn, clinica.id, phone_number_id=PHONE_ID, waba_id=WABA_ID, token=TOKEN, app_secret="s")
    conexao.trocar_provedor(conn, clinica.id, "meta")

    c = conexao.cliente_da_clinica(conn, clinica.id)
    assert isinstance(c, ClienteMeta) and c.phone_number_id == PHONE_ID
    assert isinstance(envio._cliente(conn, clinica.id, None), ClienteMeta)  # fila de mensagens automáticas
    assert isinstance(conexao.cliente_da_clinica(conn, outra_clinica.id), ClienteWaha)  # a outra segue no WAHA

    conexao.trocar_provedor(conn, clinica.id, "waha")  # voltar é só trocar de novo; dados da Meta ficam
    assert isinstance(conexao.cliente_da_clinica(conn, clinica.id), ClienteWaha)
    assert conexao.estado_meta(conn, clinica.id)["token_final"] == "wxyz"


def test_meta_sem_dados_da_erro_claro(conn, clinica):
    conexao.trocar_provedor(conn, clinica.id, "meta")
    with pytest.raises(MetaErro, match="não configurado"):
        conexao.cliente_da_clinica(conn, clinica.id)


def test_provedor_invalido(conn, clinica):
    with pytest.raises(ValueError):
        conexao.trocar_provedor(conn, clinica.id, "outro")
