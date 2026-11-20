import { createContext, useContext, useEffect, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ErroApi, EVENTO_SESSAO, type Usuario } from './api'
import { Login } from '../pages/Login'
import { TrocarSenha } from '../pages/TrocarSenha'

type Contexto = { usuario: Usuario; sair: () => Promise<void> }
const Ctx = createContext<Contexto | null>(null)

const PAPEL: Record<string, string> = {
  super_admin: 'Admin da plataforma',
  clinic_admin: 'Administrador',
  reception: 'Recepção',
}
export const nomePapel = (p: string) => PAPEL[p] ?? p

/** Só mostra o painel para quem está logado. Sem login → tela de entrar; senha provisória → troca obrigatória. */
export function ProvedorAuth({ children }: { children: ReactNode }) {
  const qc = useQueryClient()
  const me = useQuery({
    queryKey: ['me'],
    queryFn: () => api.get<Usuario>('/auth/me'),
    retry: false,
    staleTime: Infinity,
  })

  // Qualquer chamada que volte "não autenticado" ou "troque a senha" faz a tela de login reaparecer
  useEffect(() => {
    const recarregar = () => qc.invalidateQueries({ queryKey: ['me'] })
    window.addEventListener(EVENTO_SESSAO, recarregar)
    return () => window.removeEventListener(EVENTO_SESSAO, recarregar)
  }, [qc])

  async function sair() {
    await api.post('/auth/logout').catch(() => undefined)
    // Recarrega na página inicial: limpa tudo da sessão (cache, tempo real, cor) e mostra a tela de entrar.
    // (Antes o cache era limpo sem avisar a tela, que ficava parada no painel.)
    window.location.replace('/')
  }

  if (me.isLoading) return <div className="grid h-full place-items-center text-muted">Carregando…</div>
  if (me.isError) {
    const e = me.error
    if (!(e instanceof ErroApi) || e.codigo === 'ERRO' || e.codigo === 'ENVIO_FALHOU') {
      return <div className="grid h-full place-items-center p-8 text-center text-muted">Não consegui falar com o backend. Ele está rodando? (<code>.\dev.ps1</code>)</div>
    }
    return <Login aviso={e instanceof ErroApi && e.codigo === 'SEM_ACESSO' ? e.message : undefined} />
  }
  if (!me.data) return <Login />
  if (me.data.trocar_senha) return <TrocarSenha obrigatoria />
  return <Ctx.Provider value={{ usuario: me.data, sair }}>{children}</Ctx.Provider>
}

export function useAuth(): Contexto {
  const c = useContext(Ctx)
  if (!c) throw new Error('useAuth fora do ProvedorAuth')
  return c
}
