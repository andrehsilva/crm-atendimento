// Formatação para exibir em português, sempre no fuso da clínica.

export function telefone(e164: string): string {
  const d = e164.replace(/\D/g, '')
  const local = d.startsWith('55') ? d.slice(2) : d
  if (local.length === 11) return `(${local.slice(0, 2)}) ${local.slice(2, 7)}-${local.slice(7)}`
  if (local.length === 10) return `(${local.slice(0, 2)}) ${local.slice(2, 6)}-${local.slice(6)}`
  return e164
}

export function hora(iso: string, tz: string): string {
  return new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit', timeZone: tz }).format(new Date(iso))
}

export function dataCurta(iso: string, tz: string): string {
  return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', timeZone: tz }).format(new Date(iso))
}

export function dataHora(iso: string, tz: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    weekday: 'short', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: tz,
  }).format(new Date(iso))
}

/** Partes da data no fuso da clínica: {ano, mes, dia, h, min, diaSemana(0=seg)} */
export function partes(iso: string | Date, tz: string) {
  const f = new Intl.DateTimeFormat('en-CA', {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    weekday: 'short', timeZone: tz,
  })
  const p = Object.fromEntries(f.formatToParts(new Date(iso)).map((x) => [x.type, x.value]))
  const dias = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  return {
    ano: Number(p.year), mes: Number(p.month), dia: Number(p.day),
    h: Number(p.hour), min: Number(p.minute), diaSemana: dias.indexOf(p.weekday),
    ymd: `${p.year}-${p.month}-${p.day}`,
  }
}

/** Soma dias a uma data "AAAA-MM-DD" (sem fuso, calendário puro). */
export function somarDias(ymd: string, n: number): string {
  const [a, m, d] = ymd.split('-').map(Number)
  const dt = new Date(Date.UTC(a, m - 1, d + n))
  return dt.toISOString().slice(0, 10)
}

/** Segunda-feira da semana que contém `ymd`. */
export function segundaDaSemana(ymd: string): string {
  const [a, m, d] = ymd.split('-').map(Number)
  const ds = (new Date(Date.UTC(a, m - 1, d)).getUTCDay() + 6) % 7
  return somarDias(ymd, -ds)
}

export function hojeYmd(tz: string): string {
  return partes(new Date(), tz).ymd
}

export function diaLegivel(ymd: string): string {
  const [a, m, d] = ymd.split('-').map(Number)
  return new Intl.DateTimeFormat('pt-BR', { weekday: 'long', day: '2-digit', month: '2-digit', timeZone: 'UTC' }).format(
    new Date(Date.UTC(a, m - 1, d)),
  )
}

export function horasDesde(iso: string): number {
  return Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000))
}

export function tempoParado(iso: string): string {
  const h = horasDesde(iso)
  if (h < 1) return 'agora há pouco'
  if (h < 72) return `há ${h}h`
  return `há ${Math.floor(h / 24)}d`
}
