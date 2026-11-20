# Perguntas para responder

Este é o **único lugar** com as perguntas em aberto do projeto.

**Como usar**

- Responda aqui mesmo, na linha `Resposta:`, ou pelo chat. Eu passo a resposta para cá.
- Quando a pergunta estiver respondida, eu marco `[x]` e registro a decisão em [DECISOES.md](DECISOES.md) (código Dxx).
- Se a resposta mudar alguma regra, também atualizo [REGRAS-DE-NEGOCIO.md](REGRAS-DE-NEGOCIO.md).
- Se você concordar com a **sugestão**, basta escrever "ok".
- "Veremos depois" → a pergunta vai para **⏸ Adiadas** (não bloqueia nada agora).

**Progresso:** 25 de 37 resolvidas (22 respondidas · 3 adiadas) — 20/11/2026.

---

## 🔴 Bloqueia a Etapa 1 (Fundação)

✅ Nada pendente — Etapa 1 liberada.

## 🟣 Bloqueia a Etapa 5 (WhatsApp WAHA)

✅ Nada pendente — Etapa 5 liberada.

## ⚪ Bloqueia a Etapa 7 (Admin multi-tenant e WhatsApp oficial)

- [ ] **Q2 — Terceira entrada:** você citou três opções de entrada para o chat. A terceira é (a) o WhatsApp oficial separado do WAHA, (b) o Telegram ou (c) outra?
  - Sugestão: (a). As entradas ficam: página web (teste) · WhatsApp pelo WAHA (principal) · WhatsApp oficial (depois).
  - Resposta:
- [ ] **Q25 — Templates do WhatsApp oficial:** no WhatsApp oficial, os disparos precisam de um modelo de mensagem aprovado pela Meta e são pagos. Você aceita usar modelos fixos da plataforma?
  - Sugestão: sim. Os modelos são fixos e a clínica personaliza só o trecho de texto livre.
  - Resposta:
- [ ] **Q15 — Criação de clínicas:** quem cria as clínicas? Só você (dono da plataforma) ou a clínica pode se cadastrar sozinha?
  - Sugestão: só você, como super-admin.
  - Resposta:

## ⚫ Bloqueia a Etapa 8 (Produção)

- [ ] **Q26 — IA em produção:** o OpenCode Go foi feito para ferramentas de programação, e o OpenCode monitora o uso que foge desse padrão. Para atender clínicas de verdade, você aceita trocar para uma API paga por uso (OpenCode Zen ou OpenAI direto)? O código continua o mesmo.
  - Sugestão: usar o Go durante o desenvolvimento e reavaliar antes da Etapa 8.
  - Resposta:

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
