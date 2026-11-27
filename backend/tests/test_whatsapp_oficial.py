"""Etapa 36A (D131): WhatsApp oficial (Meta) como 2ª opção por clínica. Meta simulada; nada sai de verdade.

O ponto principal: clínica em WAHA (o padrão) continua exatamente como antes.
"""

import json
import re

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
    msgs, entregas, falhas, _ = meta.interpretar_webhook(ev, SESSAO_META, PHONE_ID)
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
    assert meta.interpretar_webhook(ev, "s", PHONE_ID) == ([], [], [], [])


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
    (msg,), _, _, _ = meta.interpretar_webhook(_evento(mensagens=[_texto_in("wamid.in1", "Oi")]), SESSAO_META, PHONE_ID)
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


# ---------------------------------------------------------------------------
# Etapa 36C — modelos (templates) e janela de 24 h
# ---------------------------------------------------------------------------
from datetime import UTC, datetime, timedelta  # noqa: E402

from app.agenda import servico as S  # noqa: E402
from app.agenda.erros import AgendaError  # noqa: E402
from app.canais import modelos_meta  # noqa: E402
from app.config import Settings  # noqa: E402
from app.mensagens import regras as R  # noqa: E402
from app.mensagens import resumo_dia  # noqa: E402
from tests.conftest import AGORA, as_  # noqa: E402

TEL_CLIENTE = "+5511988887777"


def _cfg():
    return Settings(_env_file=None, env="prod", envio_somente_para="", waha_api_url="http://waha", waha_api_key="x")


def _meta_falsa(chamadas):
    return ClienteMeta(PHONE_ID, TOKEN, base_url="https://graph.test/v23.0", transport=_meta_simulada(chamadas))


def _recebeu_mensagem(conn, clinica, pid, quando):
    """O cliente escreveu para a clínica em `quando` (abre a janela de 24 h)."""
    cid = conn.execute("""insert into conversations (clinic_id, patient_id, channel, external_chat_id)
                          values (%s, %s, 'whatsapp', '5511988887777')
                          on conflict (clinic_id, patient_id, channel) do update set external_chat_id = excluded.external_chat_id
                          returning id""", (clinica.id, pid)).fetchone()[0]
    conn.execute("""insert into messages (clinic_id, conversation_id, direction, author, content, created_at)
                    values (%s, %s, 'in', 'paciente', 'oi', %s)""", (clinica.id, cid, quando))
    return cid


def test_catalogo_parametros_batem_com_os_exemplos():
    for m in modelos_meta.CATALOGO.values():
        n = len(set(re.findall(r"\{\{(\d+)\}\}", m.texto)))
        assert n == len(m.exemplo), m.nome
        pedido = modelos_meta.pedido_de_criacao(m)
        assert pedido["language"] == "pt_BR" and pedido["category"] in ("UTILITY", "MARKETING")
        assert all(len(b) <= 25 for b in m.botoes)
    assert modelos_meta.CATALOGO["temhorario_aniversario"].rodape  # marketing sempre com "PARAR"
    assert set(modelos_meta.POR_TIPO) >= {"lembrete", "confirmacao", "remarcacao", "cancelamento", "aniversario",
                                          "pos_consulta", "retorno", "tratamento"}


def test_parametro_sem_quebra_de_linha_e_nunca_vazio():
    assert modelos_meta._param("linha 1\nlinha 2\t  fim") == "linha 1 · linha 2 · fim"
    assert modelos_meta._param("") == "-" and modelos_meta._param(None) == "-"


def test_botoes_do_lembrete_valem_como_resposta():
    assert [R.resposta_ao_lembrete(b) for b in modelos_meta.CATALOGO["temhorario_lembrete"].botoes] == [
        "confirmar", "remarcar", "cancelar"]


def test_janela_de_24h(conn, clinica):
    pid = conn.execute("insert into patients (clinic_id, name, phone) values (%s, 'Rita Moraes', %s) returning id",
                       (clinica.id, TEL_CLIENTE)).fetchone()[0]
    assert not modelos_meta.janela_aberta(conn, clinica.id, pid, AGORA)
    _recebeu_mensagem(conn, clinica, pid, AGORA - timedelta(hours=25))
    assert not modelos_meta.janela_aberta(conn, clinica.id, pid, AGORA)
    _recebeu_mensagem(conn, clinica, pid, AGORA - timedelta(hours=23))
    assert modelos_meta.janela_aberta(conn, clinica.id, pid, AGORA)


