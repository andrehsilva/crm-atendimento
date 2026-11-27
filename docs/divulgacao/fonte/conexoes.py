from comum import CSS, logo


def _rodape(pag, total=3):
    return (f'<div class="rodape"><span>{logo(14)}<span class="sep">·</span>Duas formas de conectar o WhatsApp</span>'
            f'<span>{pag}/{total}</span></div>')


def _lista(itens, tipo):
    return "".join(f'<li class="{tipo}">{i}</li>' for i in itens)


# (tema, QR code, oficial) — o selo marca quem leva vantagem naquele ponto
COMPARA = [
    ("Como conecta", "Lendo um QR code com o celular da clínica, como o WhatsApp Web.", None,
     "Pela conta oficial da clínica na Meta (dona do WhatsApp), com a verificação da empresa.", None),
    ("Tempo para ativar", "No mesmo dia.", "qr", "Alguns dias: verificação da empresa e aprovação dos modelos de mensagem.", None),
    ("Custo por mensagem", "Nenhum.", "qr", "Sim, cobrado pela Meta direto da clínica. Aparece no painel todo mês.", None),
    ("Risco de bloqueio do número", "Existe: é uma integração não oficial, que o WhatsApp não autoriza.", None,
     "Sem risco por integração não oficial. Vale a política normal do WhatsApp.", "of"),
    ("Estabilidade", "Às vezes é preciso ler o QR code de novo para reconectar.", None,
     "Conexão estável, sem celular no meio.", "of"),
    ("O número no celular", "Continua funcionando no aplicativo do celular.", "qr",
     "Em geral passa a ser usado só pelo painel. Avaliamos o seu caso na implantação.", None),
    ("Mensagens depois de 24 h", "Texto livre, do jeito da clínica.", "qr",
     "Lembrete, aniversário e retorno saem em modelos aprovados pela Meta (texto padrão com o nome do cliente).", None),
    ("Campanhas", "Saem na data marcada.", "qr", "Cada campanha passa pela aprovação da Meta antes de sair.", None),
    ("Lembrete", "Cliente responde 1, 2 ou 3.", None, "Cliente toca em botões: Confirmar · Remarcar · Cancelar.", "of"),
    ("Imagem da clínica", "Número comum.", None, "Conta comercial oficial, com o nome da clínica aprovado pela Meta.", "of"),
]


