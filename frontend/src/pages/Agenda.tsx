import { useState } from 'react'
import { Plus } from 'lucide-react'
import type { Consulta } from '../lib/api'
import { PageHeader } from '../components/PageHeader'
import { AgendaSemana } from '../components/agenda/AgendaSemana'
import { ModalConsulta } from '../components/agenda/ModalConsulta'
import { ModalNovaConsulta, type Previa } from '../components/agenda/ModalNovaConsulta'
import { Botao } from '../components/ui'
import { useTermos } from '../lib/termos'

export function Agenda() {
  const pal = useTermos()
  const [aberta, setAberta] = useState<Consulta | null>(null)
  const [previa, setPrevia] = useState<Previa | undefined>()

  return (
    <>
      <div className="flex items-start justify-between gap-4">
        <PageHeader titulo="Agenda" subtitulo={`Clique num horário vazio para marcar; clique em ${pal.uma} ${pal.atendimento} para ver ou alterar`} />
        <Botao onClick={() => setPrevia({})}><Plus className="size-4" />{pal.Nova} {pal.atendimento}</Botao>
      </div>
      <div className="h-[calc(100vh-220px)] min-h-[520px] rounded-3xl bg-surface p-5">
        <AgendaSemana onConsulta={setAberta} onVazio={(dia, hora, professionalId) => setPrevia({ dia, hora, professionalId })} />
      </div>
      <ModalConsulta consulta={aberta} onFechar={() => setAberta(null)} />
      <ModalNovaConsulta aberto={!!previa} previa={previa} onFechar={() => setPrevia(undefined)} />
    </>
  )
}
