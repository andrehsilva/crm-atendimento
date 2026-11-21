import { useState } from 'react'
import { Moon, Sun } from 'lucide-react'
import { useClinicaOpcional } from '../lib/clinica'
import { useSaude } from '../lib/saude'
import { aplicarTema, temaAtual, type Tema } from '../lib/tema'

export function Topbar() {
  const [tema, setTema] = useState<Tema>(temaAtual)
  const clinica = useClinicaOpcional()?.clinica ?? null
  const q = useSaude()
  const saude = q.data ?? null
  const erro = q.isError

  function alternar() {
    const novo: Tema = tema === 'claro' ? 'escuro' : 'claro'
    aplicarTema(novo)
    setTema(novo)
  }

  const cor = erro ? 'bg-red-500' : saude ? 'bg-green-500' : 'bg-amber-400'
  const texto = erro
    ? 'Backend fora do ar'
    : saude
      ? `Backend ok · banco: ${saude.banco.status} · ${clinica ? `IA da clínica: ${clinica.ia_ativa ? 'ligada' : 'desligada'}` : `IA da plataforma: ${saude.ia.status}`}`
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
