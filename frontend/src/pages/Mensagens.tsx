import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, CheckCheck, ChevronRight, Clock, Inbox } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { RelogioTeste } from '../components/RelogioTeste'
import { TIPO_MENSAGEM } from '../components/tipoMensagem'
import { Seletor, Selo, Vazio } from '../components/ui'
import { api, type Mensagem } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { dataHora, telefone } from '../lib/formato'
import { useTermos } from '../lib/termos'

/** Etapa 14B: as mensagens separadas pelo que importa para a recepção — o que vai sair, o que saiu e o que deu errado. */
const GRUPOS = {
  fila: { rotulo: 'Na fila', icone: Clock, status: ['agendada'], vazio: 'Nada esperando para sair.' },
  enviadas: { rotulo: 'Enviadas', icone: CheckCheck, status: ['enviada', 'entregue', 'lida'], vazio: 'Nenhuma mensagem enviada ainda.' },
  problemas: { rotulo: 'Não enviadas', icone: AlertCircle, status: ['falhou', 'cancelada'], vazio: 'Nenhum problema. 🎉' },
} as const
type Grupo = keyof typeof GRUPOS

const SITUACAO: Record<Mensagem['status'], [string, 'azul' | 'verde' | 'vermelho' | 'cinza']> = {
  agendada: ['na fila', 'azul'], enviada: ['enviada', 'verde'], entregue: ['entregue', 'verde'], lida: ['lida', 'verde'],
  falhou: ['falhou', 'vermelho'], cancelada: ['cancelada', 'cinza'],
}

export function Mensagens() {
  const { clinica } = useClinica()
  const pal = useTermos()
  const tz = clinica.timezone
  const [grupo, setGrupo] = useState<Grupo>('fila')
  const [tipo, setTipo] = useState('')
  const q = useQuery({
    queryKey: ['mensagens', clinica.id, 'todas'],
    queryFn: () => api.get<Mensagem[]>(`/clinics/${clinica.id}/outbound?limite=500`),
  })
  const todas = useMemo(() => (q.data ?? []).filter((m) => !tipo || m.kind === tipo), [q.data, tipo])
  const doGrupo = (g: Grupo) => todas.filter((m) => (GRUPOS[g].status as readonly string[]).includes(m.status))
  const lista = doGrupo(grupo)
    .slice()
    .sort((a, b) => (grupo === 'fila' ? a.scheduled_for.localeCompare(b.scheduled_for) : (b.sent_at ?? b.created_at).localeCompare(a.sent_at ?? a.created_at)))

  return (
    <>
      <PageHeader titulo="Mensagens" subtitulo={`O que vai sair, o que já saiu e o que não deu certo para os ${pal.clientes}`} />

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div role="tablist" aria-label="Situação das mensagens" className="flex flex-wrap gap-2">
          {(Object.keys(GRUPOS) as Grupo[]).map((g) => {
            const G = GRUPOS[g]
            const n = doGrupo(g).length
            return (
              <button key={g} type="button" role="tab" aria-selected={grupo === g} onClick={() => setGrupo(g)}
                className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm transition ${grupo === g ? 'bg-primary text-primary-contrast' : 'bg-surface text-muted hover:text-text'}`}>
                <G.icone className="size-4" />{G.rotulo}
                <span className={`rounded-full px-2 text-xs font-semibold ${grupo === g ? 'bg-white/25' : 'bg-surface-muted'}`}>{n}</span>
              </button>
            )
          })}
        </div>
        <label className="flex items-center gap-2 text-sm text-muted">
          Tipo
          <Seletor value={tipo} onChange={(e) => setTipo(e.target.value)} className="!w-auto !py-1.5">
            <option value="">Todos</option>
            {Object.entries(TIPO_MENSAGEM).map(([v, [r]]) => <option key={v} value={v}>{r}</option>)}
          </Seletor>
        </label>
      </div>

      <section className="rounded-3xl bg-surface p-2 sm:p-4" aria-live="polite">
        {q.isLoading ? <p className="p-4 text-sm text-muted">Carregando…</p>
          : lista.length === 0 ? <Vazio icone={<Inbox className="size-8" />} texto={GRUPOS[grupo].vazio} />
          : (
            <ul className="divide-y divide-line">
              {lista.map((m) => {
                const [tRot, tCor] = TIPO_MENSAGEM[m.kind] ?? [m.kind, 'cinza']
                const [sRot, sCor] = SITUACAO[m.status]
                const quando = m.status === 'agendada' ? `sai ${dataHora(m.scheduled_for, tz)}` : dataHora(m.sent_at ?? m.created_at, tz)
                return (
                  <li key={m.id}>
                    <details className="group">
                      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-4 gap-y-1 rounded-2xl px-3 py-3 hover:bg-surface-muted">
                        <ChevronRight className="size-4 shrink-0 text-muted transition group-open:rotate-90" aria-hidden />
                        <span className="w-28 shrink-0"><Selo cor={tCor}>{tRot}</Selo></span>
                        <span className="min-w-40 flex-1">
                          <span className="font-medium">{m.paciente ?? 'Sem nome'}</span>
                          <span className="ml-2 text-sm text-muted">{telefone(m.telefone)}</span>
                        </span>
                        <span className="text-sm tabular-nums text-muted">{quando}</span>
                        <span className="w-24 text-right"><Selo cor={sCor}>{sRot}</Selo></span>
                      </summary>
                      <div className="mb-3 ml-11 mr-3 rounded-2xl bg-surface-muted px-4 py-3 text-sm">
                        <p className="whitespace-pre-line">{m.body}</p>
                        {m.error && <p className="mt-2 text-xs text-muted">Motivo: {m.error}</p>}
                      </div>
                    </details>
                  </li>
                )
              })}
            </ul>
          )}
      </section>

      <details className="mt-6 text-sm text-muted">
        <summary className="cursor-pointer">Ferramentas de teste (só em desenvolvimento)</summary>
        <div className="mt-3"><RelogioTeste /></div>
      </details>
    </>
  )
}
