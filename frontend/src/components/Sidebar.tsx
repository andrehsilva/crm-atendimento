import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { nomePapel, useAuth } from '../lib/auth'
import { useClinica } from '../lib/clinica'
import {
  CalendarDays,
  ChevronLeft,
  KanbanSquare,
  LogOut,
  LayoutDashboard,
  MessageSquare,
  MonitorPlay,
  Settings,
  Users,
} from 'lucide-react'

// Menu definido na decisão D21 (docs/DECISOES.md)
const itens = [
  { to: '/', rotulo: 'Dashboard', icone: LayoutDashboard },
  { to: '/crm', rotulo: 'CRM', icone: KanbanSquare },
  { to: '/agenda', rotulo: 'Agenda', icone: CalendarDays },
  { to: '/mensagens', rotulo: 'Mensagens', icone: MessageSquare },
  { to: '/clientes', rotulo: 'Leads / Clientes', icone: Users },
  { to: '/configuracoes', rotulo: 'Configurações', icone: Settings },
]

export function Sidebar() {
  const [recolhida, setRecolhida] = useState(false)
  const { clinica } = useClinica()
  const { usuario, sair } = useAuth()
  const papel = usuario.super_admin ? 'super_admin' : (usuario.clinicas.find((c) => c.clinic_id === clinica.id)?.papel ?? '')
  const iniciais = (usuario.nome || usuario.email).split(/[\s@.]+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join('')

  return (
    <aside
      className={`relative flex h-full shrink-0 flex-col border-r border-line bg-surface transition-[width] ${
        recolhida ? 'w-20' : 'w-72'
      }`}
    >
      <div className="flex items-center gap-3 border-b border-line px-5 py-5">
        <div className="grid size-11 shrink-0 place-items-center rounded-xl bg-primary text-lg font-semibold text-primary-contrast">
          {clinica.name.replace(/^Clínica\s+/i, '').charAt(0)}
        </div>
        {!recolhida && <span className="truncate text-lg font-medium" title={clinica.name}>{clinica.name}</span>}
      </div>

      <button
        type="button"
        onClick={() => setRecolhida(!recolhida)}
        aria-label={recolhida ? 'Expandir menu' : 'Recolher menu'}
        className="absolute -right-3.5 top-7 grid size-7 place-items-center rounded-full border border-line bg-surface text-muted hover:text-text"
      >
        <ChevronLeft className={`size-4 transition-transform ${recolhida ? 'rotate-180' : ''}`} />
      </button>

      <nav className="flex flex-1 flex-col gap-1 p-3">
        {itens.map(({ to, rotulo, icone: Icone }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            title={rotulo}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-4 py-3 text-[15px] transition-colors ${
                isActive ? 'bg-primary-soft text-primary' : 'text-muted hover:bg-surface-muted hover:text-text'
              }`
            }
          >
            <Icone className="size-5 shrink-0" />
            {!recolhida && rotulo}
          </NavLink>
        ))}
      </nav>

      <div className="px-3 pb-3">
        <Link
          to="/demo"
          title="Demonstração: chat + agenda + mensagens"
          className="flex items-center gap-3 rounded-xl border border-dashed border-line px-4 py-3 text-sm text-muted hover:border-primary hover:text-primary"
        >
          <MonitorPlay className="size-5 shrink-0" />
          {!recolhida && 'Abrir demonstração'}
        </Link>
      </div>

      <div className="flex items-center gap-3 border-t border-line px-5 py-4">
        <div className="grid size-10 shrink-0 place-items-center rounded-full bg-surface-muted text-sm font-medium uppercase">
          {iniciais}
        </div>
        {!recolhida && (
          <div className="min-w-0 flex-1 leading-tight">
            <div className="truncate text-sm font-medium" title={usuario.email}>{usuario.nome || usuario.email}</div>
            <div className="text-xs text-muted">{nomePapel(papel)}</div>
          </div>
        )}
        <button type="button" onClick={sair} title="Sair" aria-label="Sair"
          className="rounded-lg p-2 text-muted hover:bg-surface-muted hover:text-text">
          <LogOut className="size-4" />
        </button>
      </div>
    </aside>
  )
}
