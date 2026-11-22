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

## Envio (implementado na Etapa 6)
- Processo em segundo plano dentro do backend (`app/mensagens/agendador.py`), a cada 30 s: gera os aniversários do dia e envia a fila vencida (`status='agendada' AND scheduled_for <= agora`), uma por vez, com `FOR UPDATE SKIP LOCKED`.
- Envia pelo WAHA da clínica (`whatsapp_instances`), com "visto" + "digitando…". Sucesso → `enviada`; falha → tenta de novo em alguns minutos, até 3 vezes → `falhou`.
- Travas no código: silêncio 21h–08h (RN-MS-09), 20/min e 300/dia por clínica (RN-DP-07), PARAR/SAIR só afeta aniversário (RN-DP-04).
- A mensagem enviada também entra na conversa do paciente: aparece no painel e a Ísis vê no histórico (RN-DP-09).
- **Modo de teste (ENV=dev):** só envia para os telefones de `ENVIO_SOMENTE_PARA`; os demais ficam `cancelada` com o motivo. Os dados de exemplo têm telefones inventados que podem ser de pessoas reais.
- Status `entregue`/`lida` pelo WhatsApp: Etapa 20 (D85).

## Resposta ao lembrete (sem IA)
- "1" (ou "confirmo") → consulta `confirmada` e card em *Confirmado*, com resposta fixa. Só vale se o lembrete for a **última mensagem enviada** na conversa e tiver no máximo 72 h.
- "2" e "3" → vão para a Ísis, que vê o lembrete no histórico e remarca/cancela em dois passos.
- "PARAR"/"SAIR" → desliga os disparos (aniversário).

## Relógio simulado (desenvolvimento)
Na tela **Mensagens**: "Avançar até o próximo lembrete" adianta o relógio do envio até o horário do lembrete e envia a fila na hora. "Voltar ao horário real" desfaz. O ajuste vale só para o envio automático e some quando o backend reinicia.

## Textos (templates editáveis por clínica)
```
Confirmação: Olá, {nome}! Sua consulta de {procedimento} com {profissional} está marcada para {dia_semana}, {data} às {hora}. Endereço: {endereco}.
Lembrete:    Olá, {nome}! Lembrando da sua consulta amanhã ({dia_semana}, {data}) às {hora} com {profissional}. Responda: 1 Confirmar · 2 Remarcar · 3 Cancelar
```
