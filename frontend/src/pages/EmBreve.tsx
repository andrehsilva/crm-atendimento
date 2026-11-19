import { Construction } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'

// Página provisória: cada tela será construída na etapa indicada (docs/PLANO.md).
export function EmBreve({ titulo, subtitulo, etapa }: { titulo: string; subtitulo: string; etapa: string }) {
  return (
    <>
      <PageHeader titulo={titulo} subtitulo={subtitulo} />
      <section className="flex flex-col items-center justify-center gap-3 rounded-3xl bg-surface px-6 py-20 text-center text-muted">
        <span className="grid size-12 place-items-center rounded-2xl bg-primary-soft text-primary">
          <Construction className="size-6" />
        </span>
        <p className="text-base">
          Esta tela será construída na <strong className="text-text">{etapa}</strong>.
        </p>
      </section>
    </>
  )
}
