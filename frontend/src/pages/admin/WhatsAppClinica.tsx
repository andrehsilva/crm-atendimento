import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Loader2, QrCode, RefreshCw, Server, Smartphone, Unplug, Webhook } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Modal, Secao, Selo } from '../../components/ui'
import { api, type ConexaoWhatsapp, type SessaoWaha, type StatusWhatsapp } from '../../lib/api'
import { telefone } from '../../lib/formato'
import { SeloWhatsapp } from './Clinicas'

/**
 * Etapa 31 (D122–D124): WhatsApp de uma clínica em 3 passos.
 * 1. servidor (plataforma ou próprio) · 2. número/sessão · 3. webhook exclusivo, apontado sozinho.
 */
export function WhatsAppClinica({ id, slug }: { id: string; slug: string }) {
  const aviso = useAviso()
  const qc = useQueryClient()
  const base = `/admin/clinicas/${id}/whatsapp`
  const chave = ['admin', 'whatsapp', id]
  const st = useQuery({
    queryKey: chave,
    queryFn: () => api.get<StatusWhatsapp>(base),
    // enquanto a sessão reinicia ou espera o QR, atualiza sozinho
    refetchInterval: (q) => (q.state.data?.ligado && q.state.data.status !== 'WORKING' ? 4000 : false),
  })
  const atualizar = (s?: StatusWhatsapp & { aviso?: string; reiniciando?: boolean }) => {
    if (s) qc.setQueryData(chave, s)
    qc.invalidateQueries({ queryKey: ['admin'] })
    if (s?.aviso) aviso.erro(new Error(s.aviso))
  }

  if (st.isLoading || !st.data) return <p className="text-sm text-muted">Carregando…</p>
  const s = st.data
  return (
    <div className="grid max-w-5xl gap-6">
      <PassoServidor id={id} conexao={s.conexao} ligado={s.ligado} onSalvo={() => qc.invalidateQueries({ queryKey: chave })} />
      {s.ligado
        ? <Ligado id={id} s={s} onMudou={atualizar} />
        : <PassoNumero id={id} slug={slug} onLigado={(r) => { atualizar(r); aviso.ok(r.reiniciando
            ? 'WhatsApp ligado. A sessão está reiniciando para receber o webhook (alguns segundos).'
            : 'WhatsApp ligado.') }} />}
      <p className="text-xs text-muted">
        O webhook é exclusivo desta clínica (endereço e segredo próprios) e é apontado sozinho ao ligar.
        Mudar o webhook de uma sessão faz o WAHA reiniciá-la: o número fica alguns segundos sem conexão.
      </p>
    </div>
  )
}

