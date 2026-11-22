import { useCallback, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
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
  // ?dia=2026-11-24&consulta=<id> (vindo do sino)
  const [busca, setBusca] = useSearchParams()
  const diaPedido = busca.get('dia')
  const consultaPedida = busca.get('consulta')
  const ir = useMemo(() => (diaPedido && /^\d{4}-\d{2}-\d{2}$/.test(diaPedido) ? { dia: diaPedido, consultaId: consultaPedida } : undefined),
    [diaPedido, consultaPedida])
  const irFeito = useCallback(() => setBusca({}, { replace: true }), [setBusca])

  return (
    <>
      <div className="flex items-start justify-between gap-4">
        <PageHeader titulo="Agenda" subtitulo={`Clique num horário vazio para marcar; clique em ${pal.uma} ${pal.atendimento} para ver ou alterar`} />
        <Botao onClick={() => setPrevia({})}><Plus className="size-4" />{pal.Nova} {pal.atendimento}</Botao>
      </div>
      <div className="h-[calc(100vh-220px)] min-h-[520px] rounded-3xl bg-surface p-5">
        <AgendaSemana ir={ir} onIrFeito={irFeito} onConsulta={setAberta} onVazio={(dia, hora, professionalId) => setPrevia({ dia, hora, professionalId })} />
      </div>
      <ModalConsulta consulta={aberta} onFechar={() => setAberta(null)} />
      <ModalNovaConsulta aberto={!!previa} previa={previa} onFechar={() => setPrevia(undefined)} />
    </>
  )
}
