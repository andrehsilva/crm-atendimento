import type { StatusConsulta } from '../../lib/api'
import { Selo, type CorSelo } from '../ui'

const MAPA: Record<StatusConsulta, [string, CorSelo]> = {
  agendada: ['Aguardando confirmação', 'ambar'],
  confirmada: ['Confirmada', 'verde'],
  realizada: ['Compareceu', 'azul'],
  faltou: ['Faltou', 'vermelho'],
  cancelada: ['Cancelada', 'vermelho'],
}

export function SeloStatus({ status }: { status: StatusConsulta }) {
  const [texto, cor] = MAPA[status]
  return <Selo cor={cor}>{texto}</Selo>
}