def test_montar_modelos_da_agenda_e_campanha_sem_modelo(conn, clinica):
    c = S.marcar(conn, clinica.id, telefone=TEL_CLIENTE, nome="Rita Moraes", professional_id=clinica.prof_a,
                 service_id=clinica.servico, inicio=as_(24, 9), ator="recepcao", agora=AGORA)
    cl = S.carregar_clinica(conn, clinica.id)
    o = {"kind": "lembrete", "patient_id": c["patient_id"], "appointment_id": c["id"]}
    modelo, params, texto = modelos_meta.montar(conn, cl, o)
    assert modelo.nome == "temhorario_lembrete"
    assert params[0] == "Rita" and params[1] == cl["name"] and "24/11 às 09:00" in params[2] and "Dra. A" in params[3]
    assert "{{" not in texto and "Rita" in texto

    nova = S.remarcar(conn, clinica.id, appointment_id=c["id"], telefone=None, ator="recepcao",
                      novo_inicio=as_(25, 10), agora=AGORA)["consulta"]
    _, p_rem, _ = modelos_meta.montar(conn, cl, {"kind": "remarcacao", "patient_id": c["patient_id"],
                                                  "appointment_id": nova["id"]})
    assert "24/11 às 09:00" in p_rem[2] and "25/11 às 10:00" in p_rem[3]

    _, p_aniv, t_aniv = modelos_meta.montar(conn, cl, {"kind": "aniversario", "patient_id": c["patient_id"]})
    assert p_aniv == ["Rita", cl["name"]] and modelos_meta.RODAPE_PARAR in t_aniv

    with pytest.raises(modelos_meta.SemModelo):
        modelos_meta.montar(conn, cl, {"kind": "campanha", "patient_id": c["patient_id"]})


def _fila_meta(conn, clinica, kind="lembrete", body="Texto livre de sempre"):
    _na_meta(conn, clinica)
    pid = conn.execute("insert into patients (clinic_id, name, phone) values (%s, 'Rita Moraes', %s) returning id",
                       (clinica.id, TEL_CLIENTE)).fetchone()[0]
    oid = conn.execute("""insert into outbound_messages (clinic_id, patient_id, kind, body, scheduled_for)
                          values (%s, %s, %s, %s, %s) returning id""",
                       (clinica.id, pid, kind, body, AGORA - timedelta(minutes=1))).fetchone()[0]
    return pid, oid


def test_fila_fora_da_janela_sai_como_modelo(conn, clinica):
    pid, oid = _fila_meta(conn, clinica, kind="aniversario")
    chamadas: list = []
    assert envio.enviar_pendentes(SemCommit(conn), AGORA, cliente=_meta_falsa(chamadas), s=_cfg(), so_clinica=clinica.id) == 1
    corpo = json.loads(chamadas[0].content)
    assert corpo["type"] == "template" and corpo["template"]["name"] == "temhorario_aniversario"
    assert corpo["template"]["language"]["code"] == "pt_BR"
    assert [p["text"] for p in corpo["template"]["components"][0]["parameters"]][0] == "Rita"
    st, ext = conn.execute("select status, external_id from outbound_messages where id = %s", (oid,)).fetchone()
    assert (st, ext) == ("enviada", "wamid.ABC")
    gravada = conn.execute("""select content from messages where clinic_id = %s and external_id = 'wamid.ABC'""",
                           (clinica.id,)).fetchone()[0]
    assert gravada.startswith("Feliz aniversário, Rita!")  # a conversa mostra o texto do modelo, não o livre


