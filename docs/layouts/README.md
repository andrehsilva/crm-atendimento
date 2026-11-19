# Telas de referência de layout

Layout **aprovado como proposta** pelo usuário em 16/11/2026. As specs que usam estas telas:
[06-painel-operacional](../specs/06-painel-operacional.md) · [07-painel-admin](../specs/07-painel-admin.md) · [10-disparos](../specs/10-disparos.md) · [11-design-visual](../specs/11-design-visual.md)

| Arquivo | Tela | O que aproveitar |
|---|---|---|
| `01-crm-kanban-escuro.png` | CRM (kanban), tema escuro | Colunas do funil, cards com selos, contador por coluna |
| `02-crm-kanban-claro.png` | CRM (kanban), tema claro | Mesmo layout: **os dois temas são obrigatórios** |
| `03-demo-chat-agenda-mensagens.png` | Demonstração em 3 colunas (vídeo de referência "Ísis") | Chat + agenda da semana + mensagens enviadas lado a lado; filtro por especialidade; legenda de status; botão "Reiniciar demonstração" |
| `04-config-mensagens-aniversario.png` | Configurações › Mensagens | Mensagem de aniversário com variáveis, contador de caracteres, **prévia com dados reais**; seção "Mensagens programadas" |
| `05-config-procedimentos.png` | Configurações › Procedimentos | Lista com liga/desliga, descrição, expandir, editar, excluir, "+ Novo Procedimento" |
| `06-config-perfil.png` | Configurações › Perfil | Trocar senha, logo da clínica, nome da clínica |
| `07-config-horarios.png` | Configurações › Horários de Funcionamento | Um dia por linha: liga/desliga, início "até" fim, salvar |

## Padrões que se repetem (viram componentes)
- **Barra lateral fixa** (recolhível pelo botão `‹`): logo + nome da clínica no topo; menu Dashboard · CRM · Leads/Clientes · Configurações; usuário logado (foto, nome, papel) no rodapé.
- **Cabeçalho de página:** título grande + subtítulo cinza explicando a tela.
- **Card de seção:** fundo branco, cantos bem arredondados, ícone em quadrado rosa-claro + título.
- **Abas em pílula** (Configurações): aba ativa preenchida na cor principal.
- **Selos (badges)** coloridos e arredondados para status.
- **Botão principal** na cor principal; desabilitado fica rosa-claro.

## Pontos ainda não definidos
- Tela **Dashboard** (não veio imagem) — ver `DECISOES.md` Q19.
- Tela **Leads/Clientes** (não veio imagem) — proposta em spec 06.
- Onde ficam **Agenda da semana** e **Mensagens enviadas** no menu — proposta em spec 06.
