import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { CalendarClock, Check, UserCheck, UserX, XCircle } from 'lucide-react'
import { api, type Consulta, type Slot } from '../../lib/api'
import { useClinica } from '../../lib/clinica'
import { dataHora, diaLegivel, hora, partes, telefone } from '../../lib/formato'
import { useAviso } from '../Aviso'
import { Botao, Campo, Entrada, Modal, Selo } from '../ui'
import { SeloStatus } from './status'

type Modo = 'ver' | 'remarcar' | 'cancelar'

/** Detalhes de uma consulta + ações da recepção (mesmas regras da Ísis, RN-PN-03). */
export function ModalConsulta({ consulta, onFechar }: { consulta: Consulta | null; onFechar: () => void }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const tz = clinica.timezone
  const [modo, setModo] = useState<Modo>('ver')
  const [dia, setDia] = useState('')
  const [novo, setNovo] = useState<Slot | null>(null)
  const [motivo, setMotivo] = useState('')

  useEffect(() => {
    setModo('ver')
    setNovo(null)
    setMotivo('')
    if (consulta) setDia(partes(consulta.starts_at, tz).ymd)
  }, [consulta, tz])

  const base = consulta ? `/clinics/${clinica.id}/appointments/${consulta.id}` : ''
  const ativa = consulta && (consulta.status === 'agendada' || consulta.status === 'confirmada')

  const slots = useQuery({
    queryKey: ['slots', 'remarcar', consulta?.id, dia],
    queryFn: () => api.get<Slot[]>(
      `/clinics/${clinica.id}/availability?service_id=${consulta!.service_id}&de=${dia}&ate=${dia}&limite=100&professional_id=${consulta!.professional_id}`,
    ),
    enabled: modo === 'remarcar' && !!consulta && !!dia,
  })

  const fim = (texto: string) => { aviso.ok(texto); onFechar() }

  const status = useMutation({
    mutationFn: (s: 'confirmada' | 'realizada' | 'faltou') => api.post(`${base}/status`, { status: s }),
    onSuccess: (_, s) => fim({ confirmada: 'Consulta confirmada', realizada: 'Presença registrada', faltou: 'Falta registrada' }[s]),
    onError: aviso.erro,
  })
  const remarcar = useMutation({
    mutationFn: () => api.post<{ aviso_politica: boolean }>(`${base}/reschedule`, { novo_inicio: novo!.starts_at }),
    onSuccess: (r) => fim(r.aviso_politica ? 'Remarcada (em cima da hora — confira a política da clínica)' : 'Consulta remarcada'),
    onError: aviso.erro,
  })
  const cancelar = useMutation({
    mutationFn: () => api.post<{ aviso_politica: boolean }>(`${base}/cancel`, { motivo: motivo || null }),
    onSuccess: (r) => fim(r.aviso_politica ? 'Cancelada com menos de 24h — confira a política da clínica' : 'Consulta cancelada'),
    onError: aviso.erro,
  })
  const ocupado = status.isPending || remarcar.isPending || cancelar.isPending

  if (!consulta) return null
  return (
    <Modal titulo={consulta.paciente ?? 'Consulta'} aberto onFechar={onFechar}>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
        <dt className="text-muted">Quando</dt><dd>{dataHora(consulta.starts_at, tz)} – {hora(consulta.ends_at, tz)}</dd>
        <dt className="text-muted">Procedimento</dt><dd>{consulta.procedimento}</dd>
        <dt className="text-muted">Dentista</dt><dd>{consulta.profissional}</dd>
        <dt className="text-muted">Telefone</dt><dd>{telefone(consulta.telefone)}</dd>
        <dt className="text-muted">Status</dt><dd><SeloStatus status={consulta.status} /></dd>
        <dt className="text-muted">Marcada por</dt><dd><Selo>{{ isis: 'Ísis', recepcao: 'Recepção', paciente_botao: 'Paciente' }[consulta.source] ?? consulta.source}</Selo></dd>
      </dl>

      {modo === 'ver' && ativa && (
        <div className="mt-6 flex flex-wrap gap-2">
          {consulta.status === 'agendada' && (
            <Botao variante="secundario" disabled={ocupado} onClick={() => status.mutate('confirmada')}><Check className="size-4" />Confirmar</Botao>
          )}
          <Botao variante="secundario" disabled={ocupado} onClick={() => status.mutate('realizada')}><UserCheck className="size-4" />Compareceu</Botao>
          <Botao variante="secundario" disabled={ocupado} onClick={() => status.mutate('faltou')}><UserX className="size-4" />Faltou</Botao>
          <Botao variante="secundario" disabled={ocupado} onClick={() => setModo('remarcar')}><CalendarClock className="size-4" />Remarcar</Botao>
          <Botao variante="perigo" disabled={ocupado} onClick={() => setModo('cancelar')}><XCircle className="size-4" />Cancelar</Botao>
        </div>
      )}

      {modo === 'remarcar' && (
        <div className="mt-6 space-y-3">
          <Campo rotulo="Novo dia"><Entrada type="date" value={dia} onChange={(e) => { setDia(e.target.value); setNovo(null) }} /></Campo>
          <p className="text-sm text-muted">{dia && diaLegivel(dia)} — horários livres com {consulta.profissional}</p>
          <div className="flex max-h-44 flex-wrap gap-2 overflow-y-auto">
            {slots.data?.length === 0 && <span className="text-sm text-muted">Nenhum horário livre.</span>}
            {slots.data?.map((s) => (
              <button key={s.starts_at} type="button" onClick={() => setNovo(s)}
                className={`rounded-xl border px-3 py-1.5 text-sm ${novo?.starts_at === s.starts_at ? 'border-primary bg-primary text-primary-contrast' : 'border-line hover:border-primary'}`}>
                {hora(s.starts_at, tz)}
              </button>
            ))}
          </div>
          <div className="flex justify-end gap-2">
            <Botao variante="fantasma" onClick={() => setModo('ver')}>Voltar</Botao>
            <Botao disabled={!novo || ocupado} onClick={() => remarcar.mutate()}>Remarcar</Botao>
          </div>
        </div>
      )}

      {modo === 'cancelar' && (
        <div className="mt-6 space-y-3">
          <Campo rotulo="Motivo (opcional)"><Entrada value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Ex.: paciente pediu por telefone" /></Campo>
          <p className="text-sm text-muted">O paciente recebe uma mensagem avisando do cancelamento.</p>
          <div className="flex justify-end gap-2">
            <Botao variante="fantasma" onClick={() => setModo('ver')}>Voltar</Botao>
            <Botao variante="perigo" disabled={ocupado} onClick={() => cancelar.mutate()}>Confirmar cancelamento</Botao>
          </div>
        </div>
      )}
    </Modal>
  )
}
