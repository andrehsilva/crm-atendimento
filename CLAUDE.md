# Instruções do projeto Ísis

## Como trabalhamos
- Idioma: **português simples**, sem jargão desnecessário. Quando usar um termo técnico, explique em uma frase.
- Construção **em etapas** (ver `docs/PLANO.md`). Ao fim de cada etapa:
  1. diga em poucas linhas **o que foi feito** e **o que testar** (passo a passo);
  2. **PARE** e espere o usuário dizer **"pode seguir"**.
- Nunca avance de etapa sem o "pode seguir".
- Antes de codar algo novo: conferir se a regra está em `docs/REGRAS-DE-NEGOCIO.md`.
- **Perguntas ao usuário vivem só em `docs/PERGUNTAS.md`** (checklist `- [ ]`). Se surgir uma pergunta nova, ela entra lá, na seção da etapa que ela bloqueia. Quando o usuário responder (no chat ou no arquivo):
  1. preencher `Resposta:`, marcar `[x]` e mover para "✅ Respondidas" com a data e o código Dxx;
  2. registrar a decisão em `docs/DECISOES.md`, atualizar as regras e specs afetadas;
  3. atualizar a linha "Progresso: X de Y respondidas".
- Nunca começar uma etapa enquanto houver pergunta aberta na seção que bloqueia aquela etapa.

## Princípios técnicos (não negociáveis)
- **O que não pode falhar fica no código, não na memória da IA.** Conflito de horário, horário de funcionamento, verificação de telefone, envio de lembrete: tudo validado pelo backend/banco. A Ísis só *pede*; o backend *decide*.
- **Multi-tenant desde o primeiro dia:** toda tabela de negócio tem `clinic_id`; toda consulta filtra por ele.
- **Identidade vem da sessão, nunca do texto do paciente:** o telefone da clínica e o do paciente são injetados pelo canal; as ferramentas do agente não recebem esses valores como argumento.
- Datas sempre com fuso (`timestamptz`), exibidas em `America/Sao_Paulo` (ou fuso da clínica).
- Segredos só no `.env` (nunca no chat, nunca no git). Manter `.env.example` atualizado.

## Estrutura (alvo)
```
backend/   FastAPI + Agno (app/, tests/)
frontend/  React + Vite (painel operacional, chat web, admin)
supabase/  migrations SQL e seed
docs/      plano, specs, regras
```
