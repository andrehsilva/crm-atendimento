import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Gauge, PauseCircle } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Secao } from '../../components/ui'
import { api, type SituacaoUsoIa, type UsoIa as Uso } from '../../lib/api'
import { useClinica } from '../../lib/clinica'
import { diaLegivel, dolar, inteiro, real } from '../../lib/formato'

const MES = (ym: string) => {
  const [a, m] = ym.split('-').map(Number)
  return new Date(a, m - 1, 1).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
}

/** Etapa 10B (D44, D45): quanto a IA gastou, estimado pela tabela de preços, e o teto do mês. */
export function UsoIa({ podeEditar }: { podeEditar: boolean }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const url = `/clinics/${clinica.id}/config/uso-ia`
  const q = useQuery({ queryKey: ['config', 'uso-ia', clinica.id], queryFn: () => api.get<Uso>(url) })
  const [teto, setTeto] = useState('')
  useEffect(() => { if (q.data) setTeto(q.data.situacao.teto_usd ? String(q.data.situacao.teto_usd) : '') }, [q.data])

  const salvar = useMutation({
    mutationFn: () => api.put<Uso>(`${url}/teto`, { teto_usd: teto.trim() ? Number(teto.replace(',', '.')) : null }),
    onSuccess: (u) => {
      qc.setQueryData(['config', 'uso-ia', clinica.id], u)
      qc.invalidateQueries({ queryKey: ['clinica'] })
      aviso.ok(u.situacao.teto_usd ? 'Teto salvo.' : 'Teto removido: a assistente não pausa por gasto.')
    },
    onError: aviso.erro,
  })

  if (!q.data) return <p className="text-sm text-muted">Carregando…</p>
  const u = q.data
  const s = u.situacao
  const emReais = (v: number) => (u.cotacao_brl ? real(v * u.cotacao_brl) : null)
  const tetoValido = !teto.trim() || Number(teto.replace(',', '.')) > 0

  function enviar(e: FormEvent) {
    e.preventDefault()
    if (tetoValido) salvar.mutate()
  }

  return (
    <div className="grid gap-6">
      <Secao titulo="Este mês" icone={<Gauge className="size-5" />}>
        <div className="flex flex-wrap items-end gap-x-10 gap-y-4">
          <div>
            <div className="text-4xl font-semibold tabular-nums tracking-tight">{dolar(s.gasto_usd)}</div>
            <div className="mt-1 text-sm text-muted">
              gasto estimado{emReais(s.gasto_usd) && <> · cerca de {emReais(s.gasto_usd)}</>}
            </div>
          </div>
          {s.teto_usd && (
            <div className="min-w-64 flex-1">
              <Medidor s={s} />
            </div>
          )}
        </div>
        {u.sem_preco.length > 0 && (
          <p role="status" className="mt-5 flex gap-2 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            <span>
              Sem preço cadastrado para {u.sem_preco.map((p) => p.model).join(', ')}: essas respostas não entram no custo
              e o teto não consegue agir sobre elas. O administrador da plataforma cadastra o preço.
            </span>
          </p>
        )}
        <p className="mt-4 text-xs text-muted">
          Valor estimado pela tabela de preços da plataforma. O valor oficial é o da conta da clínica no provedor de IA.
        </p>
      </Secao>

      <Secao titulo="Teto mensal" icone={<PauseCircle className="size-5" />}>
        <form onSubmit={enviar} className="flex flex-wrap items-end gap-3">
          <div className="w-48">
            <Campo rotulo="Teto em US$" ajuda="Vazio = sem teto.">
              <Entrada inputMode="decimal" disabled={!podeEditar} value={teto} placeholder="ex.: 20"
                onChange={(e) => setTeto(e.target.value)} />
            </Campo>
          </div>
          {podeEditar && <Botao type="submit" disabled={!tetoValido || salvar.isPending}>{salvar.isPending ? 'Salvando…' : 'Salvar teto'}</Botao>}
        </form>
        <p className="mt-3 max-w-2xl text-sm text-muted">
          Aos 80% aparece um aviso no painel. Aos 100% a assistente pausa até o fim do mês: as conversas vão para a equipe e
          o cliente é avisado. Lembretes, confirmações e aniversários continuam, porque não usam IA.
        </p>
      </Secao>

      <Secao titulo="Dia a dia deste mês">
        {u.dias.length === 0 ? <p className="text-sm text-muted">Nenhuma resposta da assistente neste mês ainda.</p> : (
          <Tabela cabecalho={['Dia', 'Respostas', 'Áudio (min)', 'Tokens de entrada', 'Tokens de saída', 'Custo (US$)']}
            linhas={u.dias.map((d) => [diaLegivel(d.dia), inteiro(d.respostas), (d.audio_segundos / 60).toLocaleString('pt-BR', { maximumFractionDigits: 1 }), inteiro(d.tokens_entrada), inteiro(d.tokens_saida), dolar(d.custo_usd)])} />
        )}
      </Secao>

      {u.meses.length > 0 && (
        <Secao titulo="Últimos meses">
          <Tabela cabecalho={['Mês', 'Respostas', 'Tokens', 'Custo (US$)', ...(u.cotacao_brl ? ['Custo (R$)'] : [])]}
            linhas={u.meses.map((m) => [MES(m.mes), inteiro(m.respostas), inteiro(m.tokens), dolar(m.custo_usd),
              ...(u.cotacao_brl ? [real(m.custo_usd * u.cotacao_brl)] : [])])} />
        </Secao>
      )}
    </div>
  )
}

