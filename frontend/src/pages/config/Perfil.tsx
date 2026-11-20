import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building, KeyRound } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Secao } from '../../components/ui'
import { api, type PerfilClinica, type Usuario } from '../../lib/api'
import { useClinica } from '../../lib/clinica'
import { telefone } from '../../lib/formato'
import { problemaSenha } from '../TrocarSenha'

export function Perfil({ podeEditar }: { podeEditar: boolean }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const url = `/clinics/${clinica.id}/config/perfil`
  const q = useQuery({ queryKey: ['config', 'perfil', clinica.id], queryFn: () => api.get<PerfilClinica>(url) })
  const [f, setF] = useState({ nome: '', endereco: '', telefone_urgencia: '', sobre: '' })
  useEffect(() => {
    if (q.data) setF({ nome: q.data.nome, endereco: q.data.endereco ?? '', telefone_urgencia: q.data.telefone_urgencia ? telefone(q.data.telefone_urgencia) : '', sobre: q.data.sobre ?? '' })
  }, [q.data])
  const salvar = useMutation({
    mutationFn: () => api.put(url, f),
    onSuccess: () => {
      aviso.ok('Perfil salvo.')
      qc.invalidateQueries({ queryKey: ['config'] })
      qc.invalidateQueries({ queryKey: ['clinica'] })
    },
    onError: aviso.erro,
  })
  if (!q.data) return <p className="text-sm text-muted">Carregando…</p>

  return (
    <div className="grid max-w-5xl gap-6 lg:grid-cols-[1fr_22rem]">
      <Secao titulo="Dados da clínica" icone={<Building className="size-5" />}>
        <form onSubmit={(e) => { e.preventDefault(); salvar.mutate() }} className="grid gap-4 sm:grid-cols-2">
          <Campo rotulo="Nome da clínica" ajuda="Aparece no topo da barra lateral e nas mensagens.">
            <Entrada required disabled={!podeEditar} value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} />
          </Campo>
          <Campo rotulo="Telefone da clínica" ajuda="É a chave da clínica; só o admin da plataforma muda.">
            <Entrada disabled value={telefone(q.data.telefone)} />
          </Campo>
          <Campo rotulo="Endereço" ajuda="Vai na confirmação de consulta.">
            <Entrada disabled={!podeEditar} value={f.endereco} onChange={(e) => setF({ ...f, endereco: e.target.value })} />
          </Campo>
          <Campo rotulo="Telefone de urgência" ajuda="A assistente passa este número em casos urgentes.">
            <Entrada disabled={!podeEditar} value={f.telefone_urgencia} placeholder={telefone(q.data.telefone)}
              onChange={(e) => setF({ ...f, telefone_urgencia: e.target.value })} />
          </Campo>
          <div className="sm:col-span-2">
            <Campo rotulo="Sobre a clínica" ajuda="A assistente usa este texto para tirar dúvidas: convênios, estacionamento, acompanhantes, acessibilidade…">
              <textarea rows={5} maxLength={1500} disabled={!podeEditar} value={f.sobre} onChange={(e) => setF({ ...f, sobre: e.target.value })}
                placeholder="Ex.: Temos estacionamento conveniado na Rua B. Crianças podem acompanhar os pais. Não atendemos convênios."
                className="rounded-xl border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-primary disabled:opacity-60" />
            </Campo>
          </div>
          {podeEditar && (
            <div className="flex justify-end sm:col-span-2">
              <Botao type="submit" disabled={salvar.isPending}>{salvar.isPending ? 'Salvando…' : 'Salvar'}</Botao>
            </div>
          )}
        </form>
      </Secao>
      <TrocarMinhaSenha />
    </div>
  )
}

/** Imagem 06: troca de senha com "Mostrar senhas"; o botão só habilita quando está válido. */
function TrocarMinhaSenha() {
  const aviso = useAviso()
  const qc = useQueryClient()
  const [f, setF] = useState({ atual: '', nova: '', confirmar: '' })
  const [mostrar, setMostrar] = useState(false)
  const problema = problemaSenha(f.nova, f.confirmar)
  const trocar = useMutation({
    mutationFn: () => api.post<Usuario>('/auth/trocar-senha', { atual: f.atual, nova: f.nova }),
    onSuccess: (u) => {
      qc.setQueryData(['me'], u)
      setF({ atual: '', nova: '', confirmar: '' })
      aviso.ok('Senha trocada.')
    },
    onError: aviso.erro,
  })
  const tipo = mostrar ? 'text' : 'password'
  return (
    <Secao titulo="Minha senha" icone={<KeyRound className="size-5" />}>
      <form onSubmit={(e) => { e.preventDefault(); trocar.mutate() }} className="flex flex-col gap-4">
        <Campo rotulo="Senha atual"><Entrada type={tipo} autoComplete="current-password" value={f.atual} onChange={(e) => setF({ ...f, atual: e.target.value })} /></Campo>
        <Campo rotulo="Nova senha" ajuda="Mínimo de 8 caracteres, com letras e números.">
          <Entrada type={tipo} autoComplete="new-password" value={f.nova} onChange={(e) => setF({ ...f, nova: e.target.value })} />
        </Campo>
        <Campo rotulo="Confirmar nova senha"><Entrada type={tipo} autoComplete="new-password" value={f.confirmar} onChange={(e) => setF({ ...f, confirmar: e.target.value })} /></Campo>
        <label className="flex items-center gap-2 text-sm text-muted">
          <input type="checkbox" checked={mostrar} onChange={(e) => setMostrar(e.target.checked)} className="size-4 accent-[var(--primary)]" />
          Mostrar senhas
        </label>
        {f.nova && problema && <p className="text-xs text-muted">{problema}</p>}
        <Botao type="submit" disabled={trocar.isPending || !f.atual || !!problema}>Trocar senha</Botao>
        <p className="text-xs text-muted">Esqueceu a senha? Use "Esqueci minha senha" na tela de entrar.</p>
      </form>
    </Secao>
  )
}
