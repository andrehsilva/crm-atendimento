import { useEffect, useState, type ReactNode } from 'react'
import { aplicarMarca, clinicaLembrada } from '../lib/marca'

/** Moldura das telas de acesso (entrar, trocar senha, redefinir senha).
 *  Mostra a última clínica usada neste navegador (nome, cor e logo); sem ela, a marca da plataforma. */
export function CartaoAcesso({ titulo, subtitulo, children }: { titulo: string; subtitulo?: string; children: ReactNode }) {
  const [marca] = useState(clinicaLembrada)
  const [semLogo, setSemLogo] = useState(false)
  useEffect(() => {
    aplicarMarca(marca?.cor ?? null)
    if (marca) document.title = `${marca.nome} · Entrar`
    return () => aplicarMarca(null)
  }, [marca])

  const nome = marca?.nome ?? 'Ísis'
  return (
    <main className="grid min-h-full place-items-center bg-bg px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex items-center justify-center gap-3">
          {marca?.logo_versao && !semLogo ? (
            <img src={`/api/auth/marca/${marca.id}/logo?v=${marca.logo_versao}`} alt="" onError={() => setSemLogo(true)}
              className="size-11 rounded-xl object-contain" />
          ) : (
            <span aria-hidden className="grid size-11 place-items-center rounded-xl bg-primary text-lg font-semibold text-primary-contrast">
              {nome.trim().charAt(0).toUpperCase()}
            </span>
          )}
          <span className="text-2xl font-semibold tracking-tight">{nome}</span>
        </div>
        <section className="rounded-3xl bg-surface p-7 shadow-sm">
          <h1 className="text-xl font-semibold">{titulo}</h1>
          {subtitulo && <p className="mt-1 text-sm text-muted">{subtitulo}</p>}
          <div className="mt-6">{children}</div>
        </section>
        <p className="mt-6 text-center text-xs text-muted">{marca ? 'Painel de atendimento' : 'Atendimento com IA para clínicas e consultórios'}</p>
      </div>
    </main>
  )
}

export function ErroForm({ texto }: { texto?: string | null }) {
  if (!texto) return null
  return <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{texto}</p>
}
