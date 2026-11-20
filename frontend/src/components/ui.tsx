import { useEffect, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from 'react'
import { X } from 'lucide-react'

// ---------------------------------------------------------------- Botão
type Variante = 'primario' | 'secundario' | 'perigo' | 'fantasma'
const estilos: Record<Variante, string> = {
  primario: 'bg-primary text-primary-contrast hover:opacity-90 disabled:bg-primary-soft disabled:text-primary',
  secundario: 'bg-surface-muted text-text hover:bg-line',
  perigo: 'bg-red-600 text-white hover:bg-red-700',
  fantasma: 'text-muted hover:bg-surface-muted hover:text-text',
}

export function Botao({ variante = 'primario', className = '', ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variante?: Variante }) {
  return (
    <button
      type="button"
      {...p}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed ${estilos[variante]} ${className}`}
    />
  )
}

// ---------------------------------------------------------------- Selo
const cores = {
  rosa: 'bg-[#fce7ee] text-[#a63e5f] dark:bg-[#4a2632] dark:text-[#f2a7bd]',
  azul: 'bg-[#e3effa] text-[#1f6aa8] dark:bg-[#1e3446] dark:text-[#8cc3f0]',
  verde: 'bg-[#e1f4e8] text-[#1f7a43] dark:bg-[#1d3a29] dark:text-[#86d6a5]',
  vermelho: 'bg-[#fce8e6] text-[#c0362e] dark:bg-[#4a2220] dark:text-[#f3a29b]',
  ambar: 'bg-[#fcf1dc] text-[#9a6a0c] dark:bg-[#43341a] dark:text-[#f0c86e]',
  roxo: 'bg-[#f1e8fb] text-[#7340a8] dark:bg-[#34264a] dark:text-[#c9a6f0]',
  cinza: 'bg-surface-muted text-muted',
}
export type CorSelo = keyof typeof cores

export function Selo({ cor = 'cinza', children, className = '' }: { cor?: CorSelo; children: ReactNode; className?: string }) {
  return <span className={`inline-flex items-center gap-1 rounded-lg px-2 py-0.5 text-xs font-medium ${cores[cor]} ${className}`}>{children}</span>
}

// ---------------------------------------------------------------- Campos
export function Campo({ rotulo, children, ajuda }: { rotulo: string; children: ReactNode; ajuda?: string }) {
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <span className="font-medium">{rotulo}</span>
      {children}
      {ajuda && <span className="text-xs text-muted">{ajuda}</span>}
    </label>
  )
}

const campoCls = 'rounded-xl border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-primary'
export const Entrada = (p: InputHTMLAttributes<HTMLInputElement>) => <input {...p} className={`${campoCls} ${p.className ?? ''}`} />
export const Seletor = (p: SelectHTMLAttributes<HTMLSelectElement>) => <select {...p} className={`${campoCls} ${p.className ?? ''}`} />

// ---------------------------------------------------------------- Modal
export function Modal({ titulo, aberto, onFechar, children, largura = 'max-w-lg' }: {
  titulo: string
  aberto: boolean
  onFechar: () => void
  children: ReactNode
  largura?: string
}) {
  useEffect(() => {
    if (!aberto) return
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && onFechar()
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [aberto, onFechar])
  if (!aberto) return null
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" onMouseDown={onFechar}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
        className={`max-h-[90vh] w-full overflow-y-auto rounded-3xl bg-surface p-6 shadow-xl ${largura}`}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="mb-5 flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold">{titulo}</h2>
          <button type="button" aria-label="Fechar" onClick={onFechar} className="rounded-lg p-1 text-muted hover:bg-surface-muted">
            <X className="size-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- Cartão de seção
export function Secao({ titulo, icone, children, acao, className = '' }: {
  titulo?: string
  icone?: ReactNode
  children: ReactNode
  acao?: ReactNode
  className?: string
}) {
  return (
    <section className={`rounded-3xl bg-surface p-6 ${className}`}>
      {titulo && (
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            {icone && <span className="grid size-10 place-items-center rounded-xl bg-primary-soft text-primary">{icone}</span>}
            <h2 className="text-lg font-semibold">{titulo}</h2>
          </div>
          {acao}
        </div>
      )}
      {children}
    </section>
  )
}

export function Vazio({ icone, texto }: { icone: ReactNode; texto: string }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-center text-sm text-muted">
      <span className="opacity-60">{icone}</span>
      {texto}
    </div>
  )
}
