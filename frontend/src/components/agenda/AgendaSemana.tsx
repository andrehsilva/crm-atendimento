import { useEffect, useMemo, useRef, useState, type MouseEvent, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-react'
import { api, type Consulta } from '../../lib/api'
import { useClinica } from '../../lib/clinica'
import { hojeYmd, hora, partes, segundaDaSemana, somarDias } from '../../lib/formato'

const DIAS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
const DIAS_LONGOS = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
const MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
const minutos = (hhmm: string) => Number(hhmm.slice(0, 2)) * 60 + Number(hhmm.slice(3, 5))
const hhmm = (m: number) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
const diaDaSemana = (ymd: string) => (new Date(`${ymd}T12:00:00Z`).getUTCDay() + 6) % 7 // 0 = segunda
const num = (ymd: string) => Number(ymd.slice(8, 10))
const mes = (ymd: string) => Number(ymd.slice(5, 7)) - 1

type Modo = 'dia' | 'semana'

function tituloPeriodo(modo: Modo, ini: string, fim: string): string {
  if (modo === 'dia') return `${DIAS_LONGOS[diaDaSemana(ini)]}, ${num(ini)} de ${MESES[mes(ini)]}`
  const ano = ini.slice(0, 4)
  if (mes(ini) === mes(fim)) return `${num(ini)} – ${num(fim)} de ${MESES[mes(ini)]} de ${ano}`
  return `${num(ini)} de ${MESES[mes(ini)].slice(0, 3)}. – ${num(fim)} de ${MESES[mes(fim)].slice(0, 3)}. de ${fim.slice(0, 4)}`
}

function modoInicial(): Modo {
  try {
    const salvo = localStorage.getItem('isis:agenda:modo')
    if (salvo === 'dia' || salvo === 'semana') return salvo
  } catch { /* sem armazenamento: segue o padrão */ }
  return typeof window !== 'undefined' && window.innerWidth < 768 ? 'dia' : 'semana'
}

/** Agenda por dia ou por semana (spec 06 / imagem 03). Atualiza sozinha pelos avisos em tempo real. */
export function AgendaSemana({
  compacta = false,
  onVazio,
  onConsulta,
}: {
  compacta?: boolean
  onVazio?: (dia: string, hora: string, professionalId?: string) => void
  onConsulta?: (c: Consulta) => void
}) {
  const { clinica, cadastros } = useClinica()
  const tz = clinica.timezone
  const hoje = hojeYmd(tz)
  const [modo, setModoBruto] = useState<Modo>(modoInicial)
  const [dia, setDia] = useState(hoje)
  const [filtro, setFiltro] = useState<string>('todas')
  const [agora, setAgora] = useState(() => partes(new Date(), tz))
  const seletorData = useRef<HTMLInputElement>(null)
  const alturaSlot = compacta ? 26 : 44 // px por 30 min
  const segunda = segundaDaSemana(dia)

  useEffect(() => {
    const t = setInterval(() => setAgora(partes(new Date(), tz)), 60_000)
    return () => clearInterval(t)
  }, [tz])

  function setModo(m: Modo) {
    setModoBruto(m)
    try { localStorage.setItem('isis:agenda:modo', m) } catch { /* ignora */ }
  }

  const abertos = useMemo(() => new Set(clinica.horario.map((h) => h.weekday)), [clinica.horario])
  const diasDaSemana = useMemo(
    () => [0, 1, 2, 3, 4, 5, 6].filter((d) => abertos.has(d)).map((d) => ({ d, ymd: somarDias(segunda, d) })),
    [abertos, segunda],
  )

  /** Próximo dia em que a clínica abre (pulando os fechados). */
  function proximoAberto(ymd: string, passo: 1 | -1): string {
    let x = ymd
    for (let i = 0; i < 7; i++) {
      x = somarDias(x, passo)
      if (abertos.has(diaDaSemana(x))) return x
    }
    return somarDias(ymd, passo)
  }

  const andar = (passo: 1 | -1) => setDia(modo === 'dia' ? proximoAberto(dia, passo) : somarDias(dia, 7 * passo))
  const abrirDia = (ymd: string) => { setDia(ymd); setModo('dia') }

  const inicioMin = Math.min(...clinica.horario.map((h) => minutos(h.start_time)))
  const fimMin = Math.max(...clinica.horario.map((h) => minutos(h.end_time)))
  const linhas = Math.ceil((fimMin - inicioMin) / 30)
  const alturaGrade = linhas * alturaSlot

  const consultas = useQuery({
    queryKey: ['agenda', clinica.id, segunda],
    queryFn: () => api.get<Consulta[]>(`/clinics/${clinica.id}/appointments?de=${segunda}T00:00:00&ate=${somarDias(segunda, 7)}T00:00:00`),
  })

  const profs = cadastros.profissionais
  const visiveis = (consultas.data ?? []).filter((c) => filtro === 'todas' || c.professional_id === filtro)
  const faixas = filtro === 'todas' ? profs.map((p) => p.id) : [filtro]
  const porDia = useMemo(() => {
    const m = new Map<string, Consulta[]>()
    for (const c of visiveis) {
      const ymd = partes(c.starts_at, tz).ymd
      m.set(ymd, [...(m.get(ymd) ?? []), c])
    }
    return m
  }, [visiveis, tz])
  const ativas = (lista: Consulta[] = []) => lista.filter((c) => c.status !== 'cancelada').length

  const fechadoHoje = modo === 'dia' && !abertos.has(diaDaSemana(dia))
  const totalPeriodo = modo === 'dia' ? ativas(porDia.get(dia)) : diasDaSemana.reduce((s, x) => s + ativas(porDia.get(x.ymd)), 0)
  const fimSemana = diasDaSemana[diasDaSemana.length - 1]?.ymd ?? somarDias(segunda, 6)
  const titulo = tituloPeriodo(modo, modo === 'dia' ? dia : diasDaSemana[0]?.ymd ?? segunda, fimSemana)

  // Colunas da grade: dias (semana) ou profissionais (dia)
  const colunas = modo === 'semana'
    ? diasDaSemana.map(({ d, ymd }) => ({ chave: ymd, ymd, d, prof: undefined as string | undefined }))
    : (filtro === 'todas' ? profs : profs.filter((p) => p.id === filtro)).map((p) => ({ chave: p.id, ymd: dia, d: diaDaSemana(dia), prof: p.id }))

  function cliqueVazio(e: MouseEvent<HTMLDivElement>, ymd: string, prof?: string) {
    if (!onVazio) return
    const y = e.clientY - e.currentTarget.getBoundingClientRect().top
    onVazio(ymd, hhmm(inicioMin + Math.floor(y / alturaSlot) * 30), prof)
  }

  function escolherData() {
    const el = seletorData.current
    if (!el) return
    try { el.showPicker() } catch { el.click() }
  }

  const minAgora = agora.h * 60 + agora.min
  const linhaAgora = minAgora >= inicioMin && minAgora <= fimMin ? ((minAgora - inicioMin) / 30) * alturaSlot : null

  function blocoDia(d: number, ymd: string, cabecalho = false) {
    const n = ativas(porDia.get(ymd))
    const selecionado = modo === 'dia' && ymd === dia
    const ehHoje = ymd === hoje
    const passado = ymd < hoje
    return (
      <button key={ymd} type="button" role={cabecalho ? undefined : 'tab'} aria-selected={cabecalho ? undefined : selecionado}
        onClick={() => abrirDia(ymd)} title={`Ver só ${DIAS_LONGOS[d]}, ${num(ymd)}/${ymd.slice(5, 7)}`}
        className={`flex w-full flex-col items-center px-1 py-2 transition ${cabecalho ? '' : 'rounded-2xl'} ${
          selecionado ? 'bg-primary text-primary-contrast' : 'hover:bg-surface-muted'
        } ${passado && !selecionado ? 'opacity-55' : ''}`}>
        <span className={`text-xs font-medium ${selecionado ? '' : ehHoje ? 'text-primary' : 'text-muted'}`}>{DIAS[d]}</span>
        <span className={`mt-0.5 grid size-9 place-items-center rounded-full text-lg font-bold leading-none ${
          ehHoje && !selecionado ? 'bg-primary text-primary-contrast' : ''}`}>{num(ymd)}</span>
        <span className={`mt-1 h-4 text-[11px] ${selecionado ? 'opacity-90' : 'text-muted'}`}>
          {n > 0 ? `${n} ${n === 1 ? 'consulta' : 'consultas'}` : ''}
        </span>
      </button>
    )
  }

  return (
    <div className="flex h-full flex-col">
      {/* Barra: período + navegação */}
      <div className="mb-4 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <h2 className={`font-semibold first-letter:uppercase ${compacta ? 'text-base' : 'text-xl'}`}>{titulo}</h2>
          <p className="text-sm text-muted">
            {fechadoHoje ? 'Clínica fechada neste dia' : totalPeriodo === 0 ? 'Nenhuma consulta' : `${totalPeriodo} ${totalPeriodo === 1 ? 'consulta' : 'consultas'}`}
            {consultas.isFetching && <span className="ml-2 text-xs">atualizando…</span>}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div role="group" aria-label="Visão da agenda" className="flex rounded-xl bg-surface-muted p-1">
            {(['dia', 'semana'] as const).map((m) => (
              <button key={m} type="button" aria-pressed={modo === m} onClick={() => setModo(m)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${modo === m ? 'bg-surface text-text shadow-sm' : 'text-muted hover:text-text'}`}>
                {m === 'dia' ? 'Dia' : 'Semana'}
              </button>
            ))}
          </div>

          <div className="flex items-center rounded-xl border border-line">
            <button type="button" aria-label={modo === 'dia' ? 'Dia anterior' : 'Semana anterior'} onClick={() => andar(-1)}
              className="grid size-9 place-items-center rounded-l-xl text-muted hover:bg-surface-muted hover:text-text"><ChevronLeft className="size-5" /></button>
            <button type="button" onClick={() => setDia(hoje)} disabled={modo === 'dia' ? dia === hoje : segunda === segundaDaSemana(hoje)}
              className="h-9 border-x border-line px-3 text-sm font-medium hover:bg-surface-muted disabled:text-muted disabled:hover:bg-transparent">Hoje</button>
            <button type="button" aria-label={modo === 'dia' ? 'Próximo dia' : 'Próxima semana'} onClick={() => andar(1)}
              className="grid size-9 place-items-center rounded-r-xl text-muted hover:bg-surface-muted hover:text-text"><ChevronRight className="size-5" /></button>
          </div>

          <div className="relative">
            <button type="button" onClick={escolherData} aria-label="Ir para uma data"
              className="grid size-9 place-items-center rounded-xl border border-line text-muted hover:bg-surface-muted hover:text-text">
              <CalendarDays className="size-[18px]" />
            </button>
            <input ref={seletorData} type="date" value={dia} tabIndex={-1} aria-hidden
              onChange={(e) => e.target.value && setDia(e.target.value)}
              className="pointer-events-none absolute inset-0 opacity-0" />
          </div>
        </div>
      </div>

      {/* Dias da semana (visão do dia): clicar troca o dia */}
      {modo === 'dia' && (
        <div role="tablist" aria-label="Dias da semana" className="mb-4 grid gap-1.5"
          style={{ gridTemplateColumns: `repeat(${diasDaSemana.length}, minmax(0, 1fr))` }}>
          {diasDaSemana.map(({ d, ymd }) => blocoDia(d, ymd))}
        </div>
      )}

      {/* Profissionais + legenda */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          <Pilula ativa={filtro === 'todas'} onClick={() => setFiltro('todas')}>Todos</Pilula>
          {profs.map((p) => (
            <Pilula key={p.id} ativa={filtro === p.id} onClick={() => setFiltro(p.id)} cor={p.color ?? undefined}>{p.name}</Pilula>
          ))}
        </div>
        {!compacta && (
          <div className="flex flex-wrap gap-4 text-xs text-muted">
            <span className="flex items-center gap-1.5"><span className="h-3 w-1 rounded border-l-2 border-dashed border-current" />aguardando confirmação</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-1 rounded bg-current" />confirmada</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-[repeating-linear-gradient(45deg,var(--border)_0_3px,transparent_3px_6px)]" />pausa</span>
          </div>
        )}
      </div>

      {fechadoHoje || colunas.length === 0 ? (
        <div className="grid flex-1 place-items-center rounded-2xl border border-dashed border-line p-8 text-center text-sm text-muted">
          {fechadoHoje ? (
            <div>
              <p>A clínica não abre neste dia.</p>
              <button type="button" onClick={() => setDia(proximoAberto(dia, 1))} className="mt-2 font-medium text-primary hover:underline">Ir para o próximo dia de atendimento</button>
            </div>
          ) : 'Nenhum profissional cadastrado.'}
        </div>
      ) : (
        <div className="flex-1 overflow-auto rounded-2xl border border-line">
          <div className={`grid ${modo === 'semana' ? 'min-w-[560px]' : ''}`} style={{ gridTemplateColumns: `56px repeat(${colunas.length}, minmax(${modo === 'dia' ? 160 : 0}px, 1fr))` }}>
            {/* cabeçalho das colunas */}
            <div className="sticky top-0 z-20 border-b border-line bg-surface" />
            {colunas.map((col) => {
              if (col.prof) {
                const p = profs.find((x) => x.id === col.prof)!
                const n = ativas(porDia.get(dia)?.filter((c) => c.professional_id === p.id))
                return (
                  <div key={col.chave} className="sticky top-0 z-20 flex items-center justify-center gap-2 border-b border-l border-line bg-surface px-2 py-2.5 text-sm">
                    <span className="size-2.5 shrink-0 rounded-full" style={{ background: p.color ?? 'var(--primary)' }} />
                    <span className="truncate font-medium">{p.name}</span>
                    <span className="text-xs text-muted">{n || ''}</span>
                  </div>
                )
              }
              return (
                <div key={col.chave} className={`sticky top-0 z-20 border-b border-l border-line bg-surface ${col.ymd === hoje ? 'bg-primary-soft/40' : ''}`}>
                  {blocoDia(col.d, col.ymd, true)}
                </div>
              )
            })}

            {/* coluna de horas */}
            <div className="relative border-r border-transparent" style={{ height: alturaGrade }}>
              {Array.from({ length: linhas }, (_, i) => {
                const m = inicioMin + i * 30
                const cheia = m % 60 === 0
                return (
                  <div key={i} className={`absolute right-2 text-[11px] tabular-nums ${cheia ? 'font-medium text-text' : 'text-muted/70'}`}
                    style={{ top: i * alturaSlot + 3 }}>
                    {hhmm(m)}
                  </div>
                )
              })}
            </div>

            {/* corpo */}
            {colunas.map((col) => {
              const expediente = clinica.horario.find((h) => h.weekday === col.d)!
              const fechadoAntes = ((minutos(expediente.start_time) - inicioMin) / 30) * alturaSlot
              const fechadoDepois = ((fimMin - minutos(expediente.end_time)) / 30) * alturaSlot
              const ehHoje = col.ymd === hoje
              const daColuna = (porDia.get(col.ymd) ?? []).filter((c) => !col.prof || c.professional_id === col.prof)
              const lanes = col.prof ? [col.prof] : faixas
              return (
                <div
                  key={col.chave}
                  className={`relative border-l border-line ${onVazio ? 'cursor-pointer' : ''} ${ehHoje && modo === 'semana' ? 'bg-primary-soft/25' : ''}`}
                  style={{
                    height: alturaGrade,
                    backgroundImage: `repeating-linear-gradient(to bottom, var(--border) 0 1px, transparent 1px ${alturaSlot * 2}px), repeating-linear-gradient(to bottom, transparent 0 ${alturaSlot}px, color-mix(in srgb, var(--border) 45%, transparent) ${alturaSlot}px ${alturaSlot + 1}px, transparent ${alturaSlot + 1}px ${alturaSlot * 2}px)`,
                  }}
                  onClick={(e) => cliqueVazio(e, col.ymd, col.prof)}
                >
                  {fechadoAntes > 0 && <div className="absolute inset-x-0 top-0 bg-surface-muted" style={{ height: fechadoAntes }} />}
                  {fechadoDepois > 0 && <div className="absolute inset-x-0 bottom-0 bg-surface-muted" style={{ height: fechadoDepois }} />}
                  {clinica.pausas.filter((p) => p.weekday === col.d).map((p) => (
                    <div
                      key={p.start_time}
                      className="absolute inset-x-0 bg-[repeating-linear-gradient(45deg,var(--border)_0_3px,transparent_3px_8px)]"
                      style={{ top: ((minutos(p.start_time) - inicioMin) / 30) * alturaSlot, height: ((minutos(p.end_time) - minutos(p.start_time)) / 30) * alturaSlot }}
                      title="Pausa"
                    />
                  ))}

                  {daColuna.map((c) => {
                    const ini = partes(c.starts_at, tz)
                    const fim = partes(c.ends_at, tz)
                    const top = ((ini.h * 60 + ini.min - inicioMin) / 30) * alturaSlot
                    const altura = Math.max(((fim.h * 60 + fim.min - (ini.h * 60 + ini.min)) / 30) * alturaSlot - 2, 18)
                    const faixa = Math.max(0, lanes.indexOf(c.professional_id))
                    const largura = 100 / lanes.length
                    const cor = c.cor ?? 'var(--primary)'
                    const largo = modo === 'dia' || lanes.length === 1
                    return (
                      <button
                        key={c.id}
                        type="button"
                        onClick={(e) => { e.stopPropagation(); onConsulta?.(c) }}
                        title={`${hora(c.starts_at, tz)} ${c.paciente} — ${c.procedimento} (${c.profissional})`}
                        className={`absolute z-10 overflow-hidden rounded-lg px-1.5 py-0.5 text-left text-[11px] leading-tight shadow-sm transition hover:brightness-95 ${
                          c.status === 'agendada' ? 'border-l-[3px] border-dashed' : 'border-l-[3px]'
                        } ${c.status === 'realizada' || c.status === 'faltou' || c.status === 'cancelada' ? 'opacity-60' : ''} ${c.status === 'cancelada' ? 'line-through' : ''}`}
                        style={{
                          top: top + 1, height: altura, left: `calc(${faixa * largura}% + 2px)`, width: `calc(${largura}% - 4px)`,
                          borderLeftColor: cor, background: `color-mix(in srgb, ${cor} 16%, var(--surface))`,
                        }}
                      >
                        <div className="truncate font-semibold">
                          {largo && <span className="mr-1 font-normal tabular-nums text-muted">{hora(c.starts_at, tz)}</span>}
                          {c.paciente}
                        </div>
                        {!compacta && <div className="truncate text-muted">{c.procedimento}</div>}
                      </button>
                    )
                  })}

                  {ehHoje && linhaAgora !== null && (
                    <div className="pointer-events-none absolute inset-x-0 z-10" style={{ top: linhaAgora }} aria-hidden>
                      <div className="relative h-0.5 bg-primary">
                        <span className="absolute -left-1 -top-[3px] size-2 rounded-full bg-primary" />
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function Pilula({ ativa, onClick, children, cor }: { ativa: boolean; onClick: () => void; children: ReactNode; cor?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={ativa}
      className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition ${ativa ? 'border-text bg-text text-bg' : 'border-line text-muted hover:text-text'}`}
    >
      {cor && <span className="size-2 rounded-full" style={{ background: cor }} />}
      {children}
    </button>
  )
}
