import { BrowserRouter, Outlet, Route, Routes } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { Topbar } from './components/Topbar'
import { EmBreve } from './pages/EmBreve'

function Layout() {
  return (
    <div className="flex h-full">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Topbar />
        <div className="px-10 pb-10 pt-2">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

const paginas = [
  { path: '', titulo: 'Dashboard', subtitulo: 'Resumo do dia da clínica', etapa: 'Etapa 3' },
  { path: 'crm', titulo: 'CRM', subtitulo: 'Arraste os leads entre as colunas para atualizar o status do funil', etapa: 'Etapa 3' },
  { path: 'agenda', titulo: 'Agenda', subtitulo: 'Consultas da semana, atualizadas em tempo real', etapa: 'Etapa 3' },
  { path: 'mensagens', titulo: 'Mensagens', subtitulo: 'Confirmações, lembretes e felicitações enviadas', etapa: 'Etapa 3' },
  { path: 'clientes', titulo: 'Leads / Clientes', subtitulo: 'Pacientes e contatos da clínica', etapa: 'Etapa 3' },
  { path: 'configuracoes', titulo: 'Configurações', subtitulo: 'Gerencie o perfil, horários e procedimentos da clínica', etapa: 'Etapa 7' },
]

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          {paginas.map(({ path, ...p }) =>
            path === '' ? (
              <Route key="index" index element={<EmBreve {...p} />} />
            ) : (
              <Route key={path} path={path} element={<EmBreve {...p} />} />
            ),
          )}
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
