from comum import CSS, logo, whatsapp, lembrete, dashboard, agenda, kanban, celular_painel


def slide(miolo, n, escuro=False, classe=""):
    rod = f'<div class="rod"><span>{logo(18, cor_texto="currentColor")}</span><span>{n}</span></div>' if n else ""
    return f'<section class="sl {"escuro" if escuro else ""} {classe}">{miolo}{rod}</section>'


def apresentacao(contato):
    s = []
    s.append(slide(f"""<div style="display:grid;grid-template-columns:1.15fr 1fr;height:100%;align-items:center;gap:50px">
<div>{logo(54, cor_texto="#fff")}<h1 style="margin-top:46px">Atendimento pelo WhatsApp e agenda da clínica <em>em um só lugar.</em></h1>
<p class="lead" style="color:#cfcbd2">Conheça a Ísis, a assistente virtual do TemHorario.</p></div>
<div style="display:flex;justify-content:center">{whatsapp()}</div></div>""", "", escuro=True))

    s.append(slide("""<span class="kick">O dia a dia de hoje</span><h2>A agenda da clínica começa no WhatsApp.<br>E é aí que a recepção se perde.</h2>
<div class="tres">
<div class="bx"><div class="big">💬</div><b>Mensagens o dia todo</b><p>“Oi”, “tem horário?”, “quanto custa?” — muitas chegam com a recepção ocupada ou fora do expediente.</p></div>
<div class="bx"><div class="big">🗂️</div><b>Informação espalhada</b><p>WhatsApp num lugar, agenda em outro, planilha em outro. Fica difícil saber quem está esperando resposta.</p></div>
<div class="bx"><div class="big">⏱️</div><b>Tempo em tarefas repetidas</b><p>Confirmar consulta por consulta, remarcar, lembrar do retorno. A equipe faz tudo à mão.</p></div>
</div>""", 2, classe="centro"))

    s.append(slide(f"""<div style="display:grid;grid-template-columns:1fr 330px;gap:50px;align-items:center;height:100%">
<div><span class="kick">A solução</span><h2>A Ísis atende no WhatsApp.<br><em>Sua equipe acompanha pelo painel.</em></h2>
<ul class="lista">
<li><b>Responde</b> sobre a clínica com as informações que vocês cadastraram.</li>
<li><b>Oferece horários livres</b> e marca, remarca ou cancela.</li>
<li><b>Entende</b> mensagens picadas e áudios.</li>
<li><b>Passa para a recepção</b> quando o caso pede uma pessoa.</li></ul></div>
<div style="display:flex;justify-content:center">{whatsapp()}</div></div>""", 3))

    s.append(slide("""<span class="kick">Como funciona</span><h2>Três passos, do cadastro ao atendimento.</h2>
<div class="tres passos">
<div class="bx"><div class="n">1</div><b>A clínica configura</b><p>Horários, pausas, profissionais e a agenda de cada um, procedimentos, convênios e o jeito de falar com os clientes.</p></div>
<div class="bx"><div class="n">2</div><b>A Ísis conversa</b><p>No WhatsApp da clínica, ela atende, oferece horários e cuida das marcações seguindo essas regras.</p></div>
<div class="bx"><div class="n">3</div><b>A equipe acompanha</b><p>Conversas, agenda e contatos aparecem em tempo real no painel. A recepção assume quando quiser.</p></div>
</div>
<p class="nota">A segurança da agenda fica no sistema: conflito de horário, expediente e agenda do profissional são conferidos pelo código — a Ísis só pede, o sistema decide.</p>""", 4, classe="centro"))

    s.append(slide(f"""<div class="duas"><div><span class="kick">Agenda</span><h2>Uma agenda que <em>não deixa marcar errado.</em></h2>
<ul class="lista"><li>Visão por dia ou semana, por profissional.</li><li>Arraste uma sessão para remarcar.</li>
<li>Séries de sessões e horário fixo semanal para tratamentos.</li><li>Status claros: aguardando, confirmada, compareceu, faltou.</li></ul></div>
<div>{agenda()}<div class="ilustra">Ilustração com dados fictícios</div></div></div>""", 5))

    s.append(slide(f"""<div class="duas" style="grid-template-columns:1fr 330px"><div><span class="kick">Confirmação e lembrete</span><h2>O cliente confirma <em>respondendo um número.</em></h2>
<ul class="lista"><li>Aviso na hora ao marcar, remarcar ou cancelar.</li><li>Lembrete na véspera: 1 Confirmar · 2 Remarcar · 3 Cancelar.</li>
<li>A resposta já atualiza a agenda e o CRM.</li><li>Resumo do dia no WhatsApp do profissional, de manhã.</li></ul></div>
<div style="display:flex;justify-content:center">{lembrete()}</div></div>""", 6))

    s.append(slide(f"""<div class="duas"><div><span class="kick">CRM</span><h2>Cada contato no <em>seu momento.</em></h2>
<ul class="lista"><li>Novo contato, agendado, confirmado, cancelado.</li><li>Atendimento automático ou manual em cada conversa.</li>
<li>Alerta de contato parado há mais de 24 horas.</li><li>Observações e histórico de cada cliente.</li></ul></div>
<div>{kanban()}<div class="ilustra">Ilustração com dados fictícios</div></div></div>""", 7))

    s.append(slide("""<span class="kick">Relacionamento</span><h2>Depois da consulta, <em>a clínica continua presente.</em></h2>
<div class="quatro">
<div class="bx"><div class="big">🩺</div><b>Pós-consulta</b><p>Mensagem de cuidado depois do atendimento.</p></div>
<div class="bx"><div class="big">🔁</div><b>Retorno</b><p>Convite para voltar na data combinada.</p></div>
<div class="bx"><div class="big">🎂</div><b>Aniversário</b><p>Mensagem automática no dia, com o nome do cliente.</p></div>
<div class="bx"><div class="big">📣</div><b>Campanhas</b><p>Natal, férias, avisos — com envio espaçado.</p></div>
</div>""", 8, classe="centro"))

    s.append(slide(f"""<div class="duas" style="grid-template-columns:1fr 300px"><div><span class="kick">No bolso da equipe</span><h2>O dia da clínica <em>no celular.</em></h2>
<ul class="lista"><li>Agenda do dia, com setas para os próximos dias.</li><li>CRM simples: nome e status de quem falou hoje.</li>
<li>Mensagens e clientes, com comentário rápido.</li><li>Configurações e relatórios ficam no computador.</li></ul></div>
<div style="display:flex;justify-content:center">{celular_painel()}</div></div>""", 9))

    s.append(slide("""<span class="kick">Gestão</span><h2>Informação para decidir, <em>sem planilha manual.</em></h2>
<div class="tres">
<div class="bx"><div class="big">📥</div><b>Relatórios em Excel</b><p>Atendimentos, produção por profissional, faltas e cancelamentos, aniversariantes e pacientes para chamar de volta.</p></div>
<div class="bx"><div class="big">❓</div><b>Pergunte à assistente</b><p>A equipe pergunta “quantos pacientes vieram este mês?” e recebe a resposta — só leitura, só dados da clínica.</p></div>
<div class="bx"><div class="big">🎨</div><b>Do jeito da clínica</b><p>Logo, cores, termos do segmento (consulta, sessão, atendimento) e o tom de voz da Ísis.</p></div>
</div>""", 10, classe="centro"))

    s.append(slide("""<span class="kick">Para quem</span><h2>Feito para quem trabalha <em>com horário marcado.</em></h2>
<div class="chips"><span>Odontologia</span><span>Medicina</span><span>Fisioterapia</span><span>Psicologia</span><span>Psicanálise</span><span>Psiquiatria</span><span>Estética</span><span>Outros consultórios</span></div>
<p class="nota" style="margin-top:40px">Cada segmento já vem com termos, procedimentos iniciais e orientações próprios. Convênios, vários profissionais e horários diferentes por profissional são suportados.</p>""", 11, classe="centro"))

    s.append(slide(f"""<div style="display:grid;grid-template-columns:1.2fr 1fr;gap:60px;align-items:center;height:100%">
<div><span class="kick" style="color:#f2a7bd">Próximo passo</span><h1 style="font-size:46px">Vamos ver a Ísis atendendo <em>a sua clínica?</em></h1>
<p class="lead" style="color:#cfcbd2">Uma demonstração de 20 minutos com os seus horários e procedimentos.</p></div>
<div class="contato">{logo(40, cor_texto="#fff")}<div class="cv">Fale com a gente</div><div class="cn">{contato}</div></div></div>""", "", escuro=True))

    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>TemHorario · Apresentação</title>
