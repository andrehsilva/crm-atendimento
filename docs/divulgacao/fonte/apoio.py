from comum import CSS, logo


def apoio(contato):
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>TemHorario · Material de apoio à venda</title>
<style>{CSS}
@page{{size:A4;margin:16mm 16mm 16mm}}
body{{font-size:10.6px;line-height:1.55;color:#2c2a2f}}
.capa{{height:262mm;display:flex;flex-direction:column;justify-content:space-between;page-break-after:always}}
.capa h1{{font-size:38px;line-height:1.1;font-weight:800;letter-spacing:-.03em;margin-top:40mm}}
.capa h1 em{{font-style:normal;color:var(--marca)}}
.capa p{{font-size:13px;color:var(--muted);max-width:120mm;margin-top:6mm}}
.sumario{{columns:2;font-size:11.5px;line-height:2}}
.sumario b{{color:var(--marca);display:inline-block;width:8mm}}
h2{{font-size:19px;font-weight:800;letter-spacing:-.02em;margin:0 0 4mm;padding-top:2mm;color:var(--text)}}
h2 span{{color:var(--marca);margin-right:6px}}
h3{{font-size:12.5px;font-weight:700;margin:4mm 0 1.5mm;color:var(--text)}}
.sec{{page-break-before:always}}
p{{margin-bottom:2.5mm}}
ul,ol{{padding-left:5mm;margin-bottom:3mm}}li{{margin-bottom:1.2mm}}
.caixa{{background:var(--bg);border-radius:12px;padding:4mm 5mm;margin:3mm 0;break-inside:avoid}}
.fala{{border-left:3px solid var(--marca);background:#fbf5f7;border-radius:0 10px 10px 0;padding:3mm 4.5mm;margin:2.5mm 0;font-size:11px;break-inside:avoid}}
.fala b.q{{display:block;color:var(--marca);font-size:10px;letter-spacing:.06em;text-transform:uppercase;margin-bottom:1mm}}
table{{width:100%;border-collapse:collapse;margin:2mm 0 4mm;font-size:10.2px}}
th{{text-align:left;font-weight:600;background:var(--bg);padding:2mm 3mm}}td{{padding:2mm 3mm;border-bottom:1px solid var(--line);vertical-align:top}}
tr{{break-inside:avoid}}
.kw{{display:flex;flex-wrap:wrap;gap:1.3mm;margin:1mm 0 2mm}}
.kw span{{background:var(--marca-soft);color:var(--marca-escura);border-radius:6px;padding:.4mm 2.2mm;font-size:9.6px}}
.kw.neg span{{background:var(--vermelho-soft);color:var(--vermelho)}}
.kw.hash span{{background:var(--azul-soft);color:var(--azul)}}
.nao li::marker{{content:'✕  ';color:var(--vermelho)}}
.sim li::marker{{content:'✓  ';color:var(--verde)}}
.chk li{{list-style:none;margin-left:-5mm}}.chk li::before{{content:'☐ ';font-size:12px;color:var(--marca)}}
.alerta{{background:var(--ambar-soft);color:#6d4b08;border-radius:10px;padding:3mm 4mm;margin:3mm 0;font-size:10.3px}}
</style></head><body>

<section class="capa">
<div>{logo(42)}
<h1>Material de apoio<br><em>à venda</em></h1>
<p>Roteiros, perguntas, respostas para objeções, palavras-chave e textos prontos para apresentar e vender o TemHorario
para clínicas e consultórios. Uso interno.</p></div>
<div class="sumario">
<div><b>1</b>Em uma frase</div><div><b>2</b>Pitch de 30 s e de 2 min</div><div><b>3</b>Cliente ideal</div>
<div><b>4</b>Perguntas de descoberta</div><div><b>5</b>Roteiro da demonstração</div><div><b>6</b>Objeções e respostas</div>
<div><b>7</b>Perguntas frequentes</div><div><b>8</b>O que não prometer</div><div><b>9</b>Palavras-chave</div>
<div><b>10</b>Textos prontos</div><div><b>11</b>Checklist de implantação</div><div><b>12</b>Acompanhamento das vendas</div>
</div>
<div style="font-size:9.5px;color:var(--muted)">Contato comercial nas peças: <b>{contato}</b></div>
</section>

<section>
<h2><span>1</span>Em uma frase</h2>
<div class="fala"><b class="q">Frase principal</b>O TemHorario junta o atendimento pelo WhatsApp e a agenda da clínica num lugar só: a Ísis, nossa assistente virtual, conversa com os clientes e cuida das marcações, e a equipe acompanha tudo pelo painel.</div>
<p><b>Versões curtas:</b> “WhatsApp, agenda e atendimento da clínica, juntos.” · “A Ísis atende pelo WhatsApp. Sua equipe acompanha pelo painel.” · “Mais organização para a agenda. Mais clareza para a equipe.”</p>
<p><b>Nomes:</b> TemHorario é a plataforma; Ísis é a assistente. Na primeira menção: “Ísis, a assistente virtual do TemHorario”.</p>

<h2 style="margin-top:7mm"><span>2</span>Pitch de 30 segundos e de 2 minutos</h2>
<div class="fala"><b class="q">30 segundos</b>Hoje quase toda marcação de clínica começa no WhatsApp, e a recepção passa o dia respondendo “tem horário?”, confirmando consulta e remarcando. O TemHorario coloca a Ísis, uma assistente virtual, no WhatsApp da clínica: ela responde, oferece os horários livres e marca seguindo as regras de vocês. A equipe vê tudo num painel e assume a conversa quando quiser. Posso te mostrar em 20 minutos com a agenda da sua clínica?</div>
<div class="fala"><b class="q">2 minutos</b>
<p><b>Problema.</b> A agenda da clínica começa no WhatsApp, mas o WhatsApp não é agenda. As mensagens chegam o dia todo, a informação fica espalhada e a equipe gasta tempo em tarefas repetidas: confirmar, lembrar, remarcar.</p>
<p><b>Como resolvemos.</b> A clínica cadastra horários, profissionais e procedimentos. A Ísis conversa no WhatsApp, entende mensagens picadas e áudio, oferece horários e marca. Quem garante que não haja conflito é o sistema, não a IA: ela só pede, o sistema decide.</p>
<p><b>O que a equipe ganha.</b> Um painel com agenda, CRM e conversas em tempo real; lembrete na véspera com “1 Confirmar · 2 Remarcar · 3 Cancelar”; pós-consulta, retorno, aniversário e campanhas; relatórios em Excel. E a recepção assume qualquer conversa a qualquer momento.</p>
<p><b>Convite.</b> Que tal uma demonstração rápida com os seus horários e procedimentos?</p></div>

<h2 style="margin-top:7mm"><span>3</span>Cliente ideal</h2>
<table><tr><th style="width:38%">Perfil</th><th>Sinais de que vale a conversa</th></tr>
<tr><td>Clínicas e consultórios com agenda marcada: odontologia, medicina, fisioterapia, psicologia, psicanálise, psiquiatria, estética.</td><td>Recebe a maior parte das marcações pelo WhatsApp.</td></tr>
<tr><td>De 1 a vários profissionais, com recepção pequena ou o próprio profissional atendendo.</td><td>Reclama de tempo gasto confirmando consultas ou de mensagens sem resposta.</td></tr>
<tr><td>Quem decide: dono(a), gestor(a) ou responsável pela recepção.</td><td>Usa agenda de papel, planilha ou um sistema que não conversa com o WhatsApp.</td></tr>
<tr><td>Atendimento particular e/ou convênio.</td><td>Tem tratamentos com várias sessões, retornos ou pacientes recorrentes.</td></tr></table>
<p>Fale com quem administra a clínica, não com o paciente. A dor mais forte é operacional: tempo e organização da equipe.</p>
</section>

<section class="sec">
<h2><span>4</span>Perguntas de descoberta</h2>
<p>Use antes de mostrar o produto. Anote as respostas: elas guiam a demonstração.</p>
<h3>Como é hoje</h3><ol>
<li>Por onde chegam os pedidos de marcação? Quanto é pelo WhatsApp?</li>
<li>Quem responde o WhatsApp? Essa pessoa faz outras coisas ao mesmo tempo?</li>
<li>Onde fica a agenda hoje (papel, planilha, sistema)? Quantos profissionais?</li>
<li>Como vocês confirmam as consultas? Quanto tempo isso leva por dia?</li></ol>
<h3>Onde dói</h3><ol start="5">
<li>O que acontece com as mensagens que chegam à noite ou no fim de semana?</li>
<li>Vocês têm muitos clientes que faltam ou cancelam em cima da hora?</li>
<li>Já perderam um paciente porque demoraram para responder?</li>
<li>Como vocês lembram o paciente de voltar (retorno, revisão, manutenção)?</li></ol>
<h3>Decisão</h3><ol start="9">
<li>Se a marcação e a confirmação andassem sozinhas, o que a equipe faria com esse tempo?</li>
<li>Quem mais participa da decisão? Existe uma data em que vocês gostariam de começar?</li></ol>

<h2 style="margin-top:7mm"><span>5</span>Roteiro da demonstração (20 minutos)</h2>
<table><tr><th style="width:16%">Tempo</th><th style="width:30%">O que mostrar</th><th>O que dizer</th></tr>
<tr><td>0–3 min</td><td>Retomar as dores</td><td>“Você comentou que … Vou mostrar como fica isso no TemHorario.”</td></tr>
<tr><td>3–8 min</td><td>Conversa no WhatsApp com a Ísis</td><td>Pedir horário, escolher, receber a confirmação. Mandar mensagens picadas e um áudio.</td></tr>
<tr><td>8–12 min</td><td>Agenda e CRM no painel</td><td>A marcação aparece na hora. Mostrar o card andar no CRM e a recepção assumindo a conversa.</td></tr>
<tr><td>12–15 min</td><td>Lembrete e confirmação</td><td>Mostrar o lembrete “1 · 2 · 3” e a agenda mudando para “Confirmada”.</td></tr>
<tr><td>15–17 min</td><td>Celular e relatórios</td><td>Agenda do dia no celular; relatórios em Excel; pergunte à assistente.</td></tr>
<tr><td>17–20 min</td><td>Próximo passo</td><td>Combinar implantação: o que a clínica precisa enviar (seção 11) e a data de início.</td></tr></table>
<div class="alerta"><b>Antes da demo:</b> use a clínica de demonstração com nomes e telefones fictícios; confira que WhatsApp, lembretes e recursos que vai mostrar estão ligados; nunca mostre dados reais de pacientes.</div>
</section>

<section class="sec">
<h2><span>6</span>Objeções e respostas</h2>
<table><tr><th style="width:32%">O cliente diz</th><th>Como responder</th></tr>
<tr><td>“Robô atendendo vai parecer frio.”</td><td>A Ísis fala com o tom que a clínica escolher e chama o cliente pelo nome. E a recepção vê tudo e assume a conversa quando quiser — ela não substitui a equipe, tira dela o repetitivo.</td></tr>
<tr><td>“E se a IA marcar errado?”</td><td>Quem decide a agenda é o sistema: expediente, pausas, agenda do profissional e conflitos são conferidos pelo código. A Ísis só pede; se não couber, o sistema recusa e ela oferece outro horário.</td></tr>
<tr><td>“Meus pacientes são mais velhos, não vão gostar.”</td><td>A conversa é no WhatsApp que eles já usam, em linguagem simples, e aceita áudio. Quem preferir falar com uma pessoa é passado para a recepção.</td></tr>
<tr><td>“Já tenho um sistema de agenda.”</td><td>O TemHorario resolve a parte que costuma ficar de fora: a conversa no WhatsApp virando marcação, confirmação e lembrete, tudo no mesmo lugar.</td></tr>
<tr><td>“Não tenho tempo para implantar.”</td><td>A implantação começa com uma lista curta (seção 11): horários, profissionais, procedimentos e o número do WhatsApp. A gente ajuda a cadastrar.</td></tr>
<tr><td>“Vou perder o controle das conversas.”</td><td>Todas as conversas ficam no painel, em tempo real. Dá para pausar a Ísis no WhatsApp e atender só manualmente quando quiser.</td></tr>
<tr><td>“Quanto custa?”</td><td>Responda com a tabela vigente. Se ainda não houver preço definido, combine a demonstração primeiro: “Depende do tamanho da clínica; na demonstração eu já te passo a proposta.”</td></tr>
<tr><td>“E a privacidade dos pacientes?”</td><td>Cada clínica só vê os próprios dados; downloads de relatórios ficam registrados e os relatórios não trazem conversas nem observações clínicas. Não prometa certificações que não foram verificadas.</td></tr>
<tr><td>“O WhatsApp pode bloquear meu número?”</td><td>Seja transparente: a conexão é por integração não oficial (WAHA). O sistema espaça os envios em massa e respeita limites por minuto e por dia para reduzir o risco, mas não existe garantia.</td></tr></table>

<h2 style="margin-top:6mm"><span>7</span>Perguntas frequentes</h2>
<p><b>Precisa de outro número?</b> Não: a clínica usa o próprio número. Na implantação, ele é conectado lendo um QR code, como no WhatsApp Web.</p>
<p><b>A Ísis entende áudio?</b> Sim: o áudio é transcrito e ela responde normalmente. Para imagens, pede com educação que a pessoa escreva.</p>
<p><b>Funciona com convênio?</b> Sim. A clínica cadastra os convênios e a Ísis pergunta “convênio ou particular?” no primeiro contato.</p>
<p><b>Serve para tratamentos longos?</b> Sim: séries de sessões, horário fixo semanal e lembrete por tratamento.</p>
<p><b>Dá para usar no celular?</b> Sim, para o dia a dia: agenda do dia, CRM, mensagens e clientes. Configurações e relatórios ficam no computador.</p>
<p><b>Quem controla o gasto com a IA?</b> Cada clínica tem um teto de uso; ao chegar nele, a Ísis pausa e a equipe é avisada.</p>
</section>

<section class="sec">
<h2><span>8</span>O que não prometer</h2>
<ul class="nao">
<li>Preço, plano gratuito ou período de teste que ainda não foram definidos.</li>
<li>WhatsApp oficial ou “API oficial da Meta” — a integração é não oficial (WAHA), sem SLA.</li>
<li>Atendimento 100% automático, disponibilidade garantida 24 horas ou ausência de erros.</li>
<li>Aumento de faturamento, redução garantida de faltas ou porcentagens de economia de tempo.</li>
<li>Site próprio da clínica em domínio próprio como recurso já disponível.</li>
<li>Certificações de segurança ou conformidade legal que não foram verificadas formalmente.</li></ul>
<p><b>Pode dizer:</b></p>
<ul class="sim"><li>Ajuda a organizar o atendimento e a agenda.</li><li>As regras da agenda são conferidas pelo sistema.</li>
<li>A equipe acompanha e assume quando quiser.</li><li>Lembrete com confirmação por número reduz o trabalho de confirmar uma a uma.</li></ul>

<h2 style="margin-top:7mm"><span>9</span>Palavras-chave</h2>
<p>Para anúncios no Google, conteúdo do site/blog, perfil no Google e redes sociais. Agrupe os anúncios por intenção e mande cada grupo para uma página que fale exatamente daquilo.</p>
<h3>Intenção de compra (anúncios)</h3>
<div class="kw"><span>secretária virtual para clínica</span><span>atendente virtual whatsapp clínica</span><span>assistente virtual para consultório</span><span>agendamento pelo whatsapp para clínica</span><span>sistema de agendamento para clínica</span><span>agenda online para consultório</span><span>chatbot whatsapp clínica</span><span>software para clínica com whatsapp</span><span>crm para clínica</span><span>automação de whatsapp para clínica</span></div>
<h3>Confirmação e lembrete</h3>
<div class="kw"><span>confirmação de consulta pelo whatsapp</span><span>lembrete de consulta whatsapp</span><span>mensagem automática de confirmação de consulta</span><span>como confirmar consultas automaticamente</span><span>lembrete automático para pacientes</span></div>
<h3>Por segmento</h3>
<div class="kw"><span>agenda para dentista</span><span>sistema para consultório odontológico</span><span>secretária virtual dentista</span><span>agenda para psicólogo</span><span>agendamento online psicologia</span><span>sistema para clínica de fisioterapia</span><span>agenda para clínica de estética</span><span>agenda médica online</span><span>agendamento para psiquiatra</span><span>agenda para psicanalista</span></div>
<h3>Conteúdo e dúvidas (blog, posts, vídeos)</h3>
<div class="kw"><span>como organizar a agenda da clínica</span><span>como diminuir faltas no consultório</span><span>como responder pacientes no whatsapp</span><span>whatsapp para clínicas: boas práticas</span><span>mensagem de aniversário para pacientes</span><span>como chamar paciente de volta</span><span>pós-consulta pelo whatsapp</span><span>recepção de clínica sobrecarregada</span></div>
<h3>Palavras negativas (para não pagar clique errado)</h3>
<div class="kw neg"><span>grátis</span><span>gratuito</span><span>download</span><span>curso</span><span>vaga</span><span>emprego</span><span>secretária presencial</span><span>modelo de planilha</span><span>pdf</span><span>whatsapp business oficial</span></div>
<h3>Hashtags</h3>
<div class="kw hash"><span>#gestaodeclinicas</span><span>#marketingodontologico</span><span>#gestaoodontologica</span><span>#consultorio</span><span>#clinicadeestetica</span><span>#psicologia</span><span>#fisioterapia</span><span>#secretariavirtual</span><span>#atendimentoaopaciente</span><span>#agendaonline</span><span>#temhorario</span></div>
</section>

<section class="sec">
<h2><span>10</span>Textos prontos</h2>
<h3>WhatsApp — primeira abordagem</h3>
<div class="fala">Olá, [nome]! Tudo bem? Sou [seu nome], do TemHorario. A gente ajuda clínicas a organizar o atendimento pelo WhatsApp: a Ísis, nossa assistente virtual, responde os pacientes e cuida das marcações seguindo as regras da clínica, e a equipe acompanha tudo num painel. Posso te mostrar em 20 minutos como ficaria na [nome da clínica]?</div>
<h3>WhatsApp — retomada (3 a 5 dias depois)</h3>
<div class="fala">Oi, [nome]! Passando para saber se faz sentido aquela demonstração do TemHorario. Consigo mostrar com os horários e procedimentos de vocês — [dia] ou [dia] fica bom?</div>
<h3>WhatsApp — depois da demonstração</h3>
<div class="fala">[Nome], obrigado pelo tempo hoje! Como combinamos, para começar preciso de: horários de funcionamento, profissionais e seus horários, procedimentos com duração e o número do WhatsApp da clínica. Se quiser, mando a lista completa e já marcamos a implantação.</div>
<h3>Post — apresentação</h3>
<div class="fala"><b>Arte:</b> Sua agenda também começa no WhatsApp? Conheça o TemHorario.<br>
<b>Legenda:</b> As mensagens chegam, a equipe consulta horários, confirma marcações e ainda precisa acompanhar cada conversa. Com o TemHorario, a Ísis atende pelo WhatsApp e ajuda a marcar, remarcar e cancelar conforme as regras da clínica. A equipe acompanha tudo pelo painel e assume quando precisa. Fale com a gente! #gestaodeclinicas #secretariavirtual</div>
<h3>Post — rotina da equipe</h3>
<div class="fala"><b>Arte:</b> Conversas no WhatsApp. Agenda organizada. Equipe no controle.<br><b>Legenda:</b> Cada clínica configura horários, profissionais e serviços; a Ísis usa essas regras para atender, e a recepção continua participando quando necessário.</div>
<h3>Bio do Instagram</h3>
<div class="fala">TemHorario 🕘 Atendimento pelo WhatsApp + agenda da clínica em um só lugar. Conheça a Ísis, nossa assistente virtual. 👇 Peça sua demonstração</div>
<h3>Vídeo curto (20 a 30 s)</h3>
<ol><li><b>Notificações e agenda aberta:</b> “O atendimento da sua clínica começa no WhatsApp?”</li>
<li><b>Conversa com a Ísis:</b> “A Ísis conversa com seus clientes e ajuda a marcar, remarcar e cancelar.”</li>
<li><b>Painel:</b> “E sua equipe acompanha conversas e agenda em um só painel.”</li>
<li><b>Marca:</b> “TemHorario. Atendimento e agenda mais organizados. Fale com a gente.”</li></ol>
</section>

<section class="sec">
<h2><span>11</span>Checklist de implantação</h2>
<p>O que pedir à clínica para começar:</p>
<ul class="chk">
<li>Nome, endereço, telefone, logo e cor da clínica.</li>
<li>Tipo de clínica (odontologia, psicologia…) — define os termos e procedimentos iniciais.</li>
<li>Horário de funcionamento e pausas (almoço, feriados).</li>
<li>Profissionais: nome, especialidade e horário de cada um (se for diferente do da clínica).</li>
<li>Procedimentos: nome, duração e valor de tabela (opcional).</li>
<li>Convênios atendidos, se houver.</li>
<li>Informações que a Ísis pode responder: endereço, estacionamento, formas de pagamento, preparo para consulta.</li>
<li>O jeito de falar: mais formal ou mais próximo.</li>
<li>Quem da equipe vai usar o painel (e-mail de cada um) e quem é o administrador.</li>
<li>Número do WhatsApp da clínica e um celular com ele em mãos para ler o QR code.</li>
<li>Mensagem de aniversário e se quer lembrete, pós-consulta e retorno ligados.</li></ul>

<h2 style="margin-top:7mm"><span>12</span>Acompanhamento das vendas</h2>
<table><tr><th style="width:22%">Etapa</th><th>O que fazer</th><th style="width:24%">Próximo passo</th></tr>
<tr><td>Contato</td><td>Mensagem de abordagem ou indicação.</td><td>Marcar a conversa.</td></tr>
<tr><td>Descoberta</td><td>Perguntas da seção 4; anotar as dores.</td><td>Marcar a demonstração.</td></tr>
<tr><td>Demonstração</td><td>Roteiro da seção 5, com as dores anotadas.</td><td>Enviar proposta.</td></tr>
<tr><td>Proposta</td><td>Valor, prazo de implantação e o que a clínica envia.</td><td>Fechamento em até 7 dias.</td></tr>
<tr><td>Implantação</td><td>Checklist da seção 11; conectar o WhatsApp.</td><td>Acompanhar a 1ª semana.</td></tr>
<tr><td>Pós-venda</td><td>Conferir uso após 15 e 30 dias; pedir indicação.</td><td>Indicações e depoimento.</td></tr></table>
<div class="caixa"><b>Dica:</b> depois de 30 dias de uso, peça permissão para contar a experiência da clínica (com números reais dela). Depoimento verdadeiro vende mais que qualquer promessa — e é a única forma de falar em resultado.</div>
<p style="margin-top:8mm;font-size:9.5px;color:var(--muted)">Base: docs/DIVULGACAO-TEMHORARIO.md e recursos registrados em docs/PLANO.md. Imagens nos outros materiais são ilustrações com dados fictícios.</p>
</section>
</body></html>"""
