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

## 2. WhatsApp não oficial — WAHA
- WAHA roda em Docker; 1 sessão por clínica, conectada por QR code (exibido no admin).
- Webhook `POST /webhooks/waha?secret=...` evento `message`.
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
