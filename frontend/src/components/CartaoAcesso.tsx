import { type ReactNode } from 'react'

/** Moldura das telas de acesso (entrar, trocar senha, redefinir senha). */
export function CartaoAcesso({ titulo, subtitulo, children }: { titulo: string; subtitulo?: string; children: ReactNode }) {
  return (
    <main className="grid min-h-full place-items-center bg-bg px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex items-center justify-center gap-3">
          <span className="grid size-11 place-items-center rounded-xl bg-primary text-lg font-semibold text-primary-contrast">Í</span>
          <span className="text-2xl font-semibold tracking-tight">Ísis</span>
        </div>
        <section className="rounded-3xl bg-surface p-7 shadow-sm">
          <h1 className="text-xl font-semibold">{titulo}</h1>
          {subtitulo && <p className="mt-1 text-sm text-muted">{subtitulo}</p>}
          <div className="mt-6">{children}</div>
        </section>
        <p className="mt-6 text-center text-xs text-muted">Atendimento com IA para clínicas odontológicas</p>
      </div>
    </main>
  )
}

export function ErroForm({ texto }: { texto?: string | null }) {
  if (!texto) return null
  return <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{texto}</p>
}