def test_fila_dentro_da_janela_sai_como_texto(conn, clinica):
    pid, oid = _fila_meta(conn, clinica, kind="aniversario", body="Parabéns do jeito da clínica!")
    _recebeu_mensagem(conn, clinica, pid, AGORA - timedelta(hours=2))
    chamadas: list = []
    envio.enviar_pendentes(SemCommit(conn), AGORA, cliente=_meta_falsa(chamadas), s=_cfg(), so_clinica=clinica.id)
    corpo = json.loads(chamadas[0].content)
    assert corpo["type"] == "text" and corpo["text"]["body"] == "Parabéns do jeito da clínica!"


def test_campanha_fora_da_janela_falha_com_motivo_sem_tentar_de_novo(conn, clinica):
    _, oid = _fila_meta(conn, clinica, kind="campanha")
    chamadas: list = []
    envio.enviar_pendentes(SemCommit(conn), AGORA, cliente=_meta_falsa(chamadas), s=_cfg(), so_clinica=clinica.id)
    assert chamadas == []
    st, erro = conn.execute("select status, error from outbound_messages where id = %s", (oid,)).fetchone()
    assert st == "falhou" and "modelo" in erro


def test_equipe_fora_da_janela_recebe_aviso_claro(conn, clinica):
    _na_meta(conn, clinica)
    pid = conn.execute("insert into patients (clinic_id, name, phone) values (%s, 'Rita Moraes', %s) returning id",
                       (clinica.id, TEL_CLIENTE)).fetchone()[0]
    cid = _recebeu_mensagem(conn, clinica, pid, AGORA - timedelta(days=3))
    conversa = {"id": cid, "patient_id": pid, "external_chat_id": "5511988887777"}
    chamadas: list = []
    with pytest.raises(AgendaError) as e:
        whatsapp.enviar_da_equipe(conn, clinica.id, conversa, "Oi!", cliente=_meta_falsa(chamadas))
    assert e.value.codigo == "FORA_DA_JANELA" and chamadas == []
    conn.execute("update messages set created_at = now() where conversation_id = %s", (cid,))
    assert whatsapp.enviar_da_equipe(conn, clinica.id, conversa, "Oi!", cliente=_meta_falsa(chamadas)) == "wamid.ABC"


def test_resumo_do_dia_na_meta_vai_como_modelo():
    chamadas: list = []
    texto = ("Bom dia, Dra. A! ☀️\nHoje, terça-feira, 24/11, você tem 2 consultas na Clínica Teste:\n\n"
             "09:00 · Rita · Limpeza ✅\n10:00 · Bruno · Avaliação ⏳\n\n🕒 Livre: 11:00–12:00")
    resumo_dia._mandar(_meta_falsa(chamadas), "s", "+5511977776666", texto, "Dra. A", as_(24, 9).date(),
                       {"name": "Clínica Teste"})
    corpo = json.loads(chamadas[0].content)
    assert corpo["to"] == "5511977776666" and corpo["template"]["name"] == "temhorario_resumo_dia"
    params = [p["text"] for p in corpo["template"]["components"][0]["parameters"]]
    assert params[:3] == ["Dra. A", "terça-feira, 24/11", "Clínica Teste"]
    assert "09:00 · Rita · Limpeza ✅" in params[3] and "\n" not in params[3]


def test_criar_modelos_que_faltam_e_situacao():
    existentes = [{"name": "temhorario_lembrete", "language": "pt_BR", "status": "APPROVED"},
                  {"name": "temhorario_aniversario", "language": "pt_BR", "status": "REJECTED",
                   "rejected_reason": "INVALID_FORMAT"}]
    criados: list = []

    class Falso:
        def listar_modelos(self, waba):
            return existentes + [{"name": n, "language": "pt_BR", "status": "PENDING"} for n in criados]

        def criar_modelo(self, waba, pedido):
            criados.append(pedido["name"])
            return {"id": "1", "status": "PENDING"}

    lista = {m["nome"]: m for m in modelos_meta.criar_faltantes(Falso(), WABA_ID)}
    assert "temhorario_lembrete" not in criados and "temhorario_aniversario" not in criados  # já existem
    assert len(criados) == len(modelos_meta.CATALOGO) - 2
    assert lista["temhorario_lembrete"]["situacao"] == "aprovado"
    assert lista["temhorario_aniversario"]["situacao"] == "recusado"
    assert lista["temhorario_aniversario"]["motivo"] == "INVALID_FORMAT"
    assert lista["temhorario_confirmacao"]["situacao"] == "em análise"


