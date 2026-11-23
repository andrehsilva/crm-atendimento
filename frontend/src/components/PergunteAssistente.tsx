import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useMutation } from '@tanstack/react-query'
import { Eraser, Loader2, MessageCircleQuestion, SendHorizontal, X } from 'lucide-react'
import { api } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { Formatado } from './TextoRico'

type Fala = { autor: 'equipe' | 'assistente'; texto: string }

const SUGESTOES = [
  'Quantas consultas tivemos este mês?',
  'Qual procedimento sai mais?',
  'Quem mais faltou nos últimos 3 meses?',
  'Quantos contatos novos chegaram esta semana?',
]

/** Etapa 30 (D117–D120): a equipe pergunta sobre os dados da clínica. Só consulta; a conversa some ao fechar. */
export function PergunteAssistente({ onFechar }: { onFechar: () => void }) {
  const { clinica } = useClinica()
  const [falas, setFalas] = useState<Fala[]>([])
  const [texto, setTexto] = useState('')
  const fim = useRef<HTMLDivElement>(null)
  const campo = useRef<HTMLTextAreaElement>(null)

  const perguntar = useMutation({
    mutationFn: (mensagens: Fala[]) =>
      api.post<{ resposta: string }>(`/clinics/${clinica.id}/pergunte`, { mensagens: mensagens.slice(-10) }),
    onSuccess: (r) => setFalas((f) => [...f, { autor: 'assistente', texto: r.resposta }]),
    onError: (e) => setFalas((f) => [...f, { autor: 'assistente', texto: e instanceof Error ? e.message : 'Não consegui responder agora.' }]),
  })

  useEffect(() => { fim.current?.scrollIntoView({ behavior: 'smooth' }) }, [falas, perguntar.isPending])
  useEffect(() => { campo.current?.focus() }, [])
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && onFechar()
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onFechar])

  function enviar(pergunta: string) {
    const t = pergunta.trim()
    if (!t || perguntar.isPending) return
    const novas: Fala[] = [...falas, { autor: 'equipe', texto: t }]
    setFalas(novas)
    setTexto('')
    perguntar.mutate(novas)
  }

  return createPortal(
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30" onMouseDown={onFechar}>
      <section role="dialog" aria-modal="true" aria-label="Perguntar à assistente"
        className="flex h-full w-full max-w-md flex-col border-l border-line bg-surface shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}>
        <header className="flex items-center gap-3 border-b border-line px-5 py-4">
          <div className="grid size-9 place-items-center rounded-xl bg-primary-soft text-primary">
            <MessageCircleQuestion className="size-5" />
          </div>
          <div className="min-w-0 flex-1 leading-tight">
            <h2 className="font-semibold">Perguntar à assistente</h2>
            <p className="text-xs text-muted">Só consulta os dados da {clinica.name}. Não altera nada.</p>
          </div>
          {falas.length > 0 && (
            <button type="button" title="Limpar conversa" aria-label="Limpar conversa" onClick={() => setFalas([])}
              className="rounded-lg p-1.5 text-muted hover:bg-surface-muted hover:text-text"><Eraser className="size-5" /></button>
          )}
          <button type="button" title="Fechar" aria-label="Fechar" onClick={onFechar}
            className="rounded-lg p-1.5 text-muted hover:bg-surface-muted hover:text-text"><X className="size-5" /></button>
        </header>

        <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
          {falas.length === 0 && (
            <div className="space-y-3 text-sm">
              <p className="text-muted">Pergunte sobre agenda, clientes, procedimentos, tratamentos ou CRM. Por exemplo:</p>
              <div className="flex flex-col gap-2">
                {SUGESTOES.map((s) => (
                  <button key={s} type="button" onClick={() => enviar(s)}
                    className="rounded-xl border border-line px-3 py-2 text-left hover:border-primary hover:bg-primary-soft hover:text-primary">
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {falas.map((f, i) => (
            <div key={i} className={`flex ${f.autor === 'equipe' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                f.autor === 'equipe' ? 'bg-primary text-primary-contrast' : 'bg-surface-muted text-text'}`}>
                {f.autor === 'equipe' ? <span className="whitespace-pre-wrap">{f.texto}</span> : <Formatado texto={f.texto} />}
              </div>
            </div>
          ))}
          {perguntar.isPending && (
            <div className="flex items-center gap-2 text-sm text-muted"><Loader2 className="size-4 animate-spin" />Consultando os dados…</div>
          )}
          <div ref={fim} />
        </div>

        <form className="flex items-end gap-2 border-t border-line p-4" onSubmit={(e) => { e.preventDefault(); enviar(texto) }}>
          <textarea ref={campo} rows={2} value={texto} maxLength={2000} placeholder="Ex.: quantas vezes o André veio aqui?"
            onChange={(e) => setTexto(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviar(texto) } }}
            className="min-h-[44px] flex-1 resize-none rounded-xl border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-primary" />
          <button type="submit" disabled={!texto.trim() || perguntar.isPending} aria-label="Enviar pergunta" title="Enviar"
            className="grid size-11 place-items-center rounded-xl bg-primary text-primary-contrast disabled:opacity-50">
            <SendHorizontal className="size-5" />
          </button>
        </form>
      </section>
    </div>,
    document.body,
  )
}
