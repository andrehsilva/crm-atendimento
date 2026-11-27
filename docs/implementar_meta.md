# Implementar WhatsApp oficial (Meta) como 2ª opção por clínica

> Ideia registrada em 27/11/2026. Ainda não implementada — estimativa e plano.


## Contexto
Hoje todo o WhatsApp passa pelo WAHA (integração não oficial, risco de bloqueio, sem SLA). O usuário quer que **cada
clínica escolha**: continuar no WAHA ou usar a **API oficial (WhatsApp Cloud API)**. Na oficial, **o cadastro na Meta e
o pagamento ficam com a clínica**, igual já é com a chave de IA (D42/D43: a clínica cola a chave, guardada cifrada).
Pedido: estimar o esforço e o custo por mensagem, inclusive de uma conversa com 5 mensagens de cada lado.

## Quem escolhe: chave no Admin geral (pedido do usuário)
- **Admin geral › clínica › WhatsApp** ganha a escolha **"Provedor: WAHA | Meta (oficial)"**, que só o dono da
  plataforma (super admin) muda. A clínica não troca sozinha.
- **Padrão = WAHA.** A migration cria a coluna com valor `waha` para todas as clínicas existentes → no dia do deploy
  nada muda para ninguém. Só a clínica que você trocar para "Meta" passa pelo caminho novo.
- Com "Meta", a clínica (ou você) preenche os dados da Meta em Configurações › Canais; com "WAHA", a tela continua a de hoje.
- Voltar de Meta para WAHA é trocar a chave de novo (os dados da Meta ficam guardados, como hoje no "Desligar", D122–D124).

### Isso garante que não quebra o que já existe?
Reduz bastante o risco, mas não é prova sozinha. O que dá a segurança:
1. **Chave com padrão WAHA:** clínicas atuais nunca entram no código novo.
2. **Código do WAHA não é reescrito:** `waha.py` fica como está; só os 4 pontos que criam o cliente passam a perguntar
   "qual provedor?" e, para WAHA, devolvem exatamente o mesmo `ClienteWaha` de hoje.
3. **Os ~410 testes atuais rodam sem mudança** (todos em WAHA) — se algo do fluxo atual mudar, eles acusam.
4. **Testes novos** garantindo que clínica WAHA nunca chama a Meta e vice-versa.
5. **Liberação aos poucos:** primeiro uma clínica de teste em "Meta" (número de teste grátis da Meta), as reais ficam
   em WAHA até a homologação.

## O que já existe e será reaproveitado
- `backend/app/canais/waha.py` — `ClienteWaha` (enviar_texto, digitando, baixar_midia, sessão/QR) e `interpretar()` →
  `MensagemEntrada`. Vira **um dos dois** "canais"; o novo `ClienteMeta` terá os mesmos métodos.
- `backend/app/canais/whatsapp.py` — fluxo de entrada (agrupar mensagens picadas, áudio, Ísis, `enviar_da_equipe`,
  `registrar_entrega` para entregue/lida). Continua igual; só passa a receber o cliente certo.
- `backend/app/canais/conexao.py` (`cliente_da_clinica`, webhook por clínica com token) e `backend/app/mensagens/envio.py`
  (fila: silêncio noturno, limites, espaçamento, tentativas). Fila continua igual; muda só o "como enviar".
- `backend/app/ia.py` — `cifrar/decifrar` (Fernet com `IA_CHAVE_MESTRA`), `estado_publico`, `salvar_chave`, `testar`:
  mesmo padrão para guardar o token da Meta da clínica.
- `backend/app/uso_ia.py` + tela Uso da IA — modelo para mostrar o gasto estimado de WhatsApp oficial por mês.
- Tabela `whatsapp_instances` (migrations 0004, 0022, 0034) — ganha as colunas do provedor oficial.

## Estimativa de esforço (≈ 13 a 18 dias de desenvolvimento, em 5 etapas)
| Etapa | O que | Dias |
|---|---|---|
| 36A | **Base:** migration (`provedor` waha/oficial, `phone_number_id`, `waba_id`, token e app secret cifrados, token de verificação); interface comum de canal; `ClienteMeta` (Graph API: enviar texto, marcar lido, baixar mídia); trocar os 4 pontos que criam `ClienteWaha` (`conexao.cliente_da_clinica`, `envio._cliente`, `whatsapp._enviar`, `enviar_da_equipe`) | 2–3 |
| 36B | **Webhook oficial:** GET de verificação (challenge), assinatura `X-Hub-Signature-256`, mensagens recebidas (texto, áudio, imagem) → `MensagemEntrada`; status sent/delivered/read/failed → `registrar_entrega` (D85) | 1,5–2 |
| 36C | **Janela de 24 h e modelos (templates)** — a parte maior. Fora da janela só sai modelo aprovado pela Meta: lembrete, confirmação/remarcação/cancelamento feitos pela recepção, aniversário, pós-consulta, retorno, tratamento, resumo do dia do profissional. Catálogo fixo de modelos "utilidade" do TemHorario criados na conta da clínica pela API; cada tipo de mensagem vira modelo + variáveis (os textos editáveis viram só as partes variáveis). Lembrete com **botões** Confirmar/Remarcar/Cancelar ligados à resposta atual (RN-MS-04). Recepção tentando escrever fora da janela → aviso "precisa de modelo" | 4–6 |
| 36D | **Tela de configuração:** no Admin geral, a chave WAHA/Meta (só super admin, padrão WAHA); em Configurações › Canais, quando for Meta: colar IDs e token (mascarado, botão Testar, como a IA); mostrar URL do webhook + token de verificação para colar na Meta; situação dos modelos (aprovado/pendente/rejeitado); passo a passo da Meta para a clínica | 2–3 |
| 36E | **Custo e acabamento:** contador mensal de mensagens cobradas e gasto estimado (tabela de preços editável, como em Uso da IA); campanhas como modelo "marketing" (cada campanha passa por aprovação da Meta antes de sair); testes, docs (DECISOES/REGRAS/PLANO) e homologação com uma conta real | 3–4 |

