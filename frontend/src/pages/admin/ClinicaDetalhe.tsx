import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, KeyRound, LogIn, PauseCircle, PlayCircle, UserPlus } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Modal, Secao, Seletor, Selo } from '../../components/ui'
import { api, type AdminClinica, type IaClinica, type UsuarioClinica } from '../../lib/api'
import { nomePapel } from '../../lib/auth'
import { escolherClinica } from '../../lib/clinicaGuardada'
import { telefone } from '../../lib/formato'
import { FUSOS } from './Clinicas'
import { SenhaProvisoria } from './SenhaProvisoria'
import { WhatsAppClinica } from './WhatsAppClinica'

const ABAS = ['Dados', 'WhatsApp', 'IA', 'Usuários'] as const

export function AdminClinicaDetalhe() {
  const { id = '' } = useParams()
  const aviso = useAviso()
  const qc = useQueryClient()
  const navegar = useNavigate()
  const [aba, setAba] = useState<(typeof ABAS)[number]>('Dados')
  const [confirmar, setConfirmar] = useState(false)
  const q = useQuery({ queryKey: ['admin', 'clinica', id], queryFn: () => api.get<AdminClinica>(`/admin/clinicas/${id}`) })

  const entrar = useMutation({
    mutationFn: () => api.post(`/admin/clinicas/${id}/entrar`),
    onSuccess: () => {
      escolherClinica(id)
      qc.removeQueries({ queryKey: ['clinica'] })
      qc.invalidateQueries({ queryKey: ['clinicas'] })
      navegar('/')
    },
    onError: aviso.erro,
  })
  const status = useMutation({
    mutationFn: (novo: 'ativa' | 'suspensa') => api.patch(`/admin/clinicas/${id}`, { status: novo }),
    onSuccess: (_, novo) => {
      aviso.ok(novo === 'suspensa' ? 'Clínica suspensa.' : 'Clínica reativada.')
      setConfirmar(false)
      qc.invalidateQueries({ queryKey: ['admin'] })
    },
    onError: aviso.erro,
  })

  if (q.isLoading || !q.data) return <p className="text-sm text-muted">Carregando…</p>
  const c = q.data
  const suspensa = c.status === 'suspensa'

  return (
    <>
      <Link to="/admin" className="mb-4 inline-flex items-center gap-1 text-sm text-muted hover:text-text"><ArrowLeft className="size-4" /> Clínicas</Link>
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">{c.name}</h1>
            {suspensa ? <Selo cor="vermelho">suspensa</Selo> : <Selo cor="verde">ativa</Selo>}
          </div>
          <p className="mt-1 text-muted">{telefone(c.phone)} · /{c.slug} · assistente {c.nome_assistente}</p>
        </div>
        <div className="flex gap-2">
          <Botao variante="secundario" onClick={() => entrar.mutate()} disabled={suspensa || entrar.isPending}
            title={suspensa ? 'Reative a clínica para entrar' : 'Abre o painel desta clínica (fica registrado)'}>
            <LogIn className="size-4" /> Entrar como
          </Botao>
          {suspensa ? (
            <Botao onClick={() => status.mutate('ativa')} disabled={status.isPending}><PlayCircle className="size-4" /> Reativar</Botao>
          ) : (
            <Botao variante="perigo" onClick={() => setConfirmar(true)}><PauseCircle className="size-4" /> Suspender</Botao>
          )}
        </div>
      </header>

      <div role="tablist" className="mb-6 flex gap-2">
        {ABAS.map((a) => (
          <button key={a} type="button" role="tab" aria-selected={aba === a} onClick={() => setAba(a)}
            className={`rounded-full px-4 py-1.5 text-sm transition ${aba === a ? 'bg-primary text-primary-contrast' : 'bg-surface text-muted hover:text-text'}`}>
            {a}
          </button>
        ))}
      </div>
      {aba === 'Dados' && <Dados c={c} />}
      {aba === 'WhatsApp' && q.data && <WhatsAppClinica id={id} slug={q.data.slug} />}
      {aba === 'IA' && <Ia id={id} />}
      {aba === 'Usuários' && <Usuarios id={id} />}

      <Modal titulo="Suspender clínica?" aberto={confirmar} onFechar={() => setConfirmar(false)}>
        <p className="text-sm">
          Enquanto estiver suspensa, a equipe de <strong>{c.name}</strong> não entra no painel, a assistente para de responder
          e nenhuma mensagem automática é enviada. Os dados ficam guardados e dá para reativar depois.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <Botao variante="fantasma" onClick={() => setConfirmar(false)}>Cancelar</Botao>
          <Botao variante="perigo" onClick={() => status.mutate('suspensa')} disabled={status.isPending}>Suspender</Botao>
        </div>
      </Modal>
    </>
  )
}