/* ---------------------------------------------------------------- 1. Servidor */
function PassoServidor({ id, conexao, ligado, onSalvo }: { id: string; conexao: ConexaoWhatsapp; ligado: boolean; onSalvo: () => void }) {
  const aviso = useAviso()
  const base = `/admin/clinicas/${id}/whatsapp`
  const [f, setF] = useState({ numero: '', proprio: false, url: '', chave: '' })
  // só recarrega o formulário quando o salvo muda (a tela atualiza sozinha enquanto a sessão reinicia)
  const { numero_cadastrado, servidor_proprio, servidor_url } = conexao
  useEffect(() => {
    setF({ numero: numero_cadastrado ?? '', proprio: servidor_proprio, url: servidor_url ?? '', chave: '' })
  }, [numero_cadastrado, servidor_proprio, servidor_url])
  const salvar = useMutation({
    mutationFn: () => api.put<ConexaoWhatsapp>(`${base}/conexao`, { numero: f.numero || null, url: f.proprio ? f.url : null, chave: f.proprio ? f.chave || null : null }),
    onSuccess: () => { aviso.ok('Servidor salvo.'); onSalvo() },
    onError: aviso.erro,
  })
  const testar = useMutation({
    mutationFn: () => api.post<{ ok: boolean; sessoes?: string[]; detalhe?: string }>(`${base}/testar`),
    onSuccess: (r) => (r.ok ? aviso.ok(`Servidor respondeu. Sessões: ${r.sessoes?.join(', ') || 'nenhuma'}`) : aviso.erro(new Error(r.detalhe))),
    onError: aviso.erro,
  })
  return (
    <Secao titulo="1. Servidor do WhatsApp" icone={<Server className="size-5" />}
      acao={conexao.servidor_proprio ? <Selo cor="azul">servidor próprio</Selo> : <Selo>servidor da plataforma</Selo>}>
      <form onSubmit={(e: FormEvent) => { e.preventDefault(); salvar.mutate() }} className="flex flex-col gap-4">
        <fieldset className="flex flex-wrap gap-x-6 gap-y-2 text-sm" disabled={ligado}>
          <label className="flex items-center gap-2"><input type="radio" checked={!f.proprio} onChange={() => setF({ ...f, proprio: false })} className="size-4 accent-[var(--primary)]" />Servidor da plataforma</label>
          <label className="flex items-center gap-2"><input type="radio" checked={f.proprio} onChange={() => setF({ ...f, proprio: true })} className="size-4 accent-[var(--primary)]" />Servidor próprio desta clínica</label>
        </fieldset>
        {ligado && <p className="text-xs text-muted">Para trocar de servidor, desligue o WhatsApp da clínica primeiro (nada se perde).</p>}
        {f.proprio && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo rotulo="Endereço do servidor WAHA"><Entrada type="url" required disabled={ligado} value={f.url} placeholder="https://waha.clinica.com.br" onChange={(e) => setF({ ...f, url: e.target.value })} /></Campo>
            <Campo rotulo="Chave da API (WAHA_API_KEY)" ajuda={conexao.chave_final ? `Salva, termina em ${conexao.chave_final}. Vazio = manter.` : 'Fica guardada criptografada.'}>
              <Entrada type="password" autoComplete="off" value={f.chave} onChange={(e) => setF({ ...f, chave: e.target.value })} />
            </Campo>
          </div>
        )}
        <Campo rotulo="Número do WhatsApp da clínica (opcional)" ajuda="Com DDD. Serve para conferir se o número conectado é o certo.">
          <Entrada value={f.numero} placeholder="(16) 99128-9152" onChange={(e) => setF({ ...f, numero: e.target.value })} />
        </Campo>
        <div className="flex flex-wrap justify-end gap-2">
          <Botao type="button" variante="secundario" disabled={testar.isPending} onClick={() => testar.mutate()}>
            {testar.isPending ? <><Loader2 className="size-4 animate-spin" />Testando…</> : 'Testar servidor salvo'}
          </Botao>
          <Botao type="submit" disabled={salvar.isPending}>{salvar.isPending ? 'Salvando…' : 'Salvar'}</Botao>
        </div>
      </form>
    </Secao>
  )
}

