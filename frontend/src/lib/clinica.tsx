import { createContext, useContext, useEffect, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import { useAuth } from './auth'
import { aplicarMarca, lembrarClinica } from './marca'
import { clinicaGuardada } from './clinicaGuardada'
import { api, EVENTO_SESSAO, type Cadastros, type Clinica } from './api'

/** apresentacao = clínica de apresentação da plataforma (D55), para o botão "Voltar para…" do admin da plataforma */
type ItemLista = { id: string; name: string; apresentacao: boolean }
type Contexto = { clinica: Clinica; cadastros: Cadastros; apresentacao: ItemLista | null }
const Ctx = createContext<Contexto | null>(null)

// Qual "tipo" de aviso do backend atualiza quais dados da tela
const INVALIDA: Record<string, string[]> = {
  agenda: ['agenda', 'dashboard', 'kanban', 'pacientes', 'slots', 'notificacoes'],
  crm: ['kanban', 'pacientes', 'dashboard', 'notificacoes'],
  mensagens: ['mensagens', 'dashboard', 'notificacoes'],
  conversa: ['kanban', 'dashboard', 'chat', 'notificacoes'],
  clinica: ['clinica', 'config'], // 10C: configuração concluída libera o painel na hora para toda a equipe
  whatsapp: ['canais', 'clinica', 'notificacoes'], // D79: conexão ou pausa mudou
}

/** Escuta o backend (SSE) e recarrega só o que mudou. */
function useTempoReal(clinicId: string | undefined) {
  const qc = useQueryClient()
  useEffect(() => {
    if (!clinicId) return
    let es: EventSource | null = null
    let espera: ReturnType<typeof setTimeout> | undefined
    let ativo = true
    const conectar = () => {
      es = new EventSource(`/api/clinics/${clinicId}/events`)
      es.onmessage = (m) => {
        try {
          const ev = JSON.parse(m.data) as { tipo: string }
          for (const chave of INVALIDA[ev.tipo] ?? []) qc.invalidateQueries({ queryKey: [chave] })
        } catch {
          // aviso mal formado: ignora
        }
      }
      es.onerror = () => {
        if (es?.readyState !== EventSource.CLOSED || !ativo) return
        // A conexão foi recusada (ex.: o crachá venceu). /auth/me renova a sessão; depois reconecta.
        espera = setTimeout(() => {
          api.get('/auth/me').then(conectar).catch(() => window.dispatchEvent(new Event(EVENTO_SESSAO)))
        }, 3000)
      }
    }
    conectar()
    return () => {
      ativo = false
      clearTimeout(espera)
      es?.close()
    }
  }, [clinicId, qc])
}

export function ProvedorClinica({ children }: { children: ReactNode }) {
  // A lista já vem filtrada pelo backend: só as clínicas do usuário (super admin: todas)
  const { usuario } = useAuth()
  // A lista vem com a clínica de apresentação primeiro (D55): sem escolha guardada, é por ela que se entra
  const lista = useQuery({ queryKey: ['clinicas'], queryFn: () => api.get<ItemLista[]>('/clinics') })
  const guardada = clinicaGuardada()
  const id = lista.data?.find((c) => c.id === guardada)?.id ?? lista.data?.[0]?.id
  const clinica = useQuery({ queryKey: ['clinica', id], queryFn: () => api.get<Clinica>(`/clinics/${id}`), enabled: !!id })
  const cadastros = useQuery({
    queryKey: ['cadastros', id],
    queryFn: () => api.get<Cadastros>(`/clinics/${id}/cadastros`),
    enabled: !!id,
  })
  useTempoReal(id)
  // Cor da clínica no painel todo; ao sair (ex.: admin geral) volta para a cor da Ísis
  const cor = clinica.data?.cor ?? null
  useEffect(() => {
    aplicarMarca(cor)
    return () => aplicarMarca(null)
  }, [cor])
  // A tela de entrar passa a mostrar esta clínica (nome, cor e logo) neste navegador
  const dados = clinica.data
  useEffect(() => {
    if (!dados) return
    lembrarClinica({ id: dados.id, nome: dados.name, cor: dados.cor, logo_versao: dados.logo_versao })
  }, [dados])

  if (lista.isError || clinica.isError) {
    return (
      <Centro>
        Não consegui carregar a clínica. Tente atualizar a página.
      </Centro>
    )
  }
  if (lista.data && lista.data.length === 0) {
    if (usuario.super_admin) return <Navigate to="/admin" replace />
    return (
      <Centro>
        Seu usuário ainda não está ligado a nenhuma clínica. Fale com o administrador.
      </Centro>
    )
  }
  if (!clinica.data || !cadastros.data) return <Centro>Carregando…</Centro>
  const apresentacao = lista.data?.find((c) => c.apresentacao) ?? null
  return <Ctx.Provider value={{ clinica: clinica.data, cadastros: cadastros.data, apresentacao }}>{children}</Ctx.Provider>
}

function Centro({ children }: { children: ReactNode }) {
  return <div className="grid h-full place-items-center p-8 text-center text-muted">{children}</div>
}

/** Igual ao useClinica, mas devolve null fora de uma clínica (ex.: Admin geral, que usa o mesmo topo). */
export function useClinicaOpcional(): Contexto | null {
  return useContext(Ctx)
}

export function useClinica(): Contexto {
  const c = useContext(Ctx)
  if (!c) throw new Error('useClinica fora do ProvedorClinica')
  return c
}
