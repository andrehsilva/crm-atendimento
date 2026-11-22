# Perguntas para responder

Este é o **único lugar** com as perguntas em aberto do projeto.

**Como usar**

- Responda aqui mesmo, na linha `Resposta:`, ou pelo chat. Eu passo a resposta para cá.
- Quando a pergunta estiver respondida, eu marco `[x]` e registro a decisão em [DECISOES.md](DECISOES.md) (código Dxx).
- Se a resposta mudar alguma regra, também atualizo [REGRAS-DE-NEGOCIO.md](REGRAS-DE-NEGOCIO.md).
- Se você concordar com a **sugestão**, basta escrever "ok".
- "Veremos depois" → a pergunta vai para **⏸ Adiadas** (não bloqueia nada agora).

**Progresso:** 67 de 76 resolvidas (64 respondidas · 3 adiadas) — 21/11/2026.

---

## 🔴 Bloqueia a Etapa 1 (Fundação)

✅ Nada pendente — Etapa 1 liberada.

## 🟣 Bloqueia a Etapa 5 (WhatsApp WAHA)

✅ Nada pendente — Etapa 5 liberada.

## ⚪ Bloqueia a Etapa 7 (Admin multi-tenant)

✅ Nada pendente — Etapa 7 liberada.


## ⚫ Bloqueia a Etapa 8 (Produção)

✅ Nada pendente — Etapa 8 liberada.

## 🟢 Bloqueia a Etapa 9 (Outros segmentos e personalização)

✅ Nada pendente — Etapa 9 liberada.

## 🟢 Bloqueia a 9C (Observações do cliente)

✅ Nada pendente — 9C liberada.

## 🔵 Bloqueia a Etapa 10 (IA de cada clínica e controle de gastos)

✅ Nada pendente — Etapa 10 liberada.

## 🟠 Bloqueia a 10C (Configuração inicial obrigatória)

✅ Nada pendente — 10C liberada.

## 🟣 Clínica de apresentação (Clínica Rodrigues)

✅ Nada pendente.

## 🟤 Bloqueia a Etapa 11 (Site de apresentação)

✅ Nada pendente — Etapa 11 liberada (o desenvolvimento usa `localhost`).

## ⚫ Bloqueia a publicação em produção com o endereço oficial

- [ ] **Q50 — Domínio da plataforma:** qual nome registrar (ex.: `isis.com.br`, `isisatende.com.br`)? Onde ficará o DNS (Registro.br, Cloudflare…)?
  *Sugestão:* registrar no Registro.br e apontar o DNS para a Cloudflare (grátis). Painel em `app.<dominio>` e sites em `<dominio>/<clinica>`.
  Resposta: *"ainda não tenho o domínio"* (20/11). Não bloqueia o desenvolvimento; só a publicação.

## 🟢 Bloqueia a Etapa 13 (WhatsApp: mensagens picadas, áudio e imagem)

✅ Nada pendente — Etapa 13 liberada.

## 🟢 Bloqueia a Etapa 14 (Mensagens de campanha e envio espaçado)

✅ Nada pendente — Etapa 14 liberada.

## 🟢 Bloqueia a Etapa 15 (Relatórios em Excel)

✅ Nada pendente — Etapa 15 liberada.

## 🟢 Bloqueia a Etapa 17 ("Jeito da clínica")

✅ Nada pendente — Etapa 17 liberada.

## ⚪ WhatsApp por clínica

✅ Nada pendente.

## 🟤 Bloqueia a Etapa 12 (Domínio próprio)

✅ Nada pendente — Etapa 12 liberada (depois da 11).

---

## Propostas que precisam do seu "ok"

Decisões que eu sugeri e que ainda não foram confirmadas. Se não houver objeção, **sigo com elas a partir da Etapa 1** (dá para mudar depois). Detalhes em [DECISOES.md](DECISOES.md).

- [ ] **D2:** stack React + Vite / FastAPI / Postgres Supabase / Agno.
- [ ] **D4:** cada clínica ganha também um código interno. O telefone continua sendo a chave única de busca, e uma troca de número não quebra os dados.
- [ ] **D5:** telefones guardados no formato internacional (`+5521987654321`).
- [ ] **D6:** as regras de agenda são validadas no sistema e no banco de dados, não pela IA.
- [ ] **D7:** as telas são atualizadas em tempo real por SSE (o servidor "empurra" as mudanças para a tela).
- [ ] **D8:** a personalidade da Ísis fica num arquivo de texto e as regras de cada clínica ficam no banco.
- [ ] **D11:** existe uma tela `/demo` com chat + agenda + mensagens lado a lado.
- [ ] **D23:** nova ordem das etapas — WhatsApp (WAHA) vem **antes** dos lembretes, já que é o canal principal (ver [PLANO.md](PLANO.md)).

