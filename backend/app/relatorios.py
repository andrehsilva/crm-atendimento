"""Relatórios em Excel (Etapa 15A — D73–D75): recall, atendimentos, produção e faltas.

Tudo filtrado pela clínica. Valores em R$ são ESTIMADOS pela tabela de preços (o sistema não registra pagamento).
Nenhum relatório traz texto de conversa nem observação clínica.
"""

from datetime import date, datetime, time, timedelta
from io import BytesIO
from uuid import UUID
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

TIPOS = {
    "recall": "Pacientes para chamar de volta",
    "atendimentos": "Atendimentos do período",
    "producao": "Produção por profissional e procedimento",
    "faltas": "Faltas e cancelamentos",
}
SITUACAO = {"agendada": "Agendada", "confirmada": "Confirmada", "realizada": "Realizada", "faltou": "Faltou", "cancelada": "Cancelada"}
ORIGEM = {"isis": "Assistente", "recepcao": "Recepção", "paciente_botao": "Paciente"}
DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
REAL = 'R$ #,##0.00'


def seguro(v):
    """Evita "injeção de fórmula": texto vindo de cadastro que comece com = + - @ não vira fórmula no Excel."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


def _aba(wb: Workbook, titulo: str, cab: list[str], linhas: list[list], formatos: dict[int, str] | None = None) -> None:
    ws = wb.create_sheet(titulo[:31])
    ws.append(cab)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="3F4A5A")
        c.alignment = Alignment(vertical="center")
    for linha in linhas:
        ws.append([seguro(v) for v in linha])
    for col, fmt in (formatos or {}).items():
        for (cel,) in ws.iter_rows(min_row=2, min_col=col, max_col=col):
            cel.number_format = fmt
    for i, nome in enumerate(cab, start=1):
        maior = max([len(str(nome))] + [len(str(r[i - 1])) for r in linhas[:500] if r[i - 1] is not None])
        ws.column_dimensions[get_column_letter(i)].width = min(max(10, maior + 2), 60)
    ws.freeze_panes = "A2"
    if linhas:
        ws.auto_filter.ref = ws.dimensions


def _periodo(de: date, ate: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    return datetime.combine(de, time.min, tz), datetime.combine(ate + timedelta(days=1), time.min, tz)


def _consultas(conn, clinic_id: UUID, de: date, ate: date, tz: ZoneInfo, prof: UUID | None, status: tuple | None = None) -> list[tuple]:
    ini, fim = _periodo(de, ate, tz)
    sql = """select a.starts_at, p.name, p.phone, s.name, pr.name, a.status, a.source, s.price_cents, pr.id, s.id
             from appointments a join patients p on p.id = a.patient_id join services s on s.id = a.service_id
             join professionals pr on pr.id = a.professional_id
             where a.clinic_id = %s and a.starts_at >= %s and a.starts_at < %s"""
    params: list = [clinic_id, ini, fim]
    if prof:
        sql += " and a.professional_id = %s"
        params.append(prof)
    if status:
        sql += " and a.status = any(%s)"
        params.append(list(status))
    return conn.execute(sql + " order by a.starts_at", params).fetchall()


def gerar(conn, clinic_id: UUID, tipo: str, *, de: date, ate: date, prof: UUID | None, meses: int) -> tuple[bytes, str]:
    nome_clinica, tz_nome = conn.execute("select name, timezone from clinics where id = %s", (clinic_id,)).fetchone()
    tz = ZoneInfo(tz_nome)
    wb = Workbook()
    wb.remove(wb.active)
    local = lambda d: d.astimezone(tz).replace(tzinfo=None)  # noqa: E731 — Excel não guarda fuso: mostra a hora da clínica

    if tipo == "recall":
        limite = datetime.now(tz) - timedelta(days=round(meses * 30.44))
        linhas = conn.execute(
            """select p.name, p.phone, u.starts_at, s.name, pr.name
               from patients p
               join lateral (select a.starts_at, a.service_id, a.professional_id from appointments a
                             where a.patient_id = p.id and a.status = 'realizada' order by a.starts_at desc limit 1) u on true
               join services s on s.id = u.service_id join professionals pr on pr.id = u.professional_id
               where p.clinic_id = %s and u.starts_at < %s
                 and not exists (select 1 from appointments f where f.patient_id = p.id
                                 and f.status in ('agendada', 'confirmada') and f.starts_at >= now())
               order by u.starts_at""", (clinic_id, limite)).fetchall()
        agora = datetime.now(tz)
        _aba(wb, "Chamar de volta", ["Paciente", "Telefone", "Última consulta", "Último procedimento", "Profissional", "Meses sem vir"],
             [[n, f, local(u).date(), s, pr, round((agora - u).days / 30.44, 1)] for n, f, u, s, pr in linhas], {3: "DD/MM/YYYY"})
        filtro = f"Sem consulta realizada há mais de {meses} meses e sem nada marcado"

    elif tipo == "atendimentos":
        c = _consultas(conn, clinic_id, de, ate, tz, prof)
        _aba(wb, "Atendimentos", ["Data", "Hora", "Paciente", "Telefone", "Procedimento", "Profissional", "Situação", "Marcada por", "Valor de tabela"],
             [[local(i).date(), local(i).time(), n, f, s, pr, SITUACAO.get(st, st), ORIGEM.get(o, o), (v or 0) / 100]
              for i, n, f, s, pr, st, o, v, _, _ in c], {1: "DD/MM/YYYY", 2: "HH:MM", 9: REAL})
        filtro = f"{de:%d/%m/%Y} a {ate:%d/%m/%Y}"

    elif tipo == "producao":
        c = _consultas(conn, clinic_id, de, ate, tz, prof)

        def resumo(chave):
            g: dict = {}
            for i, n, f, s, pr, st, o, v, pid, sid in c:
                k = chave(i, s, pr)
                d = g.setdefault(k, {"realizada": 0, "faltou": 0, "cancelada": 0, "valor": 0})
                if st in d:
                    d[st] += 1
                if st == "realizada":
                    d["valor"] += (v or 0) / 100
            linhas = []
            for k, d in g.items():
                base = d["realizada"] + d["faltou"]
                linhas.append([k, d["realizada"], d["faltou"], d["cancelada"], (d["realizada"] / base) if base else None, d["valor"]])
            return sorted(linhas, key=lambda r: str(r[0]))

        cab = ["Realizados", "Faltas", "Cancelados", "Comparecimento", "Valor estimado"]
        fmts = {5: "0%", 6: REAL}
        _aba(wb, "Por profissional", ["Profissional", *cab], resumo(lambda i, s, pr: pr), fmts)
        _aba(wb, "Por procedimento", ["Procedimento", *cab], resumo(lambda i, s, pr: s), fmts)
        _aba(wb, "Por mês", ["Mês", *cab], resumo(lambda i, s, pr: f"{local(i):%Y-%m}"), fmts)
        filtro = f"{de:%d/%m/%Y} a {ate:%d/%m/%Y}"

    elif tipo == "faltas":
        todas = _consultas(conn, clinic_id, de, ate, tz, prof)
        ruins = [r for r in todas if r[5] in ("faltou", "cancelada")]
        _aba(wb, "Lista", ["Data", "Hora", "Paciente", "Telefone", "Procedimento", "Profissional", "Situação"],
             [[local(i).date(), local(i).time(), n, f, s, pr, SITUACAO.get(st, st)] for i, n, f, s, pr, st, *_ in ruins],
             {1: "DD/MM/YYYY", 2: "HH:MM"})

        def taxa(chave, nomes):
            g: dict = {}
            for r in todas:
                if r[5] in ("realizada", "faltou", "cancelada"):
                    d = g.setdefault(chave(r[0]), [0, 0, 0])
                    d[0] += 1
                    d[1] += r[5] == "faltou"
                    d[2] += r[5] == "cancelada"
            return [[nomes(k), t, f, cc, (f / t) if t else None] for k, (t, f, cc) in sorted(g.items())]

        cab = ["Atendimentos", "Faltas", "Cancelamentos", "Taxa de falta"]
        _aba(wb, "Por dia da semana", ["Dia", *cab], taxa(lambda i: local(i).weekday(), lambda k: DIAS[k]), {5: "0%"})
        _aba(wb, "Por horário", ["Horário", *cab], taxa(lambda i: local(i).hour, lambda k: f"{k:02d}h"), {5: "0%"})
        freq: dict = {}
        for r in ruins:
            if r[5] == "faltou":
                freq[(r[1], r[2])] = freq.get((r[1], r[2]), 0) + 1
        _aba(wb, "Quem mais falta", ["Paciente", "Telefone", "Faltas"],
             sorted([[n, f, q] for (n, f), q in freq.items() if q >= 2], key=lambda r: -r[2]))
        filtro = f"{de:%d/%m/%Y} a {ate:%d/%m/%Y}"
    else:
        raise ValueError("tipo")

    sobre = wb.create_sheet("Sobre", 0)
    for linha in (["Relatório", TIPOS[tipo]], ["Clínica", nome_clinica], ["Filtro", filtro],
                  ["Gerado em", datetime.now(tz).strftime("%d/%m/%Y %H:%M")],
                  ["Observação", "Valores estimados pela tabela de preços dos procedimentos; o sistema não registra pagamentos."]):
        sobre.append([seguro(v) for v in linha])
    sobre.column_dimensions["A"].width, sobre.column_dimensions["B"].width = 14, 90
    for (c,) in sobre.iter_rows(max_col=1):
        c.font = Font(bold=True)
    saida = BytesIO()
    wb.save(saida)
    return saida.getvalue(), f"{tipo}-{date.today():%Y-%m-%d}.xlsx"
