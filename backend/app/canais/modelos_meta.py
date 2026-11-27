"""Modelos (templates) do WhatsApp oficial — Etapa 36C (D131).

Regra da Meta: fora da janela de 24 h (contada da última mensagem que o cliente mandou) só sai **modelo aprovado**.
- Janela aberta → sai o texto de sempre (o mesmo do WAHA), como mensagem comum.
- Janela fechada → sai o modelo do TemHorario para aquele tipo, com as partes variáveis (nome, data, profissional…).

O catálogo é fixo e igual para todas as clínicas: criamos os modelos na conta da Meta da clínica (botão no Admin geral)
e a Meta aprova cada um. Os textos editáveis da clínica (aniversário, pós-consulta…) valem dentro da janela; fora dela
vale o texto do modelo. Campanhas no WhatsApp oficial ficam para a Etapa 36E (cada campanha vira um modelo próprio).
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from uuid import UUID

from psycopg.rows import dict_row

IDIOMA = "pt_BR"
JANELA = timedelta(hours=24)
RODAPE_PARAR = "Responda PARAR para não receber mais."


@dataclass(frozen=True)
class Modelo:
    nome: str
    categoria: str  # UTILITY | MARKETING
    texto: str  # com {{1}}, {{2}}… (a Meta não aceita parâmetro com quebra de linha)
    exemplo: tuple[str, ...]
    botoes: tuple[str, ...] = ()
    rodape: str | None = None
    tipos: tuple[str, ...] = field(default=())  # kinds de outbound_messages que usam este modelo


CATALOGO: dict[str, Modelo] = {m.nome: m for m in (
    Modelo("temhorario_lembrete", "UTILITY",
           "Olá, {{1}}! Passando para lembrar do seu horário na {{2}}.\n\n📅 {{3}}\n{{4}}\n\nPode confirmar?",
           ("Ana", "Clínica Sorriso", "terça-feira, 24/11 às 09:00", "🦷 Limpeza com Dra. Paula"),
           botoes=("Confirmar", "Remarcar", "Cancelar"), tipos=("lembrete",)),
    Modelo("temhorario_confirmacao", "UTILITY",
           "Olá, {{1}}! Seu horário na {{2}} está marcado ✅\n\n📅 {{3}}\n{{4}}\n📍 {{5}}\n\n"
           "Precisa remarcar ou cancelar? É só responder esta mensagem.",
           ("Ana", "Clínica Sorriso", "terça-feira, 24/11 às 09:00", "🦷 Limpeza com Dra. Paula", "Rua das Flores, 100"),
           tipos=("confirmacao",)),
    Modelo("temhorario_remarcacao", "UTILITY",
           "Olá, {{1}}! Seu horário na {{2}} foi remarcado 🔄\n\nAntes: {{3}}\nAgora: 📅 {{4}}\n{{5}}",
           ("Ana", "Clínica Sorriso", "segunda-feira, 23/11 às 10:00", "terça-feira, 24/11 às 09:00",
            "🦷 Limpeza com Dra. Paula"), tipos=("remarcacao",)),
    Modelo("temhorario_cancelamento", "UTILITY",
           "Olá, {{1}}. Seu horário de {{2}} na {{3}} foi cancelado.\n\n"
           "Quando quiser marcar uma nova data, é só responder esta mensagem.",
           ("Ana", "terça-feira, 24/11 às 09:00", "Clínica Sorriso"), tipos=("cancelamento",)),
    Modelo("temhorario_pos_consulta", "UTILITY",
           "Olá, {{1}}! Aqui é da {{2}}. Como você está depois do atendimento? "
           "Se precisar de algo, é só responder esta mensagem.",
           ("Ana", "Clínica Sorriso"), tipos=("pos_consulta",)),
    Modelo("temhorario_tratamento", "UTILITY",
           "Olá, {{1}}! Aqui é da {{2}}. Já podemos seguir com o seu tratamento. "
           "Quer marcar o próximo horário? É só responder esta mensagem.",
           ("Ana", "Clínica Sorriso"), tipos=("tratamento",)),
    Modelo("temhorario_retorno", "MARKETING",
           "Olá, {{1}}! Já está na hora do seu retorno na {{2}}. "
           "Quer que a gente veja um horário para você? É só responder esta mensagem.",
           ("Ana", "Clínica Sorriso"), rodape=RODAPE_PARAR, tipos=("retorno",)),
    Modelo("temhorario_aniversario", "MARKETING",
           "Feliz aniversário, {{1}}! 🎉 Toda a equipe da {{2}} deseja um novo ano cheio de saúde e alegria.",
           ("Ana", "Clínica Sorriso"), rodape=RODAPE_PARAR, tipos=("aniversario",)),
    Modelo("temhorario_resumo_dia", "UTILITY",
           "Bom dia, {{1}}! Sua agenda de {{2}} na {{3}}: {{4}}",
           ("Dra. Paula", "terça-feira, 24/11", "Clínica Sorriso", "09:00 Ana (Limpeza) · 10:00 Bruno (Avaliação)")),
)}
POR_TIPO = {t: m for m in CATALOGO.values() for t in m.tipos}


class SemModelo(Exception):
    """Não há modelo para esta mensagem fora da janela (ex.: campanha antes da 36E) ou faltam dados."""


def janela_aberta(conn, clinic_id: UUID, patient_id: UUID, agora: datetime) -> bool:
    """O cliente mandou mensagem pelo WhatsApp nas últimas 24 h?"""
    r = conn.execute(
        """select 1 from messages m join conversations c on c.id = m.conversation_id
           where c.clinic_id = %s and c.patient_id = %s and c.channel = 'whatsapp' and m.direction = 'in'
             and m.created_at > %s limit 1""", (clinic_id, patient_id, agora - JANELA)).fetchone()
    return bool(r)


def _param(v) -> str:
    """A Meta recusa parâmetro vazio, com quebra de linha, tabulação ou mais de 4 espaços seguidos."""
    t = re.sub(r"[\r\n\t]+", " · ", str(v or "")).strip(" ·")
    t = re.sub(r" {2,}", " ", t)
    return (t or "-")[:900]


def renderizar(modelo: Modelo, params: list[str]) -> str:
    """O texto como o cliente vê (para gravar na conversa do painel)."""
    texto = modelo.texto
    for i, p in enumerate(params, 1):
        texto = texto.replace("{{%d}}" % i, p)
    return texto + (f"\n\n{modelo.rodape}" if modelo.rodape else "")


def montar(conn, clinica: dict, o: dict) -> tuple[Modelo, list[str], str]:
    """(modelo, parâmetros, texto renderizado) para a mensagem `o` da fila (outbound_messages)."""
    from app.agenda.servico import detalhar
    from app.painel.avisos import palavras, primeiro_nome, quando

    if o["kind"] == "campanha" and o.get("campaign_id"):  # 36E: modelo próprio da campanha
        return montar_campanha(conn, clinica, o)
    modelo = POR_TIPO.get(o["kind"])
    if modelo is None:
        raise SemModelo("Fora da janela de 24 h esta mensagem precisa de um modelo aprovado pela Meta.")
    nome = conn.execute("select name from patients where id = %s", (o["patient_id"],)).fetchone()[0]
    nome, clin, tz = primeiro_nome(nome), clinica["name"], clinica["tz"]
    if o["kind"] in ("lembrete", "confirmacao", "remarcacao", "cancelamento"):
        if not o.get("appointment_id"):
            raise SemModelo("mensagem de agenda sem consulta ligada")
        c = detalhar(conn, clinica["id"], o["appointment_id"])
        q, linha = quando(c["starts_at"], tz), palavras(clinica, c)["linha"]
        if o["kind"] == "lembrete":
            params = [nome, clin, q, linha]
        elif o["kind"] == "confirmacao":
            params = [nome, clin, q, linha, clinica.get("address") or "-"]
        elif o["kind"] == "remarcacao":
            antes = conn.execute("""select a.starts_at from appointments a join appointments n on n.rescheduled_from_id = a.id
                                    where n.id = %s""", (c["id"],)).fetchone()
            params = [nome, clin, quando(antes[0], tz) if antes else "-", q, linha]
        else:
            params = [nome, q, clin]
    else:
        params = [nome, clin]
    params = [_param(p) for p in params]
    return modelo, params, renderizar(modelo, params)


def resumo_dia(prof_nome: str, dia: date, clinica: dict, texto: str) -> tuple[Modelo, list[str], str]:
    """Resumo do dia do profissional (sempre modelo: o profissional quase nunca abre a janela)."""
    from app.painel.avisos import DIAS

    linhas = [ln.strip() for ln in texto.splitlines()[2:] if ln.strip()]  # "Bom dia" e "Hoje…" já estão no modelo
    modelo = CATALOGO["temhorario_resumo_dia"]
    params = [_param(prof_nome), _param(f"{DIAS[dia.weekday()]}, {dia:%d/%m}"), _param(clinica["name"]),
              _param(" · ".join(linhas))]
    return modelo, params, renderizar(modelo, params)


# ---------------------------------------------------------------------------
# Criar os modelos na conta da clínica e ver a situação de cada um
# ---------------------------------------------------------------------------
def pedido_de_criacao(m: Modelo) -> dict:
    corpo = {"type": "BODY", "text": m.texto, "example": {"body_text": [list(m.exemplo)]}}
    componentes = [corpo]
    if m.rodape:
        componentes.append({"type": "FOOTER", "text": m.rodape})
    if m.botoes:
        componentes.append({"type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": b} for b in m.botoes]})
    return {"name": m.nome, "language": IDIOMA, "category": m.categoria, "components": componentes}


SITUACAO = {"APPROVED": "aprovado", "PENDING": "em análise", "REJECTED": "recusado", "PAUSED": "pausado",
            "DISABLED": "desativado", "IN_APPEAL": "em recurso"}


def situacao(existentes: list[dict]) -> list[dict]:
    """Cada modelo do catálogo com a situação na Meta ('não criado' se ainda não existe)."""
    na_meta = {(e.get("name"), e.get("language")): e for e in existentes}
    out = []
    for m in CATALOGO.values():
        e = na_meta.get((m.nome, IDIOMA))
        out.append({"nome": m.nome, "categoria": m.categoria, "tipos": list(m.tipos) or ["resumo_dia"],
                    "situacao": SITUACAO.get((e or {}).get("status", ""), "não criado" if not e else str(e.get("status")).lower()),
                    "motivo": (e or {}).get("rejected_reason") if e and e.get("status") == "REJECTED" else None})
    return out


def criar_faltantes(cliente, waba_id: str) -> list[dict]:
    """Cria na Meta os modelos que ainda não existem nesta conta; devolve a situação atualizada."""
    existentes = cliente.listar_modelos(waba_id)
    ja = {(e.get("name"), e.get("language")) for e in existentes}
    for m in CATALOGO.values():
        if (m.nome, IDIOMA) not in ja:
            cliente.criar_modelo(waba_id, pedido_de_criacao(m))
    return situacao(cliente.listar_modelos(waba_id))


# ---------------------------------------------------------------------------
# Campanhas (Etapa 36E): cada campanha de clínica na Meta vira um modelo de marketing próprio
# ---------------------------------------------------------------------------
class AguardandoAprovacao(Exception):
    """O modelo da campanha ainda está em análise na Meta: a mensagem espera na fila."""


CONFERIR_A_CADA = timedelta(minutes=10)
ESPERA_MAXIMA = timedelta(days=3)


def nome_modelo_campanha(campanha_id) -> str:
    return f"temhorario_campanha_{str(campanha_id).replace('-', '')[:12]}"


def texto_campanha(texto: str, nome_clinica: str) -> str:
    """Texto da campanha no formato da Meta: {clinica} fica fixo; {nome} vira {{1}} (uma vez só)."""
    if texto.count("{nome}") > 1:
        raise ValueError("No WhatsApp oficial use {nome} só uma vez no texto da campanha.")
    t = texto.strip().replace("{clinica}", nome_clinica).replace("{nome}", "{{1}}")
    if t.startswith("{{1}}") or t.endswith("{{1}}"):
        raise ValueError("No WhatsApp oficial o texto não pode começar nem terminar com {nome}.")
    return t


def pedido_campanha(campanha_id, texto: str, nome_clinica: str) -> dict:
    corpo = texto_campanha(texto, nome_clinica)
    m = Modelo(nome_modelo_campanha(campanha_id), "MARKETING", corpo, ("Ana",) if "{{1}}" in corpo else (),
               rodape=RODAPE_PARAR)
    pedido = pedido_de_criacao(m)
    if not m.exemplo:  # sem variável: a Meta não aceita "example" vazio
        pedido["components"][0].pop("example", None)
    return pedido


def conferir_campanha(conn, cliente, waba_id: str, campanha_id, agora: datetime) -> None:
    """Garante que o modelo da campanha está aprovado. Em análise → AguardandoAprovacao; recusado ou
    esperando demais → SemModelo (a mensagem falha com o motivo)."""
    r = conn.execute("""select meta_modelo, meta_situacao, meta_motivo, meta_conferido_em, enviar_em
                        from campaigns where id = %s""", (campanha_id,)).fetchone()
    if not r or not r[0]:
        raise SemModelo("Esta campanha foi criada antes de a clínica usar o WhatsApp oficial: crie de novo.")
    nome, sit, motivo, conferido, enviar_em = r
    if sit != "aprovado" and (conferido is None or agora - conferido > CONFERIR_A_CADA):
        achado = next((e for e in cliente.listar_modelos(waba_id) if e.get("name") == nome), None)
        sit = SITUACAO.get((achado or {}).get("status", ""), "não criado")
        motivo = (achado or {}).get("rejected_reason")
        conn.execute("""update campaigns set meta_situacao = %s, meta_motivo = %s, meta_conferido_em = %s
                        where id = %s""", (sit, motivo, agora, campanha_id))
    if sit == "aprovado":
        return
    if sit in ("recusado", "pausado", "desativado", "não criado"):
        raise SemModelo(f"A Meta não liberou o modelo da campanha ({sit}{': ' + motivo if motivo else ''}).")
    if agora - enviar_em > ESPERA_MAXIMA:
        raise SemModelo("A Meta não aprovou o modelo da campanha em 3 dias.")
    raise AguardandoAprovacao("aguardando a Meta aprovar o modelo da campanha")


def montar_campanha(conn, clinica: dict, o: dict) -> tuple[Modelo, list[str], str]:
    from app.painel.avisos import primeiro_nome

    r = conn.execute("select meta_modelo, texto from campaigns where id = %s", (o["campaign_id"],)).fetchone()
    corpo = texto_campanha(r[1], clinica["name"])
    m = Modelo(r[0], "MARKETING", corpo, (), rodape=RODAPE_PARAR)
    nome = conn.execute("select name from patients where id = %s", (o["patient_id"],)).fetchone()[0]
    params = [_param(primeiro_nome(nome))] if "{{1}}" in corpo else []
    return m, params, renderizar(m, params)
