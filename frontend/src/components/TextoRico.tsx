import { useRef, type ReactNode } from 'react'
import { Bold, Italic, Link2, List } from 'lucide-react'

// Texto com formatação simples (Etapa 9C, D48), guardado como Markdown:
//   **negrito**  *itálico*  "- " no começo da linha = lista  [texto](https://...) = link
// O desenho é feito com elementos React (nunca HTML cru): o que alguém digita não vira código na página.

const LINK_SEGURO = /^https?:\/\//i
const TOKENS = /(\*\*[^*\n]+\*\*|\*[^*\n]+\*|\[[^\]\n]+\]\([^)\s]+\)|https?:\/\/[^\s)]+)/g

function trecho(t: string, chave: string): ReactNode[] {
  return t.split(TOKENS).filter(Boolean).map((p, i) => {
    const k = `${chave}-${i}`
    if (p.startsWith('**') && p.endsWith('**') && p.length > 4) return <strong key={k}>{p.slice(2, -2)}</strong>
    if (p.startsWith('*') && p.endsWith('*') && p.length > 2) return <em key={k}>{p.slice(1, -1)}</em>
    const md = /^\[([^\]]+)\]\(([^)\s]+)\)$/.exec(p)
    const [texto, href] = md ? [md[1], md[2]] : [p, p]
    if ((md || LINK_SEGURO.test(p)) && LINK_SEGURO.test(href)) {
      return <a key={k} href={href} target="_blank" rel="noopener noreferrer" className="text-primary underline break-all">{texto}</a>
    }
    return <span key={k}>{p}</span>
  })
}

/** Mostra o texto formatado. */
export function Formatado({ texto }: { texto: string }) {
  const blocos: ReactNode[] = []
  let lista: string[] = []
  const fecharLista = () => {
    if (!lista.length) return
    const itens = lista
    blocos.push(<ul key={`l${blocos.length}`} className="list-disc space-y-0.5 pl-5">{itens.map((t, i) => <li key={i}>{trecho(t, `li${i}`)}</li>)}</ul>)
    lista = []
  }
  texto.split('\n').forEach((linha, i) => {
    const item = /^\s*[-•]\s+(.*)$/.exec(linha)
    if (item) {
      lista.push(item[1])
      return
    }
    fecharLista()
    blocos.push(linha.trim() ? <p key={`p${i}`}>{trecho(linha, `p${i}`)}</p> : <div key={`v${i}`} className="h-2" />)
  })
  fecharLista()
  return <div className="space-y-1 text-sm leading-relaxed break-words">{blocos}</div>
}

/** Caixa de texto com botões de formatação (e Ctrl+B / Ctrl+I). */
export function EditorTexto({ valor, onMudar, placeholder, autoFocus, onEnviar }: {
  valor: string
  onMudar: (v: string) => void
  placeholder?: string
  autoFocus?: boolean
  onEnviar?: () => void
}) {
  const ref = useRef<HTMLTextAreaElement>(null)

  function envolver(antes: string, depois: string, exemplo: string) {
    const el = ref.current
    if (!el) return
    const { selectionStart: i, selectionEnd: f } = el
    const sel = valor.slice(i, f) || exemplo
    onMudar(valor.slice(0, i) + antes + sel + depois + valor.slice(f))
    requestAnimationFrame(() => {
      el.focus()
      el.setSelectionRange(i + antes.length, i + antes.length + sel.length)
    })
  }

  function lista() {
    const el = ref.current
    if (!el) return
    const ini = valor.lastIndexOf('\n', el.selectionStart - 1) + 1
    onMudar(valor.slice(0, ini) + '- ' + valor.slice(ini))
    requestAnimationFrame(() => {
      el.focus()
      el.setSelectionRange(el.selectionStart + 2, el.selectionStart + 2)
    })
  }

  const botao = (rotulo: string, icone: ReactNode, acao: () => void) => (
    <button type="button" title={rotulo} aria-label={rotulo} onClick={acao}
      className="grid size-8 place-items-center rounded-lg text-muted hover:bg-surface-muted hover:text-text">
      {icone}
    </button>
  )

  return (
    <div className="rounded-2xl border border-line bg-surface focus-within:border-primary">
      <div className="flex items-center gap-0.5 border-b border-line px-2 py-1">
        {botao('Negrito (Ctrl+B)', <Bold className="size-4" />, () => envolver('**', '**', 'texto'))}
        {botao('Itálico (Ctrl+I)', <Italic className="size-4" />, () => envolver('*', '*', 'texto'))}
        {botao('Lista', <List className="size-4" />, lista)}
        {botao('Link', <Link2 className="size-4" />, () => envolver('[', '](https://)', 'texto do link'))}
      </div>
      <textarea ref={ref} rows={4} maxLength={5000} autoFocus={autoFocus} value={valor} placeholder={placeholder}
        onChange={(e) => onMudar(e.target.value)}
        onKeyDown={(e) => {
          if (!(e.ctrlKey || e.metaKey)) return
          const k = e.key.toLowerCase()
          if (k === 'b') { e.preventDefault(); envolver('**', '**', 'texto') }
          if (k === 'i') { e.preventDefault(); envolver('*', '*', 'texto') }
          if (k === 'enter' && onEnviar) { e.preventDefault(); onEnviar() }
        }}
        className="block w-full resize-y rounded-b-2xl bg-transparent px-3 py-2 text-sm outline-none" />
    </div>
  )
}
