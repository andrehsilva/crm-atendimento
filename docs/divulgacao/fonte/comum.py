"""Peças comuns dos materiais de venda do TemHorario: estilo, marca e telas ilustrativas (dados fictícios)."""

import base64
import pathlib

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600;700;800&display=swap');
:root{--marca:#b85c74;--marca-soft:#f6e4ea;--marca-escura:#8f4257;--bg:#f3f1ee;--surface:#fff;--text:#1f1f22;
--muted:#77737a;--line:#ece8e4;--verde:#1f7a43;--verde-soft:#e1f4e8;--ambar:#9a6a0c;--ambar-soft:#fcf1dc;
--vermelho:#c0362e;--vermelho-soft:#fce8e6;--azul:#1f6aa8;--azul-soft:#e3effa}
*{box-sizing:border-box;margin:0;padding:0}
html,body{font-family:'Lexend',system-ui,sans-serif;color:var(--text);-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{background:var(--surface)}
.marca{display:inline-flex;align-items:center;gap:10px;font-weight:700;letter-spacing:-.02em}
.marca svg{flex:none}
.marca b{color:var(--marca)}
.selo{display:inline-flex;align-items:center;gap:4px;border-radius:7px;padding:2px 8px;font-size:11px;font-weight:500}
.s-verde{background:var(--verde-soft);color:var(--verde)}.s-ambar{background:var(--ambar-soft);color:var(--ambar)}
.s-vermelho{background:var(--vermelho-soft);color:var(--vermelho)}.s-rosa{background:#fce7ee;color:#a63e5f}
.s-azul{background:var(--azul-soft);color:var(--azul)}.s-cinza{background:var(--bg);color:var(--muted)}
.ilustra{font-size:10px;color:var(--muted);text-align:center;margin-top:6px}

/* ---------- celular ---------- */
.fone{width:270px;border-radius:38px;background:#1f1f22;padding:10px;box-shadow:0 18px 40px rgba(31,31,34,.18)}
.fone .tela{border-radius:30px;overflow:hidden;background:#efeae2;height:520px;display:flex;flex-direction:column;color:var(--text)}
.escuro .fone{box-shadow:0 0 0 2px #45454b,0 18px 40px rgba(0,0,0,.4)}
.chat-topo{background:#fff;display:flex;align-items:center;gap:10px;padding:16px 14px 10px;border-bottom:1px solid var(--line)}
.chat-topo .av{width:34px;height:34px;border-radius:50%;background:var(--marca);color:#fff;display:grid;place-items:center;font-weight:600;font-size:14px}
.chat-topo .n{font-size:13px;font-weight:600;line-height:1.2}.chat-topo .st{font-size:10px;color:var(--muted)}
.chat{flex:1;padding:12px 10px;display:flex;flex-direction:column;gap:6px;font-size:11.5px;line-height:1.4}
.b{max-width:82%;padding:7px 10px;border-radius:12px;box-shadow:0 1px 0 rgba(0,0,0,.06)}
.b small{display:block;text-align:right;font-size:9px;color:#8a8a8a;margin-top:2px}
.eu{align-self:flex-end;background:#dff3d9;border-bottom-right-radius:4px}
.ela{align-self:flex-start;background:#fff;border-bottom-left-radius:4px}
.dia{align-self:center;background:#fff;border-radius:8px;padding:3px 10px;font-size:9.5px;color:var(--muted);margin:4px 0}

/* ---------- painel (computador) ---------- */
.janela{border-radius:16px;overflow:hidden;background:var(--bg);box-shadow:0 18px 40px rgba(31,31,34,.14);border:1px solid var(--line)}
.barra{height:26px;background:#e7e3df;display:flex;align-items:center;gap:6px;padding:0 12px}
.barra i{width:9px;height:9px;border-radius:50%;background:#cfc9c4;display:block}
.painel{display:flex;font-size:11px}
.lado{width:150px;background:#fff;border-right:1px solid var(--line);padding:12px 8px;display:flex;flex-direction:column;gap:3px}
.lado .cl{display:flex;align-items:center;gap:7px;font-weight:600;font-size:11.5px;padding:2px 6px 10px;border-bottom:1px solid var(--line);margin-bottom:6px}
.lado .cl span{width:24px;height:24px;border-radius:7px;background:var(--marca);color:#fff;display:grid;place-items:center;font-size:11px}
.lado a{display:block;padding:6px 9px;border-radius:8px;color:var(--muted)}
.lado a.on{background:var(--marca-soft);color:var(--marca);font-weight:500}
.lado .sec{font-size:8px;letter-spacing:.08em;color:#aaa;padding:6px 9px 2px;text-transform:uppercase}
.conteudo{flex:1;padding:14px 16px}
.conteudo h4{font-size:15px;font-weight:700;margin-bottom:2px}.conteudo .sub{color:var(--muted);font-size:10px;margin-bottom:10px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px}
.card{background:#fff;border-radius:12px;padding:10px}
.card .num{font-size:18px;font-weight:700}.card .rot{font-size:9.5px;color:var(--muted)}
.linha{display:flex;align-items:center;gap:10px;padding:7px 0;border-top:1px solid var(--line)}
.linha:first-child{border-top:0}
.linha .h{font-weight:600;width:36px}.linha .q{flex:1;line-height:1.25}.linha .q span{display:block;color:var(--muted);font-size:9.5px}
/* agenda */
.grade{display:grid;grid-template-columns:34px repeat(5,1fr);background:#fff;border-radius:12px;padding:8px;gap:0 4px;font-size:9px}
.grade .cab{text-align:center;color:var(--muted);padding-bottom:6px;font-size:9px}.grade .cab b{display:block;color:var(--text);font-size:12px}
.grade .cab.hoje b{background:var(--marca);color:#fff;border-radius:50%;width:22px;height:22px;display:grid;place-items:center;margin:2px auto 0}
.col{position:relative;height:230px;border-left:1px solid var(--line)}
.horas{position:relative;height:230px}.horas div{position:absolute;right:4px;color:#aaa;font-size:8px}
.ev{position:absolute;left:2px;right:2px;border-radius:6px;padding:3px 5px;font-size:8.5px;line-height:1.2;border-left:3px solid}
.ev b{display:block;font-weight:600}
.e1{background:#f6e4ea;border-color:#b85c74}.e2{background:#e3effa;border-color:#1f6aa8}.e3{background:#e1f4e8;border-color:#1f7a43}
.e4{background:#fcf1dc;border-color:#c89416;border-left-style:dashed}
/* kanban */
.kan{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.kcol{background:rgba(255,255,255,.55);border-radius:12px;padding:7px;display:flex;flex-direction:column;gap:6px;min-height:220px}
.kcol h5{font-size:10.5px;display:flex;align-items:center;gap:5px;justify-content:space-between;padding:0 2px 2px}
.kcol h5 i{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:4px}
.kcol h5 em{font-style:normal;font-weight:400;color:var(--muted);background:#fff;border-radius:8px;padding:0 6px}
.kc{background:#fff;border-radius:10px;padding:7px;box-shadow:0 0 0 1px var(--line)}
.kc b{display:block;font-size:10px}.kc span{display:block;color:var(--muted);font-size:8.5px;margin:1px 0 4px}
/* celular painel */
.mob{color:var(--text);background:var(--bg);height:520px;display:flex;flex-direction:column;border-radius:30px;overflow:hidden;font-size:11px}
.mob .topo{background:#fff;padding:18px 12px 9px;display:flex;align-items:center;gap:8px;border-bottom:1px solid var(--line)}
.mob .topo span.lg{width:28px;height:28px;border-radius:8px;background:var(--marca);color:#fff;display:grid;place-items:center;font-weight:600}
.mob .topo .t{line-height:1.2;flex:1}.mob .topo .t b{font-size:12px}.mob .topo .t small{display:block;color:var(--muted);font-size:9px}
.mob .corpo{flex:1;min-height:0;overflow:hidden;padding:10px;display:flex;flex-direction:column;gap:7px}
.mob .nav{display:flex;align-items:center;justify-content:space-between;background:#fff;border-radius:12px;padding:8px 10px}
.mob .item{background:#fff;border-radius:12px;padding:8px 10px;display:flex;gap:8px;align-items:center}
.mob .item .h{width:38px;text-align:center;font-weight:600;line-height:1.1}.mob .item .h small{display:block;color:var(--muted);font-weight:400;font-size:9px}
.mob .item .fx{width:3px;align-self:stretch;border-radius:3px}
.mob .item .q{flex:1;line-height:1.3}.mob .item .q span{display:block;color:var(--muted);font-size:9.5px}
.mob .abas{background:#fff;border-top:1px solid var(--line);display:grid;grid-template-columns:repeat(5,1fr);text-align:center;font-size:8.5px;color:var(--muted);padding:7px 0 12px}
.mob .abas .on{color:var(--marca);font-weight:600}
.mob .abas i{display:block;width:16px;height:16px;border-radius:5px;border:1.6px solid currentColor;margin:0 auto 3px}
"""

_LOGOS = pathlib.Path(__file__).resolve().parents[2] / "temhorario"  # docs/temhorario (logo oficial)


def _img_svg(nome: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode((_LOGOS / nome).read_bytes()).decode()


def logo(tam=34, texto=True, cor_texto="var(--text)"):
    """Logo oficial de docs/temhorario. `tam` = altura em px. Fundo escuro (texto branco) usa a versão negativa."""
    if not texto:
        return f'<img class="marca" src="{_img_svg("temhorario-icone.svg")}" alt="TemHorario" style="height:{tam}px;width:{tam}px">'
    claro = str(cor_texto).lower() in ("#fff", "#ffffff", "white")
    arq = "temhorario-logo-negativo.svg" if claro else "temhorario-logo.svg"
    return f'<img class="marca" src="{_img_svg(arq)}" alt="TemHorario" style="height:{tam}px;width:auto">'


def _chat(bolhas):
    return f"""<div class="fone"><div class="tela">
<div class="chat-topo"><div class="av">Í</div><div><div class="n">Clínica Sorriso</div><div class="st">Ísis · assistente virtual</div></div></div>
<div class="chat">{bolhas}</div></div></div>"""


def whatsapp():
    return _chat("""<div class="dia">HOJE</div>
<div class="b eu">Oi, boa tarde!<small>14:02</small></div>
<div class="b eu">queria marcar uma limpeza, tem horário na quinta?<small>14:02</small></div>
<div class="b ela">Oi, Juliana! Aqui é a Ísis, da Clínica Sorriso 😊 Na quinta (27/11) tenho <b>09:00</b>, <b>10:30</b> ou <b>15:00</b> com a Dra. Ana Lima. Qual fica melhor?<small>14:02</small></div>
<div class="b eu">10:30<small>14:03</small></div>
<div class="b ela">Prontinho! Limpeza marcada para <b>quinta, 27/11, às 10:30</b> com a Dra. Ana Lima. Um dia antes eu mando um lembrete para você confirmar. 💙<small>14:03</small></div>""")


def lembrete():
    return _chat("""<div class="dia">QUARTA-FEIRA</div>
<div class="b ela">Oi, Juliana! Lembrete da Clínica Sorriso: amanhã, <b>quinta, 27/11, às 10:30</b>, limpeza com a Dra. Ana Lima.<br><br>Responda:<br><b>1</b> Confirmar<br><b>2</b> Remarcar<br><b>3</b> Cancelar<small>09:00</small></div>
<div class="b eu">1<small>09:14</small></div>
<div class="b ela">Confirmado! Até amanhã, Juliana. 😊<small>09:14</small></div>
<div class="dia">QUINTA-FEIRA</div>
<div class="b ela">Oi, Juliana! Como você está depois da limpeza? Qualquer dúvida, é só chamar. 💙<small>16:30</small></div>""")


def _lado(ativo):
    itens = ["Dashboard", "CRM", "Agenda", "Mensagens", "Leads / Clientes"]
    links = "".join(f'<a class="{"on" if i == ativo else ""}">{i}</a>' for i in itens)
    return f"""<div class="lado"><div class="cl"><span>S</span>Clínica Sorriso</div><div class="sec">Atendimento</div>{links}
<div class="sec" style="margin-top:8px">Gestão</div><a>Relatórios</a><a>Configurações</a></div>"""


def _janela(ativo, miolo, lado=True):
    return f'<div class="janela"><div class="barra"><i></i><i></i><i></i></div><div class="painel">{_lado(ativo) if lado else ""}<div class="conteudo">{miolo}</div></div></div>'


def dashboard():
    cards = [("8", "Consultas hoje"), ("6 × 2", "Confirmadas × pendentes"), ("1", "Esperando uma pessoa"), ("12", "Mensagens na fila")]
    c = "".join(f'<div class="card"><div class="num">{n}</div><div class="rot">{r}</div></div>' for n, r in cards)
    hoje = [("08:30", "Carlos Mendes", "Avaliação · Dr. Rafael Prado", "s-verde", "Confirmada"),
            ("09:00", "Mariana Costa", "Limpeza · Dra. Ana Lima", "s-verde", "Confirmada"),
            ("10:30", "Juliana Prado", "Limpeza · Dra. Ana Lima", "s-ambar", "Aguardando confirmação"),
            ("11:00", "Pedro Alves", "Canal (sessão 2 de 3) · Dr. Rafael Prado", "s-verde", "Confirmada"),
            ("14:00", "Fernanda Rocha", "Clareamento · Dra. Ana Lima", "s-azul", "Compareceu")]
    l = "".join(f'<div class="linha"><div class="h">{h}</div><div class="q">{n}<span>{p}</span></div><span class="selo {s}">{t}</span></div>' for h, n, p, s, t in hoje)
    return _janela("Dashboard", f'<h4>Dashboard</h4><div class="sub">Resumo do dia da clínica</div><div class="cards">{c}</div><div class="card"><b style="font-size:11px">Consultas de hoje</b>{l}</div>')


def agenda(lado=True):
    dias = [("Seg", 24), ("Ter", 25), ("Qua", 26), ("Qui", 27), ("Sex", 28)]
    cab = '<div></div>' + "".join(f'<div class="cab {"hoje" if d == 26 else ""}">{n}<b>{d}</b></div>' for n, d in dias)
    horas = '<div class="horas">' + "".join(f'<div style="top:{i*28}px">{8+i}:00</div>' for i in range(8)) + '</div>'
    evs = {24: [(0, 28, "e1", "Carlos M.", "Avaliação"), (56, 42, "e2", "Pedro A.", "Canal"), (168, 28, "e3", "Ana B.", "Limpeza")],
           25: [(14, 28, "e3", "Lucas M.", "Limpeza"), (84, 42, "e1", "Camila R.", "Implante"), (182, 28, "e2", "Bruno T.", "Retorno")],
           26: [(14, 28, "e3", "Mariana C.", "Limpeza"), (70, 28, "e4", "Juliana P.", "Limpeza"), (98, 42, "e2", "Pedro A.", "Canal"), (168, 28, "e1", "Fernanda R.", "Clareamento")],
           27: [(0, 28, "e1", "Thiago M.", "Avaliação"), (70, 28, "e3", "Juliana P.", "Limpeza"), (140, 42, "e2", "Rodrigo P.", "Canal")],
           28: [(28, 28, "e4", "Natália D.", "Avaliação"), (112, 28, "e3", "Felipe C.", "Limpeza"), (196, 28, "e1", "Isabela M.", "Retorno")]}
    cols = "".join('<div class="col">' + "".join(f'<div class="ev {c}" style="top:{t}px;height:{h-3}px"><b>{n}</b>{p}</div>' for t, h, c, n, p in evs[d]) + '</div>' for _, d in dias)
    return _janela("Agenda", f'<h4>Agenda</h4><div class="sub">24 – 28 de novembro · todos os profissionais</div><div class="grade">{cab}{horas}{cols}</div>', lado)


def kanban(lado=True):
    cols = [("Novo Contato", "#C2547A", [("Larissa Gomes", "Perguntou sobre clareamento", "s-cinza", "Automático"), ("Diego Barbosa", "Quer saber de convênio", "s-ambar", "Manual"), ("Aline Carvalho", "Pediu valores", "s-cinza", "Automático")]),
            ("Agendados", "#2E9E5B", [("Juliana Prado", "Limpeza · qui 27/11 10:30", "s-cinza", "Automático"), ("Thiago Moreira", "Avaliação · qui 27/11 08:00", "s-cinza", "Automático")]),
            ("Confirmado", "#1F8A4C", [("Mariana Costa", "Limpeza · qua 26/11 09:00", "s-cinza", "Automático"), ("Pedro Alves", "Canal · qua 26/11 11:00", "s-cinza", "Automático"), ("Carlos Mendes", "Avaliação · qua 26/11 08:30", "s-cinza", "Automático")]),
            ("Cancelados", "#D9473F", [("Gustavo Araújo", "Remarcar na próxima semana", "s-ambar", "Manual")])]
    html = ""
    for t, cor, cards in cols:
        cs = "".join(f'<div class="kc"><b>{n}</b><span>{d}</span><span class="selo {s}">{x}</span></div>' for n, d, s, x in cards)
        html += f'<div class="kcol"><h5><span><i style="background:{cor}"></i>{t}</span><em>{len(cards)}</em></h5>{cs}</div>'
    return _janela("CRM", f'<h4>CRM</h4><div class="sub">Cada contato no seu momento do funil</div><div class="kan">{html}</div>', lado)


def celular_painel():
    itens = [("08:30", "09:00", "#b85c74", "Carlos Mendes", "Avaliação · Dr. Rafael Prado", "s-verde", "Confirmada"),
             ("09:00", "09:40", "#1f7a43", "Mariana Costa", "Limpeza · Dra. Ana Lima", "s-verde", "Confirmada"),
             ("10:30", "11:10", "#1f7a43", "Juliana Prado", "Limpeza · Dra. Ana Lima", "s-ambar", "Aguardando"),
             ("11:00", "12:00", "#1f6aa8", "Pedro Alves", "Canal · Dr. Rafael Prado", "s-verde", "Confirmada"),
             ("14:00", "15:00", "#b85c74", "Fernanda Rocha", "Clareamento · Dra. Ana Lima", "s-azul", "Compareceu")]
    l = "".join(f'<div class="item"><div class="h">{a}<small>{b}</small></div><div class="fx" style="background:{c}"></div><div class="q"><b>{n}</b><span>{p}</span><span class="selo {s}" style="margin-top:3px;display:inline-flex">{t}</span></div></div>' for a, b, c, n, p, s, t in itens)
    abas = "".join(f'<div class="{"on" if x == "Agenda" else ""}"><i></i>{x}</div>' for x in ["Início", "CRM", "Agenda", "Mensagens", "Clientes"])
    return f"""<div class="fone"><div class="mob"><div class="topo"><span class="lg">S</span><div class="t"><b>Clínica Sorriso</b><small>● Ísis atendendo</small></div></div>
<div class="corpo"><div style="display:flex;justify-content:space-between;align-items:center"><b style="font-size:15px">Agenda</b><span class="selo" style="background:var(--marca);color:#fff;padding:4px 9px">+ Marcar</span></div>
<div class="nav"><span>‹</span><div style="text-align:center;line-height:1.2"><b>Hoje</b><small style="display:block;color:var(--muted);font-size:9px">5 consultas</small></div><span>›</span></div>{l}</div>
<div class="abas">{abas}</div></div></div>"""
