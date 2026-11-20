import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, RotateCcw } from 'lucide-react'
import { api, type Consulta } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { useAviso } from '../components/Aviso'
import { ChatTeste } from '../components/ChatTeste'
import { MensagensFeed } from '../components/MensagensFeed'
import { AgendaSemana } from '../components/agenda/AgendaSemana'
import { ModalConsulta } from '../components/agenda/ModalConsulta'
import { Botao } from '../components/ui'

/** Tela de demonstração (D11 / imagem 03): chat + agenda + mensagens lado a lado. */
export function Demo() {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const [aberta, setAberta] = useState<Consulta | null>(null)

  const reset = useMutation({
    mutationFn: () => api.post('/dev/reset-demo'),
    onSuccess: () => { qc.invalidateQueries(); aviso.ok('Demonstração reiniciada') },
    onError: aviso.erro,
  })

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link to="/" aria-label="Voltar ao painel" className="rounded-lg p-1.5 text-muted hover:bg-surface hover:text-text"><ArrowLeft className="size-5" /></Link>
          <div>
            <h1 className="text-xl font-bold">{clinica.name}</h1>
            <p className="text-sm text-muted">Demonstração · tudo muda em tempo real</p>
          </div>
        </div>
        <Botao variante="secundario" disabled={reset.isPending} onClick={() => reset.mutate()}>
          <RotateCcw className="size-4" />{reset.isPending ? 'Reiniciando…' : 'Reiniciar demonstração'}
        </Botao>
      </header>
      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(280px,1fr)_2.2fr_minmax(280px,1fr)]">
        <section className="flex min-h-[480px] flex-col rounded-3xl bg-surface p-4"><ChatTeste /></section>
        <section className="min-h-[480px] rounded-3xl bg-surface p-4"><AgendaSemana compacta onConsulta={setAberta} /></section>
        <section className="flex min-h-[480px] flex-col rounded-3xl bg-surface p-4">
          <h2 className="text-lg font-semibold">Mensagens enviadas</h2>
          <p className="mb-3 text-sm text-muted">WhatsApp dos pacientes e recados</p>
          <div className="flex-1 overflow-y-auto pr-1"><MensagensFeed limite={30} /></div>
        </section>
      </div>
      <ModalConsulta consulta={aberta} onFechar={() => setAberta(null)} />
    </div>
  )
}
