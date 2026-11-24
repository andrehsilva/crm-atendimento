# Guia de produção da Ísis

Como colocar a Ísis no ar no **seu servidor (o mesmo do WAHA)**, com HTTPS (D37). Siga na ordem.
Usa **Easypanel**? Faça o passo 1 e os passos 5–11, e troque os passos 2, 3 e 4 pelo **passo 12**.
Cada passo diz **o que fazer** e **como conferir** que deu certo.

> Termos: **container** = um "programa empacotado" que o Docker roda isolado. **Proxy** = o porteiro que recebe
> as visitas do site na porta 443 (HTTPS) e repassa para o programa certo.

---

## 0. Antes de começar (checklist)

- [ ] Servidor Linux com **Docker** e **Docker Compose** (`docker compose version` responde).
- [ ] Um **domínio** para o painel, ex.: `isis.seudominio.com.br`, apontando (registro **A**) para o IP do servidor.
- [ ] Acesso ao **supabase.com** e ao painel do **WAHA**.
- [ ] O código no servidor: `git clone <seu repositório> isis && cd isis`.

## 1. Banco de dados: um projeto Supabase só de produção

**Por quê:** o banco de desenvolvimento tem a clínica demo e os cenários de teste, com telefones inventados.
Em produção as mensagens automáticas vão para os pacientes de verdade — não podem cair nesses números.

1. No supabase.com: **New project**, região **South America (São Paulo)**, senha só com letras e números.
2. **Connect › Session pooler**: copie a connection string (porta **5432**). Ela funciona em servidores só com IPv4.
   - ⚠️ **Não** use o *Transaction pooler* (porta 6543): ele não aceita o tempo real do painel.
3. **Project Settings › API Keys**: copie a chave *publishable* e a *secret*.
4. **Authentication › URL Configuration**:
   - *Site URL*: `https://isis.seudominio.com.br`
   - *Redirect URLs*: adicione `https://isis.seudominio.com.br/redefinir-senha`
5. **Authentication › Emails › SMTP Settings**: configure um serviço de e-mail próprio (ex.: Resend, Brevo, Amazon SES).
   Sem isso, o "Esqueci minha senha" fica limitado a poucos e-mails por hora.
6. **Plano:** para backup diário automático, use o plano **Pro** (ver passo 9).

**Conferir:** a tela *Connect* mostra a região `sa-east-1`.

## 2. Arquivo de segredos do backend

```bash
cp backend/.env.producao.example backend/.env
nano backend/.env
```

Preencha tudo (os comentários do arquivo explicam cada linha). Pontos de atenção:

- `ENV=prod` — liga as proteções de produção.
- `FRONTEND_ORIGIN` e `PUBLIC_BASE_URL` = `https://isis.seudominio.com.br` (com **https**).
- `WAHA_WEBHOOK_HMAC_KEY`: gere um segredo **novo** (não reutilize o de desenvolvimento):
  `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`
- `IA_CHAVE_MESTRA`: gere uma **nova** (não reutilize a de desenvolvimento) e guarde uma cópia em lugar seguro:
  `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
  Ela criptografa as chaves de IA das clínicas; se mudar ou se perder, cada clínica precisa colar a chave de novo.
- **Nunca** coloque `CHAT_TESTE=true` em produção: o chat de teste deixa qualquer pessoa ler conversas digitando um telefone.

**Proteção automática:** em `ENV=prod` o backend **se recusa a subir** se faltar algo obrigatório, se os endereços não
forem `https://`, se ainda apontarem para `localhost`/túnel, ou se o segredo do webhook for curto. O log diz o motivo.

## 3. Escolher o modo do HTTPS

```bash
cp .env.producao.example .env
nano .env
```

Veja se as portas 80 e 443 do servidor já estão ocupadas (por exemplo, pelo proxy do WAHA):

```bash
sudo ss -ltnp | grep -E ':(80|443) '
```

### Modo A — portas livres (mais simples)

```
ENDERECO_SITE=isis.seudominio.com.br
PORTA_HTTP=80
PORTA_HTTPS=443
```

O Caddy (dentro do container `web`) tira e renova o certificado HTTPS sozinho.

### Modo B — já existe um proxy (Nginx/Traefik) nas portas 80/443

```
ENDERECO_SITE=:80
PORTA_HTTP=127.0.0.1:8080
PORTA_HTTPS=127.0.0.1:8443
```

E no proxy que já existe, crie o site `isis.seudominio.com.br` repassando para `http://127.0.0.1:8080`.
Exemplo para **Nginx** (com o certificado do próprio Nginx/Certbot):

```nginx
server {
    server_name isis.seudominio.com.br;
    listen 443 ssl;
    # ssl_certificate ... (Certbot preenche)

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_buffering off;          # tempo real do painel (SSE)
        proxy_read_timeout 1h;
    }
}
```

## 4. Criar as tabelas e subir

