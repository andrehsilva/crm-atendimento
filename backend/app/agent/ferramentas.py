"""Ferramentas da Ísis.

Regra de ouro (CLAUDE.md): a identidade vem da SESSÃO. Clínica e telefone do paciente ficam
"presos" dentro das ferramentas quando elas são criadas; o modelo nunca escolhe de quem é a consulta.
Toda mudança na agenda passa pelo mesmo motor da recepção (app.agenda.servico).
"""

import json
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.agenda import servico
from app.agenda.erros import AgendaError
from app.agent.contexto import dados_clinica
from app.eventos import avisar
from app.painel import crm
from app.painel.avisos import quando

MAX_SLOTS = 8


def _sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn").strip()


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _erro(e: AgendaError) -> str:
    return _json({"ok": False, "erro": e.codigo, "mensagem": e.mensagem})


class _Desfazer(Exception):
    """Usada para validar uma ação "de mentira" (roda tudo e desfaz)."""


@dataclass
class Sessao:
    conn: psycopg.Connection
    clinica: dict
    paciente: dict
    conversa: dict
    agora: datetime
    chamadas: list = field(default_factory=list)  # log para agent_runs

    @property
    def cid(self) -> UUID:
        return self.clinica["id"]

    @property
    def tz(self):
        return self.clinica["tz"]


