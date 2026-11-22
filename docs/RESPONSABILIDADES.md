# Quem faz o quê

Este documento divide o trabalho entre quatro papéis:
- **Assistente (Ísis)**: a IA que conversa com o paciente;
- **Secretária / recepção**: o atendimento manual, pelo painel;
- **Sistema**: o que acontece sozinho, sem IA e sem pessoa;
- **Administrador da clínica**: a configuração da clínica.

Ele reúne as regras de [REGRAS-DE-NEGOCIO.md](REGRAS-DE-NEGOCIO.md) e as decisões de [DECISOES.md](DECISOES.md). Se algo aqui conflitar com aqueles arquivos, eles valem.

> **Princípio:** a Ísis **pede**, o sistema **decide**. O que não pode falhar (conflito de horário, limite de consultas, faltas, tratamento em espera, horário de funcionamento) está no código. Mesmo que a Ísis tente, o sistema recusa.

---

## 1. Resumo em uma tabela

| Assunto | Assistente (Ísis) | Secretária / recepção | Sistema (automático) |
|---|---|---|---|
| Responder dúvidas | ✅ Sobre a clínica: endereço, horários, procedimentos, preços (se liberados), "Sobre a clínica" | ✅ Tudo o que a Ísis não sabe ou não pode | — |
| Marcar consulta | ✅ Dentro de todas as regras, uma por vez, com confirmação do paciente | ✅ Sem passar pela confirmação do paciente; pode marcar em espera de tratamento e com faltas repetidas | Confere horário, conflito, limite e regras |
| Marcar série de sessões | ❌ | ✅ "Repetir" na janela de marcar | Confere cada data; uma confirmação só |
| Remarcar / cancelar | ✅ Só consultas do próprio paciente | ✅ Qualquer consulta | Cancela os lembretes velhos e avisa o paciente |
| Confirmar presença | ✅ Quando o paciente responde ao lembrete | ✅ Pelo painel | ✅ "1" no lembrete confirma sem IA |
| Registrar presença / falta | ❌ | ✅ A partir do dia da consulta | — |
| Urgência | ✅ Orienta e passa para a equipe | ✅ Assume e resolve | Mostra o aviso no sino |
| Convênio | ✅ Pergunta só no primeiro contato e confere na lista | ✅ Corrige no cadastro | Só deixa a Ísis marcar depois da resposta |
| Tratamentos | ✅ Lê e respeita; marca a próxima sessão se estiver em andamento | ✅ Abre, põe em espera, retoma e encerra | Bloqueia a marcação se estiver aguardando |
| Mensagens automáticas | ❌ Não dispara | ✅ Campanhas (só o administrador) | ✅ Confirmação, lembrete, aniversário, retomada |
| Configurações | ❌ | Só vê | — |

---

## 2. Assistente (Ísis)

### 2.1 O que ela faz
- **Atende 24 horas** pelo WhatsApp e pelo chat do site, inclusive fora do expediente. Fora do horário, ela avisa que a resposta da equipe vem no próximo expediente.
- **Identifica o paciente pelo telefone do canal.** Ela nunca pede o telefone e nunca aceita um número digitado no meio da conversa.
- **Pede o nome completo** do paciente novo antes de marcar.
- **Convênio, só no primeiro contato** (quem ainda não veio à clínica): antes de marcar, pergunta "convênio ou particular?".
  - Com a lista da clínica, confere o nome. Se a clínica não atende aquele convênio, avisa com gentileza e oferece o particular; com dúvida ou insistência, passa para a recepção.
  - Sem lista, registra só "convênio" ou "particular".
  - Não pede carteirinha. Quem já veio não é perguntado.
- **Responde dúvidas sobre a clínica:** endereço, horários, procedimentos cadastrados, o texto "Sobre a clínica" e o "Jeito da clínica".
- **Informa preços** só se a clínica cadastrou o valor **e** ligou "mostrar preços". Ela não negocia nem faz orçamento.
- **Busca horários livres de verdade na agenda.** Oferece no máximo 3 opções por vez, dando prioridade ao dia, ao turno e ao profissional que o paciente pediu.
- **Pergunta com qual profissional**, quando há mais de um que faz o procedimento. Depois da primeira consulta, sugere primeiro o profissional de referência do paciente.
- **Marca, remarca e cancela sempre em dois passos:**
  1. mostra um resumo ("terça, 01/12, às 9h, com a Dra. Ana. Posso confirmar?");
  2. só executa depois do "sim". O sistema recusa a ação se o paciente não respondeu depois do resumo.
