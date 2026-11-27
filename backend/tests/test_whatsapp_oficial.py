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


def test_meta_sem_dados_nao_troca_e_da_erro_claro(conn, clinica):
    with pytest.raises(ValueError, match="Salve os dados da Meta"):
        conexao.trocar_provedor(conn, clinica.id, "meta")
    conn.execute("update whatsapp_instances set provider = 'meta' where clinic_id = %s", (clinica.id,))
    with pytest.raises(MetaErro, match="não configurado"):
        conexao.cliente_da_clinica(conn, clinica.id)


def test_provedor_invalido(conn, clinica):
    with pytest.raises(ValueError):
        conexao.trocar_provedor(conn, clinica.id, "outro")


# ---------------------------------------------------------------------------
# Etapa 36B — webhook da Meta
# ---------------------------------------------------------------------------
import hashlib  # noqa: E402
import hmac  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from psycopg.types.json import Jsonb  # noqa: E402

from app.canais import meta, whatsapp  # noqa: E402
from app.main import app  # noqa: E402
from tests.test_whatsapp import SemCommit  # noqa: E402

SEGREDO = "chave-secreta-do-app"
SESSAO_META = f"meta:{PHONE_ID}"


def _evento(mensagens=(), statuses=(), phone_id=PHONE_ID):
    valor = {"messaging_product": "whatsapp",
             "metadata": {"phone_number_id": phone_id, "display_phone_number": "5516991122235"},
             "contacts": [{"wa_id": "5511988887777", "profile": {"name": "Rita Moraes"}}],
             "messages": list(mensagens), "statuses": list(statuses)}
    return {"object": "whatsapp_business_account",
            "entry": [{"id": WABA_ID, "changes": [{"field": "messages", "value": valor}]}]}


def _texto_in(i, corpo):
    return {"from": "5511988887777", "id": i, "type": "text", "text": {"body": corpo}}


def _assinar(corpo: bytes, segredo=SEGREDO) -> str:
    return "sha256=" + hmac.new(segredo.encode(), corpo, hashlib.sha256).hexdigest()


def _na_meta(conn, clinica):
    conexao.salvar_meta(conn, clinica.id, phone_number_id=PHONE_ID, waba_id=WABA_ID, token=TOKEN, app_secret=SEGREDO)
    conexao.trocar_provedor(conn, clinica.id, "meta")


def _token_webhook(conn, clinica):
    return conn.execute("select webhook_token from whatsapp_instances where clinic_id = %s", (clinica.id,)).fetchone()[0]


def test_assinatura_da_meta():
    corpo = b'{"a":1}'
    assert meta.verificar_assinatura(corpo, _assinar(corpo), SEGREDO)
    assert not meta.verificar_assinatura(corpo, _assinar(corpo, "outra"), SEGREDO)
    assert not meta.verificar_assinatura(corpo, None, SEGREDO)
    assert not meta.verificar_assinatura(corpo, _assinar(corpo).replace("sha256=", ""), SEGREDO)


def test_interpretar_texto_audio_botao_e_status():
    ev = _evento(
        mensagens=[
            _texto_in("wamid.1", " Oi, tem horário? "),
            {"from": "5511988887777", "id": "wamid.2", "type": "audio", "audio": {"id": "998877665544", "mime_type": "audio/ogg"}},
            {"from": "5511988887777", "id": "wamid.3", "type": "button", "button": {"text": "Confirmar", "payload": "1"}},
            {"from": "5511988887777", "id": "wamid.4", "type": "image", "image": {"id": "11223344556", "caption": "meu exame"}},
            {"from": "5511988887777", "id": "wamid.5", "type": "location", "location": {"latitude": 1}},
        ],
        statuses=[{"id": "wamid.A", "status": "delivered"}, {"id": "wamid.B", "status": "read"},
                  {"id": "wamid.C", "status": "sent"},
                  {"id": "wamid.D", "status": "failed", "errors": [{"code": 131047, "title": "Re-engagement message"}]}])
    msgs, entregas, falhas = meta.interpretar_webhook(ev, SESSAO_META, PHONE_ID)
    texto, audio, botao, foto, outro = msgs
    assert (texto.texto, texto.telefone, texto.chat_id, texto.nome) == (
        "Oi, tem horário?", "+5511988887777", "5511988887777", "Rita Moraes")
    assert (audio.midia, audio.midia_url, audio.midia_mime, audio.texto) == ("audio", "998877665544", "audio/ogg", "")
    assert botao.texto == "Confirmar" and botao.midia is None
    assert (foto.midia, foto.texto) == ("foto", "meu exame")
    assert outro.midia == "outro"
    assert entregas == [("wamid.A", 2), ("wamid.B", 3)]
    assert falhas == [("wamid.D", "131047 Re-engagement message")]


