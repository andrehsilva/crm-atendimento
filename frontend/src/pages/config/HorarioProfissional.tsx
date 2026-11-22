import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Entrada, Modal } from '../../components/ui'
import { api } from '../../lib/api'
import { useClinica } from '../../lib/clinica'
import { dataHora } from '../../lib/formato'

const DIAS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
type Faixa = { inicio: string; fim: string }
type Horario = {
  proprio: boolean
  dias: { weekday: number; faixas: Faixa[] }[]
  clinica: { weekday: number; inicio: string; fim: string }[]
}
type Afetada = { id: string; quando: string; paciente: string | null }

const hhmm = (t: string) => t.slice(0, 5)

/** Etapa 24 (D99): o profissional segue o horário da clínica ou tem horário próprio (dentro do da clínica). */
export function ModalHorarioProfissional({ prof, podeEditar, onFechar }: { prof: { id: string; nome: string } | null; podeEditar: boolean; onFechar: () => void }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const base = `/clinics/${clinica.id}/config/profissionais/${prof?.id}/horario`
  const q = useQuery({ queryKey: ['config', 'horario-prof', prof?.id], queryFn: () => api.get<Horario>(base), enabled: !!prof })
  const [proprio, setProprio] = useState(false)
  const [dias, setDias] = useState<Record<number, Faixa[]>>({}) // dia marcado = tem faixas
  const [afetadas, setAfetadas] = useState<Afetada[] | null>(null)

  useEffect(() => {
    if (!q.data) return
    setProprio(q.data.proprio)
    const inicial: Record<number, Faixa[]> = {}
    if (q.data.proprio) {
      for (const d of q.data.dias) inicial[d.weekday] = d.faixas.map((f) => ({ inicio: hhmm(f.inicio), fim: hhmm(f.fim) }))
    } else {
      for (const c of q.data.clinica) inicial[c.weekday] = [{ inicio: hhmm(c.inicio), fim: hhmm(c.fim) }] // começa igual ao da clínica
    }
    setDias(inicial)
    setAfetadas(null)
  }, [q.data])

  const corpo = () => ({
    proprio,
    dias: Object.entries(dias).map(([w, faixas]) => ({ weekday: Number(w), faixas })),
  })
  const salvar = useMutation({
    mutationFn: () => api.put<Horario & { afetadas: Afetada[] }>(base, corpo()),
    onSuccess: (r) => {
      qc.setQueryData(['config', 'horario-prof', prof?.id], r)
      qc.invalidateQueries({ queryKey: ['config', 'profissionais'] })
      qc.invalidateQueries({ queryKey: ['agenda'] })
      aviso.ok(r.proprio ? 'Horário próprio salvo. Vale para as próximas marcações.' : 'Agora segue o horário da clínica.')
      onFechar()
    },
    onError: aviso.erro,
  })
  const conferir = useMutation({
    mutationFn: () => api.post<{ afetadas: Afetada[] }>(`${base}/impacto`, corpo()),
    onSuccess: (r) => (r.afetadas.length ? setAfetadas(r.afetadas) : salvar.mutate()),
    onError: aviso.erro,
  })

  const clinicaDias = q.data?.clinica ?? []
  const mudarFaixa = (w: number, i: number, campo: keyof Faixa, v: string) =>
    setDias({ ...dias, [w]: dias[w].map((f, j) => (j === i ? { ...f, [campo]: v } : f)) })

  return (
    <Modal titulo={`Horário · ${prof?.nome ?? ''}`} aberto={!!prof} onFechar={onFechar} largura="max-w-xl">
      {!q.data ? <p className="text-sm text-muted">Carregando…</p> : afetadas ? (
        <div className="space-y-4">
          <p className="text-sm">
            {afetadas.length === 1 ? 'Esta consulta já marcada fica' : `Estas ${afetadas.length} consultas já marcadas ficam`} fora do novo horário.
            Elas <b>continuam marcadas</b>; se precisar, remarque pela agenda.
          </p>
          <ul className="max-h-60 space-y-1 overflow-y-auto rounded-2xl bg-surface-muted p-3 text-sm">
            {afetadas.map((a) => <li key={a.id}>{dataHora(a.quando, clinica.timezone)} · {a.paciente ?? 'Sem nome'}</li>)}
          </ul>
          <div className="flex justify-end gap-2">
            <Botao variante="fantasma" onClick={() => setAfetadas(null)}>Voltar</Botao>
            <Botao disabled={salvar.isPending} onClick={() => salvar.mutate()}>Salvar mesmo assim</Botao>
          </div>
        </div>
      ) : (
        <fieldset disabled={!podeEditar} className="space-y-4">
          <div className="grid gap-2 text-sm">
            <label className="flex items-center gap-2">
              <input type="radio" checked={!proprio} onChange={() => setProprio(false)} />Segue o horário da clínica
            </label>
            <label className="flex items-center gap-2">
              <input type="radio" checked={proprio} onChange={() => setProprio(true)} />Horário próprio
            </label>
          </div>

          {proprio && (
            <ul className="divide-y divide-line rounded-2xl border border-line">
              {clinicaDias.map((c) => {
                const marcado = !!dias[c.weekday]
                return (
                  <li key={c.weekday} className="flex flex-wrap items-center gap-3 px-4 py-2.5">
                    <label className="flex w-28 items-center gap-2 text-sm font-medium">
                      <input type="checkbox" checked={marcado}
                        onChange={(e) => {
                          const novo = { ...dias }
                          if (e.target.checked) novo[c.weekday] = [{ inicio: hhmm(c.inicio), fim: hhmm(c.fim) }]
                          else delete novo[c.weekday]
                          setDias(novo)
                        }} />
                      {DIAS[c.weekday]}
                    </label>
                    {marcado ? (
                      <div className="flex flex-1 flex-wrap items-center gap-2">
                        {dias[c.weekday].map((f, i) => (
                          <span key={i} className="flex items-center gap-1">
                            <Entrada type="time" value={f.inicio} min={hhmm(c.inicio)} max={hhmm(c.fim)} className="!w-auto !py-1"
                              onChange={(e) => mudarFaixa(c.weekday, i, 'inicio', e.target.value)} />
                            –
                            <Entrada type="time" value={f.fim} min={hhmm(c.inicio)} max={hhmm(c.fim)} className="!w-auto !py-1"
                              onChange={(e) => mudarFaixa(c.weekday, i, 'fim', e.target.value)} />
                            {i === 1 && (
                              <button type="button" aria-label="Tirar a 2ª faixa" className="rounded-lg p-1 text-muted hover:bg-surface-muted"
                                onClick={() => setDias({ ...dias, [c.weekday]: dias[c.weekday].slice(0, 1) })}><X className="size-4" /></button>
                            )}
                          </span>
                        ))}
                        {dias[c.weekday].length === 1 && (
                          <button type="button" className="flex items-center gap-1 text-xs text-muted hover:text-text"
                            onClick={() => setDias({ ...dias, [c.weekday]: [...dias[c.weekday], { inicio: hhmm(c.fim), fim: hhmm(c.fim) }] })}>
                            <Plus className="size-3.5" />2ª faixa
                          </button>
                        )}
                      </div>
                    ) : <span className="text-sm text-muted">não atende</span>}
                  </li>
                )
              })}
            </ul>
          )}
          <p className="text-xs text-muted">
            {proprio
              ? 'Só dias e horários dentro do horário da clínica. Use a 2ª faixa para, por exemplo, 08–12 e 14–18. A assistente só oferece esses horários.'
              : 'O profissional atende em todo o horário de funcionamento da clínica (Configurações › Horários).'}
            {' '}Mudar vale para as próximas marcações; as já marcadas continuam.
          </p>
          {podeEditar && (
            <div className="flex justify-end gap-2">
              <Botao variante="fantasma" onClick={onFechar}>Cancelar</Botao>
              <Botao disabled={conferir.isPending || salvar.isPending} onClick={() => (proprio ? conferir.mutate() : salvar.mutate())}>Salvar</Botao>
            </div>
          )}
        </fieldset>
      )}
    </Modal>
  )
}