- **Diz quando vem o lembrete** ao terminar de marcar ou remarcar, por exemplo: "você recebe um lembrete na segunda às 9h". Se não houver lembrete, ela não promete.
- **Avisa a política da clínica** quando o paciente cancela ou remarca em cima da hora (menos de 24 h, valor ajustável).
- **Trata o tratamento em andamento:**
  - **em andamento:** marca a próxima sessão, sugerindo o mesmo profissional, o mesmo dia da semana e o mesmo horário de sempre;
  - **aguardando** (protético, exame, cicatrização…): não marca aquela sessão. Explica que a clínica entra em contato e **avisa a equipe**. Outros procedimentos ela marca normalmente;
  - segue o **recado para a assistente** que a equipe escreveu no tratamento.
- **Resolve as respostas 2 e 3 do lembrete:** quando o paciente pede para remarcar ou cancelar, ela conduz a conversa. O "1" (confirmar) é resolvido pelo sistema, sem IA.
- **Entende áudio** (vira texto) quando a clínica aceita áudio. Pede para escrever quando o áudio é longo demais e quando chega imagem ou arquivo sem legenda.
- **Junta mensagens picadas** ("oi" / "tudo bem" / "queria marcar") e responde tudo de uma vez.

### 2.2 Quando ela passa para a secretária
Ela passa a conversa para a equipe e **para de responder** até alguém devolver:
- o paciente pede para falar com uma pessoa;
- reclamação;
- **urgência**: dor forte, inchaço, sangramento, trauma, febre com dor de dente, dificuldade para engolir ou respirar. Antes de passar, ela orienta a procurar atendimento e indica o telefone de urgência, ou o SAMU 192;
- dúvida que ela não sabe responder;
- duas falhas seguidas ao tentar resolver;
- procedimento que **só a recepção marca** (ex.: urgência);
- **faltas repetidas**: 2 faltas em 45 dias (ajustável). O sistema não deixa ela marcar e a conversa vai para a equipe;
- pedidos de "encaixe", "sou amigo do doutor", "fura a fila": ela é educada, segue a agenda e oferece a recepção.

O paciente **sempre** recebe um aviso fixo de que a equipe vai continuar ali mesmo. Fora do horário, o aviso diz que a resposta vem no próximo expediente.

### 2.3 O que ela nunca faz
- Diagnosticar, indicar remédio ou dosagem.
- Inventar preço, horário, procedimento ou informação.
- Revelar dados de outros pacientes ou detalhes internos (como funciona, quais ferramentas usa).
- Mexer em consultas de outro telefone.
- Passar do limite de consultas futuras. O limite é **2**, e as sessões de tratamento não contam.
- Marcar fora do horário de funcionamento, em pausa, feriado ou bloqueio, ou com menos de 2 h de antecedência.
- Marcar a sessão de um tratamento que está **aguardando**.
- Marcar consulta nova para quem tem **faltas repetidas**.
- Mandar mensagem por conta própria. Ela só **responde**; quem manda mensagens automáticas é o sistema.
- Falar de assuntos fora da clínica.

### 2.4 Quando ela fica sem responder
- Conversa **assumida pela equipe** (atendimento manual).
- **Ísis pausada no WhatsApp** pelo administrador, em Configurações › Canais. Tudo do WhatsApp vai para a equipe; o chat do site continua normal.
- **Teto de gasto da IA atingido** no mês: o paciente é avisado e a conversa vai para a equipe.
- **Clínica sem IA configurada:** tudo vai para a equipe, sem aviso.

---

## 3. Secretária / recepção (atendimento manual)

### 3.1 Conversas
- **Assume a conversa** a qualquer momento ("Assumir conversa"). A Ísis para de responder ali.
- **Inicia a conversa** com quem nunca escreveu: a primeira mensagem sai pelo WhatsApp da clínica, e a conversa começa em atendimento manual. No modo de teste, só para os números liberados. Na mesma janela há "Marcar consulta".
- **Responde pelo painel.** A resposta sai pelo WhatsApp do paciente, com os tracinhos de enviada, entregue e lida.
- **Devolve para a Ísis** quando terminar. Isso não é possível com a Ísis pausada no WhatsApp ou com o teto da IA atingido.
- **Acompanha o sino:**
  - quem está aguardando atendimento humano (com som);
  - **consulta que já passou sem registro de presença** ("Registrar presença: Fulano"), que some quando marcam Compareceu ou Faltou;
  - WhatsApp desconectado;
  - o que a Ísis marcou, remarcou ou cancelou;
  - confirmações de pacientes;
  - mensagens que não saíram;
  - pedidos durante a espera de um tratamento;
  - previsão de espera vencida;
  - falta em sessão de tratamento.

### 3.2 Agenda
- **Marca, remarca e cancela qualquer consulta.** As regras de horário valem para ela também, mas ela não precisa da confirmação do paciente.
- **Pode o que a Ísis não pode:**
  - marcar procedimentos "só recepção" (ex.: urgência);
  - marcar a sessão de um tratamento que está aguardando, se decidir que já dá;
  - marcar para quem tem faltas repetidas.
