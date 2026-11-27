import { useQuery } from '@tanstack/react-query'
import { Receipt } from 'lucide-react'
import { Secao } from './ui'
import { api } from '../lib/api'

export type CustoMetaMes = {
  inicio: string
  linhas: { categoria: string; rotulo: string; mensagens: number; cobradas: number; preco_usd: number; custo_usd: number }[]
  gratis_atendimento: number
  total_usd: number
  total_brl: number | null
  cotacao_brl: number | null
}

const usd = (v: number) => `US$ ${v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`
const brl = (v: number) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

/** Etapa 36E (D131): gasto estimado do mês no WhatsApp oficial — quem paga é a clínica, direto para a Meta. */
export function CustoMeta({ url, chave }: { url: string; chave: unknown[] }) {
  const q = useQuery({ queryKey: chave, queryFn: () => api.get<CustoMetaMes>(url), retry: false })
  return (
    <Secao titulo="Gasto do mês no WhatsApp oficial" icone={<Receipt className="size-5" />}>
      {q.isLoading ? <p className="text-sm text-muted">Carregando…</p>
        : q.isError || !q.data ? <p className="text-sm text-muted">Não deu para calcular agora.</p>
        : (
          <>
            <p className="text-2xl font-semibold tabular-nums">
              {q.data.total_brl != null ? brl(q.data.total_brl) : usd(q.data.total_usd)}
              {q.data.total_brl != null && <span className="ml-2 text-sm font-normal text-muted">{usd(q.data.total_usd)}</span>}
            </p>
            <table className="mt-3 w-full text-sm">
              <thead><tr className="text-left text-xs text-muted"><th className="py-1 font-normal">Tipo</th><th className="font-normal">Mensagens</th><th className="font-normal">Cobradas</th><th className="text-right font-normal">Estimado</th></tr></thead>
              <tbody className="divide-y divide-line">
                {q.data.linhas.map((l) => (
                  <tr key={l.categoria}>
                    <td className="py-1.5">{l.rotulo}</td>
                    <td className="tabular-nums">{l.mensagens}</td>
                    <td className="tabular-nums">{l.cobradas}</td>
                    <td className="text-right tabular-nums">{usd(l.custo_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-3 text-xs text-muted">
              Estimativa com a tabela de preços da Meta para o Brasil. As primeiras {q.data.gratis_atendimento} respostas de
              atendimento do mês são grátis. A cobrança de verdade é feita pela Meta, no cartão da clínica.
            </p>
          </>
        )}
    </Secao>
  )
}