def conexoes(contato):
    linhas = "".join(
        f'<tr><th>{t}</th><td class="{"ganha" if vq else ""}">{q}</td><td class="{"ganha" if vo else ""}">{o}</td></tr>'
        for t, q, vq, o, vo in COMPARA)
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TemHorario · Duas formas de conectar o WhatsApp</title>
<style>{CSS}
@page{{size:A4;margin:0}}
body{{background:#e9e6e2}}
.pg{{width:210mm;height:297mm;padding:15mm 16mm 16mm;position:relative;overflow:hidden;background:#fff;page-break-after:always;margin:0 auto}}
.pg:last-child{{page-break-after:auto}}
@media screen{{.pg{{margin:8mm auto;box-shadow:0 10px 30px rgba(31,31,34,.12);border-radius:4px}}}}
.rodape{{position:absolute;left:16mm;right:16mm;bottom:9mm;display:flex;justify-content:space-between;align-items:center;font-size:9px;color:var(--muted)}}
.rodape .marca{{font-size:10px!important}}.rodape .sep{{margin:0 6px}}
.capa{{background:var(--text);color:#fff;border-radius:20px;padding:11mm 11mm 10mm;position:relative;overflow:hidden}}
.capa::after{{content:'';position:absolute;right:-30mm;top:-30mm;width:90mm;height:90mm;border-radius:50%;background:radial-gradient(circle,rgba(184,92,116,.55),rgba(184,92,116,0) 70%)}}
.capa .tag{{display:block;margin-top:6mm;font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:#f2a7bd;font-weight:600}}
.capa h1{{font-size:30px;line-height:1.12;font-weight:800;letter-spacing:-.03em;margin-top:2.5mm;max-width:150mm;position:relative;z-index:1}}
.capa h1 em{{font-style:normal;color:#f2a7bd}}
.capa p{{font-size:12px;line-height:1.6;color:#d6d2d8;margin-top:4mm;max-width:150mm;position:relative;z-index:1}}
.igual{{display:flex;gap:4mm;align-items:center;background:var(--bg);border-radius:14px;padding:4mm 5mm;margin:6mm 0 5mm;font-size:10.5px;line-height:1.5;color:#4a474d}}
.igual .ic{{font-size:18px}}
.igual b{{color:var(--text)}}
.opcoes{{display:grid;grid-template-columns:1fr 1fr;gap:5mm}}
.opcao{{border-radius:18px;padding:6mm;border:1.5px solid var(--line);display:flex;flex-direction:column}}
.opcao.of{{border-color:var(--marca);background:linear-gradient(180deg,var(--marca-soft),#fff 45%)}}
.opcao .ic{{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;font-size:19px;background:var(--bg)}}
.opcao.of .ic{{background:var(--marca);color:#fff}}
.opcao h2{{font-size:17px;font-weight:800;letter-spacing:-.02em;margin-top:3.5mm}}
.opcao .sub{{font-size:10px;color:var(--muted);margin-top:1mm}}
.opcao .resumo{{font-size:11px;line-height:1.55;color:#3d3a40;margin:3.5mm 0}}
.opcao h4{{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:2.5mm 0 1.5mm}}
ul.pc{{list-style:none;display:grid;gap:1.6mm;font-size:10.3px;line-height:1.45}}
ul.pc li{{padding-left:5.5mm;position:relative}}
ul.pc li::before{{position:absolute;left:0;top:0;font-weight:700}}
ul.pc li.mais::before{{content:'✓';color:var(--verde)}}
ul.pc li.menos::before{{content:'–';color:var(--vermelho)}}
.ideal{{margin-top:auto;padding-top:3.5mm;border-top:1px dashed var(--line);font-size:10px;color:#4a474d;line-height:1.5}}
.ideal b{{color:var(--marca-escura)}}
h2.tit{{font-size:20px;font-weight:800;letter-spacing:-.02em;margin-bottom:1.5mm}}
h2.tit em{{font-style:normal;color:var(--marca)}}
p.sub2{{font-size:10.5px;color:var(--muted);margin-bottom:5mm;line-height:1.5}}
table.cmp{{width:100%;border-collapse:separate;border-spacing:0;font-size:10px;line-height:1.45;border:1px solid var(--line);border-radius:14px;overflow:hidden}}
table.cmp thead th{{background:var(--text);color:#fff;font-size:10.5px;font-weight:600;padding:3mm 3.5mm;text-align:left}}
table.cmp thead th.of{{background:var(--marca)}}
table.cmp tbody th{{width:27%;text-align:left;font-weight:600;background:var(--bg);padding:2.6mm 3.5mm;vertical-align:top}}
table.cmp td{{padding:2.6mm 3.5mm;vertical-align:top;border-left:1px solid var(--line);color:#3d3a40}}
table.cmp tbody tr+tr th,table.cmp tbody tr+tr td{{border-top:1px solid var(--line)}}
table.cmp td.ganha{{background:#f1faf4}}
table.cmp td.ganha::before{{content:'✓ ';color:var(--verde);font-weight:700}}
.legenda{{font-size:9px;color:var(--muted);margin-top:2mm}}
.transp{{display:grid;grid-template-columns:auto 1fr;gap:5mm;align-items:start;background:var(--marca-soft);border-radius:18px;padding:6mm 7mm;margin-top:6mm}}
.transp .ic{{font-size:24px}}
.transp h3{{font-size:14px;font-weight:700;color:var(--marca-escura);margin-bottom:2mm}}
.transp p{{font-size:10.5px;line-height:1.6;color:#5b3442}}
.transp ul{{margin-top:2mm;padding-left:4mm;font-size:10.3px;line-height:1.6;color:#5b3442}}
.escolha{{display:grid;grid-template-columns:1fr 1fr;gap:5mm;margin-top:5mm}}
.escolha .bx{{border-radius:16px;padding:5mm 5.5mm;background:var(--bg)}}
.escolha .bx.of{{background:#fff;border:1.5px solid var(--marca)}}
.escolha h3{{font-size:12.5px;font-weight:700;margin-bottom:2.5mm}}
.escolha ul{{list-style:none;display:grid;gap:1.8mm;font-size:10.3px;line-height:1.45;color:#3d3a40}}
.escolha li::before{{content:'→ ';color:var(--marca);font-weight:700}}
h3.sec3{{font-size:13px;font-weight:700;margin-top:6mm}}
.ativa{{display:grid;grid-template-columns:1fr 1.3fr;gap:5mm;margin-top:2.5mm}}
.ativa>div{{border:1px solid var(--line);border-radius:14px;padding:4mm 5mm}}
.ativa>div.of{{border-color:var(--marca)}}
.ativa b{{font-size:11px}}
.ativa ol{{margin:2mm 0 0 4.5mm;font-size:10px;line-height:1.55;color:#3d3a40;display:grid;gap:1mm}}
.faq{{display:grid;grid-template-columns:1fr 1fr;gap:4mm 6mm;margin-top:6mm}}
.faq b{{display:block;font-size:11px;margin-bottom:1mm}}
.faq p{{font-size:10px;color:#57535a;line-height:1.5}}
.fim{{background:var(--text);color:#fff;border-radius:18px;padding:6mm 7mm;display:grid;grid-template-columns:1fr auto;gap:6mm;align-items:center;margin-top:6mm}}
.fim h3{{font-size:16px;font-weight:700;margin-bottom:1.5mm}}.fim p{{font-size:10px;color:#cfcbd2;line-height:1.55}}
.fim .bt{{background:var(--marca);border-radius:12px;padding:3.5mm 5mm;font-weight:600;font-size:11px;text-align:center;line-height:1.4;white-space:nowrap}}
.fim .bt small{{display:block;font-weight:400;font-size:9.5px;opacity:.9}}
.nota{{font-size:8.8px;color:var(--muted);margin-top:4mm;line-height:1.5}}
@media screen and (max-width:820px){{.pg{{width:auto;height:auto;margin:0;border-radius:0;padding:16px 16px 60px}}
.opcoes,.escolha,.faq,.fim,.ativa{{grid-template-columns:1fr}}.rodape{{left:16px;right:16px;bottom:16px}}
table.cmp{{display:block;overflow-x:auto}}}}
</style></head><body>

<section class="pg">
  <div class="capa">
    {logo(34, cor_texto="#fff")}
    <span class="tag">Guia para a clínica</span>
    <h1>Duas formas de conectar <em>o WhatsApp da sua clínica.</em></h1>
    <p>O TemHorario funciona com uma conexão rápida pelo QR code ou com o WhatsApp oficial da Meta. Aqui você vê o que
    cada uma oferece, o que se ganha e o que se abre mão — para escolher com calma o que faz mais sentido hoje.</p>
  </div>

  <div class="igual"><span class="ic">🤝</span><div><b>Nas duas, o TemHorario é o mesmo:</b> a Ísis atende, marca, remarca e
  cancela; a equipe acompanha tudo no painel, com agenda, CRM, lembretes, aniversário e relatórios. Muda só o caminho por
  onde as mensagens passam — e <b>dá para trocar depois</b>.</div></div>

  <div class="opcoes">
    <div class="opcao">
      <div class="ic">📱</div>
      <h2>Conexão pelo QR code</h2>
      <div class="sub">Integração não oficial · como o WhatsApp Web</div>
      <p class="resumo">O celular da clínica lê um QR code e o número passa a conversar também pelo TemHorario.</p>
      <h4>Ganhos</h4>
      <ul class="pc">{_lista(["Sem custo por mensagem.", "Ativa no mesmo dia.", "O número continua no celular.",
                              "Textos e campanhas sempre livres, do jeito da clínica."], "mais")}</ul>
      <h4>O que se abre mão</h4>
      <ul class="pc">{_lista(["Não é autorizada pelo WhatsApp: existe risco de bloqueio do número.",
                              "Sem garantia de funcionamento; às vezes é preciso reconectar."], "menos")}</ul>
      <div class="ideal"><b>Combina com:</b> quem quer começar já, com volume moderado de mensagens e sem custo extra.</div>
    </div>
    <div class="opcao of">
      <div class="ic">✔</div>
      <h2>WhatsApp oficial (Meta)</h2>
      <div class="sub">API oficial do WhatsApp · conta da própria clínica</div>
      <p class="resumo">A clínica tem uma conta comercial oficial na Meta e o TemHorario se conecta a ela.</p>
      <h4>Ganhos</h4>
      <ul class="pc">{_lista(["Conexão oficial: sem risco de bloqueio por integração não oficial.",
                              "Mais estável, sem depender de celular conectado.",
                              "Lembrete com botões e nome da clínica aprovado pela Meta.",
                              "Gasto do mês visível no painel."], "mais")}</ul>
      <h4>O que se abre mão</h4>
      <ul class="pc">{_lista(["Custo por mensagem, pago pela clínica à Meta.",
                              "Ativação leva alguns dias.",
                              "Depois de 24 h sem resposta, só modelos aprovados; campanhas passam por aprovação."], "menos")}</ul>
      <div class="ideal"><b>Combina com:</b> quem não pode arriscar o número, tem muitos clientes ou faz campanhas com frequência.</div>
    </div>
  </div>
  {_rodape(1)}
</section>

<section class="pg">
  <h2 class="tit">Lado a lado, <em>ponto por ponto</em></h2>
  <p class="sub2">O ✓ verde marca a opção que leva vantagem naquele ponto. Não existe uma escolha certa para todo mundo:
  depende do que pesa mais para a sua clínica.</p>
  <table class="cmp">
    <thead><tr><th></th><th>📱 Conexão pelo QR code</th><th class="of">✔ WhatsApp oficial (Meta)</th></tr></thead>
    <tbody>{linhas}</tbody>
  </table>
  <p class="legenda">“Modelo aprovado” é um texto padrão que a Meta revisa antes (por exemplo, o lembrete), preenchido com o nome
  do cliente, a data e o profissional. Dentro de 24 h depois de o cliente escrever, a conversa é livre nas duas opções.</p>

  <div class="transp">
    <span class="ic">💳</span>
    <div>
      <h3>No WhatsApp oficial, o custo é da clínica — e fica à vista</h3>
      <p>A Meta cobra por mensagem enviada pela clínica, no cartão que a própria clínica cadastra na conta da Meta.
      O TemHorario não intermedia esse pagamento. Para não ter surpresa:</p>
      <ul>
        <li>o painel mostra, todo mês, quantas mensagens foram cobradas e o gasto estimado;</li>
        <li>as mensagens que os clientes mandam não são cobradas;</li>
        <li>a Meta concede um volume mensal de respostas de atendimento sem custo;</li>
        <li>combinamos antes quais mensagens automáticas ficam ligadas (lembrete, aniversário, retorno…).</li>
      </ul>
    </div>
  </div>
  {_rodape(2)}
</section>

<section class="pg">
  <h2 class="tit">Como escolher <em>sem complicação</em></h2>
  <p class="sub2">Algumas perguntas ajudam. Se ficar em dúvida, comece pelo que é mais simples hoje — trocar depois é tranquilo.</p>
  <div class="escolha">
    <div class="bx">
      <h3>📱 Conexão pelo QR code faz sentido se…</h3>
      <ul>
        <li>a clínica quer começar ainda esta semana;</li>
        <li>não quer nenhum custo além do TemHorario;</li>
        <li>o número também é usado no celular para outras conversas;</li>
        <li>aceita o risco de, eventualmente, ter que reconectar ou trocar o número.</li>
      </ul>
    </div>
    <div class="bx of">
      <h3>✔ WhatsApp oficial faz sentido se…</h3>
      <ul>
        <li>o número é muito conhecido e perder ele seria um problema sério;</li>
        <li>a clínica tem muitos clientes ou faz campanhas com frequência;</li>
        <li>quer a conta comercial oficial e mais estabilidade;</li>
        <li>está tranquila em pagar as mensagens direto à Meta, acompanhando no painel.</li>
      </ul>
    </div>
  </div>

  <h3 class="sec3">Como fica a ativação</h3>
  <div class="ativa">
    <div><b>📱 QR code</b><ol>
      <li>A clínica informa o número no checklist.</li>
      <li>No dia combinado, o celular lê o QR code (2 minutos).</li>
      <li>Conversa de teste com a Ísis e pronto.</li></ol></div>
    <div class="of"><b>✔ WhatsApp oficial</b><ol>
      <li>A clínica cria ou usa a conta do negócio na Meta e faz a verificação da empresa.</li>
      <li>O número é registrado no WhatsApp oficial e a clínica cadastra o cartão na Meta.</li>
      <li>Conectamos o TemHorario e enviamos os modelos de mensagem para a Meta aprovar.</li>
      <li>Com tudo aprovado, conversa de teste com a Ísis e pronto.</li></ol></div>
  </div>

  <div class="faq">
    <div><b>Dá para trocar depois?</b><p>Sim. A clínica pode começar pelo QR code e passar para o oficial quando quiser
    (ou o contrário). Agenda, clientes e histórico continuam no painel.</p></div>
    <div><b>A equipe trabalha diferente?</b><p>Não. As conversas, a agenda e o CRM são os mesmos. No oficial, a equipe só
    não consegue escrever primeiro para quem está há mais de 24 h sem mandar mensagem — o painel avisa.</p></div>
    <div><b>O que a clínica precisa para o oficial?</b><p>Acesso de administrador ao Gerenciador de Negócios da Meta,
    dados da empresa para a verificação e um cartão cadastrado na Meta. A gente acompanha cada passo.</p></div>
    <div><b>E o risco de bloqueio no QR code?</b><p>Ele existe porque a conexão não é autorizada pelo WhatsApp. Para
    diminuir, as mensagens em massa saem aos poucos e quem pede para parar não recebe mais.</p></div>
  </div>

  <div class="fim"><div><h3>Quer ajuda para escolher?</h3>
    <p>Conte quantos clientes a clínica atende por mês e como usa o WhatsApp hoje. A gente indica o caminho e mostra
    as duas opções funcionando.</p></div>
    <div class="bt">Fale com a gente<small>{contato}</small></div></div>
  <p class="nota">WhatsApp e Meta são marcas da Meta Platforms. O TemHorario não é afiliado à Meta. Os valores cobrados
  no WhatsApp oficial seguem a tabela da Meta, que pode mudar.</p>
  {_rodape(3)}
</section>
</body></html>"""