def test_evento_de_outro_numero_e_ignorado():
    ev = _evento(mensagens=[_texto_in("w", "oi")], phone_id="555555555555")
    assert meta.interpretar_webhook(ev, "s", PHONE_ID) == ([], [], [])


def test_trocar_para_meta_liga_e_voltar_desliga(conn, clinica):
    conn.execute("insert into whatsapp_instances (clinic_id, session) values (%s, 'sessao-waha')", (clinica.id,))
    conexao.salvar_meta(conn, clinica.id, phone_number_id=PHONE_ID, waba_id=WABA_ID, token=TOKEN, app_secret=SEGREDO)
    with pytest.raises(ValueError, match="Desligue"):  # WAHA ligado: não troca no meio
        conexao.trocar_provedor(conn, clinica.id, "meta")
    conn.execute("update whatsapp_instances set session = null, enabled = false where clinic_id = %s", (clinica.id,))
    conexao.trocar_provedor(conn, clinica.id, "meta")
    inst = whatsapp.instancia_da_clinica(conn, clinica.id)
    assert inst["session"] == SESSAO_META and inst["enabled"]
    conexao.trocar_provedor(conn, clinica.id, "waha")
    inst = whatsapp.instancia_da_clinica(conn, clinica.id)
    assert inst["session"] is None and not inst["enabled"]


def test_verificacao_do_endereco_pela_meta(conn, clinica, monkeypatch):
    conexao.salvar_meta(conn, clinica.id, phone_number_id=PHONE_ID, waba_id=WABA_ID, token=TOKEN, app_secret=SEGREDO)
    t = _token_webhook(conn, clinica)
    achado = conexao.por_token_meta(conn, t, exigir_meta=False)  # ainda em WAHA: a verificação já funciona
    assert conexao.por_token_meta(conn, t) is None  # mas mensagens não
    monkeypatch.setattr(conexao, "por_token_meta", lambda c, tk, exigir_meta=True: achado if tk == t else None)
    verif = achado["verify_token"]
    c = TestClient(app)
    ok = c.get(f"/webhooks/meta/{t}", params={"hub.mode": "subscribe", "hub.verify_token": verif, "hub.challenge": "12345"})
    assert ok.status_code == 200 and ok.text == "12345"
    errado = {"hub.mode": "subscribe", "hub.verify_token": "errado", "hub.challenge": "1"}
    assert c.get(f"/webhooks/meta/{t}", params=errado).status_code == 403
    assert c.get("/webhooks/meta/nao-existe", params={"hub.mode": "subscribe", "hub.verify_token": verif}).status_code == 403


