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

  // Linguagem da equipe da clínica, sem termos técnicos (backend, banco…)
  const bancoOk = saude?.banco.status === 'ok'
  const assistenteLigada = clinica ? clinica.ia_ativa && clinica.uso_ia.nivel !== 'pausada' && !clinica.pausada_whatsapp : saude?.ia.status === 'configurada'
  const cor = erro || (saude && !bancoOk) ? 'bg-red-500' : saude ? (assistenteLigada ? 'bg-green-500' : 'bg-amber-400') : 'bg-amber-400'
  const texto = erro || (saude && !bancoOk)
    ? 'Sem conexão com o sistema. Atualize a página.'
    : saude
      ? clinica
        ? `Tudo funcionando · ${!clinica.ia_ativa ? 'Assistente desligada' : clinica.uso_ia.nivel === 'pausada' ? 'Assistente pausada' : clinica.pausada_whatsapp ? `${clinica.nome_assistente} pausada no WhatsApp` : `${clinica.nome_assistente} atendendo`}`
        : `Tudo funcionando · IA da plataforma ${assistenteLigada ? 'configurada' : 'não configurada'}`
      : 'Conectando…'

  return (
    <div className="flex items-center justify-end gap-3 px-10 pb-6 pt-6 text-sm">
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
