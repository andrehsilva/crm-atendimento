import { createContext, useContext, useEffect, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Cadastros, type Clinica } from './api'

type Contexto = { clinica: Clinica; cadastros: Cadastros }
const Ctx = createContext<Contexto | null>(null)

// Qual "tipo" de aviso do backend atualiza quais dados da tela
const INVALIDA: Record<string, string[]> = {
  agenda: ['agenda', 'dashboard', 'kanban', 'pacientes', 'slots'],
  crm: ['kanban', 'pacientes', 'dashboard'],
  mensagens: ['mensagens', 'dashboard'],
  conversa: ['kanban', 'dashboard', 'chat'],
}

/** Escuta o backend (SSE) e recarrega só o que mudou. */
function useTempoReal(clinicId: string | undefined) {
  const qc = useQueryClient()
  useEffect(() => {
    if (!clinicId) return
    const es = new EventSource(`/api/clinics/${clinicId}/events`)
    es.onmessage = (m) => {
      try {
        const ev = JSON.parse(m.data) as { tipo: string }
        for (const chave of INVALIDA[ev.tipo] ?? []) qc.invalidateQueries({ queryKey: [chave] })
      } catch {
        // aviso mal formado: ignora
      }
    }
    return () => es.close()
  }, [clinicId, qc])
}

export function ProvedorClinica({ children }: { children: ReactNode }) {
  // Etapa 3: sem login ainda — usamos a primeira clínica (a demo). Login/escolha na Etapa 7.
  const lista = useQuery({ queryKey: ['clinicas'], queryFn: () => api.get<{ id: string }[]>('/clinics') })
  const id = lista.data?.[0]?.id
  const clinica = useQuery({ queryKey: ['clinica', id], queryFn: () => api.get<Clinica>(`/clinics/${id}`), enabled: !!id })
  const cadastros = useQuery({
    queryKey: ['cadastros', id],
    queryFn: () => api.get<Cadastros>(`/clinics/${id}/cadastros`),
    enabled: !!id,
  })
  useTempoReal(id)

  if (lista.isError || clinica.isError) {
    return (
      <Centro>
        Não consegui falar com o backend. Ele está rodando? (<code>.\dev.ps1</code>)
      </Centro>
    )
  }
  if (lista.data && lista.data.length === 0) {
    return (
      <Centro>
        Nenhuma clínica cadastrada. Rode <code>uv run python scripts/seed_demo.py</code> na pasta backend.
      </Centro>
    )
  }
  if (!clinica.data || !cadastros.data) return <Centro>Carregando…</Centro>
  return <Ctx.Provider value={{ clinica: clinica.data, cadastros: cadastros.data }}>{children}</Ctx.Provider>
}

function Centro({ children }: { children: ReactNode }) {
  return <div className="grid h-full place-items-center p-8 text-center text-muted">{children}</div>
}

export function useClinica(): Contexto {
  const c = useContext(Ctx)
  if (!c) throw new Error('useClinica fora do ProvedorClinica')
  return c
}
