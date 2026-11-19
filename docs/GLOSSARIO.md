# Glossário

| Termo | Significado |
|---|---|
| **Clínica / Instância / Tenant** | Um cliente da plataforma. Identificado pelo telefone da clínica. |
| **Multi-tenant** | Várias clínicas no mesmo sistema, cada uma vendo só os próprios dados. |
| **Paciente** | Pessoa que conversa com a Ísis. Identificado pelo telefone **dentro de uma clínica**. |
| **Conversa (sessão)** | Histórico entre um paciente e uma clínica. Chave: telefone da clínica + telefone do paciente. |
| **Canal** | Por onde a mensagem chega: Web, WhatsApp WAHA, WhatsApp oficial. |
| **Adaptador** | Código que traduz um canal para o formato interno. |
| **Profissional** | Dentista (ou outro) que tem agenda. |
| **Procedimento / Serviço** | Tipo de atendimento (avaliação, limpeza...) com duração. |
| **Slot** | Um horário livre possível para marcar. |
| **Consulta** | Agendamento de um paciente com um profissional para um procedimento. |
| **Confirmação** | Mensagem enviada logo após marcar/remarcar/cancelar. |
| **Lembrete** | Mensagem enviada antes da consulta pedindo que o paciente confirme. |
| **Handoff** | Passar a conversa para um humano da clínica. |
| **Ferramenta (tool)** | Função do sistema que a Ísis pode chamar (ex.: "marcar consulta"). |
| **SSE** | Server-Sent Events: o servidor "empurra" atualizações para a tela. |
| **WAHA** | WhatsApp HTTP API — conexão **não oficial** via WhatsApp Web. Risco de bloqueio do número. |
| **Cloud API** | API **oficial** do WhatsApp (Meta). Exige conta Business e templates aprovados. |
| **Template (HSM)** | Mensagem pré-aprovada pela Meta, obrigatória para escrever ao paciente fora da janela de 24h. |
| **E.164** | Formato internacional de telefone: `+55` + DDD + número. |
| **RN-xxx** | Código de uma regra de negócio em `REGRAS-DE-NEGOCIO.md`. |
