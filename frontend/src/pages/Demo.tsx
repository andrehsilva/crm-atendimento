import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, RotateCcw } from 'lucide-react'
import { api, type Consulta } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { useAviso } from '../components/Aviso'
import { ChatTeste } from '../components/ChatTeste'
import { AgendaSemana } from '../components/agenda/AgendaSemana'
import { ModalConsulta } from '../components/agenda/ModalConsulta'
import { Botao, Modal } from '../components/ui'

/** Tela de demonstração (D11): conversar com a assistente e ver a agenda mudar na hora, lado a lado. */
export function Demo() {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const [aberta, setAberta] = useState<Consulta | null>(null)
  const [confirmar, setConfirmar] = useState(false)
  // O reinício vale só para a clínica de demonstração (endereço /demo), nunca para a clínica aberta (D56)
  const ehDemo = clinica.slug === 'demo'

  const reset = useMutation({
    mutationFn: () => api.post('/dev/reset-demo'),
    onSuccess: () => { qc.invalidateQueries(); setConfirmar(false); aviso.ok('Demonstração reiniciada') },
    onError: aviso.erro,
  })

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link to="/" aria-label="Voltar ao painel" className="rounded-lg p-1.5 text-muted hover:bg-surface hover:text-text"><ArrowLeft className="size-5" /></Link>
          <div>
            <h1 className="text-xl font-bold">{clinica.name}</h1>
            <p className="text-sm text-muted">Converse como {clinica.termos.cliente} à esquerda e veja a agenda mudar na hora</p>
          </div>
        </div>
        {ehDemo && (
          <Botao variante="secundario" onClick={() => setConfirmar(true)}>
            <RotateCcw className="size-4" />Reiniciar demonstração
          </Botao>
        )}
      </header>
      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(320px,380px)_1fr]">
        <section className="flex min-h-[520px] flex-col rounded-3xl bg-surface p-4"><ChatTeste /></section>
        <section className="min-h-[520px] overflow-y-auto rounded-3xl bg-surface p-5"><AgendaSemana onConsulta={setAberta} /></section>
      </div>
      <ModalConsulta consulta={aberta} onFechar={() => setAberta(null)} />
      <Modal titulo="Reiniciar a demonstração?" aberto={confirmar} onFechar={() => setConfirmar(false)}>
        <p className="text-sm">
          Apaga os {clinica.termos.clientes}, {clinica.termos.atendimentos}, conversas e mensagens de <strong>{clinica.name}</strong> e
          cria alguns exemplos novos com a sua equipe e os seus procedimentos.
        </p>
        <p className="mt-3 text-sm text-muted">
          Ficam como estão: nome, logo, cor, assistente, chave de IA, WhatsApp, horários, equipe, procedimentos e usuários.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <Botao variante="fantasma" onClick={() => setConfirmar(false)}>Cancelar</Botao>
          <Botao variante="perigo" disabled={reset.isPending} onClick={() => reset.mutate()}>
            {reset.isPending ? 'Reiniciando…' : 'Reiniciar'}
          </Botao>
        </div>
      </Modal>
    </div>
  )
}
