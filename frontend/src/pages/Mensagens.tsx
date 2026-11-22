import { useState } from 'react'
import { PageHeader } from '../components/PageHeader'
import { MensagensFeed } from '../components/MensagensFeed'
import { RelogioTeste } from '../components/RelogioTeste'
import { useTermos } from '../lib/termos'

const FILTROS = [
  ['', 'Todas'],
  ['confirmacao', 'Confirmações'],
  ['remarcacao', 'Remarcações'],
  ['cancelamento', 'Cancelamentos'],
  ['lembrete', 'Lembretes'],
  ['aniversario', 'Aniversários'],
  ['campanha', 'Campanhas'],
] as const

export function Mensagens() {
  const pal = useTermos()
  const [tipo, setTipo] = useState('')
  return (
    <>
      <PageHeader titulo="Mensagens" subtitulo={`Tudo o que foi enviado aos ${pal.clientes}. Aniversário e campanhas se configuram em Configurações › Aniversário e campanhas`} />
      <RelogioTeste />
      <div className="mb-4 flex flex-wrap gap-2">
        {FILTROS.map(([valor, rotulo]) => (
          <button key={valor} type="button" onClick={() => setTipo(valor)}
            className={`rounded-full px-4 py-1.5 text-sm transition ${tipo === valor ? 'bg-primary text-primary-contrast' : 'bg-surface text-muted hover:text-text'}`}>
            {rotulo}
          </button>
        ))}
      </div>
      <div className="rounded-3xl bg-surface p-5">
        <MensagensFeed tipo={tipo || undefined} limite={200} colunas />
      </div>
    </>
  )
}
