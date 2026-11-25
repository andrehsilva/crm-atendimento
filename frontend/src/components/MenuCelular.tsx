// Etapa 33: no celular, topo enxuto + barra de abas embaixo. Gestão (Relatórios, Configurações, Admin geral) fica
// só no computador.
import { useState, type ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { CalendarDays, KanbanSquare, LayoutDashboard, LogOut, MessageCircleQuestion, MessageSquare, Monitor, Users } from 'lucide-react'
import { useAuth } from '../lib/auth'
import { useClinica } from '../lib/clinica'
import { PergunteAssistente } from './PergunteAssistente'
import { Sino } from './Sino'

const ABAS = [
  { to: '/', rotulo: 'Início', icone: LayoutDashboard },
  { to: '/crm', rotulo: 'CRM', icone: KanbanSquare },
  { to: '/agenda', rotulo: 'Agenda', icone: CalendarDays },
  { to: '/mensagens', rotulo: 'Mensagens', icone: MessageSquare },
  { to: '/clientes', rotulo: 'Clientes', icone: Users },
]

export function TopoCelular() {
  const { clinica } = useClinica()
  const { sair } = useAuth()
  const [perguntando, setPerguntando] = useState(false)
  const ligada = clinica.ia_ativa && clinica.uso_ia.nivel !== 'pausada' && !clinica.pausada_whatsapp
  return (
    <header className="sticky top-0 z-40 flex items-center gap-3 border-b border-line bg-surface px-4 py-3"
      style={{ paddingTop: 'max(0.75rem, env(safe-area-inset-top))' }}>
      {clinica.logo_versao ? (
        <img src={`/api/clinics/${clinica.id}/logo?v=${clinica.logo_versao}`} alt=""
          className="size-9 shrink-0 rounded-lg border border-line bg-white object-contain p-0.5" />
      ) : (
        <div className="grid size-9 shrink-0 place-items-center rounded-lg bg-primary font-semibold text-primary-contrast">
          {clinica.name.replace(/^Clínica\s+/i, '').charAt(0)}
        </div>
      )}
      <div className="min-w-0 flex-1 leading-tight">
        <div className="truncate font-medium">{clinica.name}</div>
        <div className="flex items-center gap-1.5 text-xs text-muted">
          <span className={`size-2 rounded-full ${ligada ? 'bg-green-500' : 'bg-amber-400'}`} />
          {!clinica.ia_ativa ? 'Assistente desligada' : `${clinica.nome_assistente} ${ligada ? 'atendendo' : 'pausada'}`}
        </div>
      </div>
      {clinica.pergunte_liberado && (
        <button type="button" onClick={() => setPerguntando(true)} aria-label="Perguntar à assistente"
          className="grid size-9 place-items-center rounded-full bg-surface-muted text-muted">
          <MessageCircleQuestion className="size-4" />
        </button>
      )}
      <Sino />
      <button type="button" onClick={sair} aria-label="Sair" className="grid size-9 place-items-center rounded-full text-muted">
        <LogOut className="size-4" />
      </button>
      {perguntando && <PergunteAssistente onFechar={() => setPerguntando(false)} />}
    </header>
  )
}

export function BarraCelular() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-line bg-surface"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
      {ABAS.map(({ to, rotulo, icone: Icone }) => (
        <NavLink key={to} to={to} end={to === '/'}
          className={({ isActive }) => `flex flex-col items-center gap-0.5 py-2 text-[11px] ${isActive ? 'text-primary' : 'text-muted'}`}>
          <Icone className="size-5" />
          {rotulo}
        </NavLink>
      ))}
    </nav>
  )
}

/** Telas de gestão abertas no celular: avisa para usar o computador. */
export function SoComputador({ celular, children }: { celular: boolean; children: ReactNode }) {
  if (!celular) return <>{children}</>
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-16 text-center">
      <div className="grid size-14 place-items-center rounded-2xl bg-primary-soft text-primary"><Monitor className="size-7" /></div>
      <h1 className="text-xl font-semibold">Disponível no computador</h1>
      <p className="max-w-xs text-sm text-muted">Esta parte é de gestão e só abre no computador. No celular ficam o atendimento do dia: CRM, agenda, mensagens e clientes.</p>
      <NavLink to="/" className="mt-2 rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-contrast">Voltar ao início</NavLink>
    </div>
  )
}
