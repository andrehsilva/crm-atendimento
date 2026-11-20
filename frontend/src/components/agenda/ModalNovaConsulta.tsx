import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api, type Consulta, type Slot } from '../../lib/api'
import { useClinica } from '../../lib/clinica'
import { diaLegivel, hora, partes } from '../../lib/formato'
import { useAviso } from '../Aviso'
import { Botao, Campo, Entrada, Modal, Seletor } from '../ui'
import { useTermos } from '../../lib/termos'

export type Previa = { telefone?: string; nome?: string; dia?: string; hora?: string; professionalId?: string }

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

  useEffect(() => {
    if (!aberto) return
    setTelefone(previa?.telefone ?? '')
    setNome(previa?.nome ?? '')
    setServico(cadastros.procedimentos[0]?.id ?? '')
    setProf(previa?.professionalId ?? '')
    setDia(previa?.dia ?? partes(new Date(), clinica.timezone).ymd)
    setEscolhido(null)
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

      <div className="mt-6 flex justify-end gap-2">
        <Botao variante="fantasma" onClick={onFechar}>Cancelar</Botao>
        <Botao disabled={!escolhido || !telefone || marcar.isPending} onClick={() => marcar.mutate()}>
          {marcar.isPending ? 'Marcando…' : 'Marcar consulta'}
        </Botao>
      </div>
    </Modal>
  )
}
