# Plano de construção

Cada etapa termina com algo **que você vê funcionando** e uma lista curta do que testar.
Só seguimos depois do seu **"pode seguir"**. Perguntas pendentes: [PERGUNTAS.md](PERGUNTAS.md).

```
0 Planejamento ✅ ─► 1 Fundação ─► 2 Banco + agenda ─► 3 Painel em tempo real
   ─► 4 Ísis (IA) ─► 5 WhatsApp WAHA ─► 6 Lembretes + aniversário
   ─► 7 Admin multi-tenant ─► 8 Testes + produção ─► 9 Outros segmentos ─► 10 IA por clínica
```
> Ordem revista em 16/11/2026 (D23): o WAHA é o canal principal, por isso vem antes dos lembretes.

---

## Etapa 0 — Planejamento ✅
Documentos, layout de referência e primeiras respostas registradas.

## Etapa 1 — Fundação ✅ (19/11/2026)
Dividida em duas partes.

### 1A — Estrutura básica (sem banco, sem IA)
- `backend/`: FastAPI com `GET /health`, configuração lida do `.env`, CORS liberado para o frontend.
- `frontend/`: React + Vite + TypeScript, com a fonte Lexend, as cores da spec 11, tema claro/escuro, barra lateral com o menu (D21) e páginas vazias.
- `.env.example`, `.gitignore` e `dev.ps1` (sobe tudo com um comando).

**O que testar:** rodar `./dev.ps1`. Em `http://localhost:5173` deve aparecer o painel com o menu, e o botão de tema deve trocar entre claro e escuro. `http://localhost:8000/health` deve responder `ok`.

### 1B — Conexão com o banco e com a IA
**Antes de começar, você precisa ter:**
1. Um projeto criado no supabase.com (plano gratuito, região São Paulo). Guarde a senha do banco.
2. Do Supabase: a *connection string* (Connect → **Session pooler**), a *Project URL* e as chaves *anon* e *service_role*.
3. A chave do **OpenCode Go** (opencode.ai → Zen → Go → API key).

Esses dados vão **direto no arquivo `backend/.env`**, nunca aqui no chat.

**Entrega:**
- `/health` informa se o banco está conectado e se a chave da IA responde.
- Um teste de bancada (`scripts/teste_llm.py`) que lista os modelos e manda um "olá" para o `gpt-6-luna`.

**O que testar:** o `/health` mostrar `banco: ok` e `ia: ok`, e o script imprimir a resposta da Ísis.

## Etapa 2 — Banco e motor de agenda (sem IA) ✅ (19/11/2026)
**Entrega:** o "caderno" da clínica funcionando pela API.
- Tabelas (spec 08) e dados de exemplo: 1 clínica demo, 2 dentistas, procedimentos (60 min por padrão), horário da clínica com pausa de almoço.
- Serviço de agenda: horários livres, marcar, remarcar e cancelar, **com todas as validações** (conflito, expediente, pausas, antecedência, telefone, dentista de referência).
- Testes automatizados das regras RN-AG-*.

**O que testar:** pela página `/docs` do FastAPI, marcar uma consulta. Tentar marcar outra no mesmo horário (deve recusar), tentar marcar no almoço (deve recusar) e tentar cancelar com o telefone errado (deve recusar).

## Etapa 3 — Painel operacional em tempo real ✅ (19/11/2026)
**Entrega:** as telas no layout aprovado (`docs/layouts/`, specs 06 e 11), ainda sem IA.
- Dashboard (primeira versão), CRM (kanban com 4 colunas provisórias e arrastar), Agenda da semana, Mensagens enviadas e Leads/Clientes.
- Tela `/demo` em 3 colunas (chat + agenda + mensagens). Chat web de teste com resposta "eco" provisória.
- A recepção marca, remarca e cancela pelo painel (o envio ao paciente entra na Etapa 6).
- Atualização em tempo real (SSE): muda na tela sem recarregar.

**O que testar:** abrir o painel em duas abas, marcar uma consulta numa delas e ver a consulta aparecer na agenda e no kanban das duas na hora.

