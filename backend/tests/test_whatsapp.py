"""Etapa 5 — WhatsApp pelo WAHA, SEM chamar a IA nem o WAHA de verdade (a Ísis e o WAHA são simulados)."""

import pytest

from app.agenda.erros import AgendaError
from app.canais import waha, whatsapp
from app.canais.waha import MensagemEntrada, WahaErro, interpretar, verificar_assinatura
from app.painel import chat

SESSAO = "clinica-teste"


# ---------------------------------------------------------------------------
# Assinatura e leitura do webhook (sem banco)
# ---------------------------------------------------------------------------
def test_assinatura_hmac_exemplo_da_documentacao():
    corpo = b'{"event":"message","session":"default","engine":"WEBJS"}'
    ok = ("208f8a55dde9e05519e898b10b89bf0d0b3b0fdf11fdbf09b6b90476301b98d8"
          "097c462b2b17a6ce93b6b47a136cf2e78a33a63f6752c2c1631777076153fa89")
    assert verificar_assinatura(corpo, ok, "my-secret-key")
    assert not verificar_assinatura(corpo, ok, "outra-chave")
    assert not verificar_assinatura(corpo, None, "my-secret-key")


def _evento(**payload):
    base = {"id": "false_5511988887777@c.us_AAA", "from": "5511988887777@c.us", "fromMe": False,
            "body": "Oi, quero marcar", "hasMedia": False, "_data": {"notifyName": "Rita"}}
    return {"event": "message", "session": SESSAO, "me": {"id": "5511900000001@c.us"}, "payload": {**base, **payload}}


def test_interpreta_mensagem_normal():
    m = interpretar(_evento())
    assert m.telefone == "+5511988887777" and m.chat_id == "5511988887777@c.us"
    assert m.texto == "Oi, quero marcar" and m.sessao == SESSAO and m.id_externo and m.nome == "Rita"


@pytest.mark.parametrize("payload", [
    {"fromMe": True},                       # mensagem enviada pela própria clínica
    {"from": "120363000000@g.us"},          # grupo
    {"from": "status@broadcast"},           # status
    {"from": "123@newsletter"},             # canal
    {"body": "", "hasMedia": False},        # vazia
])
def test_ignora_o_que_nao_e_conversa_com_paciente(payload):
    assert interpretar(_evento(**payload)) is None


def test_ignora_outros_eventos():
    assert interpretar({"event": "message.ack", "payload": {}}) is None


def test_midia_sem_texto_vira_aviso_para_a_isis():
    assert interpretar(_evento(body="", hasMedia=True)).texto == waha.TEXTO_MIDIA


def test_lid_acha_numero_no_data():
    m = interpretar(_evento(**{"from": "99887766@lid", "_data": {"key": {"remoteJidAlt": "5511988887777@s.whatsapp.net"}}}))
    assert m.chat_id == "99887766@lid" and m.telefone == "+5511988887777"


def test_lid_sem_numero_fica_sem_telefone():
    assert interpretar(_evento(**{"from": "99887766@lid", "_data": {}})).telefone is None


# ---------------------------------------------------------------------------
# Processamento com banco (Ísis e WAHA simulados)
# ---------------------------------------------------------------------------
class SemCommit:
    """Repassa tudo para a conexão do teste, mas não confirma nada (o teste desfaz tudo no fim)."""

    def __init__(self, conn):
        self._c = conn

    def commit(self):
        pass

    def __getattr__(self, nome):
        return getattr(self._c, nome)


class WahaFalso:
    def __init__(self, falhar=False):
        self.enviadas, self.falhar = [], falhar

    def enviar_texto(self, sessao, chat_id, texto, simular_digitacao=None):
        if self.falhar:
            raise WahaErro("WAHA fora do ar")
        self.enviadas.append((sessao, chat_id, texto))
        return f"true_{chat_id}_OUT{len(self.enviadas)}"

    def numero_do_lid(self, sessao, lid):
        return None


@pytest.fixture
def isis_falsa(monkeypatch):
    monkeypatch.setattr(chat.isis, "responder", lambda conn, clinica, paciente, conversa, texto, em, ia=None: f"Resposta para: {texto}")


@pytest.fixture
def ligada(conn, clinica):
    conn.execute("insert into whatsapp_instances (clinic_id, session) values (%s, %s)", (clinica.id, SESSAO))
    return clinica


def _msg(texto="Oi", id_ext="false_5511988887777@c.us_M1", chat_id="5511988887777@c.us", tel="+5511988887777"):
    return MensagemEntrada(sessao=SESSAO, chat_id=chat_id, telefone=tel, texto=texto, id_externo=id_ext)


def _mensagens(conn, clinica):
    return conn.execute(
        "select author, content, external_id from messages where clinic_id = %s order by created_at, direction", (clinica.id,)
    ).fetchall()


