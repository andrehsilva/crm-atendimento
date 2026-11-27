from comum import CSS, logo

DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def _campo(rotulo, largura="1fr", alto=False):
    cls = "campo alto" if alto else "campo"
    return f'<label class="{cls}" style="grid-column:span {largura}"><span>{rotulo}</span><div class="ed" contenteditable="true"></div></label>'


def _caixa(texto, sub=""):
    s = f"<small>{sub}</small>" if sub else ""
    return f'<label class="cx"><input type="checkbox"><span>{texto}{s}</span></label>'


def _tabela(cabecalhos, linhas, larguras):
    cab = "".join(f'<th style="width:{l}">{c}</th>' for c, l in zip(cabecalhos, larguras))
    corpo = "".join("<tr>" + "".join('<td contenteditable="true"></td>' for _ in cabecalhos) + "</tr>" for _ in range(linhas))
    return f'<table class="tab"><tr>{cab}</tr>{corpo}</table>'


def _secao(n, titulo, sub=""):
    s = f'<p class="secsub">{sub}</p>' if sub else ""
    return f'<div class="sec"><span class="n">{n}</span><div><h2>{titulo}</h2>{s}</div></div>'


def _rodape(pag, total=5):
    return f'<div class="rodape"><span>{logo(14)}<span class="sep">·</span>Checklist de implantação</span><span>{pag}/{total}</span></div>'


def checklist(contato):
    horario = "".join(
        f'<tr><td class="dia">{d}</td><td contenteditable="true"></td><td contenteditable="true"></td>'
        f'<td contenteditable="true"></td><td class="c"><input type="checkbox"></td></tr>' for d in DIAS)

    resumo = [
        ("Dados e marca da clínica", "nome, endereço, telefone, logo e cor", 1),
        ("Tipo de clínica", "define os termos e procedimentos iniciais", 2),
        ("Horário de funcionamento", "pausas, feriados e recessos", 3),
        ("Profissionais", "nome, especialidade e horário de cada um", 4),
        ("Procedimentos", "nome, duração e valor de tabela", 5),
        ("Convênios", "se a clínica atender", 6),
        ("Informações para a Ísis", "o que ela pode responder aos clientes", 7),
        ("Jeito de falar", "mais formal ou mais próximo", 8),
        ("Equipe que vai usar o painel", "e-mail de cada pessoa e quem é o administrador", 9),
        ("WhatsApp da clínica", "como conectar (QR code ou oficial da Meta) e o número", 10),
        ("Mensagens automáticas", "lembrete, pós-consulta, retorno e aniversário", 11),
    ]
    itens = "".join(
        f'<label class="item"><input type="checkbox"><span class="num">{n}</span><span><b>{t}</b><small>{s}</small></span></label>'
        for t, s, n in resumo)

    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TemHorario · Checklist de implantação</title>