# ---------------------------------------------------------------------------
# Etapa 36D — telas: Admin geral e Configurações › Canais
# ---------------------------------------------------------------------------
from tests.test_acesso import _como, _usuario, cliente  # noqa: E402, F401


def test_admin_geral_salva_testa_e_troca_o_provedor(cliente, conn, clinica, monkeypatch):  # noqa: F811
    sup = _como(cliente, _usuario(conn, super_admin=True))
    base = f"/api/admin/clinicas/{clinica.id}/whatsapp"
    assert sup.get(f"{base}/meta").json()["provedor"] == "waha"
    assert sup.put(f"{base}/provedor", json={"provedor": "meta"}).status_code == 422  # sem dados da Meta
    r = sup.put(f"{base}/meta", json={"phone_number_id": PHONE_ID, "waba_id": WABA_ID, "token": TOKEN, "app_secret": SEGREDO})
    assert r.status_code == 200 and r.json()["token_final"] == "wxyz" and TOKEN not in r.text

    monkeypatch.setattr(ClienteMeta, "testar", lambda self: {"numero": "+55 16 99112-2235", "nome": "Clínica", "qualidade": "GREEN"})
    assert sup.post(f"{base}/meta/testar").json()["ok"] is True

    assert sup.put(f"{base}/provedor", json={"provedor": "meta"}).json()["provedor"] == "meta"
    st = sup.get(base).json()  # status não chama o WAHA para clínica na Meta
    assert st["provedor"] == "meta" and st["ligado"] is True and st["sessao"] == SESSAO_META


def test_so_super_admin_mexe_na_meta(cliente, conn, clinica):  # noqa: F811
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    base = f"/api/admin/clinicas/{clinica.id}/whatsapp"
    assert adm.get(f"{base}/meta").status_code == 403
    assert adm.put(f"{base}/provedor", json={"provedor": "meta"}).status_code == 403


def test_canais_da_clinica_na_meta_sem_qr_nem_reinicio(cliente, conn, clinica, monkeypatch):  # noqa: F811
    _na_meta(conn, clinica)
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    base = f"/api/clinics/{clinica.id}/config/canais/whatsapp"
    monkeypatch.setattr(ClienteMeta, "testar", lambda self: {"numero": "+55 16 99112-2235", "nome": "C", "qualidade": None})
    r = adm.get(base).json()
    assert (r["provedor"], r["situacao"], r["numero"]) == ("meta", "conectado", "+55 16 99112-2235")
    assert adm.get(f"{base}/qr").status_code == 422
    assert adm.post(f"{base}/reiniciar").status_code == 422

    def cai(self):
        raise MetaErro("token expirado")
    monkeypatch.setattr(ClienteMeta, "testar", cai)
    assert adm.get(base).json()["situacao"] == "sem_resposta"


# ---------------------------------------------------------------------------
# Etapa 36E — custo das mensagens e campanhas como modelo de marketing
# ---------------------------------------------------------------------------
from app.canais import custo_meta  # noqa: E402
from app.mensagens import campanhas  # noqa: E402


def test_aviso_da_meta_traz_a_cobranca():
    ev = _evento(statuses=[
        {"id": "wamid.1", "status": "sent", "pricing": {"billable": True, "pricing_model": "PMP", "category": "utility"}},
        {"id": "wamid.2", "status": "delivered", "pricing": {"billable": False, "category": "service"}},
        {"id": "wamid.3", "status": "read"},
    ])
    *_, cobrancas = meta.interpretar_webhook(ev, SESSAO_META, PHONE_ID)
    assert cobrancas == [("wamid.1", "utility", True), ("wamid.2", "service", False)]