/* ---------------------------------------------------------------- 2. Número (sessão) */
function PassoNumero({ id, slug, onLigado }: { id: string; slug: string; onLigado: (r: StatusWhatsapp & { reiniciando?: boolean }) => void }) {
  const aviso = useAviso()
  const base = `/admin/clinicas/${id}/whatsapp`
  const [nova, setNova] = useState(slug.replace(/[^A-Za-z0-9_-]/g, '-').slice(0, 40))
  const sessoes = useQuery({ queryKey: ['admin', 'sessoes', id], queryFn: () => api.get<SessaoWaha[]>(`${base}/sessoes`), retry: false })
  const ligar = useMutation({
    mutationFn: ({ sessao, criar }: { sessao: string; criar: boolean }) =>
      api.put<StatusWhatsapp & { reiniciando?: boolean }>(`${base}${criar ? '?criar=true' : ''}`, { sessao }),
    onSuccess: onLigado,
    onError: aviso.erro,
  })
  const livres = (sessoes.data ?? []).filter((x) => !x.clinic_id)
  return (
    <Secao titulo="2. Número da clínica" icone={<Smartphone className="size-5" />}>
      {ligar.isPending && (
        <p className="mb-4 flex items-center gap-2 rounded-xl bg-surface-muted px-3 py-2 text-sm">
          <Loader2 className="size-4 animate-spin" />Ligando e apontando o webhook… pode levar alguns segundos.
        </p>
      )}
      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <p className="mb-2 text-sm font-medium">Usar uma sessão que já existe neste servidor</p>
          {sessoes.isError ? (
            <p className="text-sm text-red-600">{(sessoes.error as Error).message}</p>
          ) : sessoes.isLoading ? (
            <p className="flex items-center gap-2 text-sm text-muted"><Loader2 className="size-4 animate-spin" />Consultando o servidor…</p>
          ) : !livres.length ? (
            <p className="text-sm text-muted">Nenhuma sessão livre neste servidor. Crie uma nova ao lado.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {livres.map((x) => (
                <li key={x.sessao} className="flex items-center justify-between gap-3 rounded-2xl border border-line p-3">
                  <div>
                    <div className="font-medium">{x.sessao}</div>
                    <div className="text-xs text-muted">{x.numero ? telefone(`+${x.numero}`) : 'sem número conectado'} · {x.status}</div>
                  </div>
                  <Botao variante="secundario" disabled={ligar.isPending} onClick={() => ligar.mutate({ sessao: x.sessao, criar: false })}>Usar esta</Botao>
                </li>
              ))}
            </ul>
          )}
          {/* o WAHA pode estar reiniciando na hora da consulta: dá para pedir a lista de novo */}
          <Botao className="mt-3" variante="fantasma" disabled={sessoes.isFetching} onClick={() => sessoes.refetch()}>
            <RefreshCw className={`size-4 ${sessoes.isFetching ? 'animate-spin' : ''}`} />Atualizar lista
          </Botao>
        </div>
        <form onSubmit={(e: FormEvent) => { e.preventDefault(); ligar.mutate({ sessao: nova, criar: true }) }} className="flex flex-col gap-3">
          <p className="text-sm font-medium">Ou criar uma sessão nova (lendo o QR code)</p>
          <Campo rotulo="Nome da sessão" ajuda="Letras, números, - e _. Depois de criar, o QR code aparece aqui.">
            <Entrada required pattern="[A-Za-z0-9_\-]{2,40}" value={nova} onChange={(e) => setNova(e.target.value)} />
          </Campo>
          <div><Botao type="submit" disabled={ligar.isPending || !nova}><QrCode className="size-4" />Criar e ligar</Botao></div>
        </form>
      </div>
    </Secao>
  )
}

