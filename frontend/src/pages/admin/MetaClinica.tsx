import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BadgeCheck, Check, Copy, FileText, KeyRound, ListChecks, Loader2, RefreshCw, Webhook } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Modal, Secao, Selo } from '../../components/ui'
import { api, type EstadoMeta, type ModelosMeta } from '../../lib/api'

/**
 * Etapa 36D (D131): WhatsApp oficial (Cloud API da Meta) de uma clínica, no Admin geral.
 * Dados da Meta (docs/conexao_meta.md) · endereço do webhook · modelos · trocar o provedor.
 */
export function MetaClinica({ id, emUso, ligadoWaha, onTrocou }: {
  id: string
  emUso: boolean
  ligadoWaha: boolean
  onTrocou: () => void
}) {
  const base = `/admin/clinicas/${id}/whatsapp/meta`
  const q = useQuery({ queryKey: ['admin', 'meta', id], queryFn: () => api.get<EstadoMeta>(base) })
  if (q.isLoading || !q.data) return <p className="text-sm text-muted">Carregando…</p>
  const m = q.data
  const pronto = Boolean(m.phone_number_id && m.token_final && m.tem_app_secret)
  return (
    <div className="grid gap-6">
      <PassoAPasso />
      <Dados id={id} m={m} />
      <Endereco m={m} />
      {pronto && <Modelos id={id} />}
      <Trocar id={id} emUso={emUso} pronto={pronto} ligadoWaha={ligadoWaha} onTrocou={onTrocou} />
    </div>
  )
}

function PassoAPasso() {
  return (
    <Secao titulo="Como a clínica prepara o WhatsApp oficial" icone={<ListChecks className="size-5" />}>
      <ol className="list-decimal space-y-1.5 pl-5 text-sm text-muted">
        <li>Na Meta (business.facebook.com): conta do negócio <b className="text-text">verificada</b> e cartão cadastrado — a Meta cobra cada mensagem da clínica.</li>
        <li>Em developers.facebook.com: criar um app do tipo <b className="text-text">Negócios</b> e adicionar o produto WhatsApp.</li>
        <li>Registrar o número da clínica na Cloud API (ele sai do WhatsApp do celular).</li>
        <li>Gerar um <b className="text-text">token permanente</b> de Usuário do sistema com as permissões <code>whatsapp_business_messaging</code> e <code>whatsapp_business_management</code>.</li>
        <li>Colar abaixo o ID do número, o ID da conta, o token e a chave secreta do app; depois, colar na Meta o endereço do webhook e o token de verificação (campo <b className="text-text">messages</b>).</li>
        <li>Criar os modelos e esperar a Meta aprovar (de minutos a 1 dia). Só então trocar o provedor.</li>
      </ol>
    </Secao>
  )
}

function Dados({ id, m }: { id: string; m: EstadoMeta }) {
  const aviso = useAviso()
  const qc = useQueryClient()
  const base = `/admin/clinicas/${id}/whatsapp/meta`
  const [f, setF] = useState({ phone_number_id: '', waba_id: '', token: '', app_secret: '' })
  useEffect(() => {
    setF({ phone_number_id: m.phone_number_id ?? '', waba_id: m.waba_id ?? '', token: '', app_secret: '' })
  }, [m.phone_number_id, m.waba_id])
  const salvar = useMutation({
    mutationFn: () => api.put<EstadoMeta>(base, { ...f, token: f.token || null, app_secret: f.app_secret || null }),
    onSuccess: (r) => { qc.setQueryData(['admin', 'meta', id], r); aviso.ok('Dados da Meta salvos.') },
    onError: aviso.erro,
  })
  const testar = useMutation({
    mutationFn: () => api.post<{ ok: boolean; numero?: string; nome?: string; qualidade?: string; detalhe?: string }>(`${base}/testar`),
    onSuccess: (r) => (r.ok ? aviso.ok(`A Meta respondeu: ${r.numero ?? '?'} · ${r.nome ?? ''}${r.qualidade ? ` · qualidade ${r.qualidade}` : ''}`)
      : aviso.erro(new Error(r.detalhe))),
    onError: aviso.erro,
  })
  const so = (v: string) => v.replace(/\D/g, '')
  return (
    <Secao titulo="Dados da Meta" icone={<KeyRound className="size-5" />}
      acao={m.token_final ? <Selo cor="verde">salvos</Selo> : <Selo>não configurado</Selo>}>
      <form onSubmit={(e: FormEvent) => { e.preventDefault(); salvar.mutate() }} className="flex flex-col gap-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo rotulo="ID do número (Phone Number ID)" ajuda="WhatsApp › Configuração da API, no app da Meta.">
            <Entrada required inputMode="numeric" value={f.phone_number_id} onChange={(e) => setF({ ...f, phone_number_id: so(e.target.value) })} />
          </Campo>
          <Campo rotulo="ID da conta do WhatsApp Business (WABA ID)" ajuda="Mesma tela. Serve para os modelos.">
            <Entrada required inputMode="numeric" value={f.waba_id} onChange={(e) => setF({ ...f, waba_id: so(e.target.value) })} />
          </Campo>
          <Campo rotulo="Token de acesso permanente" ajuda={m.token_final ? `Salvo, termina em ${m.token_final}. Vazio = manter.` : 'O temporário vence em 24 h: use o de Usuário do sistema.'}>
            <Entrada type="password" autoComplete="off" value={f.token} onChange={(e) => setF({ ...f, token: e.target.value })} />
          </Campo>
          <Campo rotulo="Chave secreta do app (App Secret)" ajuda={m.tem_app_secret ? 'Salva. Vazio = manter.' : 'App › Configurações › Básico. Confere que as mensagens vêm da Meta.'}>
            <Entrada type="password" autoComplete="off" value={f.app_secret} onChange={(e) => setF({ ...f, app_secret: e.target.value })} />
          </Campo>
        </div>
        <p className="text-xs text-muted">Token e chave secreta ficam guardados criptografados e nunca voltam para a tela.</p>
        <div className="flex flex-wrap justify-end gap-2">
          <Botao type="button" variante="secundario" disabled={!m.token_final || testar.isPending} onClick={() => testar.mutate()}>
            {testar.isPending ? <><Loader2 className="size-4 animate-spin" />Testando…</> : 'Testar dados salvos'}
          </Botao>
          <Botao type="submit" disabled={salvar.isPending}>{salvar.isPending ? 'Salvando…' : 'Salvar'}</Botao>
        </div>
      </form>
    </Secao>
  )
}

