# Spec 07 — Configurações da clínica e admin da plataforma

Referência visual: `docs/layouts/04..07`.

## A. Configurações (dentro do painel da clínica)
Cabeçalho: "Configurações — Gerencie o perfil, horários e procedimentos da clínica". Abas em pílula:

### Perfil (imagem 06)
- **Senha de acesso:** senha atual, nova (mín. 8), confirmar, "Mostrar senhas", botão Trocar senha (habilita só quando válido). Texto: esqueceu → "Esqueci minha senha" no login.
- **Logo da clínica:** pré-visualização quadrada + "Alterar foto" (PNG, mín. 200×200).
- **Nome da clínica:** campo + Salvar (aparece no topo da barra lateral).
- **A acrescentar (proposta):** telefone da clínica (somente leitura — é a chave), endereço, telefone de urgência, cor principal, nome/avatar da assistente.

### Horários de Funcionamento (imagem 07)
- Uma linha por dia (seg–sáb, e domingo): liga/desliga, início "até" fim, Salvar por linha.
- São os horários **da clínica**. Profissionais herdam por padrão; exceções por profissional ficam em "Profissionais" (Q22).
- Intervalo de almoço: a imagem não tem; proposta de adicionar "+ pausa" por dia (Q22).

### Procedimentos (imagem 05)
- "N procedimentos cadastrados" + **+ Novo Procedimento**.
- Item: liga/desliga (ativo para a Ísis oferecer), nome, descrição curta, expandir (⌄), editar, excluir.
- Ao expandir/editar: **duração (min)**, preço (opcional, Q9), profissionais que fazem, "Ísis pode agendar sozinha?" (ex.: *Atendimento de urgência* pode ser só por humano).

### Mensagens (imagem 04) — ver [spec 10](10-disparos.md)
- **Mensagem de aniversário:** ativar, texto com variáveis, contador 0/1000, prévia com dados desta clínica, Salvar.
- **Mensagens programadas:** campanhas e mensagens automáticas.
- **Mensagens da agenda:** textos de confirmação, lembrete, cancelamento, remarcação.

### Usuários
Lista de usuários da clínica (nome, e-mail, papel admin/secretária), convidar, desativar.

### Abas a acrescentar (proposta)
- **Profissionais:** nome, especialidade, cor na agenda, procedimentos, exceções de horário, férias.
- **Assistente (Ísis):** nome, tom, regras (antecedência, cancelamento, limite de consultas), "sobre a clínica".
- **Canais** (D79, D80): status e número do WhatsApp (toda a equipe vê); o administrador da clínica mostra o QR, reinicia a sessão e pausa/retoma a Ísis no WhatsApp. Servidor, sessão e webhook ficam no Admin geral.

## B. Admin da plataforma (super-admin)
Mesmo visual, menu próprio: **Clínicas** · **Uso** · **Configurações da plataforma**.
- Lista de clínicas: logo, nome, telefone (chave), status, canal conectado, conversas/mês.
- **Criar clínica:** nome, telefone (E.164, único), slug, fuso, primeiro usuário admin (e-mail). Gera o ambiente com procedimentos e mensagens padrão.
- Suspender/reativar; "entrar como" a clínica para suporte (registrado em log).

## Regras
- Mudanças de regra valem para **novas** ações; não alteram consultas já marcadas.
- Desligar um dia/horário com consultas já marcadas → aviso listando as afetadas.
- Desligar um procedimento → Ísis para de oferecer; consultas existentes continuam.
