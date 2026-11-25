import type { ReactNode } from 'react'
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
import { BarraCelular, SoComputador, TopoCelular } from './components/MenuCelular'
import { useCelular } from './lib/celular'


function Layout() {
  const celular = useCelular()
  if (celular) {
    // Etapa 33: no celular, topo enxuto + abas embaixo (sem a barra lateral nem a gestão)
    return (
      <div className="flex h-full flex-col">
        <main className="flex-1 overflow-y-auto pb-20">
          <TopoCelular />
          <div className="px-4 pt-4">
            <AvisoIaDesligada />
            <AvisoTetoIa />
            <Outlet />
          </div>
        </main>
        <BarraCelular />
      </div>
    )
  }
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
  const celular = useCelular()
  if (clinica.configurada) return <Outlet />
  const papel = usuario.super_admin ? 'super_admin' : usuario.clinicas.find((c) => c.clinic_id === clinica.id)?.papel
  return papel === 'clinic_admin' || papel === 'super_admin'
    ? <SoComputador celular={celular}><PrimeirosPassos /></SoComputador>
    : <AguardandoConfiguracao />
}

/** Etapa 33: gestão (Relatórios, Configurações, Admin geral) só no computador. */
function SoGestao({ children }: { children: ReactNode }) {
  const celular = useCelular()
  return <SoComputador celular={celular}>{children}</SoComputador>
}

export default function App() {
  return (
    <PersistQueryClientProvider client={queryClient} persistOptions={opcoesPersistencia}>
      <ProvedorAvisos>
        <BrowserRouter>
          <Routes>
            <Route path="redefinir-senha" element={<RedefinirSenha />} />
            <Route element={<AreaLogada />}>
              <Route path="admin" element={<SoGestao><AdminLayout /></SoGestao>}>
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
                  <Route path="relatorios" element={<SoGestao><Relatorios /></SoGestao>} />
                  <Route path="configuracoes" element={<SoGestao><Configuracoes /></SoGestao>} />
                </Route>
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </ProvedorAvisos>
    </PersistQueryClientProvider>
  )
}