## Etapa 4 — Ísis (agente com IA) ✅ (20/11/2026)
**Entrega:** a Ísis conversando de verdade no chat web de teste.
- Agno + `gpt-6-luna` (OpenCode Go).
- Personalidade e regras em arquivo de texto editável (`backend/app/agent/prompts/isis.md`) + regras da clínica vindas do banco.
- Ferramentas: ver horários, marcar, remarcar, cancelar, minhas consultas, info da clínica e chamar uma pessoa.
- Pergunta qual dentista quando houver mais de um; depois da 1ª consulta, sugere o dentista de referência.
- Memória por conversa (telefone da clínica + telefone do paciente).

**O que testar:** pelo chat, marcar → remarcar → cancelar e ver a agenda mudar na hora. Testar "rosto inchado e febre": a Ísis deve orientar atendimento imediato, não marcar uma consulta normal.

## Etapa 5 — WhatsApp (WAHA) ✅ (20/11/2026)
**Entrega:** a mesma Ísis respondendo no WhatsApp.
- WAHA no servidor do usuário (D28), conectado por QR code; 1 número = 1 clínica (D29).
- Webhook de entrada, envio de respostas e túnel para teste local (cloudflared).

**O que testar:** ler o QR com um celular de teste, mandar "oi" de outro celular, marcar uma consulta pelo WhatsApp e ver a consulta na agenda.
- Feito em 20/11/2026: tabela `whatsapp_instances`, rota `/webhooks/waha` com HMAC, envio com "digitando…", resposta da recepção pelo WhatsApp e script `scripts/whatsapp.py`. Testado pelo usuário com a sessão `what-andre` em 20/11/2026.

## Etapa 6 — Lembretes, avisos e aniversário ✅ (20/11/2026)
**Entrega:** mensagens automáticas pelo WhatsApp.
- Aviso imediato ao marcar, remarcar ou cancelar, **pela Ísis ou pela recepção** (D18).
- Lembrete às 09:00 do dia útil anterior. O paciente responde: 1 Confirmar · 2 Remarcar · 3 Cancelar.
- Mensagem de aniversário (Configurações › Mensagens, com prévia), às 09:00.
- "Relógio simulado" para testar sem esperar um dia.

**O que testar:** marcar uma consulta para depois de amanhã, avançar o relógio e ver o lembrete no WhatsApp e no painel. Responder "1" e ver o card ir para *Confirmado*. Repetir com um paciente que faz aniversário hoje.

## Etapa 7 — Admin multi-tenant ✅ (20/11/2026)
**Entrega:** criar e configurar clínicas sem mexer no código.
- Login de administrador e de usuários da clínica.
- Configurações em abas (spec 07): Perfil, Horários de Funcionamento, Procedimentos, Mensagens e Usuários (+ Profissionais, Assistente e Canais).
- Admin da plataforma: criar clínica (o telefone é a chave), suspender, entrar como.
- ~~Adaptador do WhatsApp oficial~~ → fora da 1ª versão (D32, D33); vai para o backlog.
- Painel de **admin geral** separado (D30): criar instância com nome da clínica, nome do agente, telefone e sessão do WAHA (hoje feito pelo `scripts/whatsapp.py`, D31).

- **7A ✅ feito (20/11/2026):** login pelo Supabase Auth com cookie httpOnly e renovação automática; papéis super_admin / clinic_admin / reception; todas as rotas do painel conferem a clínica (teste C16 varre todas); senha provisória com troca obrigatória; "Esqueci minha senha"; `scripts/usuarios.py`.
- **7B ✅ feito (20/11/2026):** área `/admin` só para o super admin — Clínicas (lista, criar com padrões + 1º admin com senha provisória, editar, suspender/reativar, "Entrar como" registrado em `admin_audit`), WhatsApp por clínica (ligar sessão existente ou criar nova, status, QR code, apontar webhook, reiniciar, desligar), Usuários da clínica, Uso do mês e Configurações da plataforma (somente leitura).
- **7C ✅ feito (20/11/2026):** Configurações em abas — Perfil (nome, endereço, telefone de urgência, "sobre a clínica" usado pela assistente, troca de senha), Horários (dia a dia com pausas; avisa consultas que ficariam de fora), Procedimentos (duração, preço, quem faz, "IA pode marcar"; excluir usado = desligar), Profissionais (cor, procedimentos, ativo, férias/folgas), Assistente (nome, tratamento, preços, regras da agenda), Mensagens e Usuários. Ver: toda a equipe; mudar: só o admin da clínica.
- Ficou para depois: logo da clínica (upload de imagem), aba "Canais" para o admin da clínica (hoje o WhatsApp é cuidado pelo admin geral) e horário próprio por profissional pela tela.

