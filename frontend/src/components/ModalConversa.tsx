import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bot, CalendarPlus, Check, CheckCheck, Hand, MessageSquareOff, Send, Stethoscope } from 'lucide-react'
import { AcoesArquivo } from './ArquivarContato'
import { PainelTratamentos, Tags } from './Tratamentos'
import { ModalNovaConsulta } from './agenda/ModalNovaConsulta'
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
  const [verTratamento, setVerTratamento] = useState(false)
  const [marcando, setMarcando] = useState(false)
  // objeto estável: a janela de marcar reinicia o formulário quando a prévia muda
  const previaMarcar = useMemo(() => (card ? { telefone: card.phone, nome: card.name ?? undefined } : undefined), [card])
  // Paciente que nunca escreveu: a Ísis não puxa conversa; quem inicia é a equipe (fica em atendimento manual)
  const iniciar = useMutation({
    mutationFn: (t: string) => api.post(`/clinics/${clinica.id}/patients/${card!.id}/conversation/start`, { texto: t }),
    onSuccess: () => { setTexto(''); recarregar(); aviso.ok('Conversa iniciada pelo WhatsApp. Ela fica em atendimento manual.') },
    onError: aviso.erro,
  })
  const abertos = (trat.data?.tratamentos ?? []).filter((t) => t.status === 'em_andamento' || t.status === 'aguardando')
  const base = conversa ? `/clinics/${clinica.id}/conversations/${conversa.id}` : ''

  useEffect(() => {
    fimRef.current?.scrollIntoView()
  }, [q.data?.mensagens.length])
  useEffect(() => {
    setTexto('')
  }, [card])

  // Atualiza na hora esta janela e o que depende do modo de atendimento (não espera o aviso em tempo real)
  const qc = useQueryClient()
  const recarregar = () => ['chat', 'kanban', 'dashboard', 'notificacoes'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }))
  const assumir = useMutation({ mutationFn: () => api.post(`${base}/takeover`), onSuccess: () => { recarregar(); aviso.ok(`Você assumiu a conversa. A assistente ${ia} está pausada.`) }, onError: aviso.erro })
  const devolver = useMutation({ mutationFn: () => api.post(`${base}/release`), onSuccess: () => { recarregar(); aviso.ok(`Conversa devolvida para a assistente ${ia}.`) }, onError: aviso.erro })
  const responder = useMutation({ mutationFn: (t: string) => api.post(`${base}/reply`, { texto: t }), onSuccess: () => { setTexto(''); recarregar(); aviso.ok('Mensagem enviada.') }, onError: aviso.erro })

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
        <div className="flex flex-wrap gap-2">
          {/* Etapa 21: tratamento abre numa janela, como o botão de atendimento */}
          <Botao variante="secundario" onClick={() => setVerTratamento(true)}>
            <Stethoscope className="size-4" />Tratamento
            {abertos.length > 0 && <span className="rounded-full bg-primary px-1.5 text-[11px] font-semibold text-primary-contrast">{abertos.length}</span>}
          </Botao>
          {conversa && (manual
            ? <Botao variante="secundario" disabled={devolver.isPending} onClick={() => devolver.mutate()}><Bot className="size-4" />Devolver para {ia}</Botao>
            : <Botao variante="secundario" disabled={assumir.isPending} onClick={() => assumir.mutate()}><Hand className="size-4" />Assumir conversa</Botao>)}
          {/* Etapa 29 (D112): tirar das listas o contato que entrou por engano */}
          <AcoesArquivo contato={card} onFeito={() => onFechar()} />
        </div>
      </div>

      <Tags tags={trat.data?.tags} className="mb-3 flex" />
      <Modal titulo={`Tratamento · ${card.name ?? telefone(card.phone)}`} aberto={verTratamento} onFechar={() => setVerTratamento(false)} largura="max-w-xl">
        <PainelTratamentos pacienteId={card.id} />
      </Modal>

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

      {!conversa && !q.isLoading && (
        <div className="mt-3 space-y-3">
          <p className="text-xs text-muted">A assistente só responde quando o paciente escreve. Para puxar a conversa, use uma das ações abaixo.</p>
          <form onSubmit={(e) => { e.preventDefault(); if (texto.trim()) iniciar.mutate(texto.trim()) }} className="flex gap-2">
            <Entrada className="flex-1" value={texto} onChange={(e) => setTexto(e.target.value)} maxLength={2000}
              placeholder="Escreva a primeira mensagem (sai pelo WhatsApp da clínica)" />
            <Botao type="submit" aria-label="Iniciar conversa" disabled={!texto.trim() || iniciar.isPending}><Send className="size-4" /></Botao>
          </form>
          <Botao variante="secundario" onClick={() => setMarcando(true)}><CalendarPlus className="size-4" />Marcar consulta</Botao>
        </div>
      )}
      <ModalNovaConsulta aberto={marcando} onFechar={() => setMarcando(false)} previa={previaMarcar} />

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
