"""Etapa 25 — pós-consulta e retorno automáticos (RN-AU, D100–D103)."""

from datetime import timedelta

from app import tratamentos as T
from app.agenda import servico as S
from app.mensagens import automacoes as A
from app.mensagens import envio
from tests.conftest import AGORA, as_
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401 — fixture reaproveitada

TEL = "+5511977775151"


def _ligar(conn, clinica, **extra):
    conn.execute("""update clinics set settings = settings || %s::jsonb where id = %s""",
                  (__import__("json").dumps({"pos_consulta_ativo": True, "retorno_ativo": True, **extra}), clinica.id))


def _fila(conn, clinica, kind):
    return conn.execute("select body, scheduled_for, dedupe_key from outbound_messages where clinic_id = %s and kind = %s "
                        "order by dedupe_key, created_at", (clinica.id, kind)).fetchall()


def _visita(conn, clinica, quando, tel=TEL, nome="Lia Souza"):
    p = S.obter_ou_criar_paciente(conn, clinica.id, tel, nome, "manual")
    conn.execute("""insert into appointments (clinic_id, patient_id, professional_id, service_id, starts_at, ends_at, status)
                    values (%s, %s, %s, %s, %s::timestamptz, %s::timestamptz + interval '1 hour', 'realizada')""",
                 (clinica.id, p["id"], clinica.prof_a, clinica.servico, quando, quando))
    return p


def test_pos_consulta_no_dia_seguinte(conn, clinica):
    c = conn.execute(
        """insert into appointments (clinic_id, patient_id, professional_id, service_id, starts_at, ends_at)
           values (%s, %s, %s, %s, %s, %s) returning id""",
        (clinica.id, S.obter_ou_criar_paciente(conn, clinica.id, TEL, "Lia Souza", "manual")["id"],
         clinica.prof_a, clinica.servico, AGORA - timedelta(hours=2), AGORA - timedelta(hours=1))).fetchone()[0]
    S.mudar_status(conn, clinica.id, appointment_id=c, novo="realizada", ator="recepcao")
    assert _fila(conn, clinica, "pos_consulta") == []  # começa desligado (RN-AU-01)
    conn.execute("update appointments set status = 'agendada' where id = %s", (c,))
    _ligar(conn, clinica)
    S.mudar_status(conn, clinica.id, appointment_id=c, novo="realizada", ator="recepcao")
    [(corpo, quando, _)] = _fila(conn, clinica, "pos_consulta")
    assert corpo.startswith("Olá, Lia! Aqui é da Clínica Teste A. Como você está")
    local = quando.astimezone(S.carregar_clinica(conn, clinica.id)["tz"])
    assert local.hour == 10 and local.minute == 0  # dia seguinte às 10:00
    assert A.agendar_pos_consulta(conn, S.carregar_clinica(conn, clinica.id),
                                  S._cur(conn).execute("select * from appointments where id = %s", (c,)).fetchone()) is False  # uma só


def test_pos_consulta_procedimento_desligado(conn, clinica):
    _ligar(conn, clinica, pos_consulta_excluir=[str(clinica.servico)])
    cl = S.carregar_clinica(conn, clinica.id)
    p = S.obter_ou_criar_paciente(conn, clinica.id, TEL, "Lia Souza", "manual")
    assert A.agendar_pos_consulta(conn, cl, {"id": p["id"], "patient_id": p["id"], "service_id": clinica.servico,
                                             "starts_at": AGORA}) is False


def test_retorno_convite_segundo_convite_e_para(conn, clinica):
    _ligar(conn, clinica)
    _visita(conn, clinica, "2026-05-20 10:00-03")  # 6 meses → vence 20/11
    agora = as_(20, 10, 5)
    assert A.gerar_retornos(conn, as_(20, 9, 59), so_clinica=clinica.id) == 0  # antes das 10:00
    assert A.gerar_retornos(conn, agora, so_clinica=clinica.id) == 1
    assert A.gerar_retornos(conn, agora, so_clinica=clinica.id) == 0  # não repete
    assert A.gerar_retornos(conn, agora + timedelta(days=10), so_clinica=clinica.id) == 0  # ainda não deu 15 dias
    assert A.gerar_retornos(conn, agora + timedelta(days=16), so_clinica=clinica.id) == 1  # 2º convite (D103)
    assert A.gerar_retornos(conn, agora + timedelta(days=40), so_clinica=clinica.id) == 0  # depois, para
    corpos = [b for b, _, _ in _fila(conn, clinica, "retorno")]
    assert corpos[0].startswith("Olá, Lia! Já está na hora") and corpos[1].startswith("Oi, Lia! Passando")


