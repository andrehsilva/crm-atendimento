import { useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CalendarCheck, CalendarClock, Cake, Hand, Hourglass, Send } from 'lucide-react'
import { api, type Consulta, type Dashboard as Dados } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { hora, telefone } from '../lib/formato'
import { PageHeader } from '../components/PageHeader'
import { ModalConsulta } from '../components/agenda/ModalConsulta'
import { SeloStatus } from '../components/agenda/status'
import { Secao, Vazio } from '../components/ui'

export function Dashboard() {
  const { clinica } = useClinica()
  const tz = clinica.timezone
  const [aberta, setAberta] = useState<Consulta | null>(null)
  const q = useQuery({ queryKey: ['dashboard', clinica.id], queryFn: () => api.get<Dados>(`/clinics/${clinica.id}/dashboard`) })
  const d = q.data

  return (
    <>
      <PageHeader titulo="Dashboard" subtitulo="Resumo do dia da clínica" />
      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Indicador icone={<CalendarClock />} rotulo="Consultas hoje" valor={d?.consultas_hoje.length} />
        <Indicador icone={<CalendarCheck />} rotulo="Confirmadas × pendentes" valor={d ? `${d.confirmadas} × ${d.pendentes}` : undefined} />
        <Indicador icone={<Hand />} rotulo="Esperando uma pessoa" valor={d?.precisando_humano} alerta={!!d?.precisando_humano} />
        <Indicador icone={<Hourglass />} rotulo="Leads parados +24h" valor={d?.leads_parados} alerta={!!d?.leads_parados} />
        <Indicador icone={<Send />} rotulo="Mensagens na fila" valor={d?.mensagens_na_fila} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[2fr_1fr]">
        <Secao titulo="Consultas de hoje" icone={<CalendarClock className="size-5" />}>
          {!d?.consultas_hoje.length ? (
            <Vazio icone={<CalendarClock className="size-8" />} texto="Nenhuma consulta hoje." />
          ) : (
            <ul className="divide-y divide-line">
              {d.consultas_hoje.map((c) => (
                <li key={c.id}>
                  <button type="button" onClick={() => setAberta(c)} className="flex w-full items-center gap-4 py-3 text-left hover:bg-surface-muted/50">
                    <span className="w-14 font-semibold">{hora(c.starts_at, tz)}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium">{c.paciente}</span>
                      <span className="block truncate text-sm text-muted">{c.procedimento} · {c.profissional}</span>
                    </span>
                    <SeloStatus status={c.status} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Secao>
        <Secao titulo="Aniversariantes do dia" icone={<Cake className="size-5" />}>
          {!d?.aniversariantes.length ? (
            <Vazio icone={<Cake className="size-8" />} texto="Ninguém faz aniversário hoje." />
          ) : (
            <ul className="space-y-2">
              {d.aniversariantes.map((a) => (
                <li key={a.id} className="flex items-center justify-between text-sm">
                  <span className="font-medium">🎂 {a.name}</span>
                  <span className="text-muted">{telefone(a.phone)}</span>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-4 text-xs text-muted">A felicitação automática pelo WhatsApp entra na Etapa 6.</p>
        </Secao>
      </div>
      <ModalConsulta consulta={aberta} onFechar={() => setAberta(null)} />
    </>
  )
}

function Indicador({ icone, rotulo, valor, alerta }: { icone: ReactNode; rotulo: string; valor?: number | string; alerta?: boolean }) {
  return (
    <div className="rounded-3xl bg-surface p-5">
      <span className={`mb-3 grid size-10 place-items-center rounded-xl [&>svg]:size-5 ${alerta ? 'bg-[#fce8e6] text-[#c0362e]' : 'bg-primary-soft text-primary'}`}>{icone}</span>
      <div className="text-2xl font-bold">{valor ?? '—'}</div>
      <div className="text-sm text-muted">{rotulo}</div>
    </div>
  )
}
