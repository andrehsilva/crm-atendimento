from comum import CSS, logo, whatsapp, agenda, kanban


def venda(contato):
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>TemHorario · Material de venda</title>
<style>{CSS}
@page{{size:A4;margin:0}}
.pg{{width:210mm;height:297mm;padding:16mm 16mm 14mm;position:relative;overflow:hidden;page-break-after:always}}
.pg:last-child{{page-break-after:auto}}
.topo{{display:flex;justify-content:space-between;align-items:center;margin-bottom:12mm}}
.topo .tag{{font-size:10px;color:var(--muted);letter-spacing:.12em;text-transform:uppercase}}
h1{{font-size:33px;line-height:1.12;font-weight:800;letter-spacing:-.03em;max-width:118mm}}
h1 em{{font-style:normal;color:var(--marca)}}
.lead{{font-size:13.5px;line-height:1.55;color:#4a474d;margin:5mm 0 8mm;max-width:112mm}}
.heroi{{display:grid;grid-template-columns:1fr 70mm;gap:8mm;align-items:start}}
.dor{{background:var(--bg);border-radius:14px;padding:6mm 7mm}}
.dor h3,.bloco h3{{font-size:13px;font-weight:700;margin-bottom:3mm}}
.dor ul{{list-style:none;display:grid;gap:2.2mm;font-size:11.5px;color:#4a474d}}
.dor li::before{{content:'✕';color:var(--vermelho);font-weight:700;margin-right:7px}}
.passos{{display:grid;grid-template-columns:repeat(3,1fr);gap:5mm;margin-top:9mm}}
.passo{{border:1px solid var(--line);border-radius:14px;padding:5mm}}
.passo .n{{width:26px;height:26px;border-radius:50%;background:var(--marca);color:#fff;display:grid;place-items:center;font-weight:700;font-size:12px;margin-bottom:3mm}}
.passo b{{display:block;font-size:12.5px;margin-bottom:1.5mm}}.passo p{{font-size:10.5px;color:var(--muted);line-height:1.5}}
.rodape{{position:absolute;left:16mm;right:16mm;bottom:10mm;display:flex;justify-content:space-between;font-size:9px;color:var(--muted)}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:4mm 7mm}}
.rec{{display:flex;gap:3.5mm}}
.rec .ic{{flex:none;width:30px;height:30px;border-radius:9px;background:var(--marca-soft);color:var(--marca);display:grid;place-items:center;font-size:15px}}
.rec b{{font-size:12px;display:block;margin-bottom:1mm}}.rec p{{font-size:10.3px;color:#57535a;line-height:1.5}}
h2{{font-size:21px;font-weight:800;letter-spacing:-.02em;margin-bottom:5mm}}
h2 em{{font-style:normal;color:var(--marca)}}
.seg{{display:flex;flex-wrap:wrap;gap:2mm;margin-top:3mm}}
.seg span{{border:1px solid var(--line);border-radius:20px;padding:1.5mm 4mm;font-size:10.5px}}
.cta{{background:var(--text);color:#fff;border-radius:18px;padding:8mm 9mm;display:grid;grid-template-columns:1fr auto;gap:6mm;align-items:center;margin-top:8mm}}
.cta h3{{font-size:19px;font-weight:700;margin-bottom:2mm}}.cta p{{font-size:11px;color:#cfcbd2;line-height:1.5}}
.cta .bt{{background:var(--marca);border-radius:12px;padding:4mm 6mm;font-weight:600;font-size:12px;text-align:center;line-height:1.4}}
.cta .bt small{{display:block;font-weight:400;font-size:10px;opacity:.9}}
.telas{{display:grid;grid-template-columns:1fr 1fr;gap:6mm;margin:6mm 0 3mm}}
.telas .janela{{zoom:.8}}
</style></head><body>

<section class="pg">
  <div class="topo">{logo(40)}<span class="tag">Para clínicas e consultórios</span></div>
  <div class="heroi">
    <div>
      <h1>Atendimento pelo WhatsApp e <em>agenda da clínica</em> em um só lugar.</h1>
      <p class="lead">A <b>Ísis</b>, assistente virtual do TemHorario, conversa com seus clientes no WhatsApp e ajuda a marcar,
      remarcar e cancelar seguindo as regras que a sua clínica cadastrou. Sua equipe acompanha tudo pelo painel e
      assume a conversa quando precisar de uma pessoa.</p>
      <div class="dor"><h3>Parece com a rotina da sua recepção?</h3><ul>
        <li>Mensagens chegando o dia todo, muitas fora do horário.</li>
        <li>Agenda no caderno ou planilha, e o WhatsApp em outro lugar.</li>
        <li>Tempo gasto confirmando consulta, uma por uma.</li>
        <li>Paciente que some depois do primeiro “oi”.</li>
        <li>Ninguém sabe ao certo quem já foi atendido e quem está esperando.</li>
      </ul></div>
    </div>
    <div>{whatsapp()}<div class="ilustra">Ilustração com dados fictícios</div></div>
  </div>
  <div class="passos">
    <div class="passo"><div class="n">1</div><b>A clínica configura</b><p>Horários, profissionais, procedimentos, convênios e o jeito de falar com os clientes.</p></div>
    <div class="passo"><div class="n">2</div><b>A Ísis atende no WhatsApp</b><p>Tira dúvidas, oferece horários livres e marca, remarca ou cancela — sempre dentro das regras.</p></div>
    <div class="passo"><div class="n">3</div><b>A equipe acompanha</b><p>Conversas, agenda e contatos no painel, no computador ou no celular. Assume quando quiser.</p></div>
  </div>
  <div class="rodape"><span>TemHorario · atendimento e agenda para clínicas</span><span>1/2</span></div>
</section>

<section class="pg">
  <h2>O que o TemHorario <em>faz pela sua clínica</em></h2>
  <div class="grid2">
    <div class="rec"><div class="ic">💬</div><div><b>Atendimento no WhatsApp</b><p>Entende mensagens picadas e áudios, responde sobre a clínica e conduz a marcação.</p></div></div>
    <div class="rec"><div class="ic">📅</div><div><b>Agenda que não deixa conflitar</b><p>Horário de funcionamento, pausas e agenda de cada profissional são conferidos pelo sistema, não pela memória da IA.</p></div></div>
    <div class="rec"><div class="ic">🔔</div><div><b>Confirmação e lembrete</b><p>Lembrete na véspera: o cliente responde 1 para confirmar, 2 para remarcar ou 3 para cancelar, e a agenda já se atualiza.</p></div></div>
    <div class="rec"><div class="ic">🙋</div><div><b>Equipe no controle</b><p>A recepção assume qualquer conversa, marca e cancela pelo painel. A Ísis pede ajuda quando precisa.</p></div></div>
    <div class="rec"><div class="ic">📊</div><div><b>CRM e clientes</b><p>Cada contato no seu momento: novo, agendado, confirmado, cancelado. Observações e histórico de cada cliente.</p></div></div>
    <div class="rec"><div class="ic">🔁</div><div><b>Tratamentos e retornos</b><p>Sessões em série, horário fixo semanal, pós-consulta e convite de retorno na data certa.</p></div></div>
    <div class="rec"><div class="ic">🎂</div><div><b>Aniversário e campanhas</b><p>Mensagens agendadas (Natal, férias, avisos) enviadas com intervalo, sem disparar tudo de uma vez.</p></div></div>
    <div class="rec"><div class="ic">📱</div><div><b>No celular também</b><p>Agenda do dia, CRM, mensagens e clientes num painel simples para o celular.</p></div></div>
  </div>
  <div class="telas">
    <div>{agenda(lado=False)}<div class="ilustra">Agenda da semana — ilustração com dados fictícios</div></div>
    <div>{kanban(lado=False)}<div class="ilustra">CRM — ilustração com dados fictícios</div></div>
  </div>
  <h3 style="font-size:13px;margin-top:4mm">Feito para quem trabalha com horário marcado</h3>
  <div class="seg"><span>Odontologia</span><span>Medicina</span><span>Fisioterapia</span><span>Psicologia</span><span>Psicanálise</span><span>Psiquiatria</span><span>Estética</span><span>Outros consultórios</span></div>
  <div class="cta"><div><h3>Veja a Ísis atendendo na prática.</h3>
    <p>Agende uma demonstração de 20 minutos: mostramos o WhatsApp, a agenda e o painel com os horários e procedimentos da sua clínica.</p></div>
    <div class="bt">Fale com a gente<small>{contato}</small></div></div>
  <div class="rodape"><span>Conexão com o WhatsApp por integração não oficial (WAHA). Imagens ilustrativas com dados fictícios.</span><span>2/2</span></div>
</section>
</body></html>"""
