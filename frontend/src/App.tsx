import { BrowserRouter, Outlet, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ProvedorAvisos } from './components/Aviso'
import { Sidebar } from './components/Sidebar'
import { Topbar } from './components/Topbar'
import { ProvedorClinica } from './lib/clinica'
import { Agenda } from './pages/Agenda'
import { Clientes } from './pages/Clientes'
import { Crm } from './pages/Crm'
import { Dashboard } from './pages/Dashboard'
import { Demo } from './pages/Demo'
import { EmBreve } from './pages/EmBreve'
import { Mensagens } from './pages/Mensagens'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false, retry: 1 } },
})

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

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ProvedorAvisos>
        <ProvedorClinica>
          <BrowserRouter>
            <Routes>
              <Route path="demo" element={<Demo />} />
              <Route element={<Layout />}>
                <Route index element={<Dashboard />} />
                <Route path="crm" element={<Crm />} />
                <Route path="agenda" element={<Agenda />} />
                <Route path="mensagens" element={<Mensagens />} />
                <Route path="clientes" element={<Clientes />} />
                <Route
                  path="configuracoes"
                  element={<EmBreve titulo="Configurações" subtitulo="Gerencie o perfil, horários e procedimentos da clínica" etapa="Etapa 7" />}
                />
              </Route>
            </Routes>
          </BrowserRouter>
        </ProvedorClinica>
      </ProvedorAvisos>
    </QueryClientProvider>
  )
}