def criar_ferramentas(s: Sessao) -> list:
    conn = s.conn

    def log(nome: str, args: dict, resultado: str) -> str:
        s.chamadas.append({"ferramenta": nome, "args": args, "resultado": resultado[:1500]})
        return resultado

    # ---------------------------------------------------------------- resolução de nomes
    def _procedimento(nome: str) -> dict:
        servs = conn.cursor(row_factory=dict_row).execute(
            "select id, name, bookable_by_ai from services where clinic_id = %s and active", (s.cid,)
        ).fetchall()
        alvo = _sem_acento(nome)
        achados = [x for x in servs if alvo == _sem_acento(x["name"])] or [
            x for x in servs if alvo in _sem_acento(x["name"]) or _sem_acento(x["name"]).split(" (")[0] in alvo
        ]
        if len(achados) != 1:
            raise AgendaError("DADOS_INVALIDOS", "Procedimento não identificado. Opções: " + ", ".join(x["name"] for x in servs))
        return achados[0]

    def _dentista(nome: str | None) -> dict | None:
        if not nome or _sem_acento(nome) in ("", "tanto faz", "qualquer", "qualquer um", "sem preferencia"):
            return None
        profs = conn.cursor(row_factory=dict_row).execute(
            "select id, name from professionals where clinic_id = %s and active", (s.cid,)
        ).fetchall()
        alvo = _sem_acento(nome).replace("dra.", "").replace("dr.", "").strip()
        achados = [p for p in profs if alvo and alvo in _sem_acento(p["name"])]
        if len(achados) != 1:
            raise AgendaError("DADOS_INVALIDOS", "Dentista não identificado. Opções: " + ", ".join(p["name"] for p in profs))
        return achados[0]

    def _data(texto: str) -> date:
        try:
            return date.fromisoformat(texto[:10])
        except ValueError as e:
            raise AgendaError("DADOS_INVALIDOS", "Use a data no formato AAAA-MM-DD.") from e

    def _instante(texto: str) -> datetime:
        try:
            dt = datetime.fromisoformat(texto)
        except ValueError as e:
            raise AgendaError("DADOS_INVALIDOS", "Use data e hora no formato AAAA-MM-DDTHH:MM.") from e
        return dt if dt.tzinfo else dt.replace(tzinfo=s.tz)

    def _consulta_minha(consulta_id: str) -> dict:
        try:
            uid = UUID(consulta_id)
        except ValueError as e:
            raise AgendaError("CONSULTA_NAO_ENCONTRADA", "Consulta não encontrada.") from e
        minhas = servico.consultas_do_paciente(conn, s.cid, s.paciente["phone"], agora=s.agora)
        for c in minhas:
            if c["id"] == uid:
                return c
        raise AgendaError("NAO_E_SUA", "Essa consulta não está entre as consultas futuras deste telefone.")

    def _validar(fn) -> dict:
        """Roda a ação dentro de um savepoint e DESFAZ — valida todas as regras sem gravar."""
        res: dict = {}
        try:
            with conn.transaction():
                res = fn()
                raise _Desfazer
        except _Desfazer:
            pass
        return res

    def _token(acao: str, payload: dict, resumo: str) -> str:
        tid = conn.execute(
            """insert into action_tokens (clinic_id, patient_id, action, payload, resumo)
               values (%s, %s, %s, %s, %s) returning id""",
            (s.cid, s.paciente["id"], acao, Jsonb(payload), resumo),
        ).fetchone()[0]
        return str(tid)

    # ---------------------------------------------------------------- ferramentas
    def info_clinica() -> str:
        """Dados da clínica: endereço, telefone, horário de funcionamento, dentistas e procedimentos (com duração e, se a clínica permitir, preço)."""
        return log("info_clinica", {}, _json(dados_clinica(conn, s.clinica)))

    def horarios_livres(procedimento: str, data_inicio: str, data_fim: str | None = None,
                        dentista: str | None = None, turno: str | None = None) -> str:
        """Busca horários livres de verdade na agenda.

        Args:
            procedimento: nome do procedimento (ex.: "Limpeza").
            data_inicio: primeiro dia a buscar, formato AAAA-MM-DD.
            data_fim: último dia a buscar (AAAA-MM-DD). Se vazio, busca só data_inicio.
            dentista: nome do dentista, ou vazio/"tanto faz" para qualquer um.
            turno: "manha", "tarde" ou vazio para o dia todo.
        """
        args = {"procedimento": procedimento, "data_inicio": data_inicio, "data_fim": data_fim, "dentista": dentista, "turno": turno}
        try:
            serv = _procedimento(procedimento)
            prof = _dentista(dentista)
            ini = _data(data_inicio)
            fim = _data(data_fim) if data_fim else ini
            if (fim - ini).days > 14:
                fim = ini + timedelta(days=14)
            slots = servico.horarios_livres(conn, s.cid, serv["id"], ini, fim, prof and prof["id"],
                                            s.paciente["phone"], agora=s.agora, limite=300)
            t = _sem_acento(turno or "")
            if t.startswith("manh"):
                slots = [x for x in slots if x["starts_at"].hour < 12]
            elif t.startswith("tard"):
                slots = [x for x in slots if x["starts_at"].hour >= 12]
            saida = [
                {"inicio": x["starts_at"].strftime("%Y-%m-%dT%H:%M"), "quando": quando(x["starts_at"], s.tz),
                 "dentista": x["profissional"], **({"dentista_de_referencia": True} if x["preferido"] else {})}
                for x in slots[:MAX_SLOTS]
            ]
            r = {"ok": True, "procedimento": serv["name"], "horarios": saida,
                 "observacao": "ofereça no máximo 3" if saida else "sem horários livres nesse período; sugira outros dias"}
            if not serv["bookable_by_ai"]:
                r["aviso"] = "este procedimento é marcado só pela recepção: use chamar_humano"
            return log("horarios_livres", args, _json(r))
        except AgendaError as e:
            return log("horarios_livres", args, _erro(e))

    def minhas_consultas() -> str:
        """Lista as consultas futuras do paciente desta conversa (com o id de cada uma, para remarcar ou cancelar)."""
        cs = servico.consultas_do_paciente(conn, s.cid, s.paciente["phone"], agora=s.agora)
        r = [{"id": str(c["id"]), "quando": quando(c["starts_at"], s.tz), "procedimento": c["procedimento"],
              "dentista": c["profissional"], "status": c["status"]} for c in cs]
        return log("minhas_consultas", {}, _json({"ok": True, "consultas": r}))

    def salvar_nome(nome_completo: str) -> str:
        """Salva o nome completo do paciente (obrigatório antes de marcar a primeira consulta).

        Args:
            nome_completo: nome e sobrenome, como o paciente informou.
        """
        nome = " ".join(nome_completo.split())[:200]
        if len(nome.split()) < 2:
            return log("salvar_nome", {"nome_completo": nome_completo}, _json({"ok": False, "mensagem": "Peça nome e sobrenome."}))
        conn.execute("update patients set name = %s where id = %s", (nome, s.paciente["id"]))
        s.paciente["name"] = nome
        avisar(conn, s.cid, "crm", s.paciente["id"])
        return log("salvar_nome", {"nome_completo": nome}, _json({"ok": True}))

    def preparar_agendamento(procedimento: str, inicio: str, dentista: str) -> str:
        """PASSO 1 para marcar: valida tudo SEM gravar e devolve um resumo e um token.
        Mostre o resumo ao paciente e pergunte se pode confirmar.

        Args:
            procedimento: nome do procedimento.
            inicio: data e hora escolhidas, formato AAAA-MM-DDTHH:MM (use um "inicio" de horarios_livres).
            dentista: nome do dentista do horário escolhido.
        """
        args = {"procedimento": procedimento, "inicio": inicio, "dentista": dentista}
        try:
            serv = _procedimento(procedimento)
            prof = _dentista(dentista)
            if prof is None:
                raise AgendaError("DADOS_INVALIDOS", "Informe o dentista do horário escolhido.")
            dt = _instante(inicio)
            c = _validar(lambda: servico.marcar(
                conn, s.cid, telefone=s.paciente["phone"], nome=s.paciente.get("name"), professional_id=prof["id"],
                service_id=serv["id"], inicio=dt, ator="isis", origem=s.conversa["channel"], agora=s.agora))
            resumo = f"Marcar {c['procedimento']} com {c['profissional']} em {quando(c['starts_at'], s.tz)}"
            payload = {"service_id": str(serv["id"]), "professional_id": str(prof["id"]), "inicio": dt.isoformat()}
            return log("preparar_agendamento", args, _json({"ok": True, "resumo": resumo, "token": _token("marcar", payload, resumo),
                                                             "proximo_passo": "mostre o resumo e pergunte se pode confirmar"}))
        except AgendaError as e:
            return log("preparar_agendamento", args, _erro(e))

    def preparar_remarcacao(consulta_id: str, novo_inicio: str, dentista: str | None = None) -> str:
        """PASSO 1 para remarcar: valida a troca SEM gravar e devolve resumo e token.

        Args:
            consulta_id: id da consulta (de minhas_consultas).
            novo_inicio: nova data e hora, formato AAAA-MM-DDTHH:MM (de horarios_livres).
            dentista: nome do dentista do novo horário (vazio = o mesmo).
        """
        args = {"consulta_id": consulta_id, "novo_inicio": novo_inicio, "dentista": dentista}
        try:
            antiga = _consulta_minha(consulta_id)
            prof = _dentista(dentista)
            dt = _instante(novo_inicio)
            r = _validar(lambda: servico.remarcar(
                conn, s.cid, appointment_id=antiga["id"], telefone=s.paciente["phone"], ator="isis",
                novo_inicio=dt, professional_id=prof and prof["id"], agora=s.agora))
            nova = r["consulta"]
            resumo = (f"Remarcar {antiga['procedimento']} de {quando(antiga['starts_at'], s.tz)} "
                      f"para {quando(nova['starts_at'], s.tz)} com {nova['profissional']}")
            payload = {"consulta_id": str(antiga["id"]), "novo_inicio": dt.isoformat(),
                       "professional_id": str(prof["id"]) if prof else None}
            out = {"ok": True, "resumo": resumo, "token": _token("remarcar", payload, resumo),
                   "proximo_passo": "mostre o resumo e pergunte se pode confirmar"}
            if r["aviso_politica"]:
                out["aviso_politica"] = "a consulta original é em menos de 24h: avise a política da clínica"
            return log("preparar_remarcacao", args, _json(out))
        except AgendaError as e:
            return log("preparar_remarcacao", args, _erro(e))

    def preparar_cancelamento(consulta_id: str, motivo: str | None = None) -> str:
        """PASSO 1 para cancelar: valida SEM gravar e devolve resumo e token.

        Args:
            consulta_id: id da consulta (de minhas_consultas).
            motivo: motivo informado pelo paciente, se houver.
        """
        args = {"consulta_id": consulta_id, "motivo": motivo}
        try:
            c = _consulta_minha(consulta_id)
            r = _validar(lambda: servico.cancelar(conn, s.cid, appointment_id=c["id"], telefone=s.paciente["phone"],
                                                  ator="isis", motivo=motivo, agora=s.agora))
            resumo = f"Cancelar {c['procedimento']} com {c['profissional']} de {quando(c['starts_at'], s.tz)}"
            out = {"ok": True, "resumo": resumo,
                   "token": _token("cancelar", {"consulta_id": str(c["id"]), "motivo": motivo}, resumo),
                   "proximo_passo": "mostre o resumo e pergunte se pode confirmar"}
            if r["aviso_politica"]:
                out["aviso_politica"] = "cancelamento com menos de 24h: avise a política da clínica"
            return log("preparar_cancelamento", args, _json(out))
        except AgendaError as e:
            return log("preparar_cancelamento", args, _erro(e))

    def confirmar_acao(token: str) -> str:
        """PASSO 2: executa a ação preparada. Use SOMENTE depois que o paciente respondeu que confirma.

        Args:
            token: o token devolvido pela ferramenta preparar_*.
        """
        args = {"token": token}
        try:
            try:
                tid = UUID(token)
            except ValueError as e:
                raise AgendaError("DADOS_INVALIDOS", "Token inválido.") from e
            t = conn.cursor(row_factory=dict_row).execute(
                """select *, expires_at < now() as expirado from action_tokens
                   where id = %s and clinic_id = %s and patient_id = %s for update""",
                (tid, s.cid, s.paciente["id"]),
            ).fetchone()
            if not t:
                raise AgendaError("DADOS_INVALIDOS", "Token não encontrado. Prepare a ação de novo.")
            if t["used_at"]:
                raise AgendaError("STATUS_INVALIDO", "Essa ação já foi confirmada antes.")
            if t["expirado"]:
                raise AgendaError("DADOS_INVALIDOS", "O resumo expirou. Prepare a ação de novo.")
            # RN-AG-11 no CÓDIGO: o paciente precisa ter mandado mensagem DEPOIS do resumo
            respondeu = conn.execute(
                """select exists(select 1 from messages where conversation_id = %s and author = 'paciente'
                                  and created_at > %s)""",
                (s.conversa["id"], t["created_at"]),
            ).fetchone()[0]
            if not respondeu:
                raise AgendaError("DADOS_INVALIDOS",
                                  "Ainda não houve resposta do paciente a este resumo. Mostre o resumo e pergunte se pode confirmar.")
            p = t["payload"]
            if t["action"] == "marcar":
                c = servico.marcar(conn, s.cid, telefone=s.paciente["phone"], nome=s.paciente.get("name"),
                                   professional_id=UUID(p["professional_id"]), service_id=UUID(p["service_id"]),
                                   inicio=datetime.fromisoformat(p["inicio"]), ator="isis", origem=s.conversa["channel"], agora=s.agora)
                feito = f"Marcada: {c['procedimento']} com {c['profissional']} em {quando(c['starts_at'], s.tz)}"
            elif t["action"] == "remarcar":
                r = servico.remarcar(conn, s.cid, appointment_id=UUID(p["consulta_id"]), telefone=s.paciente["phone"], ator="isis",
                                     novo_inicio=datetime.fromisoformat(p["novo_inicio"]),
                                     professional_id=UUID(p["professional_id"]) if p.get("professional_id") else None, agora=s.agora)
                c = r["consulta"]
                feito = f"Remarcada para {quando(c['starts_at'], s.tz)} com {c['profissional']}"
            else:
                r = servico.cancelar(conn, s.cid, appointment_id=UUID(p["consulta_id"]), telefone=s.paciente["phone"],
                                     ator="isis", motivo=p.get("motivo"), agora=s.agora)
                feito = "Consulta cancelada"
            conn.execute("update action_tokens set used_at = now() where id = %s", (tid,))
            return log("confirmar_acao", args, _json({"ok": True, "feito": feito,
                                                      "observacao": "o paciente vai receber a confirmação por mensagem"}))
        except AgendaError as e:
            return log("confirmar_acao", args, _erro(e))

    def chamar_humano(motivo: str) -> str:
        """Passa a conversa para a equipe da clínica (a Ísis para de responder até a equipe devolver).
        Use para: pedido de falar com pessoa, reclamação, urgência, procedimento só da recepção, ou quando não conseguir resolver.

        Args:
            motivo: motivo curto (ex.: "urgência", "pediu atendente", "reclamação").
        """
        conn.execute("update conversations set status = 'humano' where id = %s", (s.conversa["id"],))
        s.conversa["status"] = "humano"
        crm.registrar(conn, s.cid, s.paciente["id"], "aguardando_humano", "isis")
        avisar(conn, s.cid, "conversa", s.conversa["id"])
        return log("chamar_humano", {"motivo": motivo}, _json({"ok": True, "observacao": "a equipe assume a conversa e você para de responder; não prometa retorno (o aviso ao paciente é automático)"}))

    return [info_clinica, horarios_livres, minhas_consultas, salvar_nome, preparar_agendamento,
            preparar_remarcacao, preparar_cancelamento, confirmar_acao, chamar_humano]
