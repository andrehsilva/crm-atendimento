import type { Mensagem } from '../lib/api'
import type { CorSelo } from './ui'

export const TIPO_MENSAGEM: Record<Mensagem['kind'], [string, CorSelo]> = {
  confirmacao: ['Confirmação', 'verde'],
  remarcacao: ['Remarcação', 'azul'],
  cancelamento: ['Cancelamento', 'vermelho'],
  lembrete: ['Lembrete', 'ambar'],
  aniversario: ['Aniversário', 'roxo'],
}
