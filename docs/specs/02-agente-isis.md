# Spec 02 — Agente Ísis

## Montagem (Agno)
- **Modelo:** OpenCode Go, `gpt-6-luna`, pela **Responses API** (classe `OpenAIResponses` do Agno). Configuração no `.env`:
  ```
  LLM_PROVIDER=opencode-go
  LLM_BASE_URL=https://opencode.ai/inference/go/openai/v1
  LLM_API_KEY=            # chave do OpenCode (nunca no chat/git)
  LLM_MODEL=gpt-6-luna
  LLM_API_STYLE=responses # responses | chat_completions (para trocar de modelo/provedor)
  ```
  Cabeçalhos: `x-opencode-session` = id estável da conversa; `User-Agent: isis-atendimento/<versão>`. Na Etapa 4 o primeiro teste é listar `/models` e mandar um "olá" para confirmar URL e ID.
- Limites do plano Go: cota em dólar por modelo com janelas de 5 h / semana / mês. Ao estourar → mensagem padrão ao paciente + handoff para humano + alerta no painel.
- **Instruções = 3 camadas**, montadas a cada mensagem:
  1. `prompts/isis.md` — persona e regras fixas (RN-AT), editável em texto.
  2. Bloco da clínica (do banco): nome, endereço, horários, profissionais, procedimentos, políticas, tom.
  3. Bloco do momento: data/hora atual por extenso no fuso da clínica + **calendário dos próximos 14 dias** (dia da semana ↔ data), nome do paciente se conhecido, consultas futuras dele.
- **Memória:** histórico da conversa salvo no Postgres (storage do Agno), `session_id = clinic_phone:patient_phone`, últimas ~20 mensagens no contexto.

## Ferramentas
Todas recebem `clinic_id` e `patient_id` **do contexto da sessão** (não são parâmetros visíveis ao modelo).

| Ferramenta | Parâmetros (do modelo) | Faz |
|---|---|---|
| `info_clinica()` | — | Endereço, horário, procedimentos, profissionais |
| `horarios_livres(procedimento, data_inicio, data_fim, profissional?, turno?)` | | Até N slots válidos (já respeitam todas as RN-AG) |
| `minhas_consultas()` | — | Consultas futuras do paciente |
| `salvar_nome(nome_completo)` | | Cadastra/atualiza nome do paciente |
| `preparar_agendamento(slot_id \| dados)` | | Valida e devolve **resumo + token** (não grava) |
| `confirmar_acao(token)` | | Grava marcar/remarcar/cancelar previamente preparado |
| `preparar_remarcacao(consulta_id, novo_slot)` | | Idem, para remarcar |
| `preparar_cancelamento(consulta_id, motivo?)` | | Idem, para cancelar |
| `chamar_humano(motivo)` | | Handoff (RN-AT-06) |

**Dois passos (preparar → confirmar):** garante RN-AG-11 no código. O token expira em 10 min e é revalidado na confirmação (o horário pode ter sido tomado no meio-tempo).

## Fluxo de uma mensagem
```
canal → roteador (clínica, paciente) → conversa em handoff? ─sim→ só grava, avisa painel
                                                └não→ Ísis.run(texto) → ferramentas → resposta
→ grava mensagens → publica evento (SSE) → canal envia resposta
```

## Respostas determinísticas (sem IA)
- Botões do lembrete (Confirmar/Remarcar/Cancelar) → tratados por código. "Remarcar"/"Cancelar" abrem conversa com a Ísis já com o contexto.
- Saudação inicial da página web: texto fixo da config.

## Guardrails
- Se a ferramenta devolver erro de regra, a Ísis explica em linguagem simples e oferece alternativa.
- Limite de chamadas de ferramenta por mensagem (ex.: 6) e timeout do modelo; em falha → mensagem padrão + contador para handoff.
- Logs de cada execução (entrada, ferramentas chamadas, saída) para depuração no painel.
