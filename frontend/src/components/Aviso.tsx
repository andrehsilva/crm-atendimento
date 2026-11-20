import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import { CheckCircle2, AlertTriangle } from 'lucide-react'
import { ErroApi } from '../lib/api'

type Tipo = 'ok' | 'erro'
type Item = { id: number; tipo: Tipo; texto: string }
type Ctx = { ok: (t: string) => void; erro: (e: unknown) => void }

const Contexto = createContext<Ctx | null>(null)

/** Avisos rápidos no canto da tela ("Consulta marcada", "Horário ocupado"...). */
export function ProvedorAvisos({ children }: { children: ReactNode }) {
  const [itens, setItens] = useState<Item[]>([])

  const add = useCallback((tipo: Tipo, texto: string) => {
    const id = Date.now() + Math.random()
    setItens((x) => [...x, { id, tipo, texto }])
    setTimeout(() => setItens((x) => x.filter((i) => i.id !== id)), 5000)
  }, [])

  const valor: Ctx = {
    ok: (t) => add('ok', t),
    erro: (e) => add('erro', e instanceof ErroApi || e instanceof Error ? e.message : String(e)),
  }

  return (
    <Contexto.Provider value={valor}>
      {children}
      <div className="pointer-events-none fixed bottom-6 right-6 z-[60] flex flex-col gap-2" aria-live="polite">
        {itens.map((i) => (
          <div
            key={i.id}
            className={`flex max-w-sm items-start gap-2 rounded-2xl px-4 py-3 text-sm shadow-lg ${
              i.tipo === 'ok' ? 'bg-surface text-text' : 'bg-red-600 text-white'
            }`}
          >
            {i.tipo === 'ok' ? <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-green-600" /> : <AlertTriangle className="mt-0.5 size-4 shrink-0" />}
            {i.texto}
          </div>
        ))}
      </div>
    </Contexto.Provider>
  )
}

export function useAviso(): Ctx {
  const c = useContext(Contexto)
  if (!c) throw new Error('useAviso fora do ProvedorAvisos')
  return c
}
