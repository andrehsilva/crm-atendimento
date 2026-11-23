import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, KeyRound, LogIn, PauseCircle, PlayCircle, QrCode, RefreshCw, Smartphone, Unplug, UserPlus, Webhook } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Modal, Secao, Seletor, Selo } from '../../components/ui'
import { api, type AdminClinica, type IaClinica, type SessaoWaha, type StatusWhatsapp, type UsuarioClinica } from '../../lib/api'
import { nomePapel } from '../../lib/auth'
import { escolherClinica } from '../../lib/clinicaGuardada'
import { telefone } from '../../lib/formato'
import { FUSOS, SeloWhatsapp } from './Clinicas'
import { SenhaProvisoria } from './SenhaProvisoria'
import { ConexaoWhatsApp } from './ConexaoWhatsApp'

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
      {aba === 'WhatsApp' && <WhatsApp id={id} />}
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
  const [f, setF] = useState({ nome: c.name, endereco: c.address ?? '', fuso: c.timezone, nome_assistente: c.nome_assistente })
  useEffect(() => setF({ nome: c.name, endereco: c.address ?? '', fuso: c.timezone, nome_assistente: c.nome_assistente }), [c])
  const salvar = useMutation({
    mutationFn: () => api.patch(`/admin/clinicas/${c.id}`, f),
    onSuccess: () => {
      aviso.ok('Dados salvos.')
      qc.invalidateQueries({ queryKey: ['admin'] })
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
        <Campo rotulo="Telefone (chave)" ajuda="Não muda: identifica a clínica."><Entrada value={telefone(c.phone)} disabled /></Campo>
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

function WhatsApp({ id }: { id: string }) {
  const aviso = useAviso()
  const qc = useQueryClient()
  const [qr, setQr] = useState(0)
  const [nova, setNova] = useState('')
  const st = useQuery({
    queryKey: ['admin', 'whatsapp', id],
    queryFn: () => api.get<StatusWhatsapp>(`/admin/clinicas/${id}/whatsapp`),
    refetchInterval: (q) => (q.state.data?.ligado && q.state.data.status !== 'WORKING' ? 5000 : false),
  })
  const sessoes = useQuery({
    queryKey: ['admin', 'sessoes'],
    queryFn: () => api.get<SessaoWaha[]>('/admin/whatsapp/sessoes'),
    enabled: st.data?.ligado === false,
    retry: false,
  })
  const feito = (msg: string) => () => {
    aviso.ok(msg)
    qc.invalidateQueries({ queryKey: ['admin'] })
  }
  const ligar = useMutation({
    mutationFn: ({ sessao, criar }: { sessao: string; criar: boolean }) => api.put(`/admin/clinicas/${id}/whatsapp${criar ? '?criar=true' : ''}`, { sessao }),
    onSuccess: feito('WhatsApp ligado à clínica.'),
    onError: aviso.erro,
  })
  const webhook = useMutation({ mutationFn: () => api.post(`/admin/clinicas/${id}/whatsapp/webhook`), onSuccess: feito('Webhook apontado para este backend.'), onError: aviso.erro })
  const reiniciar = useMutation({ mutationFn: () => api.post(`/admin/clinicas/${id}/whatsapp/reiniciar`), onSuccess: feito('Sessão reiniciando…'), onError: aviso.erro })
  const desligar = useMutation({ mutationFn: () => api.delete(`/admin/clinicas/${id}/whatsapp`), onSuccess: feito('WhatsApp desligado da clínica.'), onError: aviso.erro })

  if (st.isLoading || !st.data) return <p className="text-sm text-muted">Carregando…</p>
  const s = st.data

  if (!s.ligado) {
    const livres = (sessoes.data ?? []).filter((x) => !x.clinic_id)
    return (
      <div className="grid max-w-5xl gap-6 lg:grid-cols-2">
        <Secao titulo="Usar uma sessão existente" icone={<Smartphone className="size-5" />}>
          {sessoes.isError ? (
            <p className="text-sm text-red-600">{(sessoes.error as Error).message}</p>
          ) : sessoes.isLoading ? (
            <p className="text-sm text-muted">Consultando o servidor WAHA…</p>
          ) : !livres.length ? (
            <p className="text-sm text-muted">Nenhuma sessão livre no servidor WAHA. Crie uma nova ao lado.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {livres.map((x) => (
                <li key={x.sessao} className="flex items-center justify-between gap-3 rounded-2xl border border-line p-3">
                  <div>
                    <div className="font-medium">{x.sessao}</div>
                    <div className="text-xs text-muted">{x.numero ? telefone(`+${x.numero}`) : 'sem número conectado'} · {x.status}</div>
                  </div>
                  <Botao variante="secundario" onClick={() => ligar.mutate({ sessao: x.sessao, criar: false })} disabled={ligar.isPending}>Ligar</Botao>
                </li>
              ))}
            </ul>
          )}
        </Secao>
        <Secao titulo="Criar sessão nova" icone={<QrCode className="size-5" />}>
          <form onSubmit={(e: FormEvent) => { e.preventDefault(); ligar.mutate({ sessao: nova, criar: true }) }} className="flex flex-col gap-4">
            <Campo rotulo="Nome da sessão" ajuda="Letras, números, - e _. Ex.: clinica-sorriso. Depois é só ler o QR code.">
              <Entrada required pattern="[A-Za-z0-9_\-]{2,40}" value={nova} onChange={(e) => setNova(e.target.value)} />
            </Campo>
            <div><Botao type="submit" disabled={ligar.isPending || !nova}>Criar e ligar</Botao></div>
          </form>
        </Secao>
      </div>
    )
  }

  const precisaQr = s.status === 'SCAN_QR_CODE'
  return (
    <div className="grid max-w-5xl gap-6 lg:grid-cols-2">
      <Secao titulo="WhatsApp da clínica" icone={<Smartphone className="size-5" />}>
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
          <dt className="text-muted">Sessão</dt><dd className="font-medium">{s.sessao}</dd>
          <dt className="text-muted">Situação</dt><dd><SeloWhatsapp status={s.status} /></dd>
          <dt className="text-muted">Número</dt><dd>{s.numero ? telefone(s.numero) : '—'}</dd>
          <dt className="text-muted">Webhook</dt>
          <dd>{s.webhook_ok ? <Selo cor="verde">aponta para este backend</Selo> : <Selo cor="ambar">não aponta para este backend</Selo>}</dd>
        </dl>
        {s.erro && <p className="mt-3 text-sm text-red-600">{s.erro}</p>}
        {!s.webhook_ok && s.webhooks && s.webhooks.length > 0 && (
          <p className="mt-3 text-xs text-muted">Hoje vai para: {s.webhooks.join(', ')}. "Apontar webhook" substitui.</p>
        )}
        <div className="mt-5 flex flex-wrap gap-2">
          {!s.webhook_ok && <Botao onClick={() => webhook.mutate()} disabled={webhook.isPending}><Webhook className="size-4" /> Apontar webhook</Botao>}
          <Botao variante="secundario" onClick={() => setQr(Date.now())}><QrCode className="size-4" /> Mostrar QR code</Botao>
          <Botao variante="secundario" onClick={() => reiniciar.mutate()} disabled={reiniciar.isPending}><RefreshCw className="size-4" /> Reiniciar</Botao>
          <Botao variante="fantasma" onClick={() => desligar.mutate()} disabled={desligar.isPending}><Unplug className="size-4" /> Desligar da clínica</Botao>
        </div>
      </Secao>
      <ConexaoWhatsApp id={id} />
      <Secao titulo="Conectar o número">
        {qr ? (
          <div className="flex flex-col items-center gap-3">
            <img src={`/api/admin/clinicas/${id}/whatsapp/qr?t=${qr}`} alt="QR code do WhatsApp" className="size-64 rounded-2xl bg-white p-2"
              onError={() => { setQr(0); aviso.erro(new Error('QR indisponível: a sessão precisa estar aguardando QR (não conectada).')) }} />
            <p className="text-center text-xs text-muted">No celular da clínica: WhatsApp › Aparelhos conectados › Conectar aparelho. O código muda a cada 20 s.</p>
            <Botao variante="fantasma" onClick={() => setQr(Date.now())}>Atualizar QR</Botao>
          </div>
        ) : (
          <p className="text-sm text-muted">
            {precisaQr ? 'A sessão está esperando a leitura do QR code. Clique em "Mostrar QR code".'
              : s.status === 'WORKING' ? 'O número já está conectado. Só precisa de QR se for trocar de aparelho.'
              : 'Quando a sessão pedir QR code, ele aparece aqui.'}
          </p>
        )}
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