function Copiavel({ rotulo, valor }: { rotulo: string; valor: string | null }) {
  const [copiado, setCopiado] = useState(false)
  return (
    <div>
      <p className="mb-1 text-xs text-muted">{rotulo}</p>
      <div className="flex items-center gap-2 rounded-xl bg-surface-muted px-3 py-2">
        <code className="min-w-0 flex-1 break-all text-xs">{valor ?? '—'}</code>
        {valor && (
          <button type="button" aria-label={`Copiar ${rotulo}`} className="shrink-0 text-muted hover:text-primary"
            onClick={() => navigator.clipboard?.writeText(valor).then(() => { setCopiado(true); setTimeout(() => setCopiado(false), 1500) }).catch(() => undefined)}>
            {copiado ? <Check className="size-4 text-green-600" /> : <Copy className="size-4" />}
          </button>
        )}
      </div>
    </div>
  )
}

function Endereco({ m }: { m: EstadoMeta }) {
  return (
    <Secao titulo="Webhook para colar na Meta" icone={<Webhook className="size-5" />}>
      {!m.verify_token ? (
        <p className="text-sm text-muted">Salve os dados da Meta para gerar o endereço e o token de verificação.</p>
      ) : (
        <div className="grid gap-3">
          <Copiavel rotulo="URL de callback" valor={m.webhook_url} />
          <Copiavel rotulo="Token de verificação" valor={m.verify_token} />
          <p className="text-xs text-muted">
            No app da Meta: WhatsApp › Configuração › Webhook › Editar. Depois de verificar, assine o campo <b>messages</b>.
            {!m.webhook_url && ' Falta PUBLIC_BASE_URL no backend para montar o endereço.'}
          </p>
        </div>
      )}
    </Secao>
  )
}

const COR_SITUACAO: Record<string, 'verde' | 'ambar' | 'vermelho' | 'cinza'> = {
  aprovado: 'verde', 'em análise': 'ambar', recusado: 'vermelho', pausado: 'vermelho', desativado: 'vermelho',
}
const NOME_TIPO: Record<string, string> = {
  lembrete: 'Lembrete', confirmacao: 'Confirmação', remarcacao: 'Remarcação', cancelamento: 'Cancelamento',
  pos_consulta: 'Pós-consulta', tratamento: 'Tratamento', retorno: 'Retorno', aniversario: 'Aniversário', resumo_dia: 'Resumo do dia',
}