```bash
docker compose build
docker compose run --rm backend python scripts/migrar.py     # cria/atualiza as tabelas
docker compose up -d
docker compose ps                                              # os 2 serviços "running"/"healthy"
```

**Conferir:**
- `curl https://isis.seudominio.com.br/health` → `"status":"ok"`, `"env":"prod"`, `"chat_teste":false`.
- Abrir `https://isis.seudominio.com.br` → tela **Entrar**.
- `https://isis.seudominio.com.br/docs` → deve mostrar a tela do painel, **não** a documentação da API (desligada em produção).

Se o backend não subir: `docker compose logs backend` mostra a lista do que falta no `.env`.

## 5. Sua conta de super admin

```bash
docker compose exec backend python scripts/usuarios.py super-admin voce@seudominio.com.br "Seu Nome"
```

Anote a senha provisória (aparece uma vez). Entre no painel e crie a sua senha.

## 6. Primeira clínica e WhatsApp

1. **Admin geral › Nova clínica** (telefone, nome da assistente, 1º dentista, admin da clínica).
2. Na clínica: aba **WhatsApp** → ligar a sessão do WAHA (ou criar uma nova e ler o QR code).
3. Clique em **Apontar webhook**: a sessão passa a mandar as mensagens para `https://isis.seudominio.com.br/webhooks/waha`,
   assinadas com o `WAHA_WEBHOOK_HMAC_KEY`.
4. **Conferir:** mande "oi" de outro celular → a assistente responde; a conversa aparece no CRM.

> Ao apontar o webhook, a sessão **deixa** de mandar mensagens para o endereço antigo (ex.: o n8n).

## 7. IA de cada clínica (D42–D46)

Cada clínica cadastra a **própria chave** (Google, OpenAI, OpenCode ou OpenRouter) em Configurações › Assistente, com o botão
"Testar conexão". Clínica sem chave fica com a assistente **desligada** (as conversas vão para a equipe).
A chave do `backend/.env` (`LLM_*`) é a **chave da plataforma**: só vale para as clínicas em que o admin geral marcar
"Usar a chave da plataforma" (Admin geral › clínica › IA), para teste grátis ou demonstração.

⚠️ O OpenCode Go foi feito para ferramentas de programação e monitora uso fora desse padrão: para a chave da plataforma
atender pacientes de verdade, use uma API paga por uso (OpenCode Zen ou OpenAI direto).

Depois: `docker compose up -d backend` e rode `curl "https://isis.seudominio.com.br/health?ia=true"` → `"ia":{"status":"ok"...}`.

## 8. Atualizar para uma versão nova

```bash
git pull
docker compose build
docker compose run --rm backend python scripts/migrar.py
docker compose up -d
```

As migrations só aplicam o que é novo; rodar de novo não faz mal.

## 9. Backup

- **Supabase Pro:** backup diário automático (7 dias). Recomendado para produção.
- **Cópia própria (extra, qualquer plano)** — um arquivo por dia, guardando os últimos 14:

```bash
# /etc/cron.d/isis-backup  (troque a connection string pela do Session pooler)
0 3 * * * root docker run --rm -v /var/backups/isis:/b postgres:17 \
  sh -c 'pg_dump "postgresql://postgres.SEU_PROJETO:SENHA@aws-0-sa-east-1.pooler.supabase.com:5432/postgres" -Fc -f /b/isis-$(date +\%F).dump' \
  && find /var/backups/isis -name '*.dump' -mtime +14 -delete
```

Teste a restauração uma vez num projeto Supabase vazio (`pg_restore`), para ter certeza de que o backup serve.

## 10. Acompanhar no dia a dia

- **Logs:** `docker compose logs -f backend` (erros da IA, do WhatsApp e do envio de lembretes aparecem aqui).
- **Painel › Admin geral › Uso:** conversas, respostas da IA, tempo médio e **falhas da IA** por clínica.
- **Monitor externo:** cadastre `https://isis.seudominio.com.br/health` num serviço de monitoramento gratuito
  (ex.: UptimeRobot) para ser avisado se o sistema cair.
- **Bateria de cenários:** depois de mudar o prompt ou o modelo de IA, rode no ambiente de desenvolvimento
  `uv run python scripts/cenarios.py` e leia o `docs/RELATORIO-CENARIOS.md`.

## 11. Cuidados que continuam valendo

- **Um processo só no backend.** O envio de lembretes e o tempo real do painel rodam dentro dele. Não aumente o
  número de *workers* nem rode duas cópias do container `backend`: os lembretes sairiam em dobro.
- **WhatsApp não oficial (WAHA) tem risco de bloqueio do número.** Lembretes e aniversários para quem nunca escreveu
  para a clínica aumentam esse risco. O sistema já limita 20 mensagens/min e 300/dia por clínica e respeita 21h–08h.
