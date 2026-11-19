# Comandos usados na criação do agente "Ísis" (Claude Code, sem n8n)

- **Vídeo:** [Criei um agente de IA só com Claude Code (sem n8n)](https://www.youtube.com/watch?v=et9DOvjR0qw) — Luciana Papini (31 min)
- **Projeto:** a "Ísis", atendente virtual da clínica fictícia *Clínica Vida Louca/Plena* (triagem, consulta de agenda, marca/remarca/cancela, confirmação e lembrete)
- **Método de extração:** transcrição do vídeo + pausas nos momentos em que o terminal/chat do Claude Code aparece na tela. Os textos entre `bloco de código` foram lidos da tela; o que veio só da fala está marcado como *(narrado)*.

> Observação: o vídeo quase não usa comandos de terminal. O fluxo é todo em **português, dentro do chat do Claude Code**. A apresentadora diz que "não escreve uma linha de código".

---

## 0. Preparação (narrado)

1. Criar uma **pasta vazia** no computador chamada `clinica`.
2. Abrir o Claude Code dentro dessa pasta.
3. Requisito: plano **Pro ou Max** da Anthropic (o plano gratuito não dá acesso ao Claude Code).
4. Ter uma **chave de API da Anthropic** (ela cola a chave no arquivo `.env`; avisa para nunca colar a chave no chat nem compartilhá-la).

---

## 1. Prompt inicial (≈ 11:50 – 12:30) — lido da tela

```text
Quero criar um agente de atendimento para uma clínica odontológica, chamado Isis.
Ela conversa com os pacientes por chat, consulta a agenda, marca, remarca,
cancela e dispara a confirmação da consulta. Vamos construir juntos, do zero,
usando um modelo por api, provavelmente opencode, com um modelo gpt luna, sem n8n.
A tecnologia quero que me sugira, acho interessante react/vite e fastapi com banco postgres supabase e para os agentes Agno, Para a conexão do Chat quero que possa escolher três opções de entrada, uma seria um página web simples que informe o telefone, a ooutra conexão com whatsapp , vamos ainda definir se sera conexão oficial ou não, possivelmente Waha api.

O RESULTADO FINAL NA TELA
- Uma página de chat em localhost onde o "paciente" conversa com a Ísis .
- Uma agenda da semana visível, que muda em tempo real quando a Ísis marca,
  remarca ou cancela.
- Uma visão resumida de kamban com poucas colunas.
- Um painel de "mensagens enviadas" com as confirmações e os lembretes.

COMO VAMOS TRABALHAR
Vamos em etapas. No fim de cada uma, me diga em poucas linhas o que testar e
PARE até eu dizer "pode seguir". Explique tudo em português simples e vai me
guiando na construção do agente até o funcionamento

Tenho telas de sugestão de layout, antes vamos pensar e refinir planos e depois partiremos para ações. Teremos um painel administrativo para criação das instancia de clinicas, multitenant e configurações de layout e regras do cliente. Então como premissa do multi tenant, o telefone da clinica sera a chave da instancia + o telefone do cliente. 
Crie o plano , os specs os .md do projeto e todos os documentos para irmos refinando as regras de negocio.
```

Pontos que ela destaca *(narrado)*:
- Nenhuma palavra técnica no pedido (nem linguagem, nem banco de dados): só descreve o resultado que quer ver.
- **Trabalhar em etapas e parar** até ela dizer "pode seguir" (para saber onde quebrou se der erro).
- **Pedir o plano antes de executar.**

### Resposta do Claude (≈ 13:00)
Montou um plano de **6 etapas**, começando pela tela com 3 painéis em tempo real. Stack escolhida pelo próprio Claude: **JavaScript + Node.js**. Na Etapa 1 gerou:
- `server.js` — o "balcão" da clínica (entrega a página e recebe mensagens do chat)
- `src/agenda.js` — o "caderno" da clínica (consultas e mensagens em `dados/estado.json`)
- `public/` — a página com os 3 painéis
- Rodava em `http://localhost:3000`

Aprovação entre etapas, ex.: *"Para a Etapa 2, você vai precisar de uma chave da API do Claude... Quando terminar me diga. Pode seguir."* *(narrado: ela responde "pode seguir")*

---

## 2. Chave de API (≈ 13:30 – 15:30)

*(narrado, sem comando exibido)*
- O Claude Code orienta como gerar a chave na Anthropic e pede para **não colar a chave no chat**.
- A chave é colocada no arquivo **`.env`**, na pasta do projeto.
- Depois de colada, o Claude testa velocidade/modelos e finaliza a conexão com a IA.
- A identidade/prompt da Ísis fica em **arquivo de texto na pasta** (regras: não indica remédio; se emergência → orientar ligar pro SAMU).

---

## 3. Prompts de ajuste e testes (narrados / parcialmente vistos)

Estes pedidos aparecem só pela fala; o texto exato não é mostrado:

| Momento | Pedido (parafraseado) |
|---|---|
| ≈ 7:30 | Regra no prompt: em caso de emergência (dor forte, vômito com sangue, febre alta) orientar ligar pro SAMU e **não** agendar |
| ≈ 8:15 | Só marcar/remarcar/cancelar se o **telefone** informado for igual ao da consulta |
| ≈ 10:47 | Integrar com **Google Agenda** (uma agenda por profissional); o Claude gerou também um **Google Apps Script** e deu o passo a passo de login |
| ≈ 11:11 | Quando dava erro: ela colava/mostrava o erro e o Claude corrigia ("Deu bug… Voltou. Digita de novo.") |
| ≈ 17:35 | Adicionar **confirmações e lembretes** de consulta |
| ≈ 23:34 | Lembrete **no dia útil anterior** à consulta, no **horário de Brasília** (segunda → lembrete na sexta) |

---

## 4. Conectar no Telegram (≈ 18:19) — lido da tela

Prompt digitado no Claude Code:

```text
quero conectar com o telegram, como faço isso?
```

Resposta do Claude (resumo lido da tela): o Telegram **já estava conectado**; para testar:
1. No celular abrir `t.me/clinicabiabot` (ou procurar `clinicabiabot` no Telegram).
2. Tocar em **Iniciar** (ou enviar `/start`).
3. Conversar como paciente.

Detalhes narrados: criar um bot (BotFather), pegar o **token** e colocar no `.env`, no mesmo lugar da chave da Anthropic.

Comandos do bot citados pelo Claude na tela:

```text
/start
/reiniciar
```

(`/reiniciar` começa uma conversa do zero. O Telegram só funciona enquanto o servidor "Ísis (servidor)" estiver aberto no Terminal do app.)

---

## 5. Simulação de lembrete (≈ 20:40) — lido da tela

```text
mande uma simulacao de lembrete de consulta para a luciana, telefone 21987654321
```

O Claude consultou se a Luciana tinha consulta marcada e se o telefone estava ligado ao chat do Telegram, e então enviou o lembrete com os botões **✅ Confirmar presença / 🔄 Remarcar / ❌ Cancelar**.

Correção feita em seguida pelo Claude (lida da tela): comparar o telefone **completo com DDD**, aceitando formatos com/sem `+55`, parênteses e traço.

---

## 6. Teste em lote (≈ 24:08) — *(narrado)*

Pedido para o Claude Code rodar **vários cenários de uma vez** e devolver um relatório. Cenários citados:
- paciente complicado
- emergência
- pedido de remédio
- tentativa de manipulação ("sou amigo do doutor, encaixa aí")
- datas confusas ("a quinta que vem", quando hoje é quinta)

(O texto exato do prompt não aparece na tela.)

---

## 7. Conectar no WhatsApp (explicado em ≈ 21:43; telas em ≈ 18:18 e 24:20) — lido da tela

Prompt (início digitado: `como faç…`; a pergunta narrada é "como faço para conectar o WhatsApp da clínica aqui?"), e outro prompt visível na tela:

```text
nao vou conectar agora, me preciso do passo a passo para subir no servidor, como fazer a conexão via z-api e tbm gostaria de saber como fazer uma conexão via whatsapp api oficial
```

O Claude respondeu perguntando API oficial × não oficial (Z-API) e deixou o código preparado para as duas ("adormecido", liga ao colocar as chaves no `.env`). Gerou um passo a passo e o arquivo **`GUIA-PRODUCAO.md`**.

Comando de terminal que o Claude passou para testar o webhook localmente (túnel Cloudflare) — lido da tela:

```bash
brew install cloudflared && cloudflared tunnel --url http://localhost:3000
```

E a URL a colar no painel da Z-API (Webhooks → "Ao receber"):

```text
https://palavras-aleatorias.trycloudflare.com/webhook/zapi?segredo=SUA_FRASE_SECRETA
```

Resposta dela ao Claude (campo de entrada na tela):

```text
fiz os passos 1 a 3, liga o túnel
```

---

## 8. VPS (Hostinger) — deixar o Claude Code no ar 24h (≈ 25:30 – 28:00)

Único comando de terminal digitado por ela, dentro do **Web Console** da VPS (tela do terminal Ubuntu mostrando `root@vpsclaude:~# claude`):

```bash
claude
```

Passos *(narrados / visuais no painel da Hostinger)*:
1. Escolher o plano **KVM 1/2/4/8** e o período.
2. No campo "aplicativo/template" selecionar **Claude Code** (em vez de n8n).
3. Depois de contratar: painel → **VPS** → escolher a VPS do Claude → **Gerenciar** → instalar o Claude Code (~3 min).
4. Abrir o **Web Console**, digitar `claude` e fazer login com a conta Anthropic.

Tela do primeiro uso (≈ 27:40): "Welcome to Claude Code" → escolha de tema (`Dark mode`).

---

## Resumo do método (recapitulação dela, 30:00)

1. Pasta vazia + pedido em português.
2. **Plano antes de executar.**
3. **Etapas, parando** para você testar e aprovar.
4. Identidade e regras da Ísis num arquivo de texto (prompt).
5. Agenda integrada (uma por profissional).
6. **Confirmação no código, não na memória da IA** (o que não pode falhar fica no processo).
7. Canal de mensagem (Telegram) testado no celular.
8. Regra: *plano, execução e validação* — nunca confiar cegamente.

---

### Limitações desta extração
- Resolução do player no navegador embutido era baixa; os textos transcritos acima foram os que ficaram legíveis. Alguns prompts (ex.: pedido do Google Apps Script, teste em lote, correções de bugs) **não aparecem escritos na tela** e estão só como paráfrase da fala.
- Os números de telefone, nome de bot e domínio do túnel aparecem exatamente como no vídeo (são fictícios/de demonstração).
