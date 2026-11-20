# Decisões

Legenda: ✅ decidido · 🟡 proposta (aguardando seu ok)

> As perguntas em aberto ficam em [PERGUNTAS.md](PERGUNTAS.md). Quando uma pergunta é respondida, a decisão entra aqui.

## Decisões tomadas

| # | Decisão | Motivo |
|---|---|---|
| D1 | ✅ Sem n8n; toda lógica em código | Pedido do usuário |
| D2 | 🟡 React+Vite / FastAPI / Postgres Supabase / Agno | Pedido do usuário, confirmado como adequado |
| D3 | ✅ Multi-tenant: **telefone da clínica identifica a instância**; conversa = telefone da clínica + telefone do paciente | Premissa do usuário |
| D4 | 🟡 Internamente cada clínica tem um `id` (UUID) e o telefone é chave **única** de busca | Se a clínica trocar de número, não precisamos reescrever todos os dados |
| D5 | 🟡 Telefones guardados em formato E.164 (`+5521987654321`) | Comparar sem erro de formato (+55, parênteses, traço, 9º dígito) |
| D6 | 🟡 Validações de agenda no backend + restrição no banco | Lição do vídeo: "o que não pode falhar fica no processo" |
| D7 | 🟡 Tempo real por SSE | Simples, sem infraestrutura extra |
| D8 | 🟡 Persona em arquivo de texto + regras da clínica no banco | Editar comportamento sem programar |
| D9 | ✅ Layout de referência = telas em `docs/layouts/` (barra lateral, CRM com 5 colunas, Configurações em abas, temas claro e escuro) | Aprovado pelo usuário em 16/11/2026 |
| D10 | ✅ Disparos de mensagens (aniversário + mensagens programadas) entram no escopo | Pedido do usuário em 16/11/2026 — spec 10 |
| D11 | 🟡 Tela `/demo` em 3 colunas (chat + agenda + mensagens) como na imagem 03 | É o "resultado final na tela" pedido |
| D12 | ✅ A assistente se chama **Ísis** em todo o projeto (nunca "Bia") | Definido pelo usuário em 16/11/2026 |
| D14 | ✅ Banco: **Supabase na nuvem** (plano gratuito) para desenvolvimento | Q4 |
| D15 | ✅ Página web do paciente é **para teste**: só digita o telefone, sem código | Q5 |
| D16 | ✅ Dentista: paciente escolhe qualquer um; com mais de um dentista a Ísis sempre pergunta; após a 1ª consulta realizada o dentista fica **associado** ao paciente (sugerido por padrão) | Q7 |
| D17 | ✅ Duração **por procedimento** no banco (padrão 60 min); sem duração por dentista | Q8 |
| D18 | ✅ Recepção marca/remarca/cancela pelo painel e o paciente **recebe mensagem** da mudança | Q11 |
| D19 | ✅ Sem gestão de orçamento. Kanban inicial com 4 colunas: Novo Contato · Agendados · Confirmado · Cancelados — **provisórias**, revisitar depois | Q16 |
| D20 | ⏸ Futuro: poucas tags por cliente (novo · recorrente · em tratamento); ao sair de "em tratamento" agenda-se um "volta em X tempo" | Q17 |
| D21 | ✅ Menu: Dashboard · CRM · Agenda · Mensagens · Leads/Clientes · Configurações | Q18 |
| D22 | ✅ Visual: fonte **Lexend** (Google Fonts) + paleta da spec 11, temas claro/escuro | Q20 (sugestão aceita) |
| D23 | 🟡 Ordem das etapas: WhatsApp WAHA (Etapa 5) antes de lembretes/disparos (Etapa 6); WhatsApp oficial vai para a Etapa 7 | Q5 "foco no WAHA" |
| D24 | ✅ Disparos na 1ª versão: só **aniversário**. Mensagens programadas (ex.: férias coletivas) e automações ficam para depois | Q24 |
| D13 | ✅ Modelo: **OpenCode Go + `gpt-6-luna`** via Responses API (`https://opencode.ai/inference/go/openai/v1`). No Agno: `OpenAIResponses(id=..., base_url=..., api_key=...)`. Enviar cabeçalho `x-opencode-session` estável por conversa e User-Agent próprio (`isis-atendimento/0.x`). Tudo no `.env`, trocável sem mexer no código | Definido pelo usuário em 16/11/2026; endpoint conforme docs do OpenCode Go |
| D25 | 🟡 Dev usa a conexão **direta** do Supabase (exige IPv6). Em produção, usar **Session pooler** se o servidor não tiver IPv6 | Etapa 1B, 19/11/2026 |
| D26 | ✅ Projeto Supabase recriado na região **South America (São Paulo)** — menor latência e dados no Brasil (LGPD) | Q27, 19/11/2026 |
| D27 | ✅ Quando a Ísis não sabe responder, ela **continua passando a conversa para a equipe** (e para de responder), mas o paciente **sempre recebe um aviso claro** de que a equipe assume dali em diante. O aviso é acrescentado pelo código | Q28, 20/11/2026 — no teste da Etapa 4 a Ísis ficou em silêncio sem avisar |
| D28 | ✅ WAHA roda num **servidor do usuário** (não no Docker local). O webhook do WAHA aponta **direto para o backend** (sem n8n, D1); em desenvolvimento, via túnel até a máquina local | Q29, 20/11/2026 |
| D29 | ✅ Primeira versão: **1 número de WhatsApp = 1 clínica** | Q12, 20/11/2026 |
| D30 | ✅ Clínicas (instâncias) são criadas **só pelo dono da plataforma**, num **painel de admin geral** separado do painel da clínica: nome da clínica, nome do agente, telefone (chave), WAHA/webhook e demais configurações | Q15, 20/11/2026 |
| D31 | ✅ Etapa 5 já guarda os dados do WAHA **por clínica no banco** (não no `.env`); a tela do admin geral para editá-los vem na Etapa 7 | 20/11/2026 |
| D32 | ✅ 1ª versão com duas entradas: página web (teste) e WhatsApp pelo WAHA. Terceira entrada fica para depois | Q2, 20/11/2026 |
| D33 | ✅ Sem WhatsApp oficial (Cloud API) na 1ª versão; templates da Meta não se aplicam. A Etapa 7 fica só com o admin multi-tenant | Q25, 20/11/2026 |
| D34 | ✅ Login pelo **Supabase Auth** (e-mail + senha). O backend confere o token do Supabase e liga o usuário à clínica (`clinic_users`) ou à plataforma (`platform_admins`). Papéis: super_admin, clinic_admin, reception | Q30, 20/11/2026 |
| D35 | ✅ Usuários da clínica criados pelo admin com **senha provisória** (mostrada uma vez, troca obrigatória no 1º acesso). Convite por e-mail depois | Q31, 20/11/2026 |
| D36 | ⏸ IA em produção decidida depois. Até lá, OpenCode Go; trocar para API paga por uso é passo obrigatório do guia antes do 1º cliente real | Q26, 20/11/2026 |
| D37 | ✅ Produção no **mesmo servidor do WAHA**: Docker Compose + Caddy (HTTPS automático), backend com 1 processo (lembretes e tempo real rodam dentro dele) | Q32, 20/11/2026 |
