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

## Etapa 9 — Outros segmentos e personalização — 🔨 em andamento
**Por quê:** vender a Ísis também para médicos, fisioterapeutas, psicólogos, estética e outros negócios com agenda (D38–D41).

- **9A — Segmentos e palavras:** ✅ feito e testado (20/11/2026, clínica de Psicologia). Segmento por clínica (escolhido ao criar no admin geral, editável no Perfil); palavras ajustáveis
  (profissional / cliente / atendimento); procedimentos iniciais por segmento; a assistente, as mensagens automáticas e as telas
  usam as palavras da clínica; urgências e "o que a assistente não é" por segmento; lembrete discreto.
- **9B — Aparência:** 🔨 em andamento. Logo e cor principal por clínica (Configurações › Perfil), aplicadas no painel.

**O que testar:** criar uma clínica de Psicologia no admin geral, conversar no chat de teste e conferir que a assistente fala
em "sessão" e "psicólogo(a)", que o lembrete não cita o procedimento e que as telas trocam as palavras.

## Etapa 10 — IA de cada clínica e controle de gastos — ⏳ liberada (D42–D46), começa depois da 9B
Cada clínica cadastra a própria chave (Google, OpenAI, OpenCode ou OpenRouter), escolhe o modelo, acompanha tokens e custo
estimado e define um teto mensal. Substitui a D36 (IA paga por uso antes do 1º cliente).
- **10A — Chave e modelo:** chave criptografada por clínica, provedores Google/OpenAI/OpenCode/OpenRouter, "Testar conexão", assistente desligada sem chave, opção "usar a chave da plataforma" no admin geral.
- **10B — Uso e teto:** tokens por resposta, tabela de preços e cotação no admin geral, tela "Uso da IA", teto mensal com aviso aos 80% e pausa aos 100%.

---

## Depois da 1ª versão (backlog)
- Mensagens programadas (ex.: férias coletivas) e automações (retorno, pós-consulta) — D24.
- Tags de cliente: novo · recorrente · em tratamento → "volta em X tempo" — D20.
- Convênios — Q10. Forma de captar a data de nascimento — Q21.
- Mais indicadores no Dashboard — Q19.