Fora do nosso tempo (responsabilidade da clínica, pode levar dias): conta Business verificada na Meta, número
registrado na Cloud API (o número não pode estar no WhatsApp do celular ao mesmo tempo), cartão cadastrado na Meta.

## Custos por mensagem — WhatsApp oficial, Brasil (Meta, cobrança por mensagem entregue)
| Tipo | US$ | ≈ R$ (US$ 1 ≈ R$ 5,15) | Usamos em |
|---|---|---|---|
| Marketing | 0,0625 | 0,32 | campanhas, aniversário, retorno |
| Utilidade | 0,0068 | 0,035 | lembrete, confirmação, remarcação, cancelamento, pós-consulta, resumo do dia |
| Atendimento (resposta dentro da janela de 24 h) | 0,0068 | 0,035 | respostas da Ísis e da equipe — **1.000 grátis por número/mês**; cobrado desde 01/10/2026 |
| Mensagem recebida do cliente | grátis | — | |

Desde 01/10/2026 a Meta também cobra mensagens de utilidade dentro da janela (antes eram grátis). O WAHA não tem custo
por mensagem (só o servidor), mas tem risco de bloqueio.

## Uma conversa com 5 mensagens de cada lado
- **WhatsApp:** só as 5 respostas da clínica contam (as do cliente são grátis).
  - Dentro das 1.000 grátis do mês: **R$ 0,00**.
  - Passou das 1.000: 5 × R$ 0,035 ≈ **R$ 0,18**.
  - Se a conversa termina em marcação: + confirmação (utilidade, R$ 0,035) + lembrete na véspera (R$ 0,035) ≈ **R$ 0,25 no total**.
  - Atenção: se a Ísis quebra uma resposta em 2 balões, são 2 mensagens cobradas — na oficial, juntar em um balão.
- **IA (já paga pela clínica hoje, igual nos dois canais):** medido no banco — cada resposta usa ~4.300–6.000 tokens de
  entrada (metade em cache) e ~200 de saída; 5 respostas ≈ 25 mil de entrada + 1 mil de saída. Com um modelo econômico
  (~US$ 0,30/milhão entrada, ~US$ 2,50/milhão saída) ≈ US$ 0,01 ≈ **R$ 0,05 a 0,10** por conversa (depende do modelo).
- **Total por conversa na oficial:** cerca de **R$ 0,05 a 0,35**. Ex.: 300 conversas/mês com marcação ≈ R$ 15 a 105.
- Campanha de Natal para 500 clientes: 500 × R$ 0,32 ≈ **R$ 160** (marketing não tem desconto por volume).

## Riscos e cuidados
- Textos automáticos ficam menos livres (modelo aprovado + variáveis); campanha precisa de aprovação antes do envio.
- Política da Meta para IA: assistentes de atendimento do próprio negócio são permitidos; conferir a política
  "AI Providers" na homologação.
- Preços mudam por trimestre: deixar a tabela editável e mostrar o custo como "estimado".
- Primeira versão sem "Embedded Signup" (cadastro guiado pela Meta, exige ser Tech Provider); a clínica cola os dados,
  como faz com a IA. Embedded Signup fica para depois.

## Verificação (quando for implementar)
- Testes automáticos com Meta simulada (como hoje com o WAHA): envio, webhook assinado, status, janela de 24 h,
  escolha de modelo, botões do lembrete; suíte completa verde.
- Homologação com número de teste da Meta (a Meta dá um número de teste grátis): "oi" → resposta da Ísis; marcar →
  confirmação; lembrete com botões; entregue/lida no painel; clínica WAHA continua funcionando igual.

## Fontes de preço
- https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing
- https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/non-template-messages
- https://whautomate.com/whatsapp-business-api-pricing-brazil (R$ 0,3217 marketing · R$ 0,0350 utilidade)