- **LGPD:** o sistema guarda telefone, nome, consultas e conversas dos pacientes. O banco fica no Brasil (São Paulo).
  Combine com cada clínica o aviso de privacidade ao paciente e quem pode acessar o painel.
- **Chat de teste e rotas de desenvolvimento** (`/api/web/...`, `/api/dev/...`) ficam desligados em produção.
- **Segredos** só no `backend/.env` do servidor. Se algum vazar, troque na origem (Supabase, WAHA, IA) e no `.env`.

## 12. Publicar com Easypanel (no lugar dos passos 2, 3 e 4) — um serviço só

No Easypanel a Ísis roda num **único serviço App**: o `Dockerfile` da raiz compila o painel e o backend entrega
as telas e a API no mesmo endereço. Domínio e HTTPS ficam com o Easypanel. (O `docker-compose.yml`, com Caddy,
continua valendo para quem não usa Easypanel.)

1. **DNS:** registro **A** do subdomínio (ex.: `isis.seudominio.com.br`) → IP da VPS
   (ou use o endereço temporário que o Easypanel gera).
2. **Supabase › Authentication › URL Configuration:** em *Redirect URLs* inclua `https://<endereço>/redefinir-senha`.
3. **Easypanel › projeto › + Serviço › Aplicativo** (ex.: `crm-atendimento`):
   - *Fonte* › **Git**: `https://github.com/andrehsilva/crm-atendimento.git`, ramo `main`, caminho de build `/`.
   - *Construção* › **Dockerfile**, arquivo `Dockerfile`.
   - *Domínios*: o subdomínio, **porta 8000**, HTTPS ligado.
   - **Uma réplica só** (lembretes e tempo real rodam dentro do processo).
4. **Ambiente** (nunca no git):
   - `ENV=prod`; `FRONTEND_ORIGIN` e `PUBLIC_BASE_URL` = `https://<endereço>`; `SITE_BASE_URL=https://<endereço>/site`.
   - `DATABASE_URL` do **Session pooler** (porta 5432): a VPS costuma ter só IPv4 e o endereço direto `db.….supabase.co` só tem IPv6.
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `LLM_*`.
   - `IA_CHAVE_MESTRA`: se o banco já tem clínicas com chave de IA, use **a mesma** de antes (outra deixa as chaves ilegíveis).
   - **No serviço do WAHA**, defina `WAHA_API_KEY` fixa (sem ela o WAHA gera uma chave nova a cada reinício e tudo passa a dar
     "401"). Pode ser no formato `sha512:<hash>`; aqui vai sempre a chave original. Painel do WAHA: `WAHA_DASHBOARD_USERNAME`/`PASSWORD`.
   - `WAHA_API_URL` (no mesmo Easypanel pode ser `http://<projeto>_<serviço-do-waha>:3000`), `WAHA_API_KEY`,
     `WAHA_WEBHOOK_HMAC_KEY` (32+ caracteres) e `MENSAGENS_AUTOMATICAS`. Nunca `CHAT_TESTE=true`.
5. **Implantar.** Se não subir, a aba *Logs* lista o que falta.
6. **Tabelas:** no *Console* do serviço: `python scripts/migrar.py` (aplica só o que for novo).
   Super admin (se for banco novo): `python scripts/usuarios.py super-admin voce@seudominio.com.br "Seu Nome"`.
7. **WhatsApp:** Admin geral › clínica › WhatsApp › **Apontar webhook** (passa a ser `https://<endereço>/webhooks/waha`).
8. **Atualizar versão:** `git push` na `main` + **Implantar** (ou o deploy automático). Depois, `migrar.py` no Console.

> ⚠️ **Mesmo banco do desenvolvimento:** dois backends ligados no mesmo banco mandam lembretes **em dobro**.
> Com a VPS no ar, rode o backend local com `MENSAGENS_AUTOMATICAS=false` (ou deixe-o desligado). E o banco de
> desenvolvimento tem a clínica de demonstração com telefones inventados: comece a VPS com `MENSAGENS_AUTOMATICAS=false`
> e só ligue depois de conferir a fila de mensagens.

**Conferir:** os mesmos testes do passo 4 (`/health` com `"env":"prod"` e `"chat_teste":false`, tela Entrar, `/docs` sem a API).

## Checklist final antes do 1º cliente

- [ ] Projeto Supabase só de produção, Session pooler, redirect `/redefinir-senha` e SMTP configurados.
- [ ] `backend/.env` completo, `ENV=prod`, segredo do webhook novo; backend sobe sem erro.
- [ ] HTTPS funcionando; `/health` com `"env":"prod"` e `"chat_teste":false`; `/docs` sem documentação da API.
- [ ] Super admin criado com senha própria.
- [ ] Clínica criada, WhatsApp ligado, webhook apontado; "oi" de outro celular é respondido.
- [ ] **IA trocada para API paga por uso (D36).**
- [ ] Backup configurado e restauração testada uma vez.
- [ ] Monitor do `/health` cadastrado.
