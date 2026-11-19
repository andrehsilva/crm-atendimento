import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'
import { aplicarTema, temaAtual, type Tema } from '../lib/tema'

type Saude = { status: string; banco: string; ia: string }

export function Topbar() {
  const [tema, setTema] = useState<Tema>(temaAtual)
  const [saude, setSaude] = useState<Saude | null>(null)
  const [erro, setErro] = useState(false)

  useEffect(() => {
    fetch('/health')
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status))
        return r.json()
      })
      .then(setSaude)
      .catch(() => setErro(true))
  }, [])

  function alternar() {
    const novo: Tema = tema === 'claro' ? 'escuro' : 'claro'
    aplicarTema(novo)
    setTema(novo)
  }

  const cor = erro ? 'bg-red-500' : saude ? 'bg-green-500' : 'bg-amber-400'
  const texto = erro
    ? 'Backend fora do ar'
    : saude
      ? `Backend ok · banco: ${saude.banco} · IA: ${saude.ia}`
      : 'Verificando backend…'

  return (
    <div className="flex items-center justify-end gap-3 px-10 pt-6 text-sm">
      <span className="flex items-center gap-2 rounded-full bg-surface px-3 py-1.5 text-muted">
        <span className={`size-2 rounded-full ${cor}`} />
        {texto}
      </span>
      <button
        type="button"
        onClick={alternar}
        aria-label="Trocar tema"
        className="grid size-9 place-items-center rounded-full bg-surface text-muted hover:text-text"
      >
        {tema === 'claro' ? <Moon className="size-4" /> : <Sun className="size-4" />}
      </button>
    </div>
  )
}