/** Barra do gasto x teto. Estado sempre com ícone + texto, nunca só cor. */
function Medidor({ s }: { s: SituacaoUsoIa }) {
  const pct = Math.min(s.pct ?? 0, 100)
  const cor = s.nivel === 'pausada' ? 'bg-red-600' : s.nivel === 'aviso' ? 'bg-amber-500' : 'bg-primary'
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-3 text-sm">
        <span className="flex items-center gap-1.5 font-medium">
          {s.nivel === 'pausada' && <><PauseCircle className="size-4 text-red-600" /> Assistente pausada</>}
          {s.nivel === 'aviso' && <><AlertTriangle className="size-4 text-amber-600" /> Perto do teto</>}
          {s.nivel === 'ok' && 'Dentro do teto'}
        </span>
        <span className="tabular-nums text-muted">{(s.pct ?? 0).toLocaleString('pt-BR')}% de {dolar(s.teto_usd ?? 0)}</span>
      </div>
      <div role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct)} aria-label="Gasto do mês em relação ao teto"
        className="h-2.5 overflow-hidden rounded-full bg-surface-muted">
        <div className={`h-full rounded-full ${cor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function Tabela({ cabecalho, linhas }: { cabecalho: string[]; linhas: string[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-line text-xs text-muted">
          <tr>{cabecalho.map((c, i) => <th key={c} className={`py-2 pr-4 font-medium ${i ? 'text-right' : ''}`}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {linhas.map((l) => (
            <tr key={l[0]} className="border-b border-line last:border-0">
              {l.map((v, i) => <td key={i} className={`py-2 pr-4 ${i ? 'text-right tabular-nums' : 'first-letter:uppercase'}`}>{v}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Aviso no topo do painel: 80% do teto ou assistente pausada (D45). */
export function AvisoTetoIa() {
  const { clinica } = useClinica()
  const s = clinica.uso_ia
  if (s.nivel === 'ok') return null
  const pausada = s.nivel === 'pausada'
  return (
    <p role="status" className={`mb-4 flex gap-2 rounded-2xl px-4 py-3 text-sm ${pausada
      ? 'bg-red-50 text-red-900 dark:bg-red-950/40 dark:text-red-200'
      : 'bg-amber-50 text-amber-900 dark:bg-amber-950/40 dark:text-amber-200'}`}>
      {pausada ? <PauseCircle className="mt-0.5 size-4 shrink-0" /> : <AlertTriangle className="mt-0.5 size-4 shrink-0" />}
      {pausada
        ? 'A assistente está pausada: o teto de gasto do mês foi atingido. As conversas vão para a equipe. Para voltar, aumente o teto em Configurações › Uso da IA.'
        : `A assistente já usou ${(s.pct ?? 0).toLocaleString('pt-BR')}% do teto de gasto do mês (${dolar(s.gasto_usd)} de ${dolar(s.teto_usd ?? 0)}).`}
    </p>
  )
}
