import { BrowserRouter, Outlet, Route, Routes } from 'react-router-dom'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { opcoesPersistencia, queryClient } from './lib/cache'
import { ProvedorAvisos } from './components/Aviso'
import { Sidebar } from './components/Sidebar'
import { Topbar } from './components/Topbar'
import { ProvedorAuth } from './lib/auth'
import { AdminLayout } from './pages/admin/AdminLayout'
import { AdminClinicaDetalhe } from './pages/admin/ClinicaDetalhe'
import { AdminClinicas } from './pages/admin/Clinicas'
import { AdminPlataforma } from './pages/admin/Plataforma'
import { AdminUso } from './pages/admin/Uso'
import { ProvedorClinica } from './lib/clinica'
import { Agenda } from './pages/Agenda'
import { Clientes } from './pages/Clientes'
import { Crm } from './pages/Crm'
import { Dashboard } from './pages/Dashboard'
import { Demo } from './pages/Demo'
import { Configuracoes } from './pages/Configuracoes'
import { Mensagens } from './pages/Mensagens'
import { Relatorios } from './pages/Relatorios'
import { AvisoIaDesligada } from './pages/config/IaClinica'
import { AvisoTetoIa } from './pages/config/UsoIa'
import { AguardandoConfiguracao, AvisoPendencias, PrimeirosPassos } from './pages/PrimeirosPassos'
import { useAuth } from './lib/auth'
import { useClinica } from './lib/clinica'
import { RedefinirSenha } from './pages/RedefinirSenha'


function Layout() {
  return (
    <div className="flex h-full">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Topbar />
        <div className="px-10 pb-10 pt-2">
          <AvisoIaDesligada />
          <AvisoTetoIa />
          <AvisoPendencias />
          <Outlet />
        </div>
      </main>
    </div>
  )
}

/** Tudo que exige login: painel da clínica e demonstração. */
function AreaLogada() {
  return (
    <ProvedorAuth>
      <Outlet />
    </ProvedorAuth>
  )
}

/** Painel de UMA clínica (a do usuário; o super admin escolhe pelo "Entrar como"). */
function AreaClinica() {
  return (
    <ProvedorClinica>
      <Portao />
    </ProvedorClinica>
  )
}

/** 10C (D52): clínica sem a configuração inicial concluída → o admin vê só os "Primeiros passos"; os outros esperam. */
function Portao() {
  const { clinica } = useClinica()
  const { usuario } = useAuth()
  if (clinica.configurada) return <Outlet />
  const papel = usuario.super_admin ? 'super_admin' : usuario.clinicas.find((c) => c.clinic_id === clinica.id)?.papel
  return papel === 'clinic_admin' || papel === 'super_admin' ? <PrimeirosPassos /> : <AguardandoConfiguracao />
}

export default function App() {
  return (
    <PersistQueryClientProvider client={queryClient} persistOptions={opcoesPersistencia}>
      <ProvedorAvisos>
        <BrowserRouter>
          <Routes>
            <Route path="redefinir-senha" element={<RedefinirSenha />} />
            <Route element={<AreaLogada />}>
              <Route path="admin" element={<AdminLayout />}>
                <Route index element={<AdminClinicas />} />
                <Route path="clinicas/:id" element={<AdminClinicaDetalhe />} />
                <Route path="uso" element={<AdminUso />} />
                <Route path="plataforma" element={<AdminPlataforma />} />
              </Route>
              <Route element={<AreaClinica />}>
                <Route path="demo" element={<Demo />} />
                <Route element={<Layout />}>
                  <Route index element={<Dashboard />} />
                  <Route path="crm" element={<Crm />} />
                  <Route path="agenda" element={<Agenda />} />
                  <Route path="mensagens" element={<Mensagens />} />
                  <Route path="clientes" element={<Clientes />} />
                  <Route path="relatorios" element={<Relatorios />} />
                  <Route path="configuracoes" element={<Configuracoes />} />
                </Route>
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </ProvedorAvisos>
    </PersistQueryClientProvider>
  )
}