function Dados({ c }: { c: AdminClinica }) {
  const aviso = useAviso()
  const qc = useQueryClient()
  const [f, setF] = useState({ nome: c.name, telefone: telefone(c.phone), endereco: c.address ?? '', fuso: c.timezone, nome_assistente: c.nome_assistente })
  useEffect(() => setF({ nome: c.name, telefone: telefone(c.phone), endereco: c.address ?? '', fuso: c.timezone, nome_assistente: c.nome_assistente }), [c])
  const salvar = useMutation({
    mutationFn: () => api.patch<AdminClinica>(`/admin/clinicas/${c.id}`, f),
    onSuccess: (atualizada) => {
      aviso.ok(atualizada.phone === c.phone ? 'Dados salvos.' : 'Dados salvos. A identificação da clínica foi atualizada; o WhatsApp conectado permanece o mesmo.')
      qc.setQueryData(['admin', 'clinica', c.id], atualizada)
      qc.invalidateQueries({ queryKey: ['admin'] })
      qc.invalidateQueries({ queryKey: ['clinicas'] })
      qc.invalidateQueries({ queryKey: ['clinica'] })
    },
    onError: aviso.erro,
  })
  const apresentacao = useMutation({
    mutationFn: (ligar: boolean) => api.patch(`/admin/clinicas/${c.id}`, { apresentacao: ligar }),
    onSuccess: (_, ligar) => {
      aviso.ok(ligar ? `${c.name} agora é a clínica de apresentação.` : 'Clínica de apresentação desmarcada.')
      qc.invalidateQueries({ queryKey: ['admin'] })
      qc.invalidateQueries({ queryKey: ['clinicas'] })
    },
    onError: aviso.erro,
  })
  return (
    <div className="flex max-w-3xl flex-col gap-6">
    <Secao titulo="Clínica de apresentação">
      <label className="flex items-start gap-3 text-sm">
        <input type="checkbox" className="mt-0.5 size-4 accent-[var(--primary)]" checked={c.apresentacao} disabled={apresentacao.isPending}
          onChange={(e) => apresentacao.mutate(e.target.checked)} />
        <span>
          Esta é a clínica de apresentação da plataforma
          <span className="block text-xs text-muted">
            Você entra sempre por ela e só nela aparece o botão "Admin geral". Nas outras clínicas aparece "Voltar para {c.name}".
            Só uma clínica pode ter esta marcação.
          </span>
        </span>
      </label>
    </Secao>
    <Secao>
      <form onSubmit={(e) => { e.preventDefault(); salvar.mutate() }} className="grid gap-4 sm:grid-cols-2">
        <Campo rotulo="Nome da clínica"><Entrada required value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} /></Campo>
        <Campo rotulo="Telefone principal da clínica" ajuda="Identificação e contato principal. Alterá-lo não troca o número conectado no WhatsApp.">
          <Entrada required value={f.telefone} onChange={(e) => setF({ ...f, telefone: e.target.value })} inputMode="tel" />
        </Campo>
        <Campo rotulo="Endereço"><Entrada value={f.endereco} onChange={(e) => setF({ ...f, endereco: e.target.value })} /></Campo>
        <Campo rotulo="Fuso horário">
          <Seletor value={f.fuso} onChange={(e) => setF({ ...f, fuso: e.target.value })}>
            {FUSOS.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
          </Seletor>
        </Campo>
        <Campo rotulo="Nome da assistente"><Entrada required value={f.nome_assistente} onChange={(e) => setF({ ...f, nome_assistente: e.target.value })} /></Campo>
        <div className="flex items-end justify-end sm:col-span-2">
          <Botao type="submit" disabled={salvar.isPending}>{salvar.isPending ? 'Salvando…' : 'Salvar'}</Botao>
        </div>
      </form>
    </Secao>
    </div>
  )
}

