import { useQuery } from '@tanstack/react-query'
import { Inbox } from 'lucide-react'
import { api, type Mensagem } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { dataCurta, hora, telefone } from '../lib/formato'
import { Selo, Vazio, type CorSelo } from './ui'

const TIPO: Record<Mensagem['kind'], [string, CorSelo]> = {
  confirmacao: ['Confirmação', 'verde'],
  remarcacao: ['Remarcação', 'azul'],
  cancelamento: ['Cancelamento', 'vermelho'],
  lembrete: ['Lembrete', 'ambar'],
  aniversario: ['Aniversário', 'roxo'],
}

const STATUS: Record<Mensagem['status'], string> = {
  agendada: '⏳ na fila (envio pelo WhatsApp na Etapa 6)',
  enviada: '✓ enviada',
  entregue: '✓✓ entregue',
  lida: '✓✓ lida',
  falhou: '⚠ falhou',
  cancelada: '— cancelada',
}

/** Painel "Mensagens enviadas" (imagem 03, coluna direita). */
export function MensagensFeed({ tipo, limite = 100 }: { tipo?: string; limite?: number }) {
  const { clinica } = useClinica()
  const tz = clinica.timezone
  const q = useQuery({
    queryKey: ['mensagens', clinica.id, tipo, limite],
    queryFn: () => api.get<Mensagem[]>(`/clinics/${clinica.id}/outbound?limite=${limite}${tipo ? `&tipo=${tipo}` : ''}`),
  })

  if (q.isLoading) return <p className="text-sm text-muted">Carregando…</p>
  if (!q.data?.length) return <Vazio icone={<Inbox className="size-8" />} texto="Nenhuma mensagem ainda." />

  return (
    <ul className="flex flex-col gap-3">
      {q.data.map((m) => {
        const [rotulo, cor] = TIPO[m.kind]
        return (
          <li key={m.id} className="rounded-2xl border border-line p-4">
            <div className="mb-1 flex items-center justify-between gap-2">
              <Selo cor={cor} className="uppercase tracking-wide">{rotulo}</Selo>
              <span className="text-xs text-muted">{dataCurta(m.created_at, tz)}, {hora(m.created_at, tz)}</span>
            </div>
            <p className="mb-2 text-xs text-muted">Para {m.paciente ?? 'paciente'} · {telefone(m.telefone)}</p>
            <p className="whitespace-pre-line text-sm">{m.body}</p>
            <p className="mt-2 text-xs text-muted">{STATUS[m.status]}</p>
          </li>
        )
      })}
    </ul>
  )
}