<style>{CSS}
@page{{size:A4;margin:0}}
body{{background:#e9e6e2}}
.pg{{width:210mm;height:297mm;padding:15mm 16mm 16mm;position:relative;overflow:hidden;background:#fff;page-break-after:always;margin:0 auto}}
.pg:last-child{{page-break-after:auto}}
@media screen{{.pg{{margin:8mm auto;box-shadow:0 10px 30px rgba(31,31,34,.12);border-radius:4px}}}}
.rodape{{position:absolute;left:16mm;right:16mm;bottom:9mm;display:flex;justify-content:space-between;align-items:center;font-size:9px;color:var(--muted)}}
.rodape .marca{{font-size:10px!important}}.rodape .sep{{margin:0 6px}}
/* capa */
.capa{{background:var(--text);color:#fff;border-radius:20px;padding:11mm 11mm 10mm;position:relative;overflow:hidden}}
.capa::after{{content:'';position:absolute;right:-30mm;top:-30mm;width:90mm;height:90mm;border-radius:50%;background:radial-gradient(circle,rgba(184,92,116,.55),rgba(184,92,116,0) 70%)}}
.capa .tag{{display:block;margin-top:6mm;font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:#f2a7bd;font-weight:600}}
.capa h1{{font-size:31px;line-height:1.1;font-weight:800;letter-spacing:-.03em;margin-top:2.5mm;max-width:140mm;position:relative;z-index:1}}
.capa h1 em{{font-style:normal;color:#f2a7bd}}
.capa p{{font-size:12px;line-height:1.6;color:#d6d2d8;margin-top:4mm;max-width:138mm;position:relative;z-index:1}}
.clinica{{display:grid;grid-template-columns:1fr 52mm;gap:4mm;margin-top:7mm;position:relative;z-index:1}}
.clinica .campo span{{color:#bdb8c0}}.clinica .ed{{border-color:#5a5a60;color:#fff}}
.passos{{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm;margin:7mm 0 6mm}}
.passo{{border:1px solid var(--line);border-radius:14px;padding:4.5mm}}
.passo .p{{width:24px;height:24px;border-radius:50%;background:var(--marca-soft);color:var(--marca);display:grid;place-items:center;font-weight:700;font-size:11px;margin-bottom:2.5mm}}
.passo b{{display:block;font-size:12px;margin-bottom:1mm}}.passo p{{font-size:10px;color:var(--muted);line-height:1.5}}
h3.tit{{font-size:14px;font-weight:700;margin-bottom:3mm;display:flex;justify-content:space-between;align-items:baseline}}
h3.tit small{{font-size:9.5px;font-weight:400;color:var(--muted)}}
.itens{{display:grid;grid-template-columns:1fr 1fr;gap:2.2mm 5mm}}
.item{{display:flex;align-items:center;gap:3mm;padding:2.6mm 3.5mm;border-radius:11px;background:var(--bg);cursor:pointer}}
.item .num{{flex:none;font-size:10px;font-weight:700;color:var(--marca);width:16px}}
.item b{{display:block;font-size:11px;font-weight:600}}.item small{{display:block;font-size:9.2px;color:var(--muted);margin-top:.3mm}}
.dica{{display:flex;gap:3.5mm;align-items:flex-start;background:var(--marca-soft);border-radius:14px;padding:4mm 5mm;margin-top:5mm;font-size:10.3px;line-height:1.55;color:#5b3442}}
.dica .ic{{font-size:15px;line-height:1}}
.dica b{{color:var(--marca-escura)}}
/* checkbox */
input[type=checkbox]{{appearance:none;-webkit-appearance:none;flex:none;width:14px;height:14px;border:1.5px solid var(--marca);border-radius:4px;background:#fff;display:grid;place-items:center;cursor:pointer;margin:0}}
input[type=checkbox]:checked{{background:var(--marca)}}
input[type=checkbox]:checked::after{{content:'';width:4px;height:7px;border:solid #fff;border-width:0 2px 2px 0;transform:rotate(45deg) translate(-.5px,-1px)}}
/* seções */
.sec{{display:flex;gap:3.5mm;align-items:flex-start;margin:6mm 0 3mm}}
.sec:first-child{{margin-top:0}}
.sec .n{{flex:none;width:26px;height:26px;border-radius:8px;background:var(--marca);color:#fff;display:grid;place-items:center;font-weight:700;font-size:12px;margin-top:1px}}
.sec h2{{font-size:16px;font-weight:700;letter-spacing:-.01em;line-height:1.3}}
.secsub{{font-size:9.8px;color:var(--muted);margin-top:.6mm;line-height:1.45}}
.grade{{display:grid;grid-template-columns:repeat(6,1fr);gap:3mm 4mm}}
.campo{{display:flex;flex-direction:column;gap:1mm}}
.campo span{{font-size:9px;color:var(--muted);letter-spacing:.02em}}
.ed{{min-height:7mm;border-bottom:1.2px solid #d6d1cc;font-size:11px;padding:1mm 0;outline:none}}
.campo.alto .ed{{min-height:15mm;border:1.2px solid #d6d1cc;border-radius:8px;padding:2mm 2.5mm;background-image:repeating-linear-gradient(transparent 0 6.6mm,#efebe7 6.6mm 6.8mm)}}
.ed:focus,td[contenteditable]:focus{{background:#fdf6f8}}
.cxs{{display:flex;flex-wrap:wrap;gap:2mm}}
.cx{{display:inline-flex;align-items:center;gap:2mm;border:1px solid var(--line);border-radius:20px;padding:1.6mm 3.4mm 1.6mm 2.4mm;font-size:10.3px;cursor:pointer}}
.cx small{{color:var(--muted);font-size:9px;margin-left:1.5mm}}
.cxs.pilha{{flex-direction:column;gap:1.6mm}}.cxs.pilha .cx{{border:0;padding:0;border-radius:0}}
.tab{{width:100%;border-collapse:separate;border-spacing:0;font-size:10.3px;border:1px solid var(--line);border-radius:10px;overflow:hidden}}
.tab th{{background:var(--bg);font-weight:600;font-size:9.2px;color:#57535a;text-align:left;padding:2mm 2.5mm;border-bottom:1px solid var(--line)}}
.tab td{{height:8mm;padding:1mm 2.5mm;border-bottom:1px solid var(--line);border-left:1px solid var(--line);outline:none}}
.tab td:first-child{{border-left:0}}.tab tr:last-child td{{border-bottom:0}}
.tab td.dia{{font-weight:500;background:#fcfbfa;width:22%}}.tab td.c{{text-align:center}}.tab td.c input{{margin:auto}}
.ex{{color:#a9a4ad;font-style:italic}}
.nota{{font-size:9.6px;color:var(--muted);line-height:1.5;margin-top:2mm}}
.nota b{{color:var(--text);font-weight:600}}
.dois{{display:grid;grid-template-columns:1fr 1fr;gap:5mm}}
.bloco{{border:1px solid var(--line);border-radius:12px;padding:3.5mm 4mm}}
.bloco b.t{{display:block;font-size:11px;margin-bottom:2mm}}
.bloco.opc p{{font-size:9.6px;color:var(--muted);line-height:1.5;margin:1.5mm 0 0 6mm}}
.bloco.opc b{{color:var(--text)}}
.aviso{{background:var(--ambar-soft);color:#6e4c08;border-radius:12px;padding:3mm 4mm;font-size:9.6px;line-height:1.5;margin-top:3mm}}
.fim{{background:var(--text);color:#fff;border-radius:18px;padding:6mm 7mm;display:grid;grid-template-columns:1fr auto;gap:6mm;align-items:center;margin-top:6mm}}
.fim h3{{font-size:16px;font-weight:700;margin-bottom:1.5mm}}.fim p{{font-size:10px;color:#cfcbd2;line-height:1.55}}
.fim .bt{{background:var(--marca);border-radius:12px;padding:3.5mm 5mm;font-weight:600;font-size:11px;text-align:center;line-height:1.4;white-space:nowrap}}
.fim .bt small{{display:block;font-weight:400;font-size:9.5px;opacity:.9}}
.linha-tempo{{display:grid;grid-template-columns:repeat(4,1fr);gap:4mm;position:relative}}
.linha-tempo::before{{content:'';position:absolute;left:4mm;right:4mm;top:12px;height:2px;background:var(--marca-soft)}}
.linha-tempo>div{{position:relative}}
.linha-tempo .p{{width:26px;height:26px;border-radius:50%;background:var(--marca);color:#fff;display:grid;place-items:center;font-weight:700;font-size:11px;margin-bottom:3mm;box-shadow:0 0 0 4px #fff}}
.linha-tempo b{{display:block;font-size:11.5px;margin-bottom:1mm}}.linha-tempo p{{font-size:9.8px;color:var(--muted);line-height:1.5}}
.imprimir{{position:fixed;right:18px;bottom:18px;background:var(--marca);color:#fff;border:0;border-radius:12px;padding:12px 18px;font:600 13px Lexend,sans-serif;box-shadow:0 8px 20px rgba(184,92,116,.35);cursor:pointer}}
@media print{{body{{background:#fff}}.linha-tempo{{display:grid;grid-template-columns:repeat(4,1fr);gap:4mm;position:relative}}
.linha-tempo::before{{content:'';position:absolute;left:4mm;right:4mm;top:12px;height:2px;background:var(--marca-soft)}}
.linha-tempo>div{{position:relative}}
.linha-tempo .p{{width:26px;height:26px;border-radius:50%;background:var(--marca);color:#fff;display:grid;place-items:center;font-weight:700;font-size:11px;margin-bottom:3mm;box-shadow:0 0 0 4px #fff}}
.linha-tempo b{{display:block;font-size:11.5px;margin-bottom:1mm}}.linha-tempo p{{font-size:9.8px;color:var(--muted);line-height:1.5}}
.imprimir{{display:none}}}}
@media screen and (max-width:820px){{.pg{{width:auto;height:auto;min-height:0;margin:0;border-radius:0;padding:16px 16px 60px}}
.grade,.dois,.itens,.passos,.clinica,.linha-tempo{{grid-template-columns:1fr!important}}.grade>*{{grid-column:auto!important}}.rodape{{left:16px;right:16px;bottom:16px}}
.tab{{display:block;overflow-x:auto}}.fim{{grid-template-columns:1fr}}}}
</style></head><body>
<button class="imprimir" onclick="window.print()">Salvar em PDF / imprimir</button>

<section class="pg">
  <div class="capa">
    {logo(34, cor_texto="#fff")}
    <span class="tag">Checklist de implantação</span>
    <h1>Vamos deixar a Ísis <em>com a cara da sua clínica.</em></h1>
    <p>Com estas informações configuramos a agenda, os profissionais e o atendimento pelo WhatsApp do jeito que a clínica já trabalha.
    Preencha o que souber — o que faltar, a gente completa juntos na conversa de implantação.</p>
    <div class="clinica">{_campo("Nome da clínica")}{_campo("Data")}</div>
  </div>

  <div class="passos">
    <div class="passo"><div class="p">1</div><b>Você preenche</b><p>Este checklist, no papel ou direto no computador. Leva uns 20 minutos.</p></div>
    <div class="passo"><div class="p">2</div><b>A gente configura</b><p>Horários, profissionais, procedimentos, mensagens e o jeito de falar da Ísis.</p></div>
    <div class="passo"><div class="p">3</div><b>Ligamos o WhatsApp</b><p>Pelo QR code ou pela conta oficial da Meta, testamos juntos e a equipe aprende o painel.</p></div>
  </div>

  <h3 class="tit">O que vamos precisar <small>marque conforme for separando</small></h3>
  <div class="itens">{itens}
    <div class="item" style="background:var(--marca-soft)"><span class="num">✓</span><span><b style="color:var(--marca-escura)">Pronto!</b><small>é só nos enviar</small></span></div>
  </div>

  <div class="dica"><span class="ic">💡</span><div><b>Não precisa estar tudo perfeito.</b> Horários, procedimentos, textos e mensagens podem ser
  mudados depois pelo próprio painel, a qualquer momento. O importante para começar é o horário da clínica, os profissionais e os procedimentos mais marcados.</div></div>
  {_rodape(1)}
</section>

<section class="pg">
  {_secao(1, "Dados e marca da clínica", "Aparecem no painel e nas mensagens. Logo e cor deixam o painel com a identidade da clínica.")}
  <div class="grade">
    {_campo("Nome como os clientes conhecem", 4)}{_campo("Telefone fixo", 2)}
    {_campo("Endereço completo (rua, número, bairro, cidade)", 6)}
    {_campo("E-mail da clínica", 3)}{_campo("Instagram ou site (opcional)", 3)}
    {_campo("Cor da marca (ou código, ex.: #B85C74)", 3)}
    <label class="campo" style="grid-column:span 3"><span>Logo</span><div class="cxs" style="padding-top:1.5mm">{_caixa("Vou enviar o arquivo", "PNG ou JPG")}{_caixa("Não temos logo")}</div></label>
  </div>

  {_secao(2, "Tipo de clínica", "Define as palavras usadas (consulta, sessão, atendimento) e os procedimentos que já vêm sugeridos.")}
  <div class="cxs">{"".join(_caixa(t) for t in ["Odontologia", "Medicina", "Fisioterapia", "Psicologia", "Psicanálise", "Psiquiatria", "Estética", "Outro: ____________"])}</div>

  {_secao(3, "Horário de funcionamento", "A Ísis só oferece horários dentro deste quadro. Deixe a pausa em branco se não houver.")}
  <table class="tab"><tr><th>Dia</th><th>Abre às</th><th>Pausa (ex.: 12h–13h30)</th><th>Fecha às</th><th style="width:14%;text-align:center">Fechado</th></tr>{horario}</table>
  <div class="dois" style="margin-top:4mm">
    {_campo("Feriados e recessos em que a clínica fecha (ex.: 24/12 a 02/01)", 1, alto=True)}
    {_campo("Antecedência mínima para marcar (ex.: 2 horas, 1 dia)", 1, alto=True)}
  </div>
  {_rodape(2)}
</section>

<section class="pg">
  {_secao(4, "Profissionais", "Se o horário for igual ao da clínica, escreva “o mesmo”. Cada profissional pode ter até duas faixas por dia. O WhatsApp é para o resumo do dia, enviado de manhã.")}
  {_tabela(["Nome", "Especialidade", "WhatsApp (resumo do dia)", "Dias e horário de atendimento"], 6, ["24%", "20%", "20%", "36%"])}

  {_secao(5, "Procedimentos", "Os mais marcados primeiro. A duração reserva o tempo certo na agenda; o valor é opcional e só é informado se a clínica quiser. “Retorno em” é para o convite de volta.")}
  {_tabela(["Procedimento", "Duração", "Valor (opcional)", "Quem faz", "Retorno em"], 9, ["32%", "13%", "16%", "22%", "17%"])}
  <p class="nota"><b>Exemplo:</b> Limpeza · 40 min · R$ 180 · Dra. Ana · 6 meses</p>

  {_secao(6, "Convênios", "Se a clínica atende convênios, liste quais. Assim a Ísis sabe responder “vocês aceitam…?”.")}
  <div class="cxs" style="margin-bottom:3mm">{_caixa("Só particular")}{_caixa("Particular e convênios")}</div>
  {_campo("Convênios aceitos (e se algum vale só para certos procedimentos ou profissionais)", 1, alto=True)}
  {_rodape(3)}
</section>

<section class="pg">
  {_secao(7, "Informações para a Ísis", "Ela só responde o que estiver cadastrado. O que não souber, passa para a recepção.")}
  <div class="dois">
    {_campo("Como chegar e estacionamento", 1, alto=True)}
    {_campo("Formas de pagamento (Pix, cartão, parcelamento…)", 1, alto=True)}
    {_campo("Preparo ou orientações antes da consulta", 1, alto=True)}
    {_campo("Outras dúvidas frequentes dos clientes", 1, alto=True)}
  </div>

  {_secao(8, "Jeito de falar")}
  <div class="dois">
    <div class="bloco"><b class="t">Tom das mensagens</b><div class="cxs pilha">{_caixa("Mais formal", "“Olá, Sr. João. Sua consulta está confirmada.”")}{_caixa("Mais próximo", "“Oi, João! Tudo certo para amanhã 😊”")}</div></div>
    <div class="bloco"><b class="t">Como tratar o cliente</b><div class="cxs pilha">{_caixa("Você", "“Você prefere de manhã ou à tarde?”")}{_caixa("Senhor(a)", "“A senhora prefere de manhã ou à tarde?”")}</div></div>
  </div>

  {_secao(9, "Equipe que vai usar o painel", "Cada pessoa recebe um acesso com senha provisória, trocada no primeiro login. O administrador mexe nas configurações; os demais cuidam do dia a dia.")}
  <table class="tab"><tr><th style="width:34%">Nome</th><th style="width:40%">E-mail</th><th style="width:26%;text-align:center">Administrador?</th></tr>
  {"".join('<tr><td contenteditable="true"></td><td contenteditable="true"></td><td class="c"><input type="checkbox"></td></tr>' for _ in range(8))}</table>

  {_rodape(4)}
</section>

<section class="pg">
  {_secao(10, "WhatsApp da clínica", "Escolha como as mensagens vão passar. A Ísis, o painel e a agenda são os mesmos nas duas — e dá para trocar depois. Veja o guia “Duas formas de conectar o WhatsApp”.")}
  <div class="dois">
    <div class="bloco opc">{_caixa("<b>Conexão pelo QR code</b>")}
      <p>Sem custo por mensagem. Ativa no mesmo dia, lendo o QR code com o celular da clínica (como o WhatsApp Web).
      É uma integração não oficial: existe risco de o WhatsApp bloquear o número.</p></div>
    <div class="bloco opc">{_caixa("<b>WhatsApp oficial (Meta)</b>")}
      <p>Conexão oficial, sem risco de bloqueio por integração não oficial. Tem um <b>custo por mensagem</b>, pago pela
      clínica direto à Meta, que aparece no painel todo mês. A ativação leva alguns dias.</p></div>
  </div>
  <div class="grade" style="margin-top:3mm">{_campo("Número que vai atender os clientes", 3)}{_campo("Quem cuida disso na clínica", 3)}</div>
  <div class="aviso"><b>Se escolher o QR code:</b> o celular com esse WhatsApp precisa estar em mãos no dia da ativação.
  <b>Se escolher o oficial:</b> separe acesso de administrador ao Gerenciador de Negócios da Meta, os dados da empresa
  para a verificação (CNPJ, site ou documento) e um cartão para a Meta cobrar as mensagens. A gente ajuda em cada passo.</div>

  {_secao(11, "Mensagens automáticas", "Todas podem ser ligadas, desligadas ou ter o texto mudado depois.")}
  <div class="dois">
    <div class="bloco"><div class="cxs pilha">
      {_caixa("Lembrete na véspera", "1 confirma · 2 remarca · 3 cancela")}
      {_caixa("Pós-consulta", "“como você está?” no dia seguinte")}
      {_caixa("Convite de retorno", "na data do “retorno em”")}
      {_caixa("Aniversário", "no dia, com o nome do cliente")}
    </div></div>
    {_campo("Texto da mensagem de aniversário (se quiser um próprio)", 1, alto=True)}
  </div>

  {_secao(12, "Quem preencheu", "Para a gente saber com quem falar se surgir alguma dúvida.")}
  <div class="grade">{_campo("Nome", 3)}{_campo("Função na clínica", 3)}{_campo("WhatsApp para contato", 3)}{_campo("Melhor horário para falarmos", 3)}</div>

  <h3 class="tit" style="margin-top:8mm">Depois que você enviar</h3>
  <div class="linha-tempo">
    <div><span class="p">1</span><b>Configuramos</b><p>Montamos a clínica no TemHorario com o que veio neste checklist.</p></div>
    <div><span class="p">2</span><b>Revisamos juntos</b><p>Mostramos a agenda e as mensagens, e ajustamos o que precisar.</p></div>
    <div><span class="p">3</span><b>Ativamos o WhatsApp</b><p>QR code ou conexão oficial, e uma conversa de teste com a Ísis.</p></div>
    <div><span class="p">4</span><b>Equipe no painel</b><p>Cada pessoa entra com o seu acesso e aprende o dia a dia.</p></div>
  </div>

  <div class="fim"><div><h3>Terminou? Envie para a gente.</h3>
    <p>Mande este arquivo preenchido (ou uma foto das páginas), junto com o logo. <b style="color:#fff">Não envie dados de pacientes</b> por aqui — como trazer a lista de clientes a gente combina na implantação.</p></div>
    <div class="bt">Fale com a gente<small>{contato}</small></div></div>
  {_rodape(5)}
</section>
</body></html>"""
