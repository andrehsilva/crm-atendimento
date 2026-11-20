import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { UserPlus } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Secao, Seletor } from '../../components/ui'
import { api, type UsuarioClinica } from '../../lib/api'
import { nomePapel, useAuth } from '../../lib/auth'
import { useClinica } from '../../lib/clinica'
import { SenhaProvisoria } from '../admin/SenhaProvisoria'

/** Equipe da clínica: o administrador cria acessos com senha provisória (D35), muda papel e desativa. */
export function Usuarios() {
  const { clinica } = useClinica()
  const { usuario } = useAuth()
  const aviso = useAviso()
  const qc = useQueryClient()
  const base = `/clinics/${clinica.id}/config/usuarios`
  const q = useQuery({ queryKey: ['config', 'usuarios', clinica.id], queryFn: () => api.get<UsuarioClinica[]>(base) })
  const [f, setF] = useState({ email: '', nome: '', papel: 'reception' })
  const [criado, setCriado] = useState<{ email: string; senha: string | null } | null>(null)
  const criar = useMutation({
    mutationFn: () => api.post<{ email: string; senha_provisoria: string | null }>(base, { ...f, nome: f.nome || null }),
    onSuccess: (r) => { setCriado({ email: r.email, senha: r.senha_provisoria }); setF({ email: '', nome: '', papel: 'reception' }); qc.invalidateQueries({ queryKey: ['config', 'usuarios'] }) },
    onError: aviso.erro,
  })
  const editar = useMutation({
    mutationFn: ({ id, dados }: { id: string; dados: Partial<{ ativo: boolean; papel: string }> }) => api.patch(`${base}/${id}`, dados),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['config', 'usuarios'] }),
    onError: aviso.erro,
  })

  return (
    <div className="grid max-w-5xl gap-6 lg:grid-cols-[1fr_20rem]">
      <Secao titulo="Equipe">
        <ul className="flex flex-col divide-y divide-line">
          {(q.data ?? []).map((u) => {
            const eu = u.id === usuario.id
            return (
              <li key={u.id} className={`flex flex-wrap items-center justify-between gap-3 py-3 ${u.ativo ? '' : 'opacity-60'}`}>
                <div className="min-w-0">
                  <div className="truncate font-medium">{u.nome || u.email}{eu && <span className="ml-2 text-xs text-muted">(você)</span>}</div>
                  <div className="truncate text-xs text-muted">{u.email}{u.senha_provisoria ? ' · ainda não criou a própria senha' : ''}</div>
                </div>
                <div className="flex items-center gap-2">
                  <Seletor value={u.papel} disabled={eu} aria-label="Papel" onChange={(e) => editar.mutate({ id: u.id, dados: { papel: e.target.value } })}>
                    <option value="clinic_admin">{nomePapel('clinic_admin')}</option>
                    <option value="reception">{nomePapel('reception')}</option>
                  </Seletor>
                  {!eu && (
                    <Botao variante={u.ativo ? 'fantasma' : 'secundario'} onClick={() => editar.mutate({ id: u.id, dados: { ativo: !u.ativo } })}>
                      {u.ativo ? 'Desativar' : 'Reativar'}
                    </Botao>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      </Secao>
      <Secao titulo="Novo acesso" icone={<UserPlus className="size-5" />}>
        <form onSubmit={(e) => { e.preventDefault(); criar.mutate() }} className="flex flex-col gap-4">
          <Campo rotulo="Nome"><Entrada value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} /></Campo>
          <Campo rotulo="E-mail"><Entrada required type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Campo>
          <Campo rotulo="Papel">
            <Seletor value={f.papel} onChange={(e) => setF({ ...f, papel: e.target.value })}>
              <option value="reception">Recepção (agenda, CRM, conversas)</option>
              <option value="clinic_admin">Administrador (também configura a clínica)</option>
            </Seletor>
          </Campo>
          <Botao type="submit" disabled={criar.isPending || !f.email}>{criar.isPending ? 'Criando…' : 'Criar com senha provisória'}</Botao>
        </form>
      </Secao>
      {criado && <SenhaProvisoria email={criado.email} senha={criado.senha} onFechar={() => setCriado(null)} />}
    </div>
  )
}
