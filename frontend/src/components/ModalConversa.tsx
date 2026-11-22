import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Bot, Check, CheckCheck, Hand, MessageSquareOff, Send } from 'lucide-react'
import { PainelTratamentos, Tags } from './Tratamentos'
import { api, type CardCrm, type MensagemChat, type TratamentosPaciente } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { dataCurta, hora, telefone } from '../lib/formato'
import { useAviso } from './Aviso'
import { Botao, Entrada, Modal, Selo, Vazio } from './ui'
import { useTermos } from '../lib/termos'

type Conversa = { conversa: { id: string; channel: string; status: 'ativa' | 'humano' | 'encerrada' } | null; mensagens: MensagemChat[] }

const AUTOR: Record<string, string> = { paciente: '', recepcao: 'Equipe', sistema: 'Sistema' }

/** Conversa do paciente + atendimento humano (RN-AT-06): assumir, responder, devolver para a Ísis. */
export function ModalConversa({ card, onFechar }: { card: Pick<CardCrm, 'id' | 'name' | 'phone'> | null; onFechar: () => void }) {
  const { clinica } = useClinica()
  const pal = useTermos()
  const ia = clinica.nome_assistente
  const autor = (a: string) => (a === 'isis' ? ia : AUTOR[a])
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
  // Etapa 21: tags e tratamentos do paciente ao lado da conversa
  const trat = useQuery({
    queryKey: ['tratamentos', clinica.id, card?.id],
    queryFn: () => api.get<TratamentosPaciente>(`/clinics/${clinica.id}/patients/${card!.id}/tratamentos`),
    enabled: !!card,
  })
  const abertos = (trat.data?.tratamentos ?? []).filter((t) => t.status === 'em_andamento' || t.status === 'aguardando')
  const base = conversa ? `/clinics/${clinica.id}/conversations/${conversa.id}` : ''

  useEffect(() => {
    fimRef.current?.scrollIntoView()
  }, [q.data?.mensagens.length])
  useEffect(() => {
    setTexto('')
  }, [card])

  const assumir = useMutation({ mutationFn: () => api.post(`${base}/takeover`), onSuccess: () => aviso.ok(`Você assumiu a conversa. A assistente ${ia} está pausada.`), onError: aviso.erro })
  const devolver = useMutation({ mutationFn: () => api.post(`${base}/release`), onSuccess: () => aviso.ok(`Conversa devolvida para a assistente ${ia}.`), onError: aviso.erro })
  const responder = useMutation({ mutationFn: (t: string) => api.post(`${base}/reply`, { texto: t }), onSuccess: () => { setTexto(''); aviso.ok('Mensagem enviada.') }, onError: aviso.erro })

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
          {conversa && (manual ? <Selo cor="ambar"><Hand className="size-3" />Atendimento manual</Selo> : <Selo><Bot className="size-3" />{ia} respondendo</Selo>)}
        </div>
        {conversa && (manual
          ? <Botao variante="secundario" disabled={devolver.isPending} onClick={() => devolver.mutate()}><Bot className="size-4" />Devolver para {ia}</Botao>
          : <Botao variante="secundario" disabled={assumir.isPending} onClick={() => assumir.mutate()}><Hand className="size-4" />Assumir conversa</Botao>)}
      </div>

      <Tags tags={trat.data?.tags} className="mb-3 flex" />
      <details className="mb-3 rounded-2xl border border-line px-4 py-2" open={abertos.length > 0 || undefined}>
        <summary className="cursor-pointer py-1 text-sm text-muted">
          Tratamentos{abertos.length ? ` (${abertos.length} aberto${abertos.length > 1 ? 's' : ''})` : ''}
        </summary>
        <div className="pb-2 pt-2"><PainelTratamentos pacienteId={card.id} compacto /></div>
      </details>

      <div className="h-[46vh] space-y-2 overflow-y-auto rounded-2xl bg-surface-muted p-3">
        {!q.data?.mensagens.length && <Vazio icone={<MessageSquareOff className="size-8" />} texto={q.isLoading ? 'Carregando…' : `Este ${pal.cliente} ainda não conversou.`} />}
        {q.data?.mensagens.map((m) => (
          <div key={m.id} className={`flex ${m.direction === 'in' ? 'justify-start' : 'justify-end'}`}>
            <div className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm ${m.direction === 'in' ? 'bg-surface' : m.author === 'recepcao' ? 'bg-[#fcf1dc] text-[#5c4108]' : 'bg-primary-soft'}`}>
              {autor(m.author) && <p className="mb-0.5 text-[11px] font-semibold opacity-70">{autor(m.author)}</p>}
              <p className="whitespace-pre-line">{m.content}</p>
              <p className="mt-1 flex items-center justify-end gap-1 text-[10px]">
                <span className="opacity-60">{dataCurta(m.created_at, tz)} {hora(m.created_at, tz)}</span>
                {m.entrega && <Entrega e={m.entrega} />}
              </p>
            </div>
          </div>
        ))}
        <div ref={fimRef} />
      </div>

      {conversa && (
        <form onSubmit={enviar} className="mt-3 flex gap-2">
          <Entrada className="flex-1" value={texto} onChange={(e) => setTexto(e.target.value)} maxLength={2000}
            placeholder={manual ? 'Responder como equipe da clínica' : 'Responder (isso pausa a assistente nesta conversa)'} />
          <Botao type="submit" aria-label="Enviar resposta" disabled={!texto.trim() || responder.isPending}><Send className="size-4" /></Botao>
        </form>
      )}
    </Modal>
  )
}

/** D85: ✓ enviada · ✓✓ entregue · ✓✓ azul lida — como no WhatsApp. */
function Entrega({ e }: { e: 'enviada' | 'entregue' | 'lida' }) {
  const rotulo = { enviada: 'Enviada', entregue: 'Entregue', lida: 'Lida' }[e]
  return (
    <span title={rotulo} aria-label={rotulo} className={e === 'lida' ? 'text-[#2f8be6] dark:text-[#6cb4f5]' : 'opacity-60'}>
      {e === 'enviada' ? <Check className="size-3.5" /> : <CheckCheck className="size-3.5" />}
    </span>
  )
}
