import { useState } from 'react'
import { CalendarX, Download, FileSpreadsheet, TrendingUp, UserRoundSearch, type LucideIcon } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Campo, Entrada, Secao, Seletor } from '../components/ui'
import { useClinica } from '../lib/clinica'
import { hojeYmd } from '../lib/formato'
import { useTermos } from '../lib/termos'

type Tipo = 'recall' | 'atendimentos' | 'producao' | 'faltas'
type Periodo = 'mes' | 'mes_passado' | '3meses' | 'outro'

function intervalo(p: Periodo, hoje: string, de: string, ate: string): [string, string] {
  const [a, m] = hoje.split('-').map(Number)
  const ymd = (y: number, mm: number, d: number) => new Date(Date.UTC(y, mm - 1, d)).toISOString().slice(0, 10)
  if (p === 'mes') return [ymd(a, m, 1), hoje]
  if (p === 'mes_passado') return [ymd(a, m - 1, 1), ymd(a, m, 0)]
  if (p === '3meses') return [ymd(a, m - 2, 1), hoje]
  return [de || hoje, ate || hoje]
}

/** Etapa 15A (D73–D75): relatórios em Excel. Só o administrador da clínica vê esta tela; cada download fica registrado. */
export function Relatorios() {
  const { clinica, cadastros } = useClinica()
  const pal = useTermos()
  const hoje = hojeYmd(clinica.timezone)
  const [periodo, setPeriodo] = useState<Periodo>('mes')
  const [de, setDe] = useState('')
  const [ate, setAte] = useState('')
  const [prof, setProf] = useState('')
  const [meses, setMeses] = useState(6)
  const [ini, fim] = intervalo(periodo, hoje, de, ate)

  const url = (t: Tipo) => {
    const q = new URLSearchParams(t === 'recall' ? { meses: String(meses) } : { de: ini, ate: fim, ...(prof ? { profissional: prof } : {}) })
    return `/api/clinics/${clinica.id}/relatorios/${t}.xlsx?${q}`
  }
  const cards: { tipo: Tipo; titulo: string; texto: string; icone: LucideIcon }[] = [
    { tipo: 'recall', titulo: `${pal.Clientes} para chamar de volta`, icone: UserRoundSearch,
      texto: `Quem não vem há ${meses} meses ou mais e não tem nada marcado. Boa lista para uma campanha de retorno.` },
    { tipo: 'atendimentos', titulo: `${pal.Atendimentos} do período`, icone: FileSpreadsheet,
      texto: 'Um por linha: data, paciente, procedimento, profissional, situação, quem marcou e valor de tabela.' },
    { tipo: 'producao', titulo: 'Produção', icone: TrendingUp,
      texto: 'Por profissional, por procedimento e por mês: realizados, faltas, comparecimento e valor estimado.' },
    { tipo: 'faltas', titulo: 'Faltas e cancelamentos', icone: CalendarX,
      texto: 'A lista, a taxa por dia da semana e por horário, e quem falta com frequência.' },
  ]

  return (
    <>
      <PageHeader titulo="Relatórios" subtitulo="Baixe em Excel. Valores estimados pela tabela de preços dos procedimentos." />
      <Secao className="mb-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Campo rotulo="Período">
            <Seletor value={periodo} onChange={(e) => setPeriodo(e.target.value as Periodo)}>
              <option value="mes">Este mês</option>
              <option value="mes_passado">Mês passado</option>
              <option value="3meses">Últimos 3 meses</option>
              <option value="outro">Outro período</option>
            </Seletor>
          </Campo>
          {periodo === 'outro' && (
            <>
              <Campo rotulo="De"><Entrada type="date" value={de} max={ate || hoje} onChange={(e) => setDe(e.target.value)} /></Campo>
              <Campo rotulo="Até"><Entrada type="date" value={ate} min={de} onChange={(e) => setAte(e.target.value)} /></Campo>
            </>
          )}
          <Campo rotulo={pal.Profissional}>
            <Seletor value={prof} onChange={(e) => setProf(e.target.value)}>
              <option value="">Todos</option>
              {cadastros.profissionais.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </Seletor>
          </Campo>
          <Campo rotulo="Chamar de volta após">
            <Seletor value={meses} onChange={(e) => setMeses(Number(e.target.value))}>
              {[3, 4, 6, 9, 12, 18, 24].map((m) => <option key={m} value={m}>{m} meses</option>)}
            </Seletor>
          </Campo>
        </div>
      </Secao>
      <div className="grid gap-4 md:grid-cols-2">
        {cards.map(({ tipo, titulo, texto, icone: Icone }) => (
          <Secao key={tipo} titulo={titulo} icone={<Icone className="size-5" />}>
            <p className="mb-4 text-sm text-muted">{texto}</p>
            <a href={url(tipo)} download
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-contrast hover:opacity-90">
              <Download className="size-4" /> Baixar Excel
            </a>
          </Secao>
        ))}
      </div>
      <p className="mt-4 text-xs text-muted">Os relatórios trazem dados pessoais dos {pal.clientes}: guarde os arquivos com cuidado. Cada download fica registrado.</p>
    </>
  )
}