def test_gasto_do_mes_desconta_atendimento_gratis(conn, clinica):
    conn.execute("""update platform_settings set meta_servico_gratis = 2, cotacao_brl = 5,
                    meta_precos_usd = '{"marketing": 0.06, "utility": 0.01, "service": 0.01, "authentication": 0.01}'::jsonb
                    where id = 1""")
    cob = [(f"s{i}", "service", True) for i in range(3)] + [("u1", "utility", True), ("m1", "marketing", True),
                                                            ("m2", "marketing", True), ("x", "utility", False)]
    assert custo_meta.registrar(conn, clinica.id, cob) == 7
    assert custo_meta.registrar(conn, clinica.id, [("u1", "utility", True)]) == 0  # o mesmo aviso de novo não conta
    r = custo_meta.do_mes(conn, clinica.id, datetime.now(UTC))
    por = {linha["categoria"]: linha for linha in r["linhas"]}
    assert (por["service"]["mensagens"], por["service"]["cobradas"]) == (3, 1)  # 2 grátis
    assert por["utility"]["mensagens"] == 1  # a não cobrável fica de fora
    assert por["marketing"]["cobradas"] == 2
    assert r["total_usd"] == pytest.approx(0.01 + 0.01 + 0.12)
    assert r["total_brl"] == pytest.approx(0.70)


def test_webhook_repassa_as_cobrancas(conn, clinica, monkeypatch):
    from app.api import webhooks

    _na_meta(conn, clinica)
    t = _token_webhook(conn, clinica)
    achado = conexao.por_token_meta(conn, t)
    monkeypatch.setattr(conexao, "por_token_meta", lambda c, tk, exigir_meta=True: achado if tk == t else None)
    recebidas: list = []
    monkeypatch.setattr(webhooks.custo_meta, "processar", lambda cid, cob: recebidas.append((cid, cob)))
    corpo = json.dumps(_evento(statuses=[{"id": "w9", "status": "sent", "pricing": {"billable": True, "category": "marketing"}}])).encode()
    assert TestClient(app).post(f"/webhooks/meta/{t}", content=corpo, headers={"x-hub-signature-256": _assinar(corpo)}).status_code == 200
    assert recebidas == [(clinica.id, [("w9", "marketing", True)])]


def test_texto_da_campanha_no_formato_da_meta():
    assert modelos_meta.texto_campanha("Olá, {nome}! A {clinica} deseja boas festas.", "Clínica X") == \
        "Olá, {{1}}! A Clínica X deseja boas festas."
    with pytest.raises(ValueError, match="só uma vez"):
        modelos_meta.texto_campanha("{nome}, oi {nome}", "X")
    with pytest.raises(ValueError, match="começar nem terminar"):
        modelos_meta.texto_campanha("Feliz Natal, {nome}", "X")
    pedido = modelos_meta.pedido_campanha("abc-123", "Aviso: a {clinica} fecha dia 24.", "Clínica X")
    assert pedido["category"] == "MARKETING" and "example" not in pedido["components"][0]
    assert pedido["components"][1] == {"type": "FOOTER", "text": modelos_meta.RODAPE_PARAR}


def _campanha_na_meta(conn, clinica, monkeypatch):
    _na_meta(conn, clinica)
    pid = conn.execute("insert into patients (clinic_id, name, phone) values (%s, 'Rita Moraes', %s) returning id",
                       (clinica.id, TEL_CLIENTE)).fetchone()[0]
    conn.execute("""insert into appointments (clinic_id, patient_id, professional_id, service_id, starts_at, ends_at, status)
                    values (%s, %s, %s, %s, %s, %s, 'realizada')""",
                 (clinica.id, pid, clinica.prof_a, clinica.servico, AGORA - timedelta(days=30), AGORA - timedelta(days=30, minutes=-60)))
    pedidos: list = []
    monkeypatch.setattr(ClienteMeta, "criar_modelo", lambda self, waba, pedido: pedidos.append(pedido) or {"id": "1"})
    r = campanhas.criar(conn, clinica.id, titulo="Natal", texto="Olá, {nome}! A {clinica} deseja boas festas.",
                        publico="todos", enviar_em=AGORA, autor=None, agora=AGORA)
    return r["id"], pedidos


