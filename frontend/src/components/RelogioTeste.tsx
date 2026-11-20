import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Clock, FastForward, RotateCcw, Send } from 'lucide-react'
import { api, type Relogio } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { dataHora } from '../lib/formato'
import { useAviso } from './Aviso'
import { Botao } from './ui'

/** Relógio de teste (só em desenvolvimento): adianta o horário para ver o lembrete sair sem esperar um dia. */
export function RelogioTeste() {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const tz = clinica.timezone
  const q = useQuery({
    queryKey: ['relogio', clinica.id],
    queryFn: () => api.get<Relogio>(`/dev/relogio?clinic_id=${clinica.id}`),
    refetchInterval: 15_000,
    retry: false,
  })

  const atualizar = () => {
    qc.invalidateQueries({ queryKey: ['relogio'] })
    qc.invalidateQueries({ queryKey: ['mensagens'] })
  }
  const proximo = useMutation({
    mutationFn: () => api.post<Relogio & { rodada: { enviadas?: number } }>(`/dev/relogio/proximo-lembrete?clinic_id=${clinica.id}`),
    onSuccess: (r) => {
      aviso.ok(`Relógio adiantado. ${r.rodada?.enviadas ?? 0} mensagem(ns) enviada(s).`)
      atualizar()
    },
    onError: aviso.erro,
  })
  const zerar = useMutation({
    mutationFn: () => api.post<Relogio>(`/dev/relogio/zerar?clinic_id=${clinica.id}`),
    onSuccess: () => {
      aviso.ok('Relógio de volta ao horário real.')
      atualizar()
    },
    onError: aviso.erro,
  })
  const rodar = useMutation({
    mutationFn: () => api.post<{ enviadas?: number }>('/dev/mensagens/rodar'),
    onSuccess: (r) => {
      aviso.ok(`${r.enviadas ?? 0} mensagem(ns) enviada(s).`)
      atualizar()
    },
    onError: aviso.erro,
  })

  if (q.isError || !q.data) return null // fora do modo de desenvolvimento a caixa não aparece
  const r = q.data
  const ocupado = proximo.isPending || zerar.isPending || rodar.isPending

  return (
    <section className="mb-6 flex flex-col gap-4 rounded-3xl border border-dashed border-line bg-surface p-5 xl:flex-row xl:items-center xl:gap-8">
      <div className="flex items-center gap-3 xl:w-72 xl:shrink-0">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary-soft text-primary">
          <Clock className="size-5" />
        </span>
        <div>
          <h2 className="font-semibold">Relógio de teste</h2>
          <p className="text-xs text-muted">Só em desenvolvimento. Adianta o horário das mensagens automáticas.</p>
        </div>
      </div>
      <dl className="grid flex-1 gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs text-muted">Horário {r.simulado ? 'simulado' : 'real'}</dt>
          <dd className={r.simulado ? 'font-semibold text-primary' : 'font-medium'}>
            {dataHora(r.agora, tz)}{r.simulado ? ` (+${r.adiantado_min} min)` : ''}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Próximo lembrete</dt>
          <dd className="font-medium">{r.proximo_lembrete ? dataHora(r.proximo_lembrete, tz) : 'nenhum na fila'}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Envio automático</dt>
          <dd className="font-medium">{r.envio_automatico ? 'ligado (a cada 30 s)' : 'desligado'}</dd>
        </div>
      </dl>
      <div className="flex flex-wrap gap-2 xl:shrink-0">
        <Botao onClick={() => proximo.mutate()} disabled={ocupado || !r.proximo_lembrete}>
          <FastForward className="size-4" /> {proximo.isPending ? 'Enviando…' : 'Avançar até o próximo lembrete'}
        </Botao>
        <Botao variante="secundario" onClick={() => rodar.mutate()} disabled={ocupado}>
          <Send className="size-4" /> Enviar fila agora
        </Botao>
        {r.simulado && (
          <Botao variante="fantasma" onClick={() => zerar.mutate()} disabled={ocupado}>
            <RotateCcw className="size-4" /> Voltar ao horário real
          </Botao>
        )}
      </div>
    </section>
  )
}