**O que testar:** criar uma 2ª clínica, conversar com a Ísis de cada uma e confirmar que **uma não enxerga nada da outra**.

## Etapa 8 — Bateria de testes e produção ✅ (20/11/2026)
**Entrega:** relatório de cenários (`CENARIOS-DE-TESTE.md`) rodado automaticamente + `GUIA-PRODUCAO.md`.

**O que testar:** ler o relatório, em que cada cenário aparece com ✅/❌ e o motivo.
- **8A ✅ feito (20/11/2026):** `scripts/cenarios.py` conversa com a IA de verdade numa clínica de teste e confere no banco; C16/C17/C18/C20 pelos testes automáticos. Resultado: 25 de 25. Achados corrigidos: transferência sem texto virava "problema técnico"; aviso da política de cancelamento não chegava ao paciente; limite de consultas só era avisado no fim; impasse (deadlock) em marcações simultâneas.
- **8B ✅ feito (20/11/2026):** proteções de produção (backend não sobe com configuração incompleta, sem `https://` ou apontando para dev; chat de teste e documentação da API desligados; cookies só por HTTPS); `docker-compose.yml` com backend (1 processo, sem root, sem segredos na imagem) + painel servido pelo Caddy com HTTPS automático (Modo A) ou atrás do proxy existente (Modo B); `docs/GUIA-PRODUCAO.md`. Testado localmente com Docker: guarda de produção, painel, API, webhook assinado, SSE e conexão pelo Session pooler.

## Etapa 9 — Outros segmentos e personalização ✅ (20/11/2026)
**Por quê:** vender a Ísis também para médicos, fisioterapeutas, psicólogos, estética e outros negócios com agenda (D38–D41).

- **9A — Segmentos e palavras:** ✅ feito e testado (20/11/2026, clínica de Psicologia). Segmento por clínica (escolhido ao criar no admin geral, editável no Perfil); palavras ajustáveis
  (profissional / cliente / atendimento); procedimentos iniciais por segmento; a assistente, as mensagens automáticas e as telas
  usam as palavras da clínica; urgências e "o que a assistente não é" por segmento; lembrete discreto.
- **9B — Aparência e fotos:** ✅ feito e testado (20/11/2026). Logo ao lado do nome da clínica e cor principal (Configurações › Perfil › Aparência, com prévia; cores claras demais são recusadas); foto de perfil de cada usuário (Perfil › Minha conta); foto de cada lead/cliente (Leads / Clientes › editar), que aparece na lista e no CRM. Imagens PNG/JPG/WebP até 512 KB guardadas no banco (D40, D47).
- **9C — Observações do cliente:** ✅ feito e testado (20/11/2026; D48, D49). Em Leads / Clientes, histórico de observações em texto com formatação, cada uma com data e autor, e um botão que abre a pasta do Google Drive do cliente (só o link, sem integração).

**O que testar:** criar uma clínica de Psicologia no admin geral, conversar no chat de teste e conferir que a assistente fala
em "sessão" e "psicólogo(a)", que o lembrete não cita o procedimento e que as telas trocam as palavras.

## Etapa 10 — IA de cada clínica e controle de gastos ✅ (20/11/2026)
Cada clínica cadastra a própria chave (Google, OpenAI, OpenCode ou OpenRouter), escolhe o modelo, acompanha tokens e custo
estimado e define um teto mensal. Substitui a D36 (IA paga por uso antes do 1º cliente).
- **10A — Chave e modelo:** ✅ feito e testado (20/11/2026; D50). Chave criptografada por clínica, provedores Google/OpenAI/OpenCode/OpenRouter, "Testar conexão", assistente desligada sem chave, opção "usar a chave da plataforma" no admin geral.
- **10C — Configuração inicial obrigatória:** ✅ feito e testado (20/11/2026; D51–D54). Passo a passo "Primeiros passos" que precisa ser concluído antes de usar o painel (clínica, assistente, aparência, horários, serviços e equipe, IA).
- **Reiniciar demonstração sem apagar a clínica (D56):** ✅ feito e testado (20/11/2026). Troca só clientes, consultas, conversas e mensagens pelos exemplos; botão só na clínica `/demo`, com confirmação.
- **Clínica de apresentação (D55):** ✅ feito e testado (20/11/2026). Marcação no Admin geral › clínica › Dados (hoje a Clínica Rodrigues); o admin da plataforma entra por ela; "Admin geral" só nela, "Voltar para…" nas outras.
- **10B — Uso e teto:** ✅ feito e testado (20/11/2026; D60). tokens por resposta, tabela de preços e cotação no admin geral, tela "Uso da IA", teto mensal com aviso aos 80% e pausa aos 100%.