---

## ⏸ Adiadas (não bloqueiam; voltamos nelas depois)

- [ ] **Q10 — Convênios:** a Ísis pergunta/filtra convênio? → *"veremos depois"*. Por ora nada de convênio no sistema.
- [ ] **Q17 — Selos/tags do cliente:** *"futuramente teremos tags por clientes, poucas: cliente novo / recorrente / em tratamento; ao sair de 'em tratamento' será colocado um 'volta em X tempo'"*. Registrado como ideia futura (D20).
- [ ] **Q21 — Data de nascimento:** como entra no sistema? → *"veremos depois"*. Por ora: campo no cadastro, editável pela recepção.

---

## ✅ Respondidas

- [x] **Q68 — Camadas:** ok — começar só pelo "Jeito da clínica"; o editor por segmento fica para depois. *(22/11 → D77)*
- [x] **Q69 — Quem edita o "Jeito da clínica":** ok — o administrador da clínica (e o admin geral). *(22/11 → D78)*
- [x] **Q60 — Servidor WAHA por clínica:** cada clínica pode ter servidor WAHA próprio, número e webhook exclusivo, cadastrados no Admin geral; sem servidor próprio, usa o da plataforma. *(22/11 → D76)*
- [x] **Q65 — Quem baixa relatórios:** ok — só o administrador da clínica; cada download registrado. *(21/11 → D73)*
- [x] **Q66 — Recall:** ok — 6 meses por padrão, ajustável de 3 a 24. *(21/11 → D74)*
- [x] **Q67 — 1ª leva:** ok — recall, atendimentos, produção e faltas; os outros 3 numa parte B. *(21/11 → D75)*
- [x] **Q61 — Para quem vai a campanha:** ok — "todos os clientes", "atendidos nos últimos 12 meses" ou "com atendimento marcado"; nunca para quem pediu PARAR. *(21/11 → D69)*
- [x] **Q62 — Intervalo entre envios:** ok — só aniversário e campanhas, 20 a 45 s aleatórios entre mensagens da mesma clínica; conversa, confirmação, remarcação e lembrete como hoje. *(21/11 → D70)*
- [x] **Q63 — Modelos prontos:** ok — Natal, Ano novo e férias, editáveis, com {nome} e {clinica}. *(21/11 → D71)*
- [x] **Q64 — Quem dispara:** ok — só o administrador da clínica; a tela mostra antes quantas pessoas recebem e quanto tempo leva. *(21/11 → D72)*
- [x] **Q57 — Mensagens picadas:** ok — espera 8 s depois da última mensagem (no máximo 30 s no total) e responde tudo junto, com "digitando…". *(20/11 → D66)*
- [x] **Q58 — Áudio:** ok — transcreve até 2 minutos; o custo entra no "Uso da IA" e no teto; mais longo, pede para resumir por texto ou passa para a equipe. *(20/11 → D67)*
- [x] **Q59 — Imagem, vídeo, figurinha e documento:** ok — "Ainda não consigo ver imagens por aqui. Pode me escrever o que precisa?"; o arquivo fica registrado na conversa para a equipe. *(20/11 → D68)*
- [x] **Q51 — Endereço da Rodrigues:** ok — o endereço curto passa de `demo` para `rodrigues`; a demonstração passa a ser a marcação "clínica de apresentação" (D55). *(20/11 → D61)*
- [x] **Q53 — Layouts iniciais:** ok — 3 layouts para todos os segmentos ("Clássico", "Moderno", "Acolhedor"), com a cor e a logo da clínica. *(20/11 → D62)*
- [x] **Q54 — Seções e fotos:** ok — galeria e bio/foto dos profissionais sim; "antes e depois" não; validar os textos padrão com um profissional antes de lançar. *(20/11 → D63)*
- [x] **Q55 — Domínio próprio:** ok — extra pago; por ora o admin geral liga em cada clínica. *(20/11 → D64)*
- [x] **Q56 — Chat no site:** ok — só o botão "Agendar pelo WhatsApp" na 1ª versão. *(20/11 → D65)*
- [x] **Q44 — Configuração inicial obrigatória:** ok — passo a passo "Primeiros passos" em 6 etapas (clínica · assistente · aparência · horários · serviços e equipe · IA); WhatsApp fica com o admin geral. *(20/11 → D51)*
- [x] **Q45 — Quem preenche:** ok — o admin da clínica (ou o admin geral pelo "Entrar como"); a recepção vê "A clínica está sendo configurada pelo administrador". *(20/11 → D52)*
- [x] **Q46 — Clínicas existentes:** ok — mesma regra; o passo a passo mostra só o que falta. *(20/11 → D53)*
- [x] **Q47 — Algo obrigatório apagado depois:** ok — não trava de novo; aviso no topo e item pendente em Configurações. *(20/11 → D54)*
- [x] **Q48 — Clínica de apresentação:** ok — marcação no Admin geral; o admin da plataforma entra sempre por ela; botão "Admin geral" só nela; nas outras, "Voltar para a Clínica Rodrigues". *(20/11 → D55)*
- [x] **Q49 — Reiniciar demonstração:** ok — apaga só consultas, conversas e mensagens de teste e recria os exemplos; nome, aparência, assistente, IA e WhatsApp ficam. *(20/11 → D56)*
- [x] **Q42 — Observações do cliente:** ok — histórico (diário) com data, hora e autor; negrito, itálico, lista e link; quem escreveu corrige/apaga a sua, o admin apaga qualquer uma; a assistente não lê; o campo antigo vira a 1ª observação. *(20/11 → D48)*
- [x] **Q43 — Pasta do Drive:** ok — um link por cliente, só `https://drive.google.com/...`; botão "Abrir pasta no Drive" em outra aba; sem integração. *(20/11 → D49)*
- [x] **Q37 — Chave de IA:** ok — o admin da clínica (ou o admin geral) cadastra em Configurações › Assistente; chave criptografada no banco com chave-mestra no `.env`; só os 4 últimos caracteres aparecem; botão "Testar conexão". *(20/11 → D42)*
- [x] **Q38 — Provedor e modelo:** ok — Google, OpenAI, OpenCode ou OpenRouter; modelo numa lista sugerida (só os aprovados na bateria de cenários) ou campo livre. *(20/11 → D43)*
- [x] **Q39 — Gastos:** ok — tokens por resposta; custo estimado pela tabela de preços do admin geral; tela "Uso da IA" com US$ e R$ (cotação do admin geral). *(20/11 → D44)*
- [x] **Q40 — Teto mensal:** ok — aviso aos 80%; aos 100% a assistente pausa e passa para a equipe; lembretes, confirmações e aniversários continuam. *(20/11 → D45)*
- [x] **Q41 — Sem chave:** ok — assistente desligada; o admin geral pode liberar "usar a chave da plataforma" (gasto aparece no Admin geral › Uso). *(20/11 → D46)*
- [x] **Q26 — IA em produção:** resolvida pela Etapa 10 — cada clínica usa a própria chave, paga por uso. *(20/11 → D36 substituída por D42–D46)*
- [x] **Q33 — Segmentos da 1ª leva:** ok para a sugestão — a clínica escolhe o segmento ao ser criada (Odontologia, Medicina, Fisioterapia, Psicologia/Psiquiatria, Estética, Outro); o segmento preenche palavras, procedimentos iniciais e o jeito da assistente. *(20/11 → D38)*
- [x] **Q34 — Palavras de cada negócio:** ok — o segmento preenche e o admin da clínica ajusta em Configurações › Perfil; valem nas telas, mensagens automáticas e assistente. *(20/11 → D39)*
- [x] **Q35 — Aparência:** ok — logo e cor principal por clínica; o produto continua **Ísis**. *(20/11 → D40)*
- [x] **Q36 — Regras por segmento:** ok — Etapa 9 traz palavras, textos, procedimentos iniciais, aparência e lembrete discreto; sessões repetidas e convênio ficam para depois. *(20/11 → D41)*
- [x] **Q1 — Provedor e modelo de IA:** OpenCode Go com `gpt-6-luna`. *(16/11 → D13)*
- [x] **Q3 — Nome da assistente:** sempre Ísis, nunca "Bia". *(16/11 → D12)*
- [x] **Q4 — Banco:** Supabase na nuvem (plano gratuito). *(16/11 → D14)*
- [x] **Q5 — Telefone na página web:** só digita (página web é para teste); **foco no WAHA**. *(16/11 → D15, D23)*
- [x] **Q6 — Colunas do kanban:** ~~5 colunas do layout~~ → revisto na Q16. *(16/11 → D19)*
- [x] **Q7 — Dentista:** pode marcar com qualquer dentista da clínica. Se houver mais de um, a Ísis **sempre pergunta** com quem; quando o paciente vira cliente de um dentista, a Ísis **associa** e passa a sugerir esse. *(16/11 → D16)*
- [x] **Q8 — Duração:** normalmente 60 min, mas cadastrada **por procedimento** no banco, e a Ísis usa esse valor. *(16/11 → D17)*
- [x] **Q9 — Preços:** só se a clínica cadastrar os valores e ligar a opção. *(16/11 → RN-AT-10)*
- [x] **Q11 — Recepção:** pode marcar/remarcar/cancelar pelo painel, e **o paciente recebe a atualização por mensagem**. *(16/11 → D18)*
- [x] **Q13 — Passar para uma pessoa:** selo "Atendimento manual", Ísis para de responder, painel avisa. *(16/11 → RN-AT-06)*
- [x] **Q14 — Lembrete:** 09:00 do dia útil anterior; confirmação na hora em que marca. *(16/11 → RN-MS-01/02)*
- [x] **Q16 — Orçamento:** não vamos gerenciar orçamento; **coluna removida**. Colunas não são definitivas — a imagem era só sugestão. *(16/11 → D19)*
- [x] **Q18 — Menu:** Dashboard · CRM · Agenda · Mensagens · Leads/Clientes · Configurações. *(16/11 → D21)*
- [x] **Q19 — Dashboard:** começa com a sugestão (consultas de hoje, confirmadas × pendentes, conversas esperando pessoa, leads parados, aniversariantes); mais itens depois. *(16/11 → spec 06)*
- [x] **Q20 — Visual:** sem Figma; eu sugeri → fonte **Lexend** + paleta rosa queimado da spec 11. *(16/11 → D22)*
- [x] **Q22 — Horários:** dentistas herdam o horário da clínica, com exceções; botão "+ pausa" por dia. *(16/11 → RN-AG-01)*
- [x] **Q23 — Aniversário:** 09:00. *(16/11 → RN-DP-01)*
- [x] **Q24 — Outros disparos:** ficam para depois (ex.: aviso de férias coletivas). Primeira versão só com **aniversário**. *(16/11 → D24)*
- [x] **Q27 — Região do banco:** recriar o projeto Supabase em **São Paulo** antes da Etapa 3. *(19/11 → D26)*
- [x] **Q28 — Dúvida que a Ísis não sabe:** continua transferindo para a equipe, mas **avisando claramente** o paciente que a equipe assume. *(20/11 → D27, RN-AT-06)*
- [x] **Q12 — Números por clínica:** 1 número de WhatsApp = 1 clínica na primeira versão. *(20/11 → D29)*
- [x] **Q29 — WAHA:** já roda num **servidor do usuário**; o webhook passa a apontar **direto para o nosso backend**, sem n8n. *(20/11 → D28)*
- [x] **Q15 — Criação de clínicas:** só o dono da plataforma, num **painel de admin geral** (separado do painel das clínicas). Lá ele cria a instância e define nome da clínica, nome do agente, telefone, webhook/WAHA e demais configurações. *(20/11 → D30)*
- [x] **Q2 — Terceira entrada:** nenhuma por agora. Entradas da 1ª versão: página web (teste) e WhatsApp pelo WAHA. *(20/11 → D32)*
- [x] **Q25 — Templates do WhatsApp oficial:** não se aplica — sem WhatsApp oficial na 1ª versão. *(20/11 → D33)*
- [x] **Q30 — Login:** **Supabase Auth** (e-mail + senha, "Esqueci minha senha" por e-mail). *(20/11 → D34)*
- [x] **Q31 — Usuários da clínica:** o admin cria com **senha provisória**, que a pessoa troca no 1º acesso; convite por e-mail fica para depois. *(20/11 → D35)*
- [x] **Q32 — Hospedagem:** no **mesmo servidor do WAHA** (servidor do usuário), com Docker e HTTPS automático. *(20/11 → D37)*
