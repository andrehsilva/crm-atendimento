# Spec 01 — Multi-tenant

## Objetivo
Uma instalação, várias clínicas, zero vazamento de dados entre elas.

## Chaves
- **Clínica:** `clinics.phone` (E.164, único) é a chave de negócio; `clinics.id` (UUID) é a chave interna usada nas relações.
- **Paciente:** único por `(clinic_id, phone)`.
- **Conversa:** única por `(clinic_id, patient_id, channel)` ativa; o histórico do agente usa `session_id = "{clinic_phone}:{patient_phone}"`.

## Como cada canal descobre a clínica

| Canal | Clínica vem de | Paciente vem de |
|---|---|---|
| Web | URL `/c/{slug}` ou `/c/{telefone}` | Telefone digitado no formulário de entrada |
| WAHA | Nome da sessão WAHA ↔ `channel_connections` (cada sessão = número da clínica) | Campo `from` do webhook |
| Cloud API | `phone_number_id` do webhook ↔ `channel_connections` | Campo `from` (wa_id) |

## Isolamento
1. **Aplicação:** todo repositório recebe `clinic_id` obrigatório; não existe função "buscar consulta por id" sem clínica.
2. **Banco:** RLS ligado nas tabelas para acessos via Supabase do frontend (admin/painel); backend usa conexão de serviço e filtra sempre.
3. **Testes:** suíte específica criando 2 clínicas e garantindo que nenhuma rota devolve dado da outra (cenário C16).

## Usuários
| Papel | Escopo | Pode |
|---|---|---|
| `super_admin` | Plataforma | Criar/desativar clínicas, ver tudo |
| `clinic_admin` | 1 clínica | Configurar layout, regras, profissionais, canais, usuários |
| `reception` | 1 clínica | Painel operacional: agenda, kanban, conversas, handoff |

## Configuração por clínica (`clinics.settings`, JSON)
- **Layout:** logo, cor primária/secundária, nome e avatar da assistente, mensagem de boas-vindas.
- **Regras:** valores das RN marcadas como Config (antecedência, horizonte, política de cancelamento, lembrete, silêncio noturno, limite de consultas).
- **Atendimento:** tratamento (você/senhor), telefone de urgência, endereço, texto livre "sobre a clínica", exibir preços (sim/não).
