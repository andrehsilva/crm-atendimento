"""Etapa 19 — sino de notificações (D81–D83)."""

from uuid import uuid4

from app import notificacoes as N
from app.agenda import servico as S
from tests.conftest import AGORA, as_
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401 — fixture reaproveitada

TEL = "+5511977771234"


def _marcar(conn, clinica, inicio, ator="isis", tel=TEL):
    return S.marcar(conn, clinica.id, telefone=tel, nome="Carla Dias", professional_id=clinica.prof_a,
                    service_id=clinica.servico, inicio=inicio, ator=ator, agora=AGORA)


def _tipos(r):
    return [i["tipo"] for i in r["itens"]]


def test_o_que_a_isis_fez_na_agenda_aparece_e_o_da_recepcao_nao(conn, clinica):
    u = uuid4()
    _marcar(conn, clinica, as_(24, 14), ator="recepcao", tel="+5511977775555")
    c = _marcar(conn, clinica, as_(24, 9))
    S.remarcar(conn, clinica.id, appointment_id=c["id"], telefone=TEL, ator="isis", novo_inicio=as_(25, 9), agora=AGORA)
    r = N.listar(conn, clinica.id, u)
    # a remarcação aparece uma vez só (a consulta nova não vira "marcou")
    assert sorted(_tipos(r)) == ["marcada", "remarcada"]
    marcou = next(i for i in r["itens"] if i["tipo"] == "marcada")
    assert marcou["titulo"] == "Ísis marcou uma consulta" and "Carla Dias" in marcou["texto"] and "terça-feira, 24/11" in marcou["texto"]
    assert r["contador"] == 2 and r["aguardando"] == 0
    assert marcou["consulta_id"] == c["id"] and marcou["dia"] == "2026-11-24"
    # remarcou: aponta para a consulta NOVA, no dia novo
    remarcou = next(i for i in r["itens"] if i["tipo"] == "remarcada")
    assert remarcou["dia"] == "2026-11-25" and remarcou["consulta_id"] != c["id"]
    assert "agora quarta-feira, 25/11" in remarcou["texto"] and "era terça-feira, 24/11" in remarcou["texto"]


def test_confirmacao_do_paciente(conn, clinica):
    c = _marcar(conn, clinica, as_(24, 9), ator="recepcao")
    S.mudar_status(conn, clinica.id, appointment_id=c["id"], novo="confirmada", ator="paciente", telefone=TEL)
    r = N.listar(conn, clinica.id, uuid4())
    assert _tipos(r) == ["confirmada"] and r["itens"][0]["titulo"] == "Carla Dias confirmou a consulta"


def test_cada_pessoa_tem_a_sua_leitura(conn, clinica):
    ana, bia = uuid4(), uuid4()
    _marcar(conn, clinica, as_(24, 9))
    _marcar(conn, clinica, as_(24, 10), tel="+5511977775555")
    chave = N.listar(conn, clinica.id, ana)["itens"][0]["chave"]
    N.marcar_lidas(conn, clinica.id, ana, [chave])
    assert N.listar(conn, clinica.id, ana)["contador"] == 1
    assert N.listar(conn, clinica.id, bia)["contador"] == 2  # a leitura da Ana não vale para a Bia
    N.marcar_lidas(conn, clinica.id, ana, None)  # "marcar todas"
    r = N.listar(conn, clinica.id, ana)
    assert r["contador"] == 0 and len(r["itens"]) == 2  # continuam na lista, só que lidas


def test_aguardando_humano_some_sozinho_e_nao_se_marca(conn, clinica):
    u = uuid4()
    p = S.obter_ou_criar_paciente(conn, clinica.id, TEL, "Maria Souza", "whatsapp")
    cv = conn.execute("insert into conversations (clinic_id, patient_id, channel, status) values (%s, %s, 'whatsapp', 'humano') returning id",
                      (clinica.id, p["id"])).fetchone()[0]
    conn.execute("insert into messages (clinic_id, conversation_id, direction, author, content) values (%s, %s, 'in', 'paciente', 'Quero falar com alguém')",
                 (clinica.id, cv))
    r = N.listar(conn, clinica.id, u)
    item = r["itens"][0]
    assert item["titulo"] == "Maria Souza aguardando atendimento humano" and item["texto"] == "Quero falar com alguém"
    assert item["situacao"] and item["paciente"]["id"] == p["id"] and r["aguardando"] == 1 and r["contador"] == 1
    N.marcar_lidas(conn, clinica.id, u, [item["chave"]])
    assert N.listar(conn, clinica.id, u)["contador"] == 1  # não some marcando
    conn.execute("update conversations set status = 'ativa' where id = %s", (cv,))  # alguém resolveu
    assert N.listar(conn, clinica.id, u)["itens"] == []


def test_whatsapp_desconectado_e_mensagem_que_nao_saiu(conn, clinica):
    conn.execute("insert into whatsapp_instances (clinic_id, session, status) values (%s, 'clinica_a', 'SCAN_QR_CODE')", (clinica.id,))
    c = _marcar(conn, clinica, as_(24, 9), ator="recepcao")
    conn.execute("update outbound_messages set status = 'falhou', error = 'número sem WhatsApp' where appointment_id = %s", (c["id"],))
    r = N.listar(conn, clinica.id, uuid4())
    assert r["itens"][0]["tipo"] == "whatsapp" and r["itens"][0]["situacao"]
    falhou = next(i for i in r["itens"] if i["tipo"] == "falhou")
    assert "Carla Dias" in falhou["texto"] and "número sem WhatsApp" in falhou["texto"]
    conn.execute("update whatsapp_instances set status = 'WORKING' where clinic_id = %s", (clinica.id,))
    assert "whatsapp" not in _tipos(N.listar(conn, clinica.id, uuid4()))


def test_gasto_da_ia(conn, clinica, monkeypatch):
    monkeypatch.setattr(N.uso_ia, "situacao", lambda conn, cid: {"nivel": "aviso", "pct": 83.4})
    u = uuid4()
    r = N.listar(conn, clinica.id, u)
    assert r["itens"][0]["titulo"] == "Gasto da IA em 83% do teto do mês" and r["contador"] == 1
    N.marcar_lidas(conn, clinica.id, u, None)
    assert N.listar(conn, clinica.id, u)["contador"] == 0


def test_rota_so_mostra_a_propria_clinica(cliente, conn, clinica, outra_clinica):  # noqa: F811
    _marcar(conn, clinica, as_(24, 9))
    rec_b = _como(cliente, _usuario(conn, clinic_id=outra_clinica.id, papel="reception"))
    assert rec_b.get(f"/api/clinics/{clinica.id}/notificacoes").status_code == 403
    assert rec_b.get(f"/api/clinics/{outra_clinica.id}/notificacoes").json()["itens"] == []
    rec_a = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    r = rec_a.get(f"/api/clinics/{clinica.id}/notificacoes").json()
    assert r["contador"] == 1
    assert rec_a.post(f"/api/clinics/{clinica.id}/notificacoes/lidas", json={}).json()["contador"] == 0
