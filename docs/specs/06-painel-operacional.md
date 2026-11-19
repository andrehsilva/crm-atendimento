# Spec 06 — Painel da clínica (operacional)

Referência visual: `docs/layouts/01..03` e [spec 11](11-design-visual.md).

## Navegação (barra lateral)
```
[logo] Clínica Dental Rodrigues   ‹
──────────────────────────────
▣ Dashboard
▥ CRM                 ← kanban (imagens 01/02)
◷ Agenda              ← proposta: agenda da semana (imagem 03, coluna do meio)
✉ Mensagens           ← proposta: mensagens enviadas + disparos (imagem 03, coluna direita)
👥 Leads / Clientes
⚙ Configurações       ← spec 07
──────────────────────────────
(foto) André Rodrigues · Secretária
```
> Menu confirmado (D21).

## Dashboard
1ª versão (Q19 — mais itens depois): cartões com **consultas de hoje**, **confirmadas x pendentes**, **conversas precisando de humano**, **leads parados há mais de 24h**, **aniversariantes do dia**, e a lista "próximas consultas de hoje".

## CRM — Kanban (imagens 01/02)
Cabeçalho: "CRM — Arraste os leads entre as colunas para atualizar o status do funil".

### Colunas
> Colunas **provisórias** (D19): a imagem foi só sugestão; não há gestão de orçamento.

| # | Coluna | Cor | Entra quando |
|---|---|---|---|
| 1 | **Novo Contato** | rosa | Primeira mensagem de um telefone desconhecido |
| 2 | **Agendados** | verde | Consulta marcada (Ísis ou recepção) |
| 3 | **Confirmado** | verde | Paciente confirmou (botão do lembrete ou conversa) |
| 4 | **Cancelados** | vermelho | Consulta cancelada |

Cabeçalho da coluna: bolinha colorida + nome + contador. Coluna vazia: ícone de caixa + "Nenhum lead aqui".

### Card do lead
```
              [🤖 Atendimento automático]   ← ou [✋ Atendimento manual] em âmbar
 (avatar) Nome
          telefone formatado
 Procedimento / motivo  (ex.: "Avaliação odontológica geral", "Retorno")
 ───────────────
 [Selo da etapa]                    ⏱ 24d   ← tempo desde que virou lead
 [Parado há 430h]                           ← tempo sem movimento (vermelho acima do limite)
 `iniciou_conversa` ⧉                       ← último evento (copiável)
```
- **Atendimento automático/manual:** se a Ísis está respondendo ou um humano assumiu a conversa.
- **Parado há Xh:** horas desde a última mensagem/mudança de etapa. Acima de 24h (config) fica vermelho.
- **Tags do cliente** (novo · recorrente · em tratamento → "volta em X tempo"): **futuro** (D20), fora da 1ª versão.
- **Último evento** (código): `iniciou_conversa`, `conversando`, `consulta_agendada`, `consulta_confirmada`, `consulta_cancelada`, `consulta_remarcada`, `lembrete_enviado`, `aguardando_humano`.
- Clicar no card abre painel lateral: dados do paciente, histórico de conversa, consultas, botões **Assumir/Devolver para Ísis**, **Marcar consulta**.
- **Arrastar** entre colunas é permitido (é o que diz o cabeçalho). Regras: arrastar para *Agendados* abre o formulário de marcação; arrastar para *Cancelados* pede confirmação e cancela a consulta; demais movimentos só mudam a etapa e ficam no histórico (RN-PN-05).

## Agenda da semana (imagem 03, coluna do meio)
- Título "Agenda desta semana" + resumo "4 ocupados · 236 livres" + setas ‹ › de semana.
- Filtros em pílula: **Todas** + um por especialidade/profissional (cor própria).
- Legenda de status: aguardando confirmação (borda tracejada) · presença confirmada (borda contínua) · bloqueado.
- Grade seg–sáb × horários (passo 30 min), dia de hoje destacado, faixa de almoço hachurada.
- Card: nome do paciente + procedimento. Clique → detalhes e ações.

## Mensagens enviadas (imagem 03, coluna direita)
Feed em cards, mais recente no topo:
```
CONFIRMAÇÃO                         ← tipo em selo colorido (confirmação/cancelamento/remarcação/lembrete/aniversário/programada)
Para Luciana Papini · 21987654321 · 08/10, 09:28
<texto exato enviado>
status: enviada ✓ / entregue ✓✓ / lida / falhou
```
Filtros por tipo e status; lembretes sem resposta destacados (RN-MS-05).

## Tela de demonstração `/demo` (imagem 03)
Três colunas lado a lado: **chat do paciente** (campo "Escreva como se fosse o paciente") · **agenda da semana** · **mensagens enviadas**, mais botão **Reiniciar demonstração**. É o "resultado final na tela" pedido; usada para testar e apresentar.

## Leads / Clientes
Tabela com busca: nome, telefone, data de nascimento, etapa, última consulta, próxima consulta, origem (web/WhatsApp), aceita mensagens (sim/não). Ações: editar, ver histórico. Como a data de nascimento entra no sistema: adiado (Q21).

## Tempo real
`GET /api/clinics/{id}/events` (SSE). Eventos: `appointment.*`, `lead.stage_changed`, `conversation.updated`, `message.created`, `outbound.updated`. Todas as telas acima se atualizam sem recarregar.