- **Marca série de sessões:** "Repetir" na janela de marcar, com N sessões a cada X dias. Vê na hora quais datas não couberam e por quê.
- **Registra presença ("realizada") e falta ("faltou")**, a partir do dia da consulta.
- **Confirma consultas** pelo painel (ex.: depois de ligar para o paciente).
- **Liga para quem não respondeu ao lembrete.** Isso aparece em destaque no painel.

### 3.3 Pacientes e tratamentos
- **Edita o cadastro:** nome, data de nascimento, **convênio**, foto, observações e pasta do Drive.
- **Abre tratamento:** procedimento, quantas sessões e recado para a assistente.
- **Põe o tratamento em espera** (protético, exame, cicatrização ou outro motivo, com previsão). A partir daí, a Ísis não marca aquela sessão.
- **Retoma** quando a espera acaba. Pode mandar ao paciente uma mensagem convidando a marcar (texto editável), e aí a Ísis conduz a marcação.
- **Encerra o tratamento:**
  - **concluído**, com "volta em X meses", que alimenta o recall;
  - **interrompido**.
- **Move cards no CRM** (Novo contato, Agendados, Confirmado, Cancelados).

### 3.4 O que a secretária **não** faz (é do administrador da clínica)
- Mudar regras da agenda, horários, procedimentos, profissionais, textos das mensagens e o "Jeito da clínica".
- Pausar a Ísis no WhatsApp, reconectar o WhatsApp (QR code) e criar usuários.
- Disparar campanhas e baixar relatórios.

---

## 4. Sistema (automático, sem IA e sem pessoa)

- **Confirmação imediata** ao marcar, remarcar ou cancelar, venha da Ísis ou da recepção. Ela traz a data, o horário, o profissional, o endereço e **quando vem o lembrete**.
- **Lembrete** no dia útil anterior às 09:00 (ajustável), com as opções 1 Confirmar · 2 Remarcar · 3 Cancelar.
  - Se a consulta foi marcada depois desse horário, não há lembrete.
  - Remarcou ou cancelou, o lembrete velho é cancelado.
- **"1" confirma e "PARAR" desliga os disparos**, resolvidos direto no código, sem IA.
- **Série de sessões:** **uma confirmação só**, com todas as datas, e um lembrete para cada sessão.
- **Aniversário** às 09:00 (se ligado), uma vez por ano.
- **Resumo do dia do profissional:** no horário dele (padrão 07:00), pelo WhatsApp pessoal, a agenda do dia com o primeiro nome dos pacientes, o procedimento e quem confirmou. Só para quem pediu, só em dia com consulta e uma vez por dia.
- **Mensagem de retomada** do tratamento, quando a recepção clica em "Retomar".
- **Pós-consulta** (se ligado): no dia seguinte às 10:00, "como você está?" para quem compareceu.
- **Retorno** (se ligado): na data de voltar ("volta em" ou X meses sem vir), convite para marcar; sem resposta, mais um convite 15 dias depois. Quando a pessoa responde, a Ísis marca.
- **Silêncio:** nada sai entre 21h e 08h. Também há limite de envios por minuto e por dia, e intervalo entre mensagens em massa.
- **Bloqueios no código:**
  - horário ocupado;
  - fora do expediente;
  - limite de consultas;
  - tratamento aguardando;
  - faltas repetidas;
  - paciente que só mexe nas próprias consultas;
  - isolamento total entre clínicas.
- **Tags automáticas:** Novo · Recorrente · Em tratamento · Aguardando · Particular / nome do convênio.
- **Entregue/lida:** vem do WhatsApp e só avança, nunca volta.
- **Sino e tempo real:** tudo o que muda aparece na hora para toda a equipe.

---

## 5. Administrador da clínica

Ele faz tudo o que a secretária faz, e mais:
- **Configurações:**
  - perfil, horários, procedimentos (duração, preço e "só recepção") e profissionais;
  - **convênios atendidos** e se a assistente pergunta o convênio no primeiro contato;
  - **resumo do dia** de cada profissional: ativar (só se ele pediu), WhatsApp pessoal e horário;
  - **horário de cada profissional**: segue o da clínica ou horário próprio (dias e até 2 faixas, dentro do horário da clínica);
  - assistente: nome, tratamento, preços, áudio, regras da agenda, **faltas para passar à recepção** e o "Jeito da clínica";
  - mensagens e campanhas, **pós-consulta e retorno automáticos** (ligar, horário, textos);
  - site e usuários.
- **Canais:** ver o status, mostrar o QR, reiniciar e **pausar ou retomar a Ísis no WhatsApp**.
- **Uso da IA:** acompanhar o gasto e ajustar o teto do mês.
- **Campanhas:** criar e disparar (com contagem e prévia antes) e cancelar.
- **Relatórios em Excel:** recall, atendimentos, produção, faltas, cadastro, aniversariantes e desempenho da assistente.