function Usuarios({ id }: { id: string }) {
  const aviso = useAviso()
  const qc = useQueryClient()
  const [f, setF] = useState({ email: '', nome: '', papel: 'reception' })
  const [criado, setCriado] = useState<{ email: string; senha: string | null } | null>(null)
  const q = useQuery({ queryKey: ['admin', 'usuarios', id], queryFn: () => api.get<UsuarioClinica[]>(`/admin/clinicas/${id}/usuarios`) })
  const criar = useMutation({
    mutationFn: () => api.post<{ email: string; senha_provisoria: string | null }>(`/admin/clinicas/${id}/usuarios`, { ...f, nome: f.nome || null }),
    onSuccess: (r) => {
      setCriado({ email: r.email, senha: r.senha_provisoria })
      setF({ email: '', nome: '', papel: 'reception' })
      qc.invalidateQueries({ queryKey: ['admin'] })
      aviso.ok('Usuário criado.')
    },
    onError: aviso.erro,
  })
  const editar = useMutation({
    mutationFn: ({ uid, dados }: { uid: string; dados: Partial<{ ativo: boolean; papel: string }> }) => api.patch(`/admin/clinicas/${id}/usuarios/${uid}`, dados),
    onSuccess: (_, v) => { qc.invalidateQueries({ queryKey: ['admin', 'usuarios', id] }); aviso.ok(v.dados.papel ? 'Papel atualizado.' : v.dados.ativo === false ? 'Acesso desativado.' : 'Acesso reativado.') },
    onError: aviso.erro,
  })

  return (
    <div className="grid max-w-5xl gap-6 lg:grid-cols-[1fr_20rem]">
      <Secao titulo="Usuários">
        {!q.data?.length ? (
          <p className="text-sm text-muted">Nenhum usuário nesta clínica.</p>
        ) : (
          <ul className="flex flex-col divide-y divide-line">
            {q.data.map((u) => (
              <li key={u.id} className={`flex flex-wrap items-center justify-between gap-3 py-3 ${u.ativo ? '' : 'opacity-60'}`}>
                <div className="min-w-0">
                  <div className="truncate font-medium">{u.nome || u.email}</div>
                  <div className="truncate text-xs text-muted">{u.email}{u.senha_provisoria ? ' · ainda com senha provisória' : ''}</div>
                </div>
                <div className="flex items-center gap-2">
                  <Seletor value={u.papel} onChange={(e) => editar.mutate({ uid: u.id, dados: { papel: e.target.value } })} aria-label="Papel">
                    <option value="clinic_admin">{nomePapel('clinic_admin')}</option>
                    <option value="reception">{nomePapel('reception')}</option>
                  </Seletor>
                  <Botao variante={u.ativo ? 'fantasma' : 'secundario'} onClick={() => editar.mutate({ uid: u.id, dados: { ativo: !u.ativo } })}>
                    {u.ativo ? 'Desativar' : 'Reativar'}
                  </Botao>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Secao>
      <Secao titulo="Novo usuário" icone={<UserPlus className="size-5" />}>
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

/** Etapa 10A (D46): o admin geral vê a situação e liga/desliga a chave da plataforma (teste grátis, demonstração). */
function Ia({ id }: { id: string }) {
  const aviso = useAviso()
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin', 'ia', id], queryFn: () => api.get<IaClinica>(`/admin/clinicas/${id}/ia`) })
  const mudar = useMutation({
    mutationFn: (ligar: boolean) => api.put<IaClinica>(`/admin/clinicas/${id}/ia`, { usa_plataforma: ligar }),
    onSuccess: (e) => {
      qc.setQueryData(['admin', 'ia', id], e)
      qc.invalidateQueries({ queryKey: ['clinica'] })
      aviso.ok(e.usa_plataforma ? 'Chave da plataforma liberada para esta clínica.' : 'Chave da plataforma desligada para esta clínica.')
    },
    onError: aviso.erro,
  })
  const pergunte = useMutation({
    mutationFn: (liberado: boolean) => api.put<IaClinica>(`/admin/clinicas/${id}/pergunte`, { liberado }),
    onSuccess: (e) => {
      qc.setQueryData(['admin', 'ia', id], e)
      qc.invalidateQueries({ queryKey: ['clinica'] })
      aviso.ok(e.pergunte_liberado ? '"Perguntar à assistente" liberado para esta clínica.' : '"Perguntar à assistente" bloqueado para esta clínica.')
    },
    onError: aviso.erro,
  })
  if (!q.data) return <p className="text-sm text-muted">Carregando…</p>
  const e = q.data
  const nome = e.provedores.find((p) => p.id === e.provedor)?.nome
  return (
    <Secao titulo="Inteligência artificial" icone={<KeyRound className="size-5" />} className="max-w-3xl">
      <dl className="grid grid-cols-[minmax(0,14rem)_1fr] gap-x-6 gap-y-3 text-sm">
        <dt className="text-muted">Situação</dt>
        <dd>{e.origem === 'clinica' ? <Selo cor="verde">ligada · chave da clínica</Selo>
          : e.origem === 'plataforma' ? <Selo cor="azul">ligada · chave da plataforma</Selo>
          : <Selo cor="ambar">desligada</Selo>}</dd>
        <dt className="text-muted">Chave da clínica</dt>
        <dd>{e.tem_chave ? `${nome} · ${e.modelo} · termina em ${e.chave_final}${e.chave_ilegivel ? ' (ilegível: recadastrar)' : ''}` : '— nenhuma'}</dd>
        <dt className="text-muted">Chave da plataforma</dt>
        <dd>{e.plataforma.configurada ? `configurada no .env (${e.plataforma.modelo})` : 'não configurada no .env'}</dd>
      </dl>
      <label className="mt-6 flex items-start gap-3 text-sm">
        <input type="checkbox" className="mt-0.5 size-4 accent-[var(--primary)]" checked={e.usa_plataforma} disabled={mudar.isPending}
          onChange={(ev) => mudar.mutate(ev.target.checked)} />
        <span>
          Usar a chave da plataforma
          <span className="block text-xs text-muted">
            Para teste grátis ou demonstração. Vale só enquanto a clínica não tiver chave própria; o gasto fica na conta da plataforma.
          </span>
        </span>
      </label>
      {/* D121: o chat interno da equipe só aparece no painel da clínica quando liberado aqui */}
      <label className="mt-4 flex items-start gap-3 text-sm">
        <input type="checkbox" className="mt-0.5 size-4 accent-[var(--primary)]" checked={e.pergunte_liberado} disabled={pergunte.isPending}
          onChange={(ev) => pergunte.mutate(ev.target.checked)} />
        <span>
          Liberar "Perguntar à assistente"
          <span className="block text-xs text-muted">
            Chat em que a equipe da clínica pergunta sobre os próprios dados (só consulta, nunca altera). O gasto entra no teto de IA da clínica.
          </span>
        </span>
      </label>
    </Secao>
  )
}
