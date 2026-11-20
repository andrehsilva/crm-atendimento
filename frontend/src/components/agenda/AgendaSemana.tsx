import { useMemo, useState, type MouseEvent, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { api, type Consulta } from '../../lib/api'
import { useClinica } from '../../lib/clinica'
import { hojeYmd, hora, partes, segundaDaSemana, somarDias } from '../../lib/formato'

const DIAS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
const minutos = (hhmm: string) => Number(hhmm.slice(0, 2)) * 60 + Number(hhmm.slice(3, 5))

/** Grade da semana (spec 06 / imagem 03). Atualiza sozinha pelos avisos em tempo real. */
export function AgendaSemana({
  compacta = false,
  onVazio,
  onConsulta,
}: {
  compacta?: boolean
  onVazio?: (dia: string, hora: string) => void
  onConsulta?: (c: Consulta) => void
}) {
  const { clinica, cadastros } = useClinica()
  const tz = clinica.timezone
  const hoje = hojeYmd(tz)
  const [segunda, setSegunda] = useState(() => segundaDaSemana(hoje))
  const [filtro, setFiltro] = useState<string>('todas')
  const alturaSlot = compacta ? 26 : 40 // px por 30 min

  const dias = useMemo(() => {
    const abertos = new Set(clinica.horario.map((h) => h.weekday))
    return [0, 1, 2, 3, 4, 5, 6].filter((d) => abertos.has(d)).map((d) => ({ d, ymd: somarDias(segunda, d) }))
  }, [clinica.horario, segunda])

  const inicioMin = Math.min(...clinica.horario.map((h) => minutos(h.start_time)))
  const fimMin = Math.max(...clinica.horario.map((h) => minutos(h.end_time)))
  const linhas = Math.ceil((fimMin - inicioMin) / 30)

  const consultas = useQuery({
    queryKey: ['agenda', clinica.id, segunda],
    queryFn: () => api.get<Consulta[]>(`/clinics/${clinica.id}/appointments?de=${segunda}T00:00:00&ate=${somarDias(segunda, 7)}T00:00:00`),
  })

  const profs = cadastros.profissionais
  const visiveis = (consultas.data ?? []).filter((c) => filtro === 'todas' || c.professional_id === filtro)
  const faixas = filtro === 'todas' ? profs.map((p) => p.id) : [filtro]

  function cliqueVazio(e: MouseEvent<HTMLDivElement>, ymd: string) {
    if (!onVazio) return
    const y = e.clientY - e.currentTarget.getBoundingClientRect().top
    const m = inicioMin + Math.floor(y / alturaSlot) * 30
    onVazio(ymd, `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`)
  }

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Agenda da semana</h2>
          <p className="text-sm text-muted">
            {visiveis.length} consulta(s) · semana de {segunda.slice(8, 10)}/{segunda.slice(5, 7)}
            {consultas.isFetching && ' · atualizando…'}
          </p>
        </div>
        <div className="flex items-center gap-1">
          <button type="button" aria-label="Semana anterior" onClick={() => setSegunda(somarDias(segunda, -7))} className="rounded-lg p-1.5 hover:bg-surface-muted"><ChevronLeft className="size-5" /></button>
          <button type="button" onClick={() => setSegunda(segundaDaSemana(hoje))} className="rounded-lg px-2 py-1 text-sm hover:bg-surface-muted">Hoje</button>
          <button type="button" aria-label="Próxima semana" onClick={() => setSegunda(somarDias(segunda, 7))} className="rounded-lg p-1.5 hover:bg-surface-muted"><ChevronRight className="size-5" /></button>
        </div>
      </div>

      <div className="mb-3 flex flex-wrap gap-2">
        <Pilula ativa={filtro === 'todas'} onClick={() => setFiltro('todas')}>Todas</Pilula>
        {profs.map((p) => (
          <Pilula key={p.id} ativa={filtro === p.id} onClick={() => setFiltro(p.id)} cor={p.color ?? undefined}>{p.name}</Pilula>
        ))}
      </div>
      <div className="mb-2 flex flex-wrap gap-4 text-xs text-muted">
        <span className="flex items-center gap-1.5"><span className="h-3 w-1 rounded border-l-2 border-dashed border-current" />aguardando confirmação</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-1 rounded bg-current" />confirmada</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-[repeating-linear-gradient(45deg,var(--border)_0_3px,transparent_3px_6px)]" />pausa</span>
      </div>

      <div className="flex-1 overflow-auto rounded-2xl border border-line">
        <div className="grid min-w-[560px]" style={{ gridTemplateColumns: `52px repeat(${dias.length}, minmax(0, 1fr))` }}>
          {/* cabeçalho */}
          <div className="sticky top-0 z-10 border-b border-line bg-surface" />
          {dias.map(({ d, ymd }) => (
            <div key={ymd} className={`sticky top-0 z-10 border-b border-l border-line bg-surface py-2 text-center text-sm ${ymd === hoje ? 'text-primary' : ''}`}>
              <div className="font-medium">{DIAS[d]}</div>
              <div className="text-xs text-muted">{ymd.slice(8, 10)}/{ymd.slice(5, 7)}{ymd === hoje && ' · hoje'}</div>
            </div>
          ))}

          {/* coluna de horas */}
          <div className="relative" style={{ height: linhas * alturaSlot }}>
            {Array.from({ length: linhas }, (_, i) => {
              const m = inicioMin + i * 30
              return (
                <div key={i} className="absolute right-2 -translate-y-1/2 text-[11px] text-muted" style={{ top: i * alturaSlot }}>
                  {i > 0 && `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`}
                </div>
              )
            })}
          </div>

          {/* dias */}
          {dias.map(({ d, ymd }) => {
            const expediente = clinica.horario.find((h) => h.weekday === d)!
            const fechadoAntes = (minutos(expediente.start_time) - inicioMin) / 30 * alturaSlot
            const fechadoDepois = (fimMin - minutos(expediente.end_time)) / 30 * alturaSlot
            return (
              <div
                key={ymd}
                className={`relative border-l border-line ${onVazio ? 'cursor-pointer' : ''} ${ymd === hoje ? 'bg-primary-soft/30' : ''}`}
                style={{ height: linhas * alturaSlot, backgroundImage: `repeating-linear-gradient(to bottom, transparent 0 ${alturaSlot - 1}px, var(--border) ${alturaSlot - 1}px ${alturaSlot}px)` }}
                onClick={(e) => cliqueVazio(e, ymd)}
              >
                {fechadoAntes > 0 && <div className="absolute inset-x-0 top-0 bg-surface-muted" style={{ height: fechadoAntes }} />}
                {fechadoDepois > 0 && <div className="absolute inset-x-0 bottom-0 bg-surface-muted" style={{ height: fechadoDepois }} />}
                {clinica.pausas.filter((p) => p.weekday === d).map((p) => (
                  <div
                    key={p.start_time}
                    className="absolute inset-x-0 bg-[repeating-linear-gradient(45deg,var(--border)_0_3px,transparent_3px_8px)]"
                    style={{ top: (minutos(p.start_time) - inicioMin) / 30 * alturaSlot, height: (minutos(p.end_time) - minutos(p.start_time)) / 30 * alturaSlot }}
                    title="Pausa"
                  />
                ))}

                {visiveis.filter((c) => partes(c.starts_at, tz).ymd === ymd).map((c) => {
                  const ini = partes(c.starts_at, tz)
                  const fim = partes(c.ends_at, tz)
                  const top = ((ini.h * 60 + ini.min) - inicioMin) / 30 * alturaSlot
                  const altura = Math.max(((fim.h * 60 + fim.min) - (ini.h * 60 + ini.min)) / 30 * alturaSlot - 2, 18)
                  const faixa = Math.max(0, faixas.indexOf(c.professional_id))
                  const largura = 100 / faixas.length
                  const cor = c.cor ?? 'var(--primary)'
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={(e) => { e.stopPropagation(); onConsulta?.(c) }}
                      title={`${hora(c.starts_at, tz)} ${c.paciente} — ${c.procedimento} (${c.profissional})`}
                      className={`absolute overflow-hidden rounded-lg px-1.5 py-0.5 text-left text-[11px] leading-tight shadow-sm transition hover:brightness-95 ${
                        c.status === 'agendada' ? 'border-l-[3px] border-dashed' : 'border-l-[3px]'
                      } ${c.status === 'realizada' || c.status === 'faltou' ? 'opacity-60' : ''}`}
                      style={{
                        top: top + 1, height: altura, left: `calc(${faixa * largura}% + 2px)`, width: `calc(${largura}% - 4px)`,
                        borderLeftColor: cor, background: `color-mix(in srgb, ${cor} 16%, var(--surface))`,
                      }}
                    >
                      <div className="truncate font-semibold">{c.paciente}</div>
                      {!compacta && <div className="truncate text-muted">{c.procedimento}</div>}
                    </button>
                  )
                })}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function Pilula({ ativa, onClick, children, cor }: { ativa: boolean; onClick: () => void; children: ReactNode; cor?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition ${ativa ? 'border-text bg-text text-bg' : 'border-line text-muted hover:text-text'}`}
    >
      {cor && <span className="size-2 rounded-full" style={{ background: cor }} />}
      {children}
    </button>
  )
}