def test_mensagem_do_whatsapp_cria_paciente_e_responde(conn, ligada, isis_falsa):
    w = WahaFalso()
    whatsapp.processar_com(SemCommit(conn), _msg("Quero marcar"), w)
    assert w.enviadas == [(SESSAO, "5511988887777@c.us", "Resposta para: Quero marcar")]
    p = conn.execute("select origin from patients where clinic_id = %s and phone = '+5511988887777'", (ligada.id,)).fetchone()
    assert p[0] == "whatsapp"
    cv = conn.execute("select channel, external_chat_id from conversations where clinic_id = %s", (ligada.id,)).fetchone()
    assert cv == ("whatsapp", "5511988887777@c.us")
    msgs = _mensagens(conn, ligada)
    assert [m[0] for m in msgs] == ["paciente", "isis"] and msgs[1][2] == "true_5511988887777@c.us_OUT1"


def test_webhook_duplicado_nao_responde_duas_vezes(conn, ligada, isis_falsa):
    w = WahaFalso()
    whatsapp.processar_com(SemCommit(conn), _msg(), w)
    whatsapp.processar_com(SemCommit(conn), _msg(), w)  # mesmo id externo
    assert len(w.enviadas) == 1 and len(_mensagens(conn, ligada)) == 2


def test_isis_pausada_nao_envia_nada(conn, ligada, isis_falsa):
    w = WahaFalso()
    whatsapp.processar_com(SemCommit(conn), _msg(id_ext="M1"), w)
    conn.execute("update conversations set status = 'humano' where clinic_id = %s", (ligada.id,))
    whatsapp.processar_com(SemCommit(conn), _msg("Alguém aí?", id_ext="M2"), w)
    assert len(w.enviadas) == 1
    msgs = [m[:2] for m in _mensagens(conn, ligada)]
    assert len(msgs) == 3 and ("paciente", "Alguém aí?") in msgs  # gravou, mas a Ísis não respondeu


def test_falha_no_envio_aparece_no_painel(conn, ligada, isis_falsa):
    whatsapp.processar_com(SemCommit(conn), _msg(), WahaFalso(falhar=True))
    autores = sorted(m[0] for m in _mensagens(conn, ligada))
    assert autores == ["isis", "paciente", "sistema"]


def test_sessao_sem_clinica_e_ignorada(conn, clinica, isis_falsa):
    w = WahaFalso()
    whatsapp.processar_com(SemCommit(conn), _msg(), w)
    assert w.enviadas == [] and _mensagens(conn, clinica) == []


def test_lid_sem_numero_e_ignorado(conn, ligada, isis_falsa):
    w = WahaFalso()
    whatsapp.processar_com(SemCommit(conn), _msg(chat_id="123@lid", tel=None), w)
    assert w.enviadas == [] and _mensagens(conn, ligada) == []


def test_clinicas_nao_se_misturam(conn, ligada, outra_clinica, isis_falsa):
    """A clínica vem da SESSÃO do WAHA: a mensagem da sessão da clínica A nunca cai na B."""
    whatsapp.processar_com(SemCommit(conn), _msg(), WahaFalso())
    assert _mensagens(conn, outra_clinica) == []


def test_equipe_responde_pelo_whatsapp(conn, ligada, isis_falsa):
    w = WahaFalso()
    whatsapp.processar_com(SemCommit(conn), _msg(), w)
    cv = conn.execute("select id, external_chat_id from conversations where clinic_id = %s", (ligada.id,)).fetchone()
    whatsapp.enviar_da_equipe(conn, ligada.id, {"id": cv[0], "external_chat_id": cv[1]}, "Olá, aqui é a Paula", cliente=w)
    assert w.enviadas[-1] == (SESSAO, "5511988887777@c.us", "Olá, aqui é a Paula")


def test_equipe_sem_whatsapp_conectado_recebe_erro_claro(conn, clinica):
    with pytest.raises(AgendaError) as e:
        whatsapp.enviar_da_equipe(conn, clinica.id, {"id": None, "external_chat_id": "x@c.us"}, "oi", cliente=WahaFalso())
    assert e.value.codigo == "DADOS_INVALIDOS"


# ---------------------------------------------------------------------------
# Rota do webhook
# ---------------------------------------------------------------------------
def test_webhook_recusa_assinatura_errada_e_aceita_a_certa(monkeypatch):
    import hashlib
    import hmac
    import json

    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.main import app

    monkeypatch.setattr(get_settings(), "waha_webhook_hmac_key", "segredo-teste")
    corpo = json.dumps({"event": "message.ack", "session": SESSAO, "payload": {}}).encode()
    cliente = TestClient(app)
    r = cliente.post("/webhooks/waha", content=corpo, headers={"X-Webhook-Hmac": "errada"})
    assert r.status_code == 401
    certa = hmac.new(b"segredo-teste", corpo, hashlib.sha512).hexdigest()
    r = cliente.post("/webhooks/waha", content=corpo, headers={"X-Webhook-Hmac": certa})
    assert r.status_code == 200 and r.json()["ignorada"] is True
