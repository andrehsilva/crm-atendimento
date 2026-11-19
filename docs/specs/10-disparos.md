# Spec 10 — Disparos de mensagens (aniversário, programadas e campanhas)

Referência visual: `docs/layouts/04-config-mensagens-aniversario.png`.

Disparo = mensagem que **a clínica inicia** (não é resposta a uma conversa). Todos usam a mesma fila de saída da [spec 05](05-confirmacoes-lembretes.md) e aparecem no painel **Mensagens enviadas**.

## Tipos

| Tipo | Gatilho | Exemplo | MVP? |
|---|---|---|---|
| **Aniversário** | Todo dia, pacientes com aniversário hoje | "Olá, {nome}! Hoje é um dia especial..." | ✅ |
| **Programada única** | Data/hora escolhida + público filtrado | "Férias coletivas de 20/12 a 05/01" | 🟡 depois (D24) |
| **Recorrente / automação** | Regra baseada em tempo | Retorno 6 meses após limpeza; pós-consulta no dia seguinte; lead parado há 3 dias | 🟡 depois |

## Mensagem de aniversário (imagem 04)
- Caixa "Enviar mensagem no aniversário dos clientes" (liga/desliga).
- Texto: "Todo dia, o sistema envia a mensagem pelo WhatsApp a quem faz aniversário e tem data de nascimento cadastrada. Cada cliente recebe uma vez por ano."
- Editor com variáveis `{nome}` (primeiro nome) e `{clinica}`, contador `160/1000`, **prévia com os dados desta clínica**, botão Salvar (habilita só se mudou).
- Horário de envio: config (padrão 09:00, Q23).

## Mensagens programadas (depois da 1ª versão — D24)
Lista + botão "+ Nova mensagem". Cada mensagem:
| Campo | Detalhe |
|---|---|
| Nome interno | "Aviso de recesso" |
| Texto | Variáveis `{nome}`, `{clinica}`, `{proxima_consulta}` (se houver) + prévia |
| Público | Todos os pacientes · por etapa do CRM · por procedimento já feito · sem consulta há X meses · aniversariantes do mês · lista manual |
| Quando | Agora · data/hora · recorrente (Q24) |
| Canal | WhatsApp da clínica (web não recebe disparo — paciente não está conectado) |

Antes de enviar: mostrar **quantas pessoas** vão receber e uma prévia. Status da campanha: rascunho → agendada → enviando → concluída (x enviadas, y falhas) / cancelada.

## Resposta do paciente
Se o paciente responder a um disparo, a conversa cai normalmente na Ísis, que recebe no contexto qual mensagem foi enviada (ex.: responder ao aniversário com "obrigado, quero marcar limpeza" → Ísis agenda).

## Cuidados (importante)
- **WhatsApp não oficial (WAHA):** disparo em massa é o principal motivo de **banimento de número**. Obrigatório: limite por minuto/dia, intervalo aleatório entre mensagens, só para quem já conversou com a clínica.
- **WhatsApp oficial:** disparos iniciados pela clínica exigem **template aprovado pela Meta** (categoria marketing para aniversário/campanhas) e são cobrados por conversa. O texto editável vira variável de um template fixo — ou cada clínica aprova o seu (Q25).
- **LGPD e opt-out:** paciente pode responder "PARAR"/"SAIR" e deixa de receber disparos (continua recebendo confirmações/lembretes de consultas). Respeitar silêncio noturno.
- Não repetir: aniversário 1× por ano por paciente; campanha 1× por paciente.
