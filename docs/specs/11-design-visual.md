# Spec 11 — Design visual

Baseado nas telas em `docs/layouts/`. Valores de cor são **estimados a partir das imagens** — ajustar quando tivermos o arquivo de design original (se houver).

## Princípios
- Visual limpo, cantos arredondados, bastante espaço em branco.
- **Tema claro e escuro** desde o início (imagens 01 e 02); usuário escolhe, padrão = sistema.
- A **cor principal é da clínica** (configurável no admin); o resto da paleta é fixo.

## Tokens (variáveis CSS)

| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `--bg` | `#F3F1EE` (bege claro) | `#1F1F22` | Fundo da página |
| `--surface` | `#FFFFFF` | `#2A2A2E` | Cards, colunas, barra lateral |
| `--surface-muted` | `#F3F1EE` | `#323236` | Prévia de mensagem, colunas do kanban |
| `--text` | `#1F1F22` | `#F2F2F2` | Texto principal |
| `--text-muted` | `#77737A` | `#A09CA3` | Subtítulos, telefones, ajuda |
| `--border` | `#ECE8E4` | `#3A3A3F` | Bordas suaves |
| `--primary` | `#B85C74` (rosa queimado) | `#C66C84` | Botões, aba ativa, toggles, item ativo do menu |
| `--primary-soft` | `#F6E4EA` | `#4A2E37` | Fundo do item ativo, ícone de seção, botão desabilitado |

Cores de status (selos e bolinhas das colunas):

| Status | Cor |
|---|---|
| Novo contato | rosa `#C2547A` |
| Orçamento em negociação | azul `#2F80C9` |
| Agendado | verde `#2E9E5B` |
| Confirmado | verde `#1F8A4C` |
| Cancelado / Parado há Xh | vermelho `#D9473F` (fundo `#FCE8E6`) |
| Atendimento manual | âmbar `#C98A12` (fundo `#FCF1DC`) |
| Paciente recorrente / ativo | roxo `#8A4FC9` (fundo `#F1E8FB`) |
| Atendimento automático | cinza (fundo `--surface-muted`) |

## Tipografia
- Fonte: **Lexend** (Google Fonts, pesos 300–700) — decidido (D22). Reserva: `system-ui, sans-serif`. Códigos: `JetBrains Mono`.
- Título de página ~32px negrito; título de card ~18px semi-negrito; corpo 15–16px; legendas/códigos 12px (código como `iniciou_conversa` em fonte monoespaçada).

## Componentes base
`Sidebar` · `PageHeader` · `SectionCard` · `PillTabs` · `Badge` · `Toggle` · `TimeInput` · `Button` (primário/secundário/ícone) · `KanbanColumn` · `LeadCard` · `TemplateEditor` (texto + variáveis + contador + prévia) · `WeekCalendar` · `ChatPanel` · `MessageFeed`.

Biblioteca: Tailwind + shadcn/ui (Radix) com os tokens acima; ícones **lucide-react** (os das imagens são do estilo Lucide).

## Responsividade
- ≥ 1280px: layout completo.
- 768–1279px: barra lateral recolhida (só ícones); kanban com rolagem horizontal.
- < 768px: menu em gaveta; kanban vira lista por coluna com abas.