function Modelos({ id }: { id: string }) {
  const aviso = useAviso()
  const qc = useQueryClient()
  const base = `/admin/clinicas/${id}/whatsapp/meta/modelos`
  const q = useQuery({ queryKey: ['admin', 'meta-modelos', id], queryFn: () => api.get<ModelosMeta>(base), retry: false })
  const criar = useMutation({
    mutationFn: () => api.post<ModelosMeta>(base),
    onSuccess: (r) => { qc.setQueryData(['admin', 'meta-modelos', id], r); aviso.ok('Modelos enviados para a Meta aprovar.') },
    onError: aviso.erro,
  })
  const faltam = (q.data?.modelos ?? []).some((m) => m.situacao === 'não criado')
  return (
    <Secao titulo="Modelos de mensagem" icone={<FileText className="size-5" />}
      acao={q.data && <Selo cor={q.data.aprovados === q.data.total ? 'verde' : 'ambar'}>{q.data.aprovados} de {q.data.total} aprovados</Selo>}>
      <p className="mb-3 text-sm text-muted">
        Fora das 24 h depois da última mensagem do cliente, a Meta só deixa enviar modelos aprovados
        (lembrete, aniversário, retorno…). São os mesmos para todas as clínicas.
      </p>
      {q.isLoading ? <p className="text-sm text-muted">Consultando a Meta…</p>
        : q.isError ? <p className="text-sm text-red-600">{(q.error as Error).message}</p>
        : (
          <ul className="divide-y divide-line text-sm">
            {q.data!.modelos.map((m) => (
              <li key={m.nome} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2">
                <span className="min-w-40 flex-1">
                  <span className="font-medium">{m.tipos.map((t) => NOME_TIPO[t] ?? t).join(', ')}</span>
                  <span className="ml-2 text-xs text-muted">{m.nome} · {m.categoria === 'MARKETING' ? 'marketing' : 'utilidade'}</span>
                  {m.motivo && <span className="block text-xs text-red-600">Motivo: {m.motivo}</span>}
                </span>
                <Selo cor={COR_SITUACAO[m.situacao] ?? 'cinza'}>{m.situacao}</Selo>
              </li>
            ))}
          </ul>
        )}
      <div className="mt-3 flex flex-wrap justify-end gap-2">
        <Botao type="button" variante="secundario" onClick={() => q.refetch()} disabled={q.isFetching}>
          <RefreshCw className={`size-4 ${q.isFetching ? 'animate-spin' : ''}`} />Atualizar
        </Botao>
        {faltam && (
          <Botao type="button" disabled={criar.isPending} onClick={() => criar.mutate()}>
            {criar.isPending ? <><Loader2 className="size-4 animate-spin" />Enviando…</> : 'Criar os que faltam na Meta'}
          </Botao>
        )}
      </div>
    </Secao>
  )
}

function Trocar({ id, emUso, pronto, ligadoWaha, onTrocou }: {
  id: string; emUso: boolean; pronto: boolean; ligadoWaha: boolean; onTrocou: () => void
}) {
  const aviso = useAviso()
  const [confirmar, setConfirmar] = useState(false)
  const trocar = useMutation({
    mutationFn: (provedor: 'waha' | 'meta') => api.put<EstadoMeta>(`/admin/clinicas/${id}/whatsapp/provedor`, { provedor }),
    onSuccess: (r) => {
      setConfirmar(false)
      aviso.ok(r.provedor === 'meta' ? 'Clínica agora usa o WhatsApp oficial.' : 'Clínica voltou para o WAHA (desligada: religue a sessão na aba WAHA).')
      onTrocou()
    },
    onError: aviso.erro,
  })
  if (emUso) {
    return (
      <Secao titulo="Em uso nesta clínica" icone={<BadgeCheck className="size-5" />}>
        <p className="mb-3 text-sm text-muted">Mensagens desta clínica saem e chegam pela Meta. Voltar para o WAHA deixa a clínica desligada até religar a sessão.</p>
        <div className="flex justify-end">
          <Botao type="button" variante="secundario" disabled={trocar.isPending} onClick={() => trocar.mutate('waha')}>Voltar para o WAHA</Botao>
        </div>
      </Secao>
    )
  }
  return (
    <Secao titulo="Usar o WhatsApp oficial nesta clínica" icone={<BadgeCheck className="size-5" />}>
      <p className="mb-3 text-sm text-muted">
        {!pronto ? 'Salve os dados da Meta primeiro.'
          : ligadoWaha ? 'Desligue o WhatsApp (WAHA) desta clínica na aba WAHA antes de trocar.'
          : 'A clínica passa a enviar e receber pela Meta. Confira antes se o webhook foi verificado e os modelos foram aprovados.'}
      </p>
      <div className="flex justify-end">
        <Botao type="button" disabled={!pronto || ligadoWaha} onClick={() => setConfirmar(true)}>Trocar para o WhatsApp oficial</Botao>
      </div>
      <Modal titulo="Trocar para o WhatsApp oficial?" aberto={confirmar} onFechar={() => setConfirmar(false)}>
        <p className="text-sm">
          A partir de agora as mensagens desta clínica saem pela Meta, que cobra cada mensagem da própria clínica.
          Os dados do WAHA continuam guardados para voltar depois.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Botao type="button" variante="secundario" onClick={() => setConfirmar(false)}>Cancelar</Botao>
          <Botao type="button" disabled={trocar.isPending} onClick={() => trocar.mutate('meta')}>{trocar.isPending ? 'Trocando…' : 'Trocar'}</Botao>
        </div>
      </Modal>
    </Secao>
  )
}
