# Spec 05 — Confirmações e lembretes

## Fila de saída (`outbound_messages`)
Toda mensagem automática vira uma linha **antes** de ser enviada:
`clinic_id, appointment_id, patient_id, kind (confirmacao|lembrete|cancelamento|remarcacao), channel, scheduled_for, status, attempts, payload, external_id, error`.

## Quando gerar
| Evento | Gera |
|---|---|
| Consulta marcada | `confirmacao` agora + `lembrete` no horário calculado (RN-MS-02/03) |
| Remarcada | `remarcacao` agora; cancela lembretes antigos; cria novo lembrete |
| Cancelada | `cancelamento` agora; cancela lembretes pendentes |

## Cálculo do lembrete
```
dia_lembrete = dia útil anterior à consulta (pula sábado, domingo e feriados da clínica)
hora = config.lembrete_hora (09:00) no fuso da clínica
se dia_lembrete/hora já passou → não cria (RN-MS-03)
ajusta para fora da janela de silêncio (RN-MS-09)
```

## Envio
- APScheduler a cada 1 min: pega `status='agendada' AND scheduled_for <= agora` com `FOR UPDATE SKIP LOCKED` → envia pelo canal da conversa → `enviada` / `falhou` (até 3 tentativas).
- Webhooks de status do WhatsApp atualizam para `entregue`/`lida`.
- Cada mudança publica evento para o painel "Mensagens enviadas".

## Relógio simulado (desenvolvimento)
Variável `FAKE_NOW` + botão no painel "avançar para o horário do próximo lembrete" — testar sem esperar.

## Textos (templates editáveis por clínica)
```
Confirmação: Olá, {nome}! Sua consulta de {procedimento} com {profissional} está marcada para {dia_semana}, {data} às {hora}. Endereço: {endereco}.
Lembrete:    Olá, {nome}! Lembrando da sua consulta amanhã ({dia_semana}, {data}) às {hora} com {profissional}. Responda: 1 Confirmar · 2 Remarcar · 3 Cancelar
```
