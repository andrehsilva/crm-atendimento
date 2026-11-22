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
| D25 | ✅ Dev usa a conexão **direta** do Supabase (exige IPv6). Em produção, **Session pooler** (porta 5432): funciona em IPv4 e aceita o tempo real (LISTEN). O *Transaction pooler* (6543) não serve | Etapa 1B, 19/11/2026; confirmado no teste Docker da 8B (20/11) |
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
| D36 | ~~⏸ IA em produção decidida depois.~~ → substituída por D42–D46. Até lá, OpenCode Go; trocar para API paga por uso é passo obrigatório do guia antes do 1º cliente real | Q26, 20/11/2026 |
| D37 | ✅ Produção no **mesmo servidor do WAHA**: Docker Compose + Caddy (HTTPS automático), backend com 1 processo (lembretes e tempo real rodam dentro dele) | Q32, 20/11/2026 |
| D38 | ✅ **Multi-segmento:** cada clínica tem um segmento (odontologia, medicina, fisioterapia, psicologia, estética, outro) que define palavras, procedimentos iniciais, área de atuação e sinais de urgência da assistente. Clínicas antigas = odontologia | Q33, 20/11/2026 |
| D39 | ✅ **Palavras ajustáveis** por clínica (profissional, cliente, atendimento — singular/plural) sobre o padrão do segmento; usadas nas telas, mensagens automáticas e assistente | Q34, 20/11/2026 |
| D40 | ✅ **Aparência por clínica:** logo (PNG/JPG/WebP, até 512 KB, guardada no banco) e cor principal; o produto continua **Ísis** | Q35, 20/11/2026 |
| D41 | ✅ Etapa 9 sem regras próprias de segmento, exceto o **lembrete discreto** (não cita procedimento; padrão ligado em psicologia). Sessões recorrentes e convênio (Q10) ficam para depois | Q36, 20/11/2026 |
| D42 | ✅ **Chave de IA por clínica**, cadastrada pelo admin da clínica ou pelo admin geral em Configurações › Assistente. Guardada **criptografada** (chave-mestra no `.env`), nunca devolvida à tela (só os 4 últimos caracteres); botão "Testar conexão" | Q37, 20/11/2026 |
| D43 | ✅ Provedores: **Google (Gemini), OpenAI, OpenCode e OpenRouter**. Modelo escolhido numa lista sugerida (só modelos aprovados na bateria de cenários) ou digitado livre | Q38, 20/11/2026 |
| D44 | ✅ Cada resposta guarda os **tokens** usados; custo estimado pela tabela de preços mantida pelo admin geral; tela "Uso da IA" com US$ e R$ (cotação do admin geral). O valor oficial é o da conta no provedor | Q39, 20/11/2026 |
| D45 | ✅ **Teto mensal** em US$ por clínica: aviso aos 80%; aos 100% a assistente pausa e as conversas vão para a equipe (paciente avisado). Lembretes, confirmações e aniversários continuam (não usam IA) | Q40, 20/11/2026 |
| D46 | ✅ Clínica **sem chave** = assistente desligada. O admin geral pode ligar "usar a chave da plataforma" (teste grátis, demonstração); esse gasto aparece no Admin geral › Uso | Q41, 20/11/2026 |
| D47 | ✅ **Fotos:** cada usuário do painel pode enviar a própria foto de perfil, e a equipe pode pôr uma foto em cada lead/cliente (aparece em Leads / Clientes e no CRM). Mesmas regras da logo: PNG/JPG/WebP até 512 KB, tipo conferido pelos bytes, guardadas no banco | Pedido do usuário, 20/11/2026 |
| D48 | ✅ **Observações do cliente** em histórico: cada nota guarda data/hora e autor, formatação simples (negrito, itálico, lista, link). Autor edita/apaga a sua; admin da clínica apaga qualquer uma. A assistente não lê as notas. O campo antigo "observações" vira a 1ª nota | Q42, 20/11/2026 |
| D49 | ✅ **Pasta do Google Drive** por cliente: só o link (`https://drive.google.com/...`) e um botão que abre em outra aba. Sem integração; o acesso à pasta é controlado no próprio Drive | Q43, 20/11/2026 |
| D50 | ✅ **Detalhes da Etapa 10A:** as clínicas que já existiam continuam na chave da plataforma (nada para de funcionar); clínica nova começa desligada. Sem IA, a mensagem do paciente fica guardada, a conversa vai para a equipe (sem resposta automática) e "Devolver para a assistente" é recusado. Chave criptografada com Fernet (`IA_CHAVE_MESTRA`, obrigatória em produção); erro do provedor nunca é repassado cru (pode conter parte da chave). Google e OpenRouter usam a API de chat; OpenAI e OpenCode, a API Responses | Etapa 10A, 20/11/2026 |
| D51 | ✅ **Configuração inicial obrigatória** (10C): "Primeiros passos" com 6 etapas — clínica (nome, urgência, endereço, segmento), assistente (nome, tratamento), aparência (confirmar cor; logo opcional), horários (≥1 dia), serviços e equipe (≥1 procedimento e ≥1 profissional que o faça), IA (chave testada com sucesso ou chave da plataforma). WhatsApp fica com o admin geral | Q44, 20/11/2026 |
| D52 | ✅ Enquanto a configuração não termina, só o admin da clínica (ou o admin geral pelo "Entrar como") entra, e vê só o passo a passo; a recepção vê "A clínica está sendo configurada pelo administrador" | Q45, 20/11/2026 |
| D53 | ✅ Clínicas que já existem seguem a mesma regra; o passo a passo mostra só o que falta | Q46, 20/11/2026 |
| D54 | ✅ Depois de concluída, a configuração não trava de novo: se algo obrigatório for apagado, aparece aviso no topo e o item fica pendente em Configurações | Q47, 20/11/2026 |
| D55 | ✅ **Clínica de apresentação** (hoje a Clínica Rodrigues): marcação no Admin geral; o admin da plataforma entra sempre por ela; o botão "Admin geral" só aparece nela; nas outras, "Voltar para a Clínica Rodrigues" | Q48, 20/11/2026 |
| D56 | ✅ **"Reiniciar demonstração"** apaga só consultas, conversas, mensagens e clientes de teste e recria os exemplos; nome, aparência, assistente, IA, WhatsApp, horários e equipe ficam | Q49, 20/11/2026 |
| D57 | ✅ ~~Endereço por clínica em subdomínio~~ → **revista em 20/11/2026:** o painel fica num endereço único (`app.<dominio>`; o login leva cada pessoa à sua clínica) e o site de cada clínica fica em `<dominio>/<clinica>`. Subdomínio por clínica descartado: muito trabalho e risco (login por endereço, certificado coringa) para pouco ganho | Pedido do usuário + revisão de infraestrutura, 20/11/2026 |
| D58 | ✅ **Site de apresentação "de graça"** para cada clínica, com layouts (templates) e os dados que ela já cadastra; botão "Agendar pelo WhatsApp". Depois, **domínio próprio** (ex.: `drarodrigues.com.br`) como extra | Pedido do usuário, 20/11/2026 |
| D59 | ✅ Ordem: depois da 10B → Etapa 11 (site de apresentação em `<dominio>/<clinica>`) → Etapa 12 (domínio próprio, só para o site, extra pago). O domínio oficial da plataforma ainda não existe (Q50) | Pedido do usuário, 20/11/2026 (revista) |
| D60 | ✅ **Detalhes da 10B:** o custo é calculado no momento da resposta com o preço da época (mudar o preço não refaz o passado); modelo sem preço cadastrado não tem custo, e a tela avisa que o teto não age sobre ele. O teto vale para todo o gasto da clínica (chave própria ou da plataforma). Pausada pelo teto, a conversa vai para a equipe e o paciente recebe o aviso uma vez; "Devolver para a assistente" fica recusado até aumentar o teto ou virar o mês | Etapa 10B, 20/11/2026 |
| D61 | ✅ O endereço curto da Clínica Rodrigues passa de `demo` para `rodrigues` (site em `<dominio>/rodrigues`). A clínica de demonstração é a que tem a marcação "apresentação" (D55), não um endereço fixo | Q51, 20/11/2026 |
| D62 | ✅ Site: 3 layouts para todos os segmentos ("Clássico", "Moderno", "Acolhedor"); textos e ícones vêm do segmento; cor e logo da clínica | Q53, 20/11/2026 |
| D63 | ✅ Site: galeria de fotos e bio/foto de cada profissional; **sem "antes e depois"** (regras de publicidade dos conselhos). Textos padrão validados com um profissional antes de lançar | Q54, 20/11/2026 |
| D64 | ✅ Domínio próprio é **extra pago**; por ora o admin geral liga o recurso em cada clínica | Q55, 20/11/2026 |
| D65 | ✅ Site sem chat na 1ª versão: só o botão "Agendar pelo WhatsApp" (a assistente atende lá) | Q56, 20/11/2026 |
| D66 | ✅ **Mensagens picadas:** a assistente espera 8 s depois da última mensagem do paciente (no máximo 30 s desde a primeira) e responde tudo de uma vez; enquanto espera, "digitando…" | Q57, 20/11/2026 |
| D67 | ✅ **Áudio:** transcrito para texto (até 2 min) e respondido normalmente; o custo entra no "Uso da IA" e no teto. Mais longo: pede para resumir por texto ou passa para a equipe | Q58, 20/11/2026 |
| D68 | ✅ **Imagem, vídeo, figurinha e documento:** resposta fixa pedindo para escrever ("Ainda não consigo ver imagens por aqui. Pode me escrever o que precisa?"); o tipo do arquivo fica registrado na conversa para a equipe | Q59, 20/11/2026 |
| D69 | ✅ **Campanhas — público:** "todos os clientes", "atendidos nos últimos 12 meses" ou "com atendimento marcado"; nunca para quem pediu PARAR (RN-DP-04) | Q61, 21/11/2026 |
| D70 | ✅ **Envio espaçado:** só mensagens em massa (aniversário e campanhas) — 20 a 45 s aleatórios entre uma e outra da mesma clínica. Conversa, confirmação, remarcação e lembrete seguem como hoje e passam na frente | Q62, 21/11/2026 |
| D71 | ✅ **Modelos prontos** de Natal, Ano novo e férias, editáveis; o texto aceita {nome} (primeiro nome) e {clinica} | Q63, 21/11/2026 |
| D72 | ✅ Só o **administrador da clínica** cria e dispara campanha; antes de confirmar, a tela mostra quantas pessoas recebem e quanto tempo o envio leva | Q64, 21/11/2026 |
| D73 | ✅ Relatórios em Excel: só o **administrador da clínica** baixa; cada download fica registrado (LGPD) | Q65, 21/11/2026 |
| D74 | ✅ Recall: paciente sem vir há **6 meses** (ajustável de 3 a 24) e sem nada marcado | Q66, 21/11/2026 |
| D75 | ✅ 1ª leva de relatórios: recall, atendimentos, produção e faltas (15A); cadastro, aniversariantes e desempenho da assistente na 15B | Q67, 21/11/2026 |
| D76 | ✅ **WhatsApp próprio por clínica:** no Admin geral › clínica, número do WhatsApp, servidor WAHA (da plataforma ou próprio, chave criptografada) e webhook exclusivo `/webhooks/waha/<código>` com segredo próprio; a sessão de uma clínica nunca entra no webhook de outra | Q60, pedido do usuário, 22/11/2026 |
| D77 | ✅ **Personalização do prompt em camadas:** o núcleo (segurança, ferramentas, confirmação) fica no código; a clínica ganha o campo **"Jeito da clínica"** (até 1.500 caracteres), numa seção própria que não pode contrariar o núcleo. Texto editável por segmento fica para depois | Q68, 22/11/2026 |
| D78 | ✅ Quem edita o "Jeito da clínica": o administrador da clínica (e o admin geral) | Q69, 22/11/2026 |
| D79 | ✅ **Aba Configurações › Canais:** o administrador da clínica vê status e número do WhatsApp, mostra o QR code e reinicia a sessão para reconectar, e pode **pausar a Ísis no WhatsApp** (as mensagens continuam chegando no painel e vão para a equipe, sem aviso ao paciente; lembretes, confirmações e "1"/"PARAR" seguem normais). Servidor WAHA, sessão e webhook continuam só com o admin geral | Q70, 22/11/2026 |
| D80 | ✅ Toda a equipe vê a aba Canais (status); só o administrador da clínica mexe | Q71, 22/11/2026 |
| D81 | ✅ **Sino de notificações** com: aguardando atendimento humano · consulta marcada/remarcada/cancelada pela Ísis · paciente confirmou pelo lembrete · mensagem não enviada · WhatsApp desconectado · gasto da IA em 80%/100% | Q72, 22/11/2026 |
| D82 | ✅ Notificações de **situação** ("aguardando humano", "WhatsApp desconectado") somem sozinhas quando resolvidas; as de **acontecimento** são marcadas como lidas por pessoa (uma a uma ou todas) | Q73, 22/11/2026 |
| D83 | ✅ Chamar atenção: contador no sino, **som curto só para "aguardando humano"** e o número no título da aba do navegador | Q74, 22/11/2026 |
| D84 | ✅ Toda ação que salva ou muda algo no painel mostra um aviso de confirmação no canto da tela (os erros já apareciam) | pedido do usuário, 22/11/2026 |
| D85 | ✅ **Entregue/lida:** o WhatsApp avisa (evento `message.ack`) e o sistema guarda; aparece na tela Mensagens (selo enviada/entregue/lida) e na conversa (✓ enviada · ✓✓ entregue · ✓✓ azul lida) nas respostas da Ísis e da equipe. Nunca volta atrás (lida não vira entregue). Se o paciente desligou a confirmação de leitura, fica em "entregue" | Q75, 22/11/2026 |
| D86 | ✅ Ao subir, o backend acrescenta sozinho o evento novo no webhook das clínicas já ligadas — só quando o webhook da sessão já aponta para este sistema (nunca toma a sessão de outro sistema) | Q76, 22/11/2026 |
| D87 | ✅ **Tratamento aguardando** (ex.: protético): a Ísis não marca a próxima sessão daquele tratamento (bloqueio no código), explica ao paciente e avisa a equipe no sino; outros procedimentos ela marca normalmente | Q77, 22/11/2026 |
| D88 | ✅ **Retomar tratamento:** a recepção clica em "Retomar"; sai uma mensagem pelo WhatsApp (texto editável antes) convidando a marcar, e a Ísis conduz quando o paciente responder | Q78, 22/11/2026 |
| D89 | ✅ **Série de sessões:** a recepção marca N semanas no mesmo dia/hora; cada data passa pelas regras e as que não couberem são mostradas. Sessões de tratamento aberto **não contam** no limite de consultas futuras (RN-AG-08). A Ísis marca uma por vez | Q79, 22/11/2026 |
| D90 | ✅ **Tags automáticas:** Novo (nunca veio) · Recorrente (2+ atendimentos realizados) · Em tratamento · Aguardando (com motivo) — calculadas pelo sistema, ninguém coloca à mão. Substitui D20 | Q80, 22/11/2026 |
| D91 | ✅ **Faltas repetidas:** com **2 faltas em 45 dias** (ajustável em Configurações › Assistente; 0 desliga), a assistente não marca consulta nova e passa a conversa para a recepção — bloqueio no código. Remarcar/cancelar o que já existe continua | Q81, 22/11/2026 |
| D92 | ✅ **Convênios:** só no primeiro contato a Ísis pergunta se é convênio ou particular; a clínica cadastra a lista de convênios aceitos; sem lista, só registra convênio sim/não (Etapa 22) | Q10, pedido do usuário, 22/11/2026 |
| D93 | ✅ **Convênio não atendido:** a Ísis diz com gentileza que a clínica não atende aquele convênio e oferece o particular; com dúvida ou insistência, passa para a recepção | Q83, 22/11/2026 |
| D94 | ✅ **Convênio fica no cadastro do paciente:** Particular, o nome do convênio (da lista da clínica) ou só "Convênio" quando a clínica não tem lista; a recepção edita; aparece como tag e na conversa; vale para as próximas consultas | Q84, 22/11/2026 |
| D95 | ✅ A Ísis **não pede** carteirinha — só o nome do convênio | Q85, 22/11/2026 |
| D96 | ✅ **Resumo do dia do profissional:** pelo WhatsApp pessoal, a grade do dia — horário, **primeiro nome** do paciente, procedimento, sessão X de N do tratamento e ✅ confirmou / ⏳ a confirmar —, mais pausas e horários livres. Nenhuma observação clínica | Q86, 22/11/2026 |
| D97 | ✅ **Privacidade:** só recebe o profissional que pediu — o administrador ativa no cadastro dele e informa o número pessoal; desativado, nada sai | Q87, 22/11/2026 |
| D98 | ✅ Às **07:00** por padrão (ajustável por profissional), **só em dia que a clínica abre** e **só se houver consulta**; uma vez por dia; mudanças depois não geram novo envio (o painel mostra na hora). Não segue o silêncio noturno dos pacientes (é mensagem da equipe) | Q88, 22/11/2026 |