def test_criar_campanha_na_meta_manda_o_modelo_para_aprovar(conn, clinica, monkeypatch):
    cid, pedidos = _campanha_na_meta(conn, clinica, monkeypatch)
    assert len(pedidos) == 1 and pedidos[0]["category"] == "MARKETING"
    nome, sit = conn.execute("select meta_modelo, meta_situacao from campaigns where id = %s", (cid,)).fetchone()
    assert nome == modelos_meta.nome_modelo_campanha(cid) and sit == "em análise"


def test_campanha_espera_aprovacao_e_depois_sai_como_modelo(conn, clinica, monkeypatch):
    cid, _ = _campanha_na_meta(conn, clinica, monkeypatch)
    nome = modelos_meta.nome_modelo_campanha(cid)
    situacao = {"status": "PENDING"}
    monkeypatch.setattr(ClienteMeta, "listar_modelos", lambda self, waba: [{"name": nome, "language": "pt_BR", **situacao}])
    chamadas: list = []
    envio.enviar_pendentes(SemCommit(conn), AGORA, cliente=_meta_falsa(chamadas), s=_cfg(), so_clinica=clinica.id)
    assert chamadas == []  # em análise: não manda
    st, erro, quando = conn.execute("select status, error, scheduled_for from outbound_messages where campaign_id = %s",
                                    (cid,)).fetchone()
    assert st == "agendada" and "aprovar" in erro and quando > AGORA

    situacao["status"] = "APPROVED"
    depois = AGORA + timedelta(minutes=31)
    envio.enviar_pendentes(SemCommit(conn), depois, cliente=_meta_falsa(chamadas), s=_cfg(), so_clinica=clinica.id)
    corpo = json.loads(chamadas[0].content)
    assert corpo["template"]["name"] == nome
    assert [p["text"] for p in corpo["template"]["components"][0]["parameters"]] == ["Rita"]
    assert conn.execute("select status from outbound_messages where campaign_id = %s", (cid,)).fetchone()[0] == "enviada"


def test_campanha_recusada_falha_com_motivo(conn, clinica, monkeypatch):
    cid, _ = _campanha_na_meta(conn, clinica, monkeypatch)
    nome = modelos_meta.nome_modelo_campanha(cid)
    monkeypatch.setattr(ClienteMeta, "listar_modelos", lambda self, waba: [
        {"name": nome, "language": "pt_BR", "status": "REJECTED", "rejected_reason": "PROMOTIONAL"}])
    chamadas: list = []
    envio.enviar_pendentes(SemCommit(conn), AGORA, cliente=_meta_falsa(chamadas), s=_cfg(), so_clinica=clinica.id)
    st, erro = conn.execute("select status, error from outbound_messages where campaign_id = %s", (cid,)).fetchone()
    assert chamadas == [] and st == "falhou" and "recusado" in erro and "PROMOTIONAL" in erro


def test_campanha_no_waha_nao_chama_a_meta(conn, clinica, monkeypatch):
    pid = conn.execute("insert into patients (clinic_id, name, phone) values (%s, 'Rita Moraes', %s) returning id",
                       (clinica.id, TEL_CLIENTE)).fetchone()[0]
    conn.execute("""insert into appointments (clinic_id, patient_id, professional_id, service_id, starts_at, ends_at, status)
                    values (%s, %s, %s, %s, %s, %s, 'realizada')""",
                 (clinica.id, pid, clinica.prof_a, clinica.servico, AGORA - timedelta(days=30), AGORA - timedelta(days=30, minutes=-60)))
    monkeypatch.setattr(ClienteMeta, "criar_modelo", lambda *a: pytest.fail("não podia chamar a Meta"))
    r = campanhas.criar(conn, clinica.id, titulo="Natal", texto="Olá, {nome}! Boas festas.", publico="todos",
                        enviar_em=AGORA, autor=None, agora=AGORA)
    assert conn.execute("select meta_modelo from campaigns where id = %s", (r["id"],)).fetchone()[0] is None


def test_custo_so_para_clinica_na_meta(cliente, conn, clinica):  # noqa: F811
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    url = f"/api/clinics/{clinica.id}/config/canais/whatsapp/custo"
    assert adm.get(url).status_code == 422
    _na_meta(conn, clinica)
    assert {x["categoria"] for x in adm.get(url).json()["linhas"]} >= {"service", "utility", "marketing"}
