import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Bot, Hand, MessageSquareOff, Send } from 'lucide-react'
import { api, type CardCrm, type MensagemChat } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { dataCurta, hora, telefone } from '../lib/formato'
import { useAviso } from './Aviso'
import { Botao, Entrada, Modal, Selo, Vazio } from './ui'

type Conversa = { conversa: { id: string; channel: string; status: 'ativa' | 'humano' | 'encerrada' } | null; mensagens: MensagemChat[] }

const AUTOR: Record<string, string> = { paciente: '', isis: 'Ísis', recepcao: 'Equipe', sistema: 'Sistema' }

/** Conversa do paciente + atendimento humano (RN-AT-06): assumir, responder, devolver para a Ísis. */
export function ModalConversa({ card, onFechar }: { card: Pick<CardCrm, 'id' | 'name' | 'phone'> | null; onFechar: () => void }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const tz = clinica.timezone
  const [texto, setTexto] = useState('')
  const fimRef = useRef<HTMLDivElement>(null)

  const q = useQuery({
    queryKey: ['chat', 'painel', card?.id],
    queryFn: () => api.get<Conversa>(`/clinics/${clinica.id}/patients/${card!.id}/conversation`),
    enabled: !!card,
  })
  const conversa = q.data?.conversa
  const base = conversa ? `/clinics/${clinica.id}/conversations/${conversa.id}` : ''

  useEffect(() => {
    fimRef.current?.scrollIntoView()
  }, [q.data?.mensagens.length])
  useEffect(() => {
    setTexto('')
  }, [card])

  const assumir = useMutation({ mutationFn: () => api.post(`${base}/takeover`), onSuccess: () => aviso.ok('Você assumiu a conversa. A Ísis está pausada.'), onError: aviso.erro })
  const devolver = useMutation({ mutationFn: () => api.post(`${base}/release`), onSuccess: () => aviso.ok('Conversa devolvida para a Ísis.'), onError: aviso.erro })
  const responder = useMutation({ mutationFn: (t: string) => api.post(`${base}/reply`, { texto: t }), onSuccess: () => setTexto(''), onError: aviso.erro })

  function enviar(e: FormEvent) {
    e.preventDefault()
    if (texto.trim()) responder.mutate(texto.trim())
  }

  if (!card) return null
  const manual = conversa?.status === 'humano'
  return (
    <Modal titulo={card.name ?? telefone(card.phone)} aberto onFechar={onFechar} largura="max-w-2xl">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm text-muted">
          {telefone(card.phone)}
          {conversa && <Selo>{conversa.channel === 'web' ? 'Chat web' : 'WhatsApp'}</Selo>}
          {conversa && (manual ? <Selo cor="ambar"><Hand className="size-3" />Atendimento manual</Selo> : <Selo><Bot className="size-3" />Ísis respondendo</Selo>)}
        </div>
        {conversa && (manual
          ? <Botao variante="secundario" disabled={devolver.isPending} onClick={() => devolver.mutate()}><Bot className="size-4" />Devolver para a Ísis</Botao>
          : <Botao variante="secundario" disabled={assumir.isPending} onClick={() => assumir.mutate()}><Hand className="size-4" />Assumir conversa</Botao>)}
      </div>

      <div className="h-[46vh] space-y-2 overflow-y-auto rounded-2xl bg-surface-muted p-3">
        {!q.data?.mensagens.length && <Vazio icone={<MessageSquareOff className="size-8" />} texto={q.isLoading ? 'Carregando…' : 'Este paciente ainda não conversou.'} />}
        {q.data?.mensagens.map((m) => (
          <div key={m.id} className={`flex ${m.direction === 'in' ? 'justify-start' : 'justify-end'}`}>
            <div className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm ${m.direction === 'in' ? 'bg-surface' : m.author === 'recepcao' ? 'bg-[#fcf1dc] text-[#5c4108]' : 'bg-primary-soft'}`}>
              {AUTOR[m.author] && <p className="mb-0.5 text-[11px] font-semibold opacity-70">{AUTOR[m.author]}</p>}
              <p className="whitespace-pre-line">{m.content}</p>
              <p className="mt-1 text-right text-[10px] opacity-60">{dataCurta(m.created_at, tz)} {hora(m.created_at, tz)}</p>
            </div>
          </div>
        ))}
        <div ref={fimRef} />
      </div>

      {conversa && (
        <form onSubmit={enviar} className="mt-3 flex gap-2">
          <Entrada className="flex-1" value={texto} onChange={(e) => setTexto(e.target.value)} maxLength={2000}
            placeholder={manual ? 'Responder como equipe da clínica' : 'Responder (isso pausa a Ísis nesta conversa)'} />
          <Botao type="submit" aria-label="Enviar resposta" disabled={!texto.trim() || responder.isPending}><Send className="size-4" /></Botao>
        </form>
      )}
    </Modal>
  )
}
