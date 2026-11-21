import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Coins, Trash2 } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Secao, Seletor } from '../../components/ui'
import { api, type Precos } from '../../lib/api'
import { dolar } from '../../lib/formato'

const PROVEDORES = [['openai', 'OpenAI'], ['google', 'Google (Gemini)'], ['opencode', 'OpenCode'], ['openrouter', 'OpenRouter']] as const
const VAZIO = { provedor: 'openai', modelo: '', entrada_usd: '', saida_usd: '', cache_usd: '' }
const num = (v: string) => Number(v.replace(',', '.'))

/** Etapa 10B (D44): preço de cada modelo (US$ por 1 milhão de tokens) e cotação do dólar. Vale para as próximas respostas. */
export function PrecosECotacao() {
  const aviso = useAviso()
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin', 'precos'], queryFn: () => api.get<Precos>('/admin/precos') })
  const [f, setF] = useState(VAZIO)
  const [cotacao, setCotacao] = useState('')
  useEffect(() => { if (q.data) setCotacao(q.data.cotacao_brl ? String(q.data.cotacao_brl).replace('.', ',') : '') }, [q.data])
  const depois = (p: Precos) => { qc.setQueryData(['admin', 'precos'], p); qc.invalidateQueries({ queryKey: ['admin', 'uso'] }) }

  const salvar = useMutation({
    mutationFn: () => api.put<Precos>('/admin/precos', {
      provedor: f.provedor, modelo: f.modelo.trim(), entrada_usd: num(f.entrada_usd), saida_usd: num(f.saida_usd),
      cache_usd: f.cache_usd.trim() ? num(f.cache_usd) : null,
    }),
    onSuccess: (p) => { depois(p); setF(VAZIO); aviso.ok('Preço salvo. Vale para as próximas respostas.') },
    onError: aviso.erro,
  })
  const apagar = useMutation({
    mutationFn: (p: { provider: string; model: string }) => api.delete<Precos>(`/admin/precos/${p.provider}/${encodeURIComponent(p.model)}`),
    onSuccess: depois,
    onError: aviso.erro,
  })
  const salvarCotacao = useMutation({
    mutationFn: () => api.put<Precos>('/admin/cotacao', { cotacao_brl: cotacao.trim() ? num(cotacao) : null }),
    onSuccess: (p) => { depois(p); aviso.ok('Cotação salva.') },
    onError: aviso.erro,
  })
  const numeroOk = (v: string, opcional = false) => (opcional && !v.trim()) || (v.trim() !== '' && num(v) >= 0)
  const valido = !!f.modelo.trim() && numeroOk(f.entrada_usd) && numeroOk(f.saida_usd) && numeroOk(f.cache_usd, true)
  const enviar = (e: FormEvent) => { e.preventDefault(); if (valido) salvar.mutate() }
  const precos = q.data?.precos ?? []

  return (
    <div className="mt-8 grid gap-6 xl:grid-cols-[1fr_20rem]">
      <Secao titulo="Preços dos modelos" icone={<Coins className="size-5" />}>
        <p className="mb-4 text-sm text-muted">
          US$ por 1 milhão de tokens, como aparece na página de preços de cada provedor. Mudar o preço vale para as próximas respostas.
        </p>
        {precos.length > 0 && (
          <div className="mb-5 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line text-xs text-muted">
                <tr>
                  <th className="py-2 pr-4 font-medium">Modelo</th>
                  <th className="py-2 pr-4 text-right font-medium">Entrada</th>
                  <th className="py-2 pr-4 text-right font-medium">Saída</th>
                  <th className="py-2 pr-4 text-right font-medium">Cache</th>
                  <th><span className="sr-only">Ações</span></th>
                </tr>
              </thead>
              <tbody>
                {precos.map((p) => (
                  <tr key={`${p.provider}/${p.model}`} className="border-b border-line last:border-0">
                    <td className="py-2 pr-4"><span className="font-medium">{p.model}</span> <span className="text-xs text-muted">{p.provider}</span></td>
                    <td className="py-2 pr-4 text-right tabular-nums">{dolar(p.entrada_usd)}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{dolar(p.saida_usd)}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{p.cache_usd == null ? '—' : dolar(p.cache_usd)}</td>
                    <td className="py-2 text-right">
                      <button type="button" aria-label={`Tirar o preço de ${p.model}`} onClick={() => apagar.mutate(p)}
                        className="rounded-md p-1 text-muted hover:bg-surface-muted hover:text-text"><Trash2 className="size-4" /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <form onSubmit={enviar} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[10rem_1fr_6rem_6rem_6rem_auto] lg:items-end">
          <Campo rotulo="Provedor">
            <Seletor value={f.provedor} onChange={(e) => setF({ ...f, provedor: e.target.value })}>
              {PROVEDORES.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
            </Seletor>
          </Campo>
          <Campo rotulo="Modelo">
            <Entrada value={f.modelo} spellCheck={false} placeholder="nome exato" onChange={(e) => setF({ ...f, modelo: e.target.value })} />
          </Campo>
          <Campo rotulo="Entrada"><Entrada inputMode="decimal" value={f.entrada_usd} onChange={(e) => setF({ ...f, entrada_usd: e.target.value })} /></Campo>
          <Campo rotulo="Saída"><Entrada inputMode="decimal" value={f.saida_usd} onChange={(e) => setF({ ...f, saida_usd: e.target.value })} /></Campo>
          <Campo rotulo="Cache">
            <Entrada inputMode="decimal" value={f.cache_usd} placeholder="opcional" onChange={(e) => setF({ ...f, cache_usd: e.target.value })} />
          </Campo>
          <Botao type="submit" disabled={!valido || salvar.isPending}>Salvar</Botao>
        </form>
        <p className="mt-2 text-xs text-muted">
          Mesmo provedor e modelo: o preço é atualizado. A IA da plataforma (OpenCode Go) usa o provedor "OpenCode".
        </p>
      </Secao>
      <Secao titulo="Cotação do dólar" className="self-start">
        <form onSubmit={(e) => { e.preventDefault(); salvarCotacao.mutate() }} className="flex items-end gap-3">
          <Campo rotulo="R$ por US$ 1" ajuda="Só para mostrar valores em reais.">
            <Entrada inputMode="decimal" value={cotacao} placeholder="ex.: 5,40" onChange={(e) => setCotacao(e.target.value)} />
          </Campo>
          <Botao type="submit" disabled={salvarCotacao.isPending}>Salvar</Botao>
        </form>
      </Secao>
    </div>
  )
}
