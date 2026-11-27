# Conexão com o WhatsApp oficial (Meta) — dados de cada clínica

> Complemento de [implementar_meta.md](implementar_meta.md). Registrado em 27/11/2026; ainda não implementado.

Para a API oficial funcionar, guardamos **4 dados da clínica** e **geramos 1 do nosso lado**.

## O que a clínica pega na Meta e cola no painel

| Dado | Onde a clínica encontra | Para que serve | É segredo? |
|---|---|---|---|
| **ID do número** (Phone Number ID) | Painel do app na Meta › WhatsApp › Configuração da API | Enviar mensagens por aquele número | Não |
| **ID da conta do WhatsApp Business** (WABA ID) | Mesma tela | Criar e consultar os modelos de mensagem (lembrete, aniversário, campanha) e ligar o recebimento de mensagens | Não |
| **Token de acesso permanente** | Configurações do negócio na Meta › Usuários do sistema › Gerar token, com as permissões `whatsapp_business_messaging` e `whatsapp_business_management` | Autorizar todos os envios e consultas | **Sim**: guardado cifrado, como a chave da IA |
| **Chave secreta do app** (App Secret) | Painel do app › Configurações › Básico | Conferir que as mensagens recebidas vieram mesmo da Meta | **Sim**: cifrada |

O token precisa ser o **permanente**. O token temporário que aparece na tela da API vence em 24 horas e faria o envio
parar no dia seguinte.

## O que nós geramos e a clínica cola na Meta

- **Endereço do webhook** (o endereço para onde a Meta manda as mensagens recebidas) e um **token de verificação**.
  A clínica cola os dois em Webhooks, na configuração do app na Meta. Já temos webhook próprio por clínica, então é o
  mesmo padrão de hoje.

## O que não precisamos guardar

- O número de telefone em si (a API informa).
- O ID do negócio.
- A senha da conta da Meta.

## Na tela de configuração (mesmo padrão da IA)

- Os dois IDs aparecem normalmente.
- O token e a chave secreta aparecem só com o final, como "…a1b2".
- Um botão **Testar** confere se o número responde antes de salvar.