def test_retorno_respondeu_nao_insiste(conn, clinica):
    _ligar(conn, clinica)
    p = _visita(conn, clinica, "2026-05-20 10:00-03")
    A.gerar_retornos(conn, as_(20, 10, 5), so_clinica=clinica.id)
    conn.execute("update outbound_messages set sent_at = %s where clinic_id = %s and kind = 'retorno'", (as_(20, 10, 6), clinica.id))
    cv = conn.execute("insert into conversations (clinic_id, patient_id, channel) values (%s, %s, 'whatsapp') returning id",
                      (clinica.id, p["id"])).fetchone()[0]
    conn.execute("""insert into messages (clinic_id, conversation_id, direction, author, content, created_at)
                    values (%s, %s, 'in', 'paciente', 'Agora não, obrigada', %s)""", (clinica.id, cv, as_(21, 9)))
    assert A.gerar_retornos(conn, as_(20, 10, 5) + timedelta(days=16), so_clinica=clinica.id) == 0


def test_quem_nao_recebe_retorno(conn, clinica):
    _ligar(conn, clinica)
    _visita(conn, clinica, "2024-01-10 10:00-03", tel="+5511900000101", nome="Muito Antigo")  # venceu há muito: só recall
    futuro = _visita(conn, clinica, "2026-05-20 10:00-03", tel="+5511900000102", nome="Tem Marcada")
    conn.execute("""insert into appointments (clinic_id, patient_id, professional_id, service_id, starts_at, ends_at)
                    values (%s, %s, %s, %s, '2026-12-10 10:00-03', '2026-12-10 11:00-03')""",
                 (clinica.id, futuro["id"], clinica.prof_a, clinica.servico))
    trat = _visita(conn, clinica, "2026-05-20 10:00-03", tel="+5511900000103", nome="Em Tratamento")
    T.criar(conn, clinica.id, trat["id"], service_id=clinica.servico, professional_id=None, sessoes_previstas=None,
            intervalo_dias=None, orientacao=None)
    parou = _visita(conn, clinica, "2026-05-20 10:00-03", tel="+5511900000104", nome="Pediu Parar")
    conn.execute("update patients set optout_disparos = true where id = %s", (parou["id"],))
    # volta_em do tratamento concluído vale mesmo com visita recente
    volta = _visita(conn, clinica, "2026-10-01 10:00-03", tel="+5511900000105", nome="Volta Hoje")
    t = T.criar(conn, clinica.id, volta["id"], service_id=clinica.servico, professional_id=None, sessoes_previstas=None,
                intervalo_dias=None, orientacao=None)
    T.encerrar(conn, clinica.id, t["id"], status="concluido", volta_em=as_(20, 0).date())
    assert A.gerar_retornos(conn, as_(20, 10, 5), so_clinica=clinica.id) == 1
    assert _fila(conn, clinica, "retorno")[0][0].startswith("Olá, Volta!")
    assert "pos_consulta" in envio.RESPEITA_PARAR and "retorno" in envio.MASSA  # PARAR e espaçamento (RN-AU-05)


def test_rotas(cliente, conn, clinica):  # noqa: F811
    url = f"/api/clinics/{clinica.id}/mensagens/automacoes"
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    cfg = rec.get(url).json()
    assert cfg["pos_consulta_ativo"] is False and cfg["retorno_meses"] == 6 and "Clínica Teste A" in cfg["previa"]["retorno"]
    corpo = {k: cfg[k] for k in A.PADRAO}
    assert rec.put(url, json={**corpo, "retorno_ativo": True}).status_code == 403
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    assert adm.put(url, json={**corpo, "retorno_ativo": True, "retorno_meses": 12}).json()["retorno_meses"] == 12
