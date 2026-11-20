import { Link, NavLink, Navigate, Outlet } from 'react-router-dom'
import { Activity, ArrowLeft, Building2, LogOut, SlidersHorizontal } from 'lucide-react'
import { Topbar } from '../../components/Topbar'
import { useAuth } from '../../lib/auth'

const itens = [
  { to: '/admin', rotulo: 'Clínicas', icone: Building2, fim: true },
  { to: '/admin/uso', rotulo: 'Uso', icone: Activity, fim: false },
  { to: '/admin/plataforma', rotulo: 'Configurações da plataforma', icone: SlidersHorizontal, fim: false },
]

/** Área do admin geral (D30): mesmo visual do painel, menu próprio. Só para o super admin. */
export function AdminLayout() {
  const { usuario, sair } = useAuth()
  if (!usuario.super_admin) return <Navigate to="/" replace />

  return (
    <div className="flex h-full">
      <aside className="flex h-full w-72 shrink-0 flex-col border-r border-line bg-surface">
        <div className="flex items-center gap-3 border-b border-line px-5 py-5">
          <div className="grid size-11 place-items-center rounded-xl bg-text text-lg font-semibold text-surface">Í</div>
          <div className="leading-tight">
            <div className="text-lg font-medium">Ísis</div>
            <div className="text-xs text-muted">Admin da plataforma</div>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {itens.map(({ to, rotulo, icone: Icone, fim }) => (
            <NavLink key={to} to={to} end={fim}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-4 py-3 text-[15px] transition-colors ${
                  isActive ? 'bg-primary-soft text-primary' : 'text-muted hover:bg-surface-muted hover:text-text'
                }`}>
              <Icone className="size-5 shrink-0" />
              {rotulo}
            </NavLink>
          ))}
        </nav>
        <div className="px-3 pb-3">
          <Link to="/" className="flex items-center gap-3 rounded-xl border border-dashed border-line px-4 py-3 text-sm text-muted hover:border-primary hover:text-primary">
            <ArrowLeft className="size-5" /> Ir para o painel da clínica
          </Link>
        </div>
        <div className="flex items-center gap-3 border-t border-line px-5 py-4">
          <div className="min-w-0 flex-1 leading-tight">
            <div className="truncate text-sm font-medium">{usuario.nome || usuario.email}</div>
            <div className="text-xs text-muted">Admin da plataforma</div>
          </div>
          <button type="button" onClick={sair} title="Sair" aria-label="Sair" className="rounded-lg p-2 text-muted hover:bg-surface-muted hover:text-text">
            <LogOut className="size-4" />
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <Topbar />
        <div className="px-10 pb-10 pt-2">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
