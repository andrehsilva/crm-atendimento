import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, CalendarClock, CheckCheck, ChevronRight, Clock, Inbox, Send } from 'lucide-react'
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

/** "hoje", "amanhã", "em 3 dias", "ontem", "há 5 dias" — conta dias de calendário no fuso da clínica. */
function diasAte(iso: string, tz: string): number {
  const dia = (d: Date) => new Date(`${new Intl.DateTimeFormat('en-CA', { timeZone: tz }).format(d)}T12:00:00Z`).getTime()
  return Math.round((dia(new Date(iso)) - dia(new Date())) / 86_400_000)
}

function relativo(dias: number): string {
  if (dias === 0) return 'hoje'
  if (dias === 1) return 'amanhã'
  if (dias === -1) return 'ontem'
  return dias > 0 ? `em ${dias} dias` : `há ${-dias} dias`
}

function Quando({ m, tz }: { m: Mensagem; tz: string }) {
  const naFila = m.status === 'agendada'
  const iso = naFila ? m.scheduled_for : (m.sent_at ?? m.created_at)
  const dias = diasAte(iso, tz)
  const [semana, resto] = dataHora(iso, tz).split(', ')
  const horaTxt = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit', timeZone: tz }).format(new Date(iso))
  const Icone = naFila ? CalendarClock : m.status === 'falhou' || m.status === 'cancelada' ? AlertCircle : Send
  const legenda = naFila ? `sai ${relativo(dias)}` : m.sent_at ? `enviada ${relativo(dias)}` : `criada ${relativo(dias)}`
  const urgente = naFila && dias <= 0
  return (
    <span className="flex w-44 items-center gap-2.5">
      <span className={`grid size-9 shrink-0 place-items-center rounded-xl ${urgente ? 'bg-primary-soft text-primary' : 'bg-surface-muted text-muted'}`}>
        <Icone className="size-4" aria-hidden />
      </span>
      <span className="leading-tight">
        <span className="block text-sm font-medium tabular-nums">
          {semana.replace('.', '')} {resto?.slice(0, 5)} <span className="text-muted">· {horaTxt}</span>
        </span>
        <span className={`block text-xs ${urgente ? 'font-medium text-primary' : 'text-muted'}`}>{legenda}</span>
      </span>
    </span>
  )
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
                        <Quando m={m} tz={tz} />
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
