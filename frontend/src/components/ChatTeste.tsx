import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Send } from 'lucide-react'
import { api, type MensagemChat } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { hora } from '../lib/formato'
import { useAviso } from './Aviso'
import { Botao, Entrada } from './ui'
import { useTermos } from '../lib/termos'

/** Chat de TESTE (D15): o "paciente" informa o telefone e conversa com a Ísis (IA). */
export function ChatTeste() {
  const { clinica } = useClinica()
  const pal = useTermos()
  const aviso = useAviso()
  const qc = useQueryClient()
  const [telefone, setTelefone] = useState('')
  const [nome, setNome] = useState('')
  const [sessao, setSessao] = useState<string | null>(null)
  const [texto, setTexto] = useState('')
  const fimRef = useRef<HTMLDivElement>(null)

  // Histórico vem do servidor e recarrega pelos avisos em tempo real (inclui respostas da equipe)
  const chave = ['chat', 'web', clinica.slug, sessao]
  const historico = useQuery({
    queryKey: chave,
    queryFn: () => api.get<MensagemChat[]>(`/web/${clinica.slug}/history?telefone=${encodeURIComponent(sessao!)}`),
    enabled: !!sessao,
  })
  const msgs = historico.data ?? []

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs.length])

  const entrar = useMutation({
    mutationFn: () => api.post(`/web/${clinica.slug}/session`, { telefone, nome: nome || null }),
    onSuccess: () => setSessao(telefone),
    onError: aviso.erro,
  })
  const enviar = useMutation({
    mutationFn: (t: string) => api.post<MensagemChat[]>(`/web/${clinica.slug}/messages`, { telefone: sessao, texto: t }),
    onSettled: () => qc.invalidateQueries({ queryKey: chave }),
    onError: aviso.erro,
  })

  function submeter(e: FormEvent) {
    e.preventDefault()
    const t = texto.trim()
    if (!t || enviar.isPending) return
    setTexto('')
    enviar.mutate(t)
  }

  if (!sessao) {
    return (
      <form className="flex h-full flex-col justify-center gap-3" onSubmit={(e) => { e.preventDefault(); entrar.mutate() }}>
        <div className="mb-2 flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-full bg-primary font-semibold text-primary-contrast">Í</span>
          <div>
            <div className="font-semibold">Ísis</div>
            <div className="text-xs text-muted">atendente virtual · {clinica.name}</div>
          </div>
        </div>
        <p className="text-sm text-muted">Para começar, informe o telefone (com DDD) como se fosse o {pal.cliente}.</p>
        <Entrada value={telefone} onChange={(e) => setTelefone(e.target.value)} placeholder="(11) 98765-4321" inputMode="tel" required />
        <Entrada value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Seu nome (opcional)" />
        <Botao type="submit" disabled={entrar.isPending || telefone.replace(/\D/g, '').length < 10}>Começar conversa</Botao>
      </form>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="mb-3 flex items-center justify-between gap-3 border-b border-line pb-3">
        <div className="flex items-center gap-3">
          <span className="grid size-9 place-items-center rounded-full bg-primary font-semibold text-primary-contrast">Í</span>
          <div>
            <div className="text-sm font-semibold">Ísis</div>
            <div className="text-xs text-muted">atendente virtual · online</div>
          </div>
        </div>
        <button type="button" className="text-xs text-muted hover:text-text" onClick={() => setSessao(null)}>trocar telefone</button>
      </div>
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
        {msgs.length === 0 && <p className="text-center text-xs text-muted">Diga "oi" para a Ísis 👋</p>}
        {msgs.map((m) => (
          <div key={m.id} className={`flex ${m.direction === 'in' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${m.direction === 'in' ? 'bg-primary text-primary-contrast' : 'bg-surface-muted'}`}>
              {m.author === 'recepcao' && <p className="mb-0.5 text-[11px] font-semibold text-primary">Equipe da clínica</p>}
              <p className="whitespace-pre-line">{m.content}</p>
              <p className="mt-1 text-right text-[10px] opacity-70">{hora(m.created_at, clinica.timezone)}</p>
            </div>
          </div>
        ))}
        {enviar.isPending && !msgs.some((m) => m.direction === 'in' && m.content === enviar.variables) && (
          <div className="flex justify-end">
            <div className="max-w-[85%] rounded-2xl bg-primary px-3 py-2 text-sm text-primary-contrast opacity-70">{enviar.variables}</div>
          </div>
        )}
        {enviar.isPending && <p className="text-xs text-muted">Ísis está digitando…</p>}
        <div ref={fimRef} />
      </div>
      <form onSubmit={submeter} className="mt-3 flex gap-2">
        <Entrada className="flex-1" value={texto} onChange={(e) => setTexto(e.target.value)} placeholder={`Escreva como se fosse o ${pal.cliente}`} maxLength={2000} />
        <Botao type="submit" aria-label="Enviar" disabled={!texto.trim() || enviar.isPending}><Send className="size-4" /></Botao>
      </form>
    </div>
  )
}