## Etapa 11 — Site de apresentação ✅ (20/11/2026) (D57 revista, D58, D59, D61–D63, D65); o domínio oficial (Q50) só é preciso para publicar
Painel e login num endereço único (`app.<dominio>`). Cada clínica ganha um site público em `<dominio>/<clinica>`, gerado no servidor
(bom para o Google e para a prévia do link no WhatsApp), com os dados que ela já cadastra: nome, logo, cor, sobre,
procedimentos, equipe, horários e endereço. Botão "Agendar pelo WhatsApp" (a assistente atende) e link "Área da clínica"
para o painel. Editor em Configurações › Site: layout, seções, textos, fotos, prévia e Publicar (só com a 10C concluída).

- **11A — Site com os dados atuais:** ✅ feito e testado (20/11/2026). Endereço da Rodrigues virou `rodrigues` (D61); site gerado no servidor em `/site/<clinica>` (dev: `localhost:5173/site/rodrigues`; produção: `<dominio>/<clinica>` quando houver domínio, Q50) com 3 layouts (D62: Elegante, Moderno e Acolhedor; cor própria por layout; foto e bio de cada profissional; carrossel quando há mais de um); Configurações › Site com escolha de layout, prévia (computador/celular) e Publicar (só com os Primeiros passos concluídos). "Reiniciar demonstração" passa a valer para a clínica de apresentação.
- **11B — Editor completo:** ✅ feito e testado (20/11/2026). Seções liga/desliga e ordem, textos próprios, escolher quais procedimentos aparecem, galeria de fotos, bio e foto de cada profissional (D63), sitemap.

## Etapa 12 — Domínio próprio (só para o site, extra pago) — ⏳ depois da 11 (D58, D64)
A clínica aponta o domínio dela (CNAME + verificação TXT) e o HTTPS sai automático, só para domínio verificado.
O painel continua sempre no endereço oficial.

## Etapa 13 — WhatsApp: mensagens picadas, áudio e imagem ✅ (21/11/2026) (D66–D68; a 12 espera o domínio, Q50)
Pedido do usuário (20/11/2026): muita gente escreve em várias mensagens curtas ("oi" / "tudo bem" / "queria saber…") e manda áudio.
- **Mensagens picadas:** a assistente espera alguns segundos depois da última mensagem e responde tudo de uma vez.
- **Áudio:** é transcrito para texto e a assistente responde normalmente; o custo entra no teto de gasto da IA.
- **Imagem:** a assistente pede, com educação, para a pessoa escrever o que precisa.
- **13A — Mensagens picadas e mídia:** ✅ feito e testado (20/11/2026; D66, D68). Áudio, por ora, recebe o pedido para escrever.
- **13B — Áudio transcrito:** ✅ feito e testado (21/11/2026; D67). Precisa de `TRANSCRICAO_API_KEY` no `backend/.env`.

## Etapa 14 — Mensagens de campanha editáveis e envio espaçado ✅ (21/11/2026)
Pedido do usuário (21/11/2026): além do aniversário (fixo), mensagens que a clínica escreve e agenda: Natal, Ano novo,
aviso de férias… E nunca mandar muitas de uma vez: mesmo no mesmo dia, um intervalo entre um envio e outro, para não
bloquear o número.
- **Campanhas:** texto editável com {nome} e {clinica}, data/hora de envio, para quem (todos os clientes, só os ativos…), prévia e cancelamento.
- **Envio espaçado:** intervalo aleatório só nas mensagens em massa (aniversário e campanhas); respostas da conversa saem na hora. Valem também os limites de hoje (20/min, 300/dia, RN-DP-07) e a janela de silêncio.
- **14A — Campanhas e envio espaçado:** ✅ feito e testado (21/11/2026; D69–D72). Configurações › Aniversário e campanhas (junto do aniversário): modelos (Natal, Ano novo, férias), {nome}/{clinica}, público com contagem e tempo estimado, data de início, andamento e cancelar.
- **14B — Tela Mensagens reorganizada** ✅ feito e testado (21/11/2026) (pedido de 21/11/2026, "está confusa"):
  - abas por andamento ("Na fila", "Enviadas", "Não enviadas") com contagem;
  - uma linha por mensagem (tipo, cliente, quando, situação), com o texto inteiro ao clicar;
  - campanhas numa área própria;
  - o "Relógio de teste" recolhido num canto e só em desenvolvimento.

