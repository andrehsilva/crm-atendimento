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

## Etapa 22 — Convênios — 🔨 em construção (D92–D95)
- Configurações: lista de convênios que a clínica atende.
- Só no primeiro contato, a Ísis pergunta "convênio ou particular?"; com lista, confere o nome; sem lista, só registra sim/não.

## Etapa 23 — Resumo do dia para o profissional — ⏳ esperando respostas (Q86–Q88)
De manhã (horário ajustável), o profissional recebe no WhatsApp pessoal a grade do dia: horários, pacientes, procedimentos e quem confirmou.

---

## Depois da 1ª versão (backlog)
- Mensagens programadas (ex.: férias coletivas) e automações (retorno, pós-consulta) — D24.
- Tags de cliente: novo · recorrente · em tratamento → "volta em X tempo" — D20.
- Forma de captar a data de nascimento — Q21.
- Mais indicadores no Dashboard — Q19.