/* ---------------------------------------------------------------- Ligado: situação, QR e desligar */
function Ligado({ id, s, onMudou }: { id: string; s: Extract<StatusWhatsapp, { ligado: true }>; onMudou: (s?: StatusWhatsapp & { aviso?: string }) => void }) {
  const aviso = useAviso()
  const base = `/admin/clinicas/${id}/whatsapp`
  const [qr, setQr] = useState(0)
  const [desligar, setDesligar] = useState(false)
  const [tirar, setTirar] = useState(true)
  const precisaQr = s.status === 'SCAN_QR_CODE'
  // QR atualiza sozinho a cada 20 s enquanto a sessão espera a leitura
  useEffect(() => {
    if (!precisaQr) return
    setQr(Date.now())
    const t = setInterval(() => setQr(Date.now()), 20000)
    return () => clearInterval(t)
  }, [precisaQr])
  const corrigir = useMutation({
    mutationFn: () => api.post<StatusWhatsapp>(`${base}/webhook`),
    onSuccess: (r) => { onMudou(r); aviso.ok('Webhook apontado. A sessão está reiniciando (alguns segundos).') },
    onError: aviso.erro,
  })
  const reiniciar = useMutation({ mutationFn: () => api.post(`${base}/reiniciar`), onSuccess: () => { onMudou(); aviso.ok('Sessão reiniciando…') }, onError: aviso.erro })
  const sair = useMutation({
    mutationFn: () => api.delete<StatusWhatsapp & { aviso?: string }>(`${base}${tirar ? '?tirar_webhook=true' : ''}`),
    onSuccess: (r) => { setDesligar(false); onMudou(r); if (!r.aviso) aviso.ok('WhatsApp desligado. Servidor e webhook continuam salvos.') },
    onError: aviso.erro,
  })
  return (
    <Secao titulo="2. Número da clínica" icone={<Smartphone className="size-5" />} acao={<SeloWhatsapp status={s.status} />}>
      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
            <dt className="text-muted">Sessão</dt><dd className="font-medium">{s.sessao}</dd>
            <dt className="text-muted">Número</dt><dd>{s.numero ? telefone(s.numero) : '—'}</dd>
            <dt className="text-muted">Webhook</dt>
            <dd>{s.erro ? <Selo cor="cinza">sem resposta</Selo>
              : s.webhook_ok ? <Selo cor="verde"><CheckCircle2 className="size-3.5" />certo</Selo>
              : <Selo cor="ambar">desalinhado</Selo>}</dd>
          </dl>
          {s.erro && <p className="mt-3 text-sm text-red-600">Servidor WAHA: {s.erro}</p>}
          {!s.erro && !s.webhook_ok && (
            <p className="mt-3 text-xs text-muted">
              A sessão não está mandando as mensagens para esta clínica{s.webhooks?.length ? ` (hoje vai para: ${s.webhooks.join(', ')})` : ''}.
            </p>
          )}
          <div className="mt-5 flex flex-wrap gap-2">
            {!s.erro && !s.webhook_ok && (
              <Botao onClick={() => corrigir.mutate()} disabled={corrigir.isPending}>
                {corrigir.isPending ? <Loader2 className="size-4 animate-spin" /> : <Webhook className="size-4" />}Corrigir webhook
              </Botao>
            )}
            <Botao variante="secundario" onClick={() => reiniciar.mutate()} disabled={reiniciar.isPending}><RefreshCw className="size-4" />Reiniciar sessão</Botao>
            <Botao variante="fantasma" onClick={() => setDesligar(true)}><Unplug className="size-4" />Desligar da clínica</Botao>
          </div>
        </div>
        <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-line p-4 text-center">
          {precisaQr && qr ? (
            <>
              <img src={`/api${base}/qr?t=${qr}`} alt="QR code do WhatsApp" className="size-56 rounded-2xl bg-white p-2" />
              <p className="text-xs text-muted">No celular da clínica: WhatsApp › Aparelhos conectados › Conectar aparelho. O código troca sozinho.</p>
            </>
          ) : s.status === 'WORKING' ? (
            <p className="text-sm text-muted">Número conectado. O QR só é preciso para trocar de aparelho.</p>
          ) : (
            <p className="flex items-center gap-2 text-sm text-muted"><Loader2 className="size-4 animate-spin" />Esperando a sessão ({(s.status || '').toLowerCase()})…</p>
          )}
        </div>
      </div>

      <Modal titulo="Desligar o WhatsApp desta clínica?" aberto={desligar} onFechar={() => setDesligar(false)}>
        <div className="grid gap-4 text-sm">
          <p>A clínica para de receber e enviar mensagens pelo WhatsApp. O servidor e o webhook ficam salvos: para religar, é só escolher a sessão de novo.</p>
          <label className="flex items-start gap-2">
            <input type="checkbox" className="mt-0.5 size-4 accent-[var(--primary)]" checked={tirar} onChange={(e) => setTirar(e.target.checked)} />
            <span>Tirar também o webhook desta clínica da sessão <b>{s.sessao}</b> no WAHA<span className="block text-xs text-muted">Recomendado. A sessão reinicia por alguns segundos.</span></span>
          </label>
          <div className="flex justify-end gap-2">
            <Botao variante="fantasma" onClick={() => setDesligar(false)}>Voltar</Botao>
            <Botao className="!bg-red-600" disabled={sair.isPending} onClick={() => sair.mutate()}>
              {sair.isPending ? <Loader2 className="size-4 animate-spin" /> : <Unplug className="size-4" />}Desligar
            </Botao>
          </div>
        </div>
      </Modal>
    </Secao>
  )
}