## Etapa 15 — Relatórios em Excel ✅ (22/11/2026)
Tela "Relatórios" com período, profissional e o botão "Baixar Excel" (.xlsx feito no servidor, com cabeçalho fixo, filtro e R$).
Relatórios propostos:
1. **Pacientes para chamar de volta (recall):** sem vir há N meses e sem nada marcado.
2. **Atendimentos do período.**
3. **Produção por profissional e por procedimento** (valor estimado pela tabela de preços).
4. **Faltas e cancelamentos** (com taxa por dia da semana e horário).
5. **Cadastro de pacientes.**
6. **Aniversariantes do mês.**
7. **Desempenho da assistente.**

Cada download fica registrado (LGPD); nenhum relatório traz conversas nem observações clínicas.
- **15A — Recall, atendimentos, produção e faltas:** ✅ feito e testado (21/11/2026; D73–D75). Menu "Relatórios" (só admin), período, profissional, meses do recall e "Baixar Excel".
- **Filtro por profissional no Dashboard:** ✅ feito e testado (22/11/2026) (pedido de 21/11/2026). A agenda do dia muda; conversas, leads, fila e aniversariantes seguem "clínica toda".
- **15B — Cadastro, aniversariantes e desempenho da assistente:** ✅ feito e testado (22/11/2026).

## Etapa 16 — WhatsApp próprio de cada clínica ✅ (22/11/2026; D76)
No Admin geral › clínica › WhatsApp:
- número do WhatsApp da clínica;
- servidor WAHA da plataforma ou próprio (endereço e chave criptografada, com "Testar conexão");
- webhook exclusivo (`/webhooks/waha/<código>`) com segredo próprio, e botões para apontar e trocar o segredo.

Envio, recebimento, QR e áudio passam a usar o servidor de cada clínica.

## Etapa 17 — "Jeito da clínica" ✅ (22/11/2026; D77, D78); texto por segmento fica para depois
O núcleo do prompt (segurança, ferramentas, confirmação em dois passos) **continua no código**, versionado e testado pela bateria de cenários. Em cima dele:
- **por segmento:** texto editável pelo admin geral, com histórico e "Voltar ao padrão";
- **por clínica:** campo "Jeito da clínica" (até 1.500 caracteres), que entra numa seção própria e não pode contrariar o núcleo.

## Etapa 18 — Aba "Canais" da clínica — 🧪 aguardando teste (D79, D80)
Configurações › Canais: status e número do WhatsApp (toda a equipe vê); o administrador da clínica mostra o QR, reinicia a conexão e pausa/retoma a Ísis no WhatsApp. Servidor, sessão e webhook continuam no Admin geral.

## Etapa 19 — Notificações e confirmação de cada ação ✅ (22/11/2026; D81–D84)
- **Sino com contador** no topo do painel: "Maria aguardando atendimento humano", e outros avisos que pedem ação da equipe.
- **Toast de confirmação** (aviso rápido no canto da tela) em **toda** ação feita: hoje só cerca de metade das ações mostra "feito"; os erros já aparecem.

## Etapa 20 — "Entregue/lida" nas mensagens ✅ (22/11/2026; D85, D86)
- O WhatsApp avisa quando a mensagem chegou ao celular e quando foi lida; o sistema guarda e nunca volta atrás.
- Tela Mensagens: selo enviada/entregue/lida. Conversa: ✓ / ✓✓ / ✓✓ azul nas respostas da Ísis e da equipe.
- Clínicas já ligadas passam a mandar o aviso sozinhas (o backend atualiza o webhook ao subir).