def test_webhook_confere_assinatura_e_repassa(conn, clinica, monkeypatch):
    from app.api import webhooks

    _na_meta(conn, clinica)
    t = _token_webhook(conn, clinica)
    achado = conexao.por_token_meta(conn, t)
    assert achado and achado["sessao"] == SESSAO_META
    monkeypatch.setattr(conexao, "por_token_meta", lambda c, tk, exigir_meta=True: achado if tk == t else None)
    recebidas, entregas, falhas = [], [], []
    monkeypatch.setattr(webhooks.whatsapp, "processar", lambda msg: recebidas.append(msg))
    monkeypatch.setattr(webhooks.whatsapp, "processar_entrega", lambda *a: entregas.append(a))
    monkeypatch.setattr(webhooks.whatsapp, "processar_falha", lambda *a: falhas.append(a))

    corpo = json.dumps(_evento(
        mensagens=[_texto_in("wamid.1", "oi")],
        statuses=[{"id": "wamid.X", "status": "read"},
                  {"id": "wamid.Y", "status": "failed", "errors": [{"code": 131026, "title": "Message undeliverable"}]}],
    )).encode()
    c = TestClient(app)
    assert c.post(f"/webhooks/meta/{t}", content=corpo,
                  headers={"x-hub-signature-256": _assinar(corpo, "errada")}).status_code == 401
    assert recebidas == []
    r = c.post(f"/webhooks/meta/{t}", content=corpo, headers={"x-hub-signature-256": _assinar(corpo)})
    assert r.json() == {"ok": True}
    assert [m.texto for m in recebidas] == ["oi"] and recebidas[0].sessao == SESSAO_META
    assert entregas == [(SESSAO_META, "wamid.X", 3)]
    assert falhas == [(SESSAO_META, "wamid.Y", "131026 Message undeliverable")]
    assert c.post("/webhooks/meta/nao-existe", content=corpo,
                  headers={"x-hub-signature-256": _assinar(corpo)}).status_code == 404


def test_mensagem_da_meta_entra_na_conversa_da_clinica(conn, clinica):
    _na_meta(conn, clinica)
    conn.execute("update clinics set settings = coalesce(settings, '{}'::jsonb) || %s where id = %s",
                 (Jsonb({"isis_pausada_whatsapp": True}), clinica.id))  # sem IA: só confere a entrada
    (msg,), _, _ = meta.interpretar_webhook(_evento(mensagens=[_texto_in("wamid.in1", "Oi")]), SESSAO_META, PHONE_ID)
    falsa = ClienteMeta(PHONE_ID, TOKEN, base_url="https://graph.test/v23.0", transport=_meta_simulada([]))
    whatsapp.processar_com(SemCommit(conn), msg, cliente=falsa)  # processar_com faz commit: aqui não pode
    r = conn.execute(
        """select p.phone, c.external_chat_id, m.content from messages m join conversations c on c.id = m.conversation_id
           join patients p on p.id = c.patient_id where m.clinic_id = %s and m.external_id = 'wamid.in1'""",
        (clinica.id,)).fetchone()
    assert r == ("+5511988887777", "5511988887777", "Oi")


def test_entregue_lida_e_falha_pela_sessao_meta(conn, clinica):
    _na_meta(conn, clinica)
    pid = conn.execute("insert into patients (clinic_id, name, phone) values (%s, 'Rita Moraes', '+5511988887777') returning id",
                       (clinica.id,)).fetchone()[0]

    def enviada(ext):
        return conn.execute(
            """insert into outbound_messages (clinic_id, patient_id, kind, body, status, sent_at, external_id)
               values (%s, %s, 'lembrete', 'x', 'enviada', now(), %s) returning id""", (clinica.id, pid, ext)).fetchone()[0]

    ok, ruim = enviada("wamid.ok"), enviada("wamid.ruim")
    assert whatsapp.registrar_entrega(conn, SESSAO_META, "wamid.ok", 3)
    assert whatsapp.registrar_falha_envio(conn, SESSAO_META, "wamid.ruim", "131047 Re-engagement message")
    st = dict(conn.execute("select id, status from outbound_messages where id = any(%s)", ([ok, ruim],)).fetchall())
    assert st == {ok: "lida", ruim: "falhou"}
    assert "131047" in conn.execute("select error from outbound_messages where id = %s", (ruim,)).fetchone()[0]