<style>{CSS}
@page{{size:1280px 720px;margin:0}}
.sl{{width:1280px;height:720px;padding:64px 80px 70px;position:relative;overflow:hidden;page-break-after:always;background:#fff}}
.sl:last-child{{page-break-after:auto}}
.sl.escuro{{background:var(--text);color:#fff}}
.sl h1{{font-size:52px;line-height:1.08;font-weight:800;letter-spacing:-.03em}}
.sl h1 em,.sl h2 em{{font-style:normal;color:var(--marca)}}.sl.escuro h1 em{{color:#f2a7bd}}
.sl h2{{font-size:38px;line-height:1.15;font-weight:800;letter-spacing:-.025em;margin-bottom:36px}}
.kick{{display:block;font-size:14px;font-weight:600;color:var(--marca);letter-spacing:.12em;text-transform:uppercase;margin-bottom:14px}}
.lead{{font-size:22px;line-height:1.5;margin-top:22px}}
.tres{{display:grid;grid-template-columns:repeat(3,1fr);gap:26px}}.quatro{{display:grid;grid-template-columns:repeat(4,1fr);gap:22px}}
.bx{{background:var(--bg);border-radius:22px;padding:30px}}
.bx b{{display:block;font-size:20px;margin:12px 0 8px}}.bx p{{font-size:15.5px;line-height:1.55;color:#57535a}}
.bx .big{{font-size:34px}}
.passos .n{{width:46px;height:46px;border-radius:50%;background:var(--marca);color:#fff;display:grid;place-items:center;font-size:20px;font-weight:700}}
.lista{{list-style:none;display:grid;gap:16px;font-size:19px;line-height:1.45;color:#3d3a40}}
.lista li{{padding-left:30px;position:relative}}.lista li::before{{content:'';position:absolute;left:0;top:9px;width:14px;height:14px;border-radius:50%;background:var(--marca-soft);box-shadow:inset 0 0 0 4px var(--marca)}}
.duas{{display:grid;grid-template-columns:420px 1fr;gap:50px;align-items:center;height:100%}}
.duas h2{{font-size:34px}}
.nota{{font-size:16px;color:var(--muted);margin-top:30px;line-height:1.5;max-width:900px}}
.chips{{display:flex;flex-wrap:wrap;gap:14px}}.chips span{{border:1.5px solid var(--line);border-radius:30px;padding:12px 24px;font-size:20px}}
.rod{{position:absolute;left:80px;right:80px;bottom:28px;display:flex;justify-content:space-between;align-items:center;font-size:13px;color:var(--muted)}}
.escuro .rod{{color:#8d8991}}
.contato{{background:#2b2b30;border-radius:26px;padding:44px}}
.contato .cv{{font-size:16px;color:#cfcbd2;margin-top:34px}}.contato .cn{{font-size:28px;font-weight:700;margin-top:6px}}
.ilustra{{font-size:12px}}
.sl.centro{{display:flex;flex-direction:column;justify-content:center}}
.sl.centro .bx{{padding:38px 32px}}
.contato .cn{{white-space:nowrap;font-size:26px}}
</style></head><body>{"".join(s)}</body></html>"""
