// Etapa 33: agenda no celular — a lista de UM dia (abre em hoje), com setas para trocar de dia.
// Usa a mesma busca da agenda da semana (mesma chave), então o tempo real e o cache valem igual.
import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CalendarDays, ChevronLeft, ChevronRight, Inbox } from 'lucide-react'
import { api, type Consulta } from '../../lib/api'
import { useClinica } from '../../lib/clinica'
import { diaLegivel, hojeYmd, hora, partes, segundaDaSemana, somarDias } from '../../lib/formato'
import { useTermos } from '../../lib/termos'
import { SeloStatus } from './status'

export function AgendaDia({ onConsulta, ir, onIrFeito }: {
  onConsulta: (c: Consulta) => void
  /** Vindo do sino: abre neste dia e, se der, já com a consulta aberta. */
  ir?: { dia: string; consultaId: string | null }
  onIrFeito?: () => void
}) {
  const { clinica } = useClinica()
  const pal = useTermos()
  const tz = clinica.timezone
  const hoje = hojeYmd(tz)
  const [dia, setDia] = useState(hoje)
  const seletor = useRef<HTMLInputElement>(null)
  const segunda = segundaDaSemana(dia)

  const q = useQuery({
    queryKey: ['agenda', clinica.id, segunda],
    queryFn: () => api.get<Consulta[]>(`/clinics/${clinica.id}/appointments?de=${segunda}T00:00:00&ate=${somarDias(segunda, 7)}T00:00:00`),
  })

  useEffect(() => { if (ir) setDia(ir.dia) }, [ir])
  useEffect(() => {
    if (!ir || segunda !== segundaDaSemana(ir.dia) || !q.data || q.isFetching) return
    const c = ir.consultaId ? q.data.find((x) => x.id === ir.consultaId) : undefined
    if (c) onConsulta(c)
    onIrFeito?.()
  }, [ir, segunda, q.data, q.isFetching, onConsulta, onIrFeito])

  const doDia = useMemo(
    () => (q.data ?? []).filter((c) => partes(c.starts_at, tz).ymd === dia).sort((a, b) => a.starts_at.localeCompare(b.starts_at)),
    [q.data, dia, tz],
  )
  const ativas = doDia.filter((c) => c.status !== 'cancelada').length

  function escolherData() {
    const el = seletor.current
    if (!el) return
    try { el.showPicker() } catch { el.click() }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2 rounded-2xl bg-surface p-2">
        <button type="button" aria-label="Dia anterior" onClick={() => setDia(somarDias(dia, -1))}
          className="grid size-10 place-items-center rounded-xl text-muted active:bg-surface-muted"><ChevronLeft className="size-5" /></button>
        <button type="button" onClick={escolherData} className="relative min-w-0 flex-1 text-center leading-tight">
          <div className="truncate font-semibold capitalize">{dia === hoje ? 'Hoje' : diaLegivel(dia)}</div>
          <div className="text-xs text-muted">{pal.contar(ativas)}</div>
          <input ref={seletor} type="date" value={dia} tabIndex={-1} aria-hidden onChange={(e) => e.target.value && setDia(e.target.value)}
            className="pointer-events-none absolute inset-0 opacity-0" />
        </button>
        <button type="button" aria-label="Próximo dia" onClick={() => setDia(somarDias(dia, 1))}
          className="grid size-10 place-items-center rounded-xl text-muted active:bg-surface-muted"><ChevronRight className="size-5" /></button>
      </div>
      {dia !== hoje && (
        <button type="button" onClick={() => setDia(hoje)} className="flex items-center gap-1.5 self-center text-sm text-primary">
          <CalendarDays className="size-4" />Voltar para hoje
        </button>
      )}

      {q.isLoading && <p className="py-8 text-center text-sm text-muted">Carregando…</p>}
      {!q.isLoading && doDia.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-12 text-sm text-muted"><Inbox className="size-7 opacity-60" />Nada marcado neste dia</div>
      )}
      <ul className="flex flex-col gap-2">
        {doDia.map((c) => (
          <li key={c.id}>
            <button type="button" onClick={() => onConsulta(c)}
              className={`flex w-full items-stretch gap-3 rounded-2xl bg-surface p-3 text-left ring-1 ring-line active:bg-surface-muted ${
                c.status === 'cancelada' ? 'opacity-60' : ''}`}>
              <div className="w-14 shrink-0 text-center leading-tight">
                <div className="font-semibold">{hora(c.starts_at, tz)}</div>
                <div className="text-xs text-muted">{hora(c.ends_at, tz)}</div>
              </div>
              <span className="w-1 shrink-0 rounded-full" style={{ background: c.cor ?? 'var(--primary)' }} />
              <div className="min-w-0 flex-1">
                <div className={`truncate font-medium ${c.status === 'cancelada' ? 'line-through' : ''}`}>{c.paciente ?? 'Sem nome'}</div>
                <div className="truncate text-sm text-muted">{c.procedimento} · {c.profissional}</div>
                <div className="mt-1.5"><SeloStatus status={c.status} /></div>
              </div>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