## Etapa 21 — Tratamentos em andamento (pacientes recorrentes) ✅ (22/11/2026; D87–D90)
**21A — Tratamento, regras da Ísis e tags**
- No paciente, a equipe abre um **Tratamento**: procedimento, profissional, sessões previstas, intervalo e uma orientação curta para a assistente.
- Situações: em andamento · aguardando (protético, exame, cicatrização…, com previsão) · concluído (com "volta em X meses") · interrompido.
- A Ísis vê o tratamento; aguardando → não marca aquela sessão (bloqueio no código) e avisa a equipe; "Retomar" chama o paciente.
- Sessões de tratamento não contam no limite de 2; o recall ignora tratamento aberto e usa o "volta em".
- Sino: perguntou do tratamento · previsão vencida · faltou à sessão. Tags automáticas no CRM, Clientes e conversa.

**21B — Marcar série** (mesmo dia/hora por N semanas, mostrando as datas que não couberam).

## Ajuste pós-21 — Faltas repetidas ✅ (22/11/2026; D91)
Com 2 faltas em 45 dias (ajustável), a Ísis não marca e passa para a recepção.

## Etapa 22 — Convênios ✅ (22/11/2026; D92–D95)
- Configurações: lista de convênios que a clínica atende.
- Só no primeiro contato, a Ísis pergunta "convênio ou particular?"; com lista, confere o nome; sem lista, só registra sim/não.

## Etapa 23 — Resumo do dia para o profissional ✅ (22/11/2026; D96–D98)
De manhã (horário ajustável), o profissional recebe no WhatsApp pessoal a grade do dia: horários, pacientes, procedimentos e quem confirmou.

## Etapa 24 — Horário de atendimento por profissional ✅ (22/11/2026; D99)
- Configurações › Profissionais › "Horário": segue o da clínica ou horário próprio (dias e até 2 faixas por dia, sempre dentro do horário da clínica).
- Antes de salvar, mostra as consultas marcadas que ficariam fora; elas continuam marcadas (a mudança vale para as novas).
- A Ísis, a série, a agenda e o resumo do dia já respeitam; a Ísis passa a saber os dias de cada profissional.
- Junto: sino lembra de registrar presença quando passa o horário da consulta (RN-PN-13).

## Etapa 25 — Retorno e pós-consulta automáticos ✅ (22/11/2026; D100–D103)
- **Pós-consulta:** depois de "Compareceu", mensagem "como você está?" (D100).
- **Retorno:** na data de voltar ("volta em" do tratamento concluído ou recall), convite para marcar; a Ísis conduz.

## Ajuste pós-25 — Tipos de clínica de saúde mental ✅ (22/11/2026; D104)
No cadastro e em Configurações › Perfil, Psicologia, Psicanálise e Psiquiatria são opções separadas, cada uma com termos,
procedimentos iniciais e orientações próprias. Clínicas existentes continuam classificadas como Psicologia.

**O que testar:** criar uma clínica de cada tipo no Admin geral e conferir, em Configurações › Perfil, que o tipo salvo
continua selecionado e que os termos e procedimentos iniciais correspondem ao nicho.

## Etapa 26 — Horário fixo e lembrete por tratamento ✅ (23/11/2026; D105–D107)
- "Abrir tratamento" ganha **"Já marcar as sessões?"**: não · horário fixo sem data para terminar · número de sessões.
  Escolhe profissional, primeira data, horário e "toda semana" / "a cada 2 semanas".
- Horário fixo: sempre as próximas 8 sessões marcadas; o sistema acrescenta sozinho; encerrar tira as futuras da agenda.
- Caixa **"A assistente manda confirmação e lembrete"** (padrão pelo tipo de clínica; Psicanálise desligado).
  No cartão do tratamento: selos "Horário fixo" / "Sem lembrete" e botões para ligar/desligar lembrete e parar o horário fixo.

## Etapa 27 — Arrastar sessão na agenda ✅ (23/11/2026; D108, D109)
Na agenda (dia e semana), arrastar uma sessão para outro horário/dia: confirmação "Mover de … para …?" com a caixa
"avisar o paciente" marcada; grava pelo mesmo caminho do Remarcar (todas as regras); se não couber, volta ao lugar com o motivo.

## Etapa 28 — Excluir profissional ✅ (23/11/2026; D110, D111)
No "Editar profissional", botão **Excluir profissional**: sem histórico apaga de vez; com histórico arquiva (some da lista,
"mostrar arquivados" traz de volta; reativar desarquiva). Com consultas marcadas, excluir ou desativar é recusado e mostra a lista.

