import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Entrada, Modal } from '../../components/ui'
import { api, type ConsultaAfetada, type DiaHorario, type Horarios as THorarios } from '../../lib/api'
import { useClinica } from '../../lib/clinica'
import { dataHora } from '../../lib/formato'
import { useTermos } from '../../lib/termos'

const hm = (t: string) => t.slice(0, 5)

/** Imagem 07: uma linha por dia (liga/desliga, início até fim, pausas), Salvar por linha. */
export function Horarios({ podeEditar }: { podeEditar: boolean }) {
  const { clinica } = useClinica()
  const pal = useTermos()
  const q = useQuery({ queryKey: ['config', 'horarios', clinica.id], queryFn: () => api.get<THorarios>(`/clinics/${clinica.id}/config/horarios`) })
  if (!q.data) return <p className="text-sm text-muted">Carregando…</p>
  return (
    <div>
      <section className="flex flex-col divide-y divide-line rounded-3xl bg-surface px-6">
        {q.data.dias.map((d) => <LinhaDia key={d.weekday} dia={d} podeEditar={podeEditar} />)}
      </section>
      <p className="mt-4 text-sm text-muted">
        {pal.Atendimentos} já marcad{pal.o}s não mudam: se um horário novo deixar alguma de fora, você vê a lista antes de salvar.
        {q.data.profissionais_com_horario_proprio.length > 0 &&
          ` Atenção: ${q.data.profissionais_com_horario_proprio.join(', ')} tem horário próprio, que não muda por aqui.`}
      </p>
    </div>
  )
}

function LinhaDia({ dia, podeEditar }: { dia: DiaHorario; podeEditar: boolean }) {
  const { clinica } = useClinica()
  const pal = useTermos()
  const aviso = useAviso()
  const qc = useQueryClient()
  const inicial = () => ({ ativo: dia.ativo, inicio: hm(dia.inicio), fim: hm(dia.fim), pausas: dia.pausas.map((p) => ({ inicio: hm(p.inicio), fim: hm(p.fim) })) })
  const [f, setF] = useState(inicial)
  const [afetadas, setAfetadas] = useState<ConsultaAfetada[] | null>(null)
  useEffect(() => setF(inicial()), [dia]) // eslint-disable-line react-hooks/exhaustive-deps
  const mudou = JSON.stringify(f) !== JSON.stringify(inicial())
  const base = `/clinics/${clinica.id}/config/horarios/${dia.weekday}`

  const salvar = useMutation({
    mutationFn: () => api.put(base, f),
    onSuccess: () => {
      aviso.ok(`Horário de ${dia.nome} salvo.`)
      setAfetadas(null)
      qc.invalidateQueries({ queryKey: ['config', 'horarios'] })
      qc.invalidateQueries({ queryKey: ['clinica'] })
    },
    onError: aviso.erro,
  })
  const conferir = useMutation({
    mutationFn: () => api.post<{ afetadas: ConsultaAfetada[] }>(`${base}/impacto`, f),
    onSuccess: (r) => (r.afetadas.length ? setAfetadas(r.afetadas) : salvar.mutate()),
    onError: aviso.erro,
  })
  const pausa = (i: number, k: 'inicio' | 'fim', v: string) => setF({ ...f, pausas: f.pausas.map((p, j) => (j === i ? { ...p, [k]: v } : p)) })

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-3 py-4">
      <label className="flex w-36 items-center gap-3 font-medium capitalize">
        <input type="checkbox" role="switch" checked={f.ativo} disabled={!podeEditar} onChange={(e) => setF({ ...f, ativo: e.target.checked })}
          className="size-4 accent-[var(--primary)]" />
        {dia.nome}
      </label>
      {f.ativo ? (
        <div className="flex flex-1 flex-wrap items-center gap-3 text-sm">
          <Entrada type="time" disabled={!podeEditar} value={f.inicio} onChange={(e) => setF({ ...f, inicio: e.target.value })} className="w-28" aria-label={`Início ${dia.nome}`} />
          <span className="text-muted">até</span>
          <Entrada type="time" disabled={!podeEditar} value={f.fim} onChange={(e) => setF({ ...f, fim: e.target.value })} className="w-28" aria-label={`Fim ${dia.nome}`} />
          {f.pausas.map((p, i) => (
            <span key={i} className="flex items-center gap-1 rounded-xl bg-surface-muted px-2 py-1">
              <span className="text-xs text-muted">pausa</span>
              <input type="time" disabled={!podeEditar} value={p.inicio} onChange={(e) => pausa(i, 'inicio', e.target.value)} className="bg-transparent text-sm" aria-label="Início da pausa" />
              –
              <input type="time" disabled={!podeEditar} value={p.fim} onChange={(e) => pausa(i, 'fim', e.target.value)} className="bg-transparent text-sm" aria-label="Fim da pausa" />
              {podeEditar && (
                <button type="button" aria-label="Remover pausa" onClick={() => setF({ ...f, pausas: f.pausas.filter((_, j) => j !== i) })}
                  className="rounded p-0.5 text-muted hover:text-text"><X className="size-3.5" /></button>
              )}
            </span>
          ))}
          {podeEditar && f.pausas.length < 4 && (
            <button type="button" onClick={() => setF({ ...f, pausas: [...f.pausas, { inicio: '12:00', fim: '13:00' }] })}
              className="flex items-center gap-1 text-xs text-muted hover:text-primary"><Plus className="size-3.5" /> pausa</button>
          )}
        </div>
      ) : (
        <span className="flex-1 text-sm text-muted">Fechado</span>
      )}
      {podeEditar && (
        <Botao variante={mudou ? 'primario' : 'secundario'} disabled={!mudou || conferir.isPending || salvar.isPending} onClick={() => conferir.mutate()}>
          Salvar
        </Botao>
      )}
      <Modal titulo={`${pal.Atendimentos} fora do novo horário`} aberto={!!afetadas} onFechar={() => setAfetadas(null)}>
        <p className="mb-3 text-sm">Est{pal.o === 'a' ? 'a' : 'e'}s {pal.atendimentos} já marcad{pal.o}s ficam fora do novo horário. Continuam <strong>marcad{pal.o}s</strong>: avise os {pal.clientes} ou remarque pela agenda.</p>
        <ul className="mb-5 flex max-h-64 flex-col gap-2 overflow-y-auto text-sm">
          {afetadas?.map((a) => (
            <li key={a.id} className="rounded-xl bg-surface-muted px-3 py-2">{dataHora(a.quando, clinica.timezone)} — {a.paciente ?? pal.cliente} com {a.profissional}</li>
          ))}
        </ul>
        <div className="flex justify-end gap-2">
          <Botao variante="fantasma" onClick={() => setAfetadas(null)}>Voltar</Botao>
          <Botao onClick={() => salvar.mutate()} disabled={salvar.isPending}>Salvar mesmo assim</Botao>
        </div>
      </Modal>
    </div>
  )
}
