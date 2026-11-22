import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Repeat, XCircle } from 'lucide-react'
import { api, type Consulta, type Slot } from '../../lib/api'
import { useClinica } from '../../lib/clinica'
import { diaLegivel, hora, partes } from '../../lib/formato'
import { useAviso } from '../Aviso'
import { Botao, Campo, Entrada, Modal, Seletor } from '../ui'
import { useTermos } from '../../lib/termos'

export type Previa = { telefone?: string; nome?: string; dia?: string; hora?: string; professionalId?: string }

/** 21B (RN-TR-07): resultado da série — o que foi marcado e o que não coube */
type ResultadoSerie = { marcadas: Consulta[]; falhas: { inicio: string; codigo: string; motivo: string }[]; tratamento_aberto: boolean }

/** Marcar consulta pela recepção. Mostra só horários livres de verdade (o backend valida tudo de novo). */
export function ModalNovaConsulta({ aberto, onFechar, previa }: { aberto: boolean; onFechar: () => void; previa?: Previa }) {
  const { clinica, cadastros } = useClinica()
  const pal = useTermos()
  const aviso = useAviso()
  const [telefone, setTelefone] = useState('')
  const [nome, setNome] = useState('')
  const [servico, setServico] = useState('')
  const [prof, setProf] = useState('')
  const [dia, setDia] = useState('')
  const [escolhido, setEscolhido] = useState<Slot | null>(null)
  const [repetir, setRepetir] = useState(false)
  const [sessoes, setSessoes] = useState('4')
  const [intervalo, setIntervalo] = useState('7')
  const [resultado, setResultado] = useState<ResultadoSerie | null>(null)
  const qc = useQueryClient()

  useEffect(() => {
    if (!aberto) return
    setTelefone(previa?.telefone ?? '')
    setNome(previa?.nome ?? '')
    setServico(cadastros.procedimentos[0]?.id ?? '')
    setProf(previa?.professionalId ?? '')
    setDia(previa?.dia ?? partes(new Date(), clinica.timezone).ymd)
    setEscolhido(null)
    setRepetir(false)
    setResultado(null)
  }, [aberto, previa, cadastros, clinica.timezone])

  const profsDoServico = useMemo(
    () => cadastros.profissionais.filter((p) => p.service_ids.includes(servico)),
    [cadastros, servico],
  )

  const slots = useQuery({
    queryKey: ['slots', servico, prof, dia, telefone],
    queryFn: () =>
      api.get<Slot[]>(
        `/clinics/${clinica.id}/availability?service_id=${servico}&de=${dia}&ate=${dia}&limite=100` +
          (prof ? `&professional_id=${prof}` : '') +
          (telefone.replace(/\D/g, '').length >= 10 ? `&telefone=${encodeURIComponent(telefone)}` : ''),
      ),
    enabled: aberto && !!servico && !!dia,
  })

  // Pré-seleciona o horário clicado na agenda, se estiver livre
  useEffect(() => {
    if (!previa?.hora || !slots.data || escolhido) return
    const s = slots.data.find((x) => hora(x.starts_at, clinica.timezone) === previa.hora && (!prof || x.professional_id === prof))
    if (s) setEscolhido(s)
  }, [slots.data, previa, prof, escolhido, clinica.timezone])

  const marcar = useMutation({
    mutationFn: () =>
      api.post<Consulta>(`/clinics/${clinica.id}/appointments`, {
        telefone, nome: nome || null, professional_id: escolhido!.professional_id, service_id: servico, inicio: escolhido!.starts_at,
      }),
    onSuccess: (c) => {
      aviso.ok(`${pal.Atendimento} marcad${pal.o}: ${c.paciente}, ${diaLegivel(partes(c.starts_at, clinica.timezone).ymd)} às ${hora(c.starts_at, clinica.timezone)}`)
      onFechar()
    },
    onError: aviso.erro,
  })

  const serie = useMutation({
    mutationFn: () =>
      api.post<ResultadoSerie>(`/clinics/${clinica.id}/appointments/serie`, {
        telefone, nome: nome || null, professional_id: escolhido!.professional_id, service_id: servico, inicio: escolhido!.starts_at,
        sessoes: Number(sessoes), intervalo_dias: Number(intervalo),
      }),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['tratamentos'] })
      if (r.falhas.length === 0) {
        aviso.ok(`${r.marcadas.length} sessões marcadas. O paciente recebe uma confirmação só, com todas as datas.`)
        onFechar()
      } else {
        aviso.ok(`${r.marcadas.length} de ${r.marcadas.length + r.falhas.length} sessões marcadas.`)
        setResultado(r) // mostra quais datas não couberam
      }
    },
    onError: aviso.erro,
  })
  const tz = clinica.timezone
  const nSessoes = Number(sessoes)
  const serieValida = nSessoes >= 2 && nSessoes <= 20 && Number(intervalo) >= 1 && Number(intervalo) <= 60

  if (resultado) {
    return (
      <Modal titulo="Resultado da série" aberto={aberto} onFechar={onFechar} largura="max-w-lg">
        <ul className="space-y-2 text-sm">
          {[...resultado.marcadas.map((c) => ({ quando: c.starts_at, ok: true, motivo: '' })),
            ...resultado.falhas.map((f) => ({ quando: f.inicio, ok: false, motivo: f.motivo }))]
            .sort((a, b) => a.quando.localeCompare(b.quando))
            .map((x) => (
              <li key={x.quando} className="flex items-start gap-2">
                {x.ok ? <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-[#1f7a43]" /> : <XCircle className="mt-0.5 size-4 shrink-0 text-red-600" />}
                <span>
                  <span className="font-medium">{diaLegivel(partes(x.quando, tz).ymd)} às {hora(x.quando, tz)}</span>
                  {!x.ok && <span className="block text-xs text-muted">Não coube: {x.motivo}</span>}
                </span>
              </li>
            ))}
        </ul>
        <p className="mt-4 rounded-2xl bg-surface-muted px-4 py-3 text-sm text-muted">
          As datas que não couberam podem ser marcadas uma a uma na agenda. {resultado.tratamento_aberto && 'Um tratamento foi aberto para este paciente.'}
        </p>
        <div className="mt-5 flex justify-end"><Botao onClick={onFechar}>Fechar</Botao></div>
      </Modal>
    )
  }

  return (
    <Modal titulo="Marcar consulta" aberto={aberto} onFechar={onFechar} largura="max-w-2xl">
      <div className="grid gap-4 sm:grid-cols-2">
        <Campo rotulo={`Telefone do ${pal.cliente}`}>
          <Entrada value={telefone} onChange={(e) => setTelefone(e.target.value)} placeholder="(11) 98765-4321" inputMode="tel" />
        </Campo>
        <Campo rotulo="Nome completo" ajuda={`Obrigatório para ${pal.cliente} novo`}>
          <Entrada value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Maria da Silva" />
        </Campo>
        <Campo rotulo="Procedimento">
          <Seletor value={servico} onChange={(e) => { setServico(e.target.value); setEscolhido(null) }}>
            {cadastros.procedimentos.map((s) => (
              <option key={s.id} value={s.id}>{s.name} · {s.duration_min} min</option>
            ))}
          </Seletor>
        </Campo>
        <Campo rotulo={pal.Profissional}>
          <Seletor value={prof} onChange={(e) => { setProf(e.target.value); setEscolhido(null) }}>
            <option value="">Qualquer um</option>
            {profsDoServico.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </Seletor>
        </Campo>
        <Campo rotulo="Dia">
          <Entrada type="date" value={dia} onChange={(e) => { setDia(e.target.value); setEscolhido(null) }} />
        </Campo>
      </div>

      <div className="mt-5">
        <p className="mb-2 text-sm font-medium">Horários livres {dia && <span className="font-normal text-muted">— {diaLegivel(dia)}</span>}</p>
        {slots.isLoading && <p className="text-sm text-muted">Buscando…</p>}
        {slots.isError && <p className="text-sm text-red-600">{(slots.error as Error).message}</p>}
        {slots.data?.length === 0 && <p className="text-sm text-muted">Nenhum horário livre neste dia.</p>}
        <div className="flex max-h-52 flex-wrap gap-2 overflow-y-auto">
          {slots.data?.map((s) => {
            const ativo = escolhido?.starts_at === s.starts_at && escolhido.professional_id === s.professional_id
            return (
              <button
                key={s.starts_at + s.professional_id}
                type="button"
                onClick={() => setEscolhido(s)}
                className={`rounded-xl border px-3 py-1.5 text-sm transition ${
                  ativo ? 'border-primary bg-primary text-primary-contrast' : 'border-line hover:border-primary'
                }`}
              >
                {hora(s.starts_at, clinica.timezone)}
                {!prof && <span className={ativo ? 'opacity-80' : 'text-muted'}> · {s.profissional.split(' ').slice(0, 2).join(' ')}</span>}
                {s.preferido && ' ★'}
              </button>
            )
          })}
        </div>
        {slots.data?.some((s) => s.preferido) && <p className="mt-2 text-xs text-muted">★ {pal.profissional} de referência do {pal.cliente}</p>}
      </div>

      <div className="mt-5 rounded-2xl border border-line p-4">
        <label className="flex items-center gap-2 text-sm font-medium">
          <input type="checkbox" checked={repetir} onChange={(e) => setRepetir(e.target.checked)} />
          <Repeat className="size-4 text-primary" />Repetir (série de sessões)
        </label>
        {repetir && (
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <Campo rotulo="Quantas sessões" ajuda="De 2 a 20, contando esta">
              <Entrada type="number" min={2} max={20} value={sessoes} onChange={(e) => setSessoes(e.target.value)} />
            </Campo>
            <Campo rotulo="A cada quantos dias" ajuda="7 = mesmo dia da semana e horário">
              <Entrada type="number" min={1} max={60} value={intervalo} onChange={(e) => setIntervalo(e.target.value)} />
            </Campo>
            <p className="text-xs text-muted sm:col-span-2">
              {escolhido && serieValida
                ? `Datas: ${Array.from({ length: nSessoes }, (_, i) => {
                    const d = new Date(new Date(escolhido.starts_at).getTime() + i * Number(intervalo) * 86_400_000)
                    return partes(d.toISOString(), tz).ymd.split('-').reverse().slice(0, 2).join('/')
                  }).join(', ')}. `
                : 'Escolha o primeiro horário abaixo. '}
              Cada data passa pelas regras da agenda; as que não couberem aparecem no fim. As sessões ficam num tratamento e não contam no limite de consultas. O paciente recebe uma confirmação só, com todas as datas.
            </p>
          </div>
        )}
      </div>

      <div className="mt-6 flex justify-end gap-2">
        <Botao variante="fantasma" onClick={onFechar}>Cancelar</Botao>
        {repetir ? (
          <Botao disabled={!escolhido || !telefone || !serieValida || serie.isPending} onClick={() => serie.mutate()}>
            {serie.isPending ? 'Marcando…' : `Marcar ${serieValida ? nSessoes : ''} sessões`}
          </Botao>
        ) : (
          <Botao disabled={!escolhido || !telefone || marcar.isPending} onClick={() => marcar.mutate()}>
            {marcar.isPending ? 'Marcando…' : 'Marcar consulta'}
          </Botao>
        )}
      </div>
    </Modal>
  )
}