## Etapa 29 — Arquivar ou excluir contato ✅ (23/11/2026; D112–D115)
No cartão do CRM, em Clientes e na conversa: **Arquivar** (toda a equipe; some das listas, dados ficam, filtro "arquivados"
para ver/desarquivar) e **Excluir de vez** (só admin, só para quem nunca teve consulta; apaga conversa e mensagens).
Arquivado que escreve de novo volta sozinho como "Novo Contato". Sem arquivamento automático.

## Etapa 30 — Perguntar à assistente ✅ (23/11/2026; D117–D121)
Botão **"Perguntar à assistente"** na barra lateral, acima de "Abrir demonstração" (só aparece se o admin geral liberou
a clínica em Admin geral › clínica › IA). Abre um painel de chat: a equipe pergunta sobre agenda, clientes, procedimentos,
tratamentos, CRM e campanhas. Perguntas livres; a IA consulta o banco só para ler e só a própria clínica (travas no banco).
Fora da plataforma → recusa; pedido de alterar → indica a tela. Conversa some ao fechar; gasto entra no teto.

## Etapa 31 — WhatsApp da clínica sem confusão ✅ (24/11/2026; D122–D124)
Admin geral › clínica › WhatsApp vira um cartão em 3 passos: **servidor** (salvar/testar antes de ligar) → **número**
(sessão livre desse servidor ou nova, com QR que se atualiza sozinho) → **webhook exclusivo apontado sozinho**.
Situação com um selo só (webhook certo / desalinhado → "Corrigir webhook"). "Desligar" pede confirmação e não apaga
servidor nem webhook. Pré-requisito: `WAHA_API_KEY` fixa no serviço do WAHA (sem ela o WAHA gera outra a cada reinício).

## Etapa 32 — Desempenho (cache) ✅ (26/11/2026; D125, D126)
**Antes** (temhorario, VPS em Helsinque × banco em São Paulo, ~0,18 s por ida e volta): dados da clínica 3,9 s ·
dashboard 3,2 s · kanban 2,0 s · clientes 2,0 s · /auth/me 1,2 s.
- Painel: telas guardadas 5 min + na aba do navegador; pré-carrega CRM e Clientes; atualiza tudo se o tempo real cair e voltar.
- Servidor: login numa consulta só (eram 3) e guardado 30 s; dados da clínica (18 consultas), cadastros e lista de
  clínicas guardados 30 s; clínica + fuso numa ida só; conexão só é conferida se ficou parada > 30 s.
  Qualquer gravação limpa o cache. Consultas na troca de tela: clínica 18→0, login 3→0, kanban 8→3, dashboard 14→9.
- **Depois** (26/11/2026, mesmo teste; 1ª vez = cache do servidor vencido · trocando de tela):
  dados da clínica 3,1 s · **0,28 s** · dashboard 2,2 s · 2,0 s · kanban 1,0 s · 1,1 s · clientes 1,2 s · 1,0 s ·
  cadastros 1,0 s · **0,26 s** · /auth/me **0,26–0,33 s**. Piso da rede (navegador → VPS, página estática): ~0,26 s.
  No painel, voltar a uma tela já vista abre na hora (cache do navegador) e atualiza por trás.
- Fica para depois: dashboard e `/health` (~2 s, chamado pela barra de situação) ainda dependem da distância até o banco (D126).

## Etapa 33 — Painel no celular (simples e do dia) ✅ (25/11/2026; D127)
Só no celular (tela < 768 px); no computador nada muda.
- **Menu:** sai a barra lateral; entra uma barra embaixo com Início · CRM · Agenda · Mensagens · Clientes.
  No topo: logo, sino, situação da assistente, "Perguntar à assistente" (se liberado) e Sair.
- **Gestão desligada:** Relatórios, Configurações e o botão **Admin geral** somem; abrir o endereço direto mostra
  "Disponível no computador".
- **Agenda:** em vez da semana, a **lista do dia** (abre em hoje, setas ‹ › para outro dia, toque abre a consulta,
  botão + para marcar).
- **CRM:** lista simples com **nome e status** de cada contato, filtro **Hoje** já ligado (consulta hoje ou movimento
  hoje; "Todos" mostra o resto). Toque no nome → conversa; toque no status → **Mover para…** (regras do arrastar, RN-PN-05).
- **Clientes:** só nome e telefone, com botão **Comentar** (registra um comentário novo nas observações; ver e editar
  o histórico fica no computador).

