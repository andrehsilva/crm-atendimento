# Spec 03 — Motor de agenda

## Cadastros
- **Horário da clínica** (`clinic_hours`): por dia da semana, início/fim + pausas (ex.: almoço). Tela "Horários de Funcionamento".
- **Profissionais** herdam o horário da clínica; **exceções** opcionais por profissional (`professional_hours`), ex.: Dra. X só às terças.
- **Procedimentos** com duração cadastrada (padrão **60 min**, D17); `professional_services` liga quem faz o quê.
- **Dentista de referência** do paciente (`patients.preferred_professional_id`): definido após a 1ª consulta realizada (D16, RN-AG-15).
- **Bloqueios** (`schedule_blocks`): férias, feriados, reuniões — por profissional ou clínica toda.

## Cálculo de horários livres
```
para cada profissional que faz o procedimento:
  para cada dia no intervalo:
    faixas do expediente
    − bloqueios
    − consultas ativas (agendada/confirmada)
    → fatiar em passos de `slot_step` (config, padrão 15 ou 30 min) com a duração do procedimento
    → descartar < agora + antecedência mínima e > horizonte
ordenar por proximidade da preferência; devolver os primeiros N
```

## Garantias no banco
- `appointments` com `EXCLUDE USING gist (professional_id WITH =, tstzrange(starts_at, ends_at) WITH &&) WHERE status IN ('agendada','confirmada')` → impossível sobrepor.
- Toda alteração gera linha em `appointment_events` (quem, quando, de → para).

## Operações (mesmas para Ísis e painel)
| Operação | Validações |
|---|---|
| marcar | RN-AG-01..05, 08; paciente com nome |
| remarcar | dona da consulta (AG-06); nova passa nas validações; transação (AG-09) |
| cancelar | dona da consulta; aviso de política (AG-07) |
| confirmar | consulta futura `agendada` |
| marcar realizada/faltou | só recepção |

Erros têm **código** (`HORARIO_OCUPADO`, `FORA_EXPEDIENTE`, `ANTECEDENCIA`, `LIMITE_CONSULTAS`, `NAO_E_SUA`...) para a Ísis explicar e o painel exibir.
