# Spec 04 — Canais de entrada

Interface comum:
```python
class Canal:
    def parse_webhook(req) -> MensagemEntrada   # clinic_phone, patient_phone, texto, tipo, id_externo
    def enviar(clinic, patient_phone, MensagemSaida) -> id_externo
```
Mensagens com `id_externo` repetido são ignoradas (webhooks podem chegar duas vezes).

## 1. Web (página do paciente)
- Rota `/c/{slug}`: tela com logo/cores da clínica → paciente digita **telefone** (e nome, se novo) → chat.
- Comunicação: `POST /api/web/{slug}/messages` + SSE para receber respostas.
- MVP sem verificação do telefone (Q5). Produção: código via WhatsApp.

## 2. WhatsApp não oficial — WAHA (Etapa 5)
- WAHA roda no **servidor do usuário** (D28); 1 sessão por clínica (D29), conectada por QR code.
- Ligação clínica ↔ sessão na tabela `whatsapp_instances` (D31). A **clínica sai da sessão** do webhook; o paciente sai do remetente (`from`). Nada vem do texto.
- Webhook `POST /webhooks/waha`, eventos `message` e `session.status`. Assinado com HMAC SHA-512 (cabeçalho `X-Webhook-Hmac`, segredo `WAHA_WEBHOOK_HMAC_KEY`); sem assinatura válida → 401.
- O webhook responde na hora; a Ísis trabalha em segundo plano. Mensagens do mesmo chat são processadas uma por vez.
- Ignorados: mensagens da própria clínica (`fromMe`), grupos (`@g.us`), status, canais e listas. Mídia sem texto → a Ísis pede para escrever.
- `@lid` (número escondido): procura o número no `_data` ou pergunta ao WAHA (`/api/{sessao}/lids/{lid}`); sem número, a mensagem é ignorada e registrada no log.
- Envio: `sendSeen` → `startTyping` → pausa proporcional ao texto → `stopTyping` → `sendText` (recomendação anti-bloqueio do WAHA). A falha de envio aparece na conversa do painel.
- Resposta manual da recepção numa conversa de WhatsApp é enviada pelo WAHA; se falhar, nada é gravado e o painel mostra o erro.
- Operação (até a tela do admin geral na Etapa 7): `backend/scripts/whatsapp.py` (sessoes, ligar, status, qr, webhook).
- Prós: grátis/barato, sem aprovação. Contras: **risco de banimento do número**, sem SLA, depende do celular/WhatsApp Web.
- Botões interativos podem não funcionar: usar opções numeradas ("1 Confirmar · 2 Remarcar · 3 Cancelar").

## 3. WhatsApp oficial — Cloud API (Meta)
- Exige conta Meta Business verificada, número dedicado, **templates aprovados** para lembretes/confirmações fora da janela de 24h; cobrança por conversa.
- Webhook `GET/POST /webhooks/whatsapp` com verificação de token e assinatura `X-Hub-Signature-256`.
- Botões de resposta rápida nativos.

## Prioridade (D15, D23)
1. **WAHA = canal principal** (Etapa 5).
2. **Web = canal de teste** (Etapa 3/4), sem verificação de telefone.
3. **Cloud API oficial = depois** (Etapa 7), opcional por clínica.

## Teste local de webhooks
`cloudflared tunnel --url http://localhost:8000` (no Windows: `winget install Cloudflare.cloudflared`).