## Etapa 34 — Marcada para menos de 24 h já confirmada ✅ (27/11/2026; D129)
- Marcou ou remarcou (Ísis ou recepção) para dali a menos de 24 h → a consulta já entra **confirmada** e o contato vai
  para **Confirmado** no CRM.
- Não sai lembrete pedindo "1 Confirmar". A mensagem da marcação continua, como comprovante, com
  "✅ Já está confirmada, não precisa confirmar". A Ísis também avisa isso na conversa.
- Configurações › Assistente › Regras da agenda: "Já confirmada se marcada com menos de (horas)" — padrão 24; 0 desliga.

## Etapa 35 — Mensagens por período e por cliente ✅ (27/11/2026; D130)
- Abre nos **últimos 7 dias** (seletor: 7, 30 ou 90); a fila do que ainda vai sair aparece sempre.
- **Cliente:** busca pelo nome/telefone ou clique no nome na lista → tudo o que foi enviado para ele, de qualquer data.
- **Disparos do período:** um cartão por campanha e um para os aniversários, com barra e números (enviadas · entregues ·
  falharam · na fila). Clicar filtra a lista e abre a aba certa ("Não enviadas" se houve falha).

## Etapa 36A — WhatsApp oficial: base ✅ (27/11/2026; D131; branch `whatsapp-oficial`)
- Banco (migration 0035): provedor `waha` (padrão) ou `meta` por clínica + dados da Meta (token e chave secreta cifrados).
- `ClienteMeta` (envio de texto, visto, baixar mídia, testar) com os mesmos métodos do WAHA; a fila, a Ísis e a equipe
  pegam o cliente certo pelo provedor da clínica. Clínica em WAHA segue exatamente o caminho de antes.
- Admin geral (API, só super admin): ver/salvar dados da Meta, testar, trocar o provedor (exige os dados salvos).
  Tela fica para a 36D; receber mensagens pela Meta, para a 36B.

## Etapa 36B — WhatsApp oficial: receber mensagens ✅ (27/11/2026; D131; branch `whatsapp-oficial`)
- Webhook exclusivo da clínica na Meta: `/webhooks/meta/<token>` (o mesmo token opaco do WAHA, D123).
  - GET: a Meta confere o endereço com o token de verificação (funciona antes de trocar o provedor).
  - POST: confere a assinatura `X-Hub-Signature-256` com a chave secreta do app; só aceita eventos do número da clínica.
- Mensagens recebidas (texto, áudio, foto, vídeo, documento, botão) entram no mesmo fluxo do WAHA: agrupar picadas,
  transcrever áudio, Ísis, equipe. Status entregue/lida igual ao D85; **falhou** marca a mensagem automática como
  "falhou" com o motivo da Meta (ou deixa aviso na conversa).
- Trocar para a Meta exige o WAHA desligado e já liga a clínica na Meta; voltar ao WAHA deixa desligada (religa pelo
  caminho de sempre). Ainda sem "visto/digitando" na Meta e sem modelos fora da janela de 24 h (36C).

## Etapa 36C — WhatsApp oficial: modelos e janela de 24 h ✅ (27/11/2026; D131; branch `whatsapp-oficial`)
- Janela aberta (cliente escreveu nas últimas 24 h) → sai o texto de sempre. Fechada → sai o **modelo aprovado** do TemHorario.
- Catálogo fixo de 9 modelos (pt_BR): lembrete (com botões Confirmar · Remarcar · Cancelar), confirmação, remarcação,
  cancelamento, pós-consulta, tratamento e resumo do dia (utilidade); retorno e aniversário (marketing, com "Responda PARAR").
- Admin geral (API): criar na conta da Meta da clínica os modelos que faltam e ver a situação (aprovado, em análise, recusado + motivo).
- Fora da janela: campanha falha com motivo claro (campanha na Meta = 36E); resposta manual da equipe é recusada com
  aviso "espere o cliente escrever ou ligue"; resumo do dia do profissional sai sempre como modelo.
- A conversa do painel mostra o texto do modelo que o cliente recebeu.

---

## Depois da 1ª versão (backlog)
- Mensagens programadas (ex.: férias coletivas) — D24. (Retorno e pós-consulta: Etapa 25.)
- Tags de cliente: novo · recorrente · em tratamento → "volta em X tempo" — D20.
- Forma de captar a data de nascimento — Q21.
- Mais indicadores no Dashboard — Q19.
