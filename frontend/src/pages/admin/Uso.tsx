import { PrecosECotacao } from './PrecosECotacao'
import { useQuery } from '@tanstack/react-query'
import { PageHeader } from '../../components/PageHeader'
import { Selo } from '../../components/ui'
import { api, type UsoClinica } from '../../lib/api'
import { dolar, inteiro } from '../../lib/formato'

const COLUNAS: [keyof UsoClinica, string][] = [
  ['conversas', 'Conversas'],
  ['mensagens_recebidas', 'Mensagens recebidas'],
  ['respostas_ia', 'Respostas da IA'],
  ['tempo_medio_s', 'Tempo médio (s)'],
  ['falhas_ia', 'Falhas da IA'],
  ['consultas_pela_ia', 'Consultas marcadas pela IA'],
  ['automaticas_enviadas', 'Mensagens automáticas'],
  ['tokens_ia', 'Tokens da IA'],
  ['custo_clinica_usd', 'Custo na chave da clínica'],
  ['custo_plataforma_usd', 'Custo na chave da plataforma'],
]
const DINHEIRO = new Set<keyof UsoClinica>(['custo_clinica_usd', 'custo_plataforma_usd'])
const fmt = (k: keyof UsoClinica, v: unknown) =>
  v == null ? '—' : DINHEIRO.has(k) ? dolar(Number(v)) : k === 'tokens_ia' ? inteiro(Number(v)) : String(v)

export function AdminUso() {
  const q = useQuery({ queryKey: ['admin', 'uso'], queryFn: () => api.get<UsoClinica[]>('/admin/uso') })
  const total = (k: keyof UsoClinica) => (q.data ?? []).reduce((s, c) => s + (Number(c[k]) || 0), 0)

  return (
    <>
      <PageHeader titulo="Uso" subtitulo="Atividade de cada clínica neste mês" />
      <section className="overflow-x-auto rounded-3xl bg-surface">
        {q.isLoading ? <p className="p-6 text-sm text-muted">Carregando…</p> : (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-6 py-3 font-medium">Clínica</th>
                {COLUNAS.map(([, r]) => <th key={r} className="px-4 py-3 text-right font-medium">{r}</th>)}
              </tr>
            </thead>
            <tbody>
              {(q.data ?? []).map((c) => (
                <tr key={c.id} className="border-b border-line last:border-0">
                  <td className="px-6 py-3">
                    {c.name} {c.status !== 'ativa' && <Selo cor="vermelho">suspensa</Selo>}
                  </td>
                  {COLUNAS.map(([k]) => (
                    <td key={k} className={`px-4 py-3 text-right tabular-nums ${k === 'falhas_ia' && Number(c[k]) > 0 ? 'text-red-600' : ''}`}>
                      {fmt(k, c[k])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
            <tfoot className="border-t border-line font-medium">
              <tr>
                <td className="px-6 py-3">Total</td>
                {COLUNAS.map(([k]) => <td key={k} className="px-4 py-3 text-right tabular-nums">{k === 'tempo_medio_s' ? '' : fmt(k, total(k))}</td>)}
              </tr>
            </tfoot>
          </table>
        )}
      </section>
      <p className="mt-3 text-xs text-muted">
        Custos estimados pela tabela de preços abaixo. O gasto na chave da plataforma é seu (teste grátis e demonstração).
      </p>
      <PrecosECotacao />
    </>
  )
}
