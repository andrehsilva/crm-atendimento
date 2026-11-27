import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, Cake, CalendarClock, CheckCheck, ChevronRight, Clock, Inbox, Megaphone, Search, Send, X } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { RelogioTeste } from '../components/RelogioTeste'
import { TIPO_MENSAGEM } from '../components/tipoMensagem'
import { Entrada, Seletor, Selo, Vazio } from '../components/ui'
import { api, type Disparo, type Mensagem, type Paciente } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { dataHora, telefone } from '../lib/formato'
import { useTermos } from '../lib/termos'

/** Etapa 14B: as mensagens separadas pelo que importa para a recepção — o que vai sair, o que saiu e o que deu errado. */
const GRUPOS = {
  fila: { rotulo: 'Na fila', icone: Clock, status: ['agendada'], vazio: 'Nada esperando para sair.' },
  enviadas: { rotulo: 'Enviadas', icone: CheckCheck, status: ['enviada', 'entregue', 'lida'], vazio: 'Nenhuma mensagem enviada ainda.' },
  problemas: { rotulo: 'Não enviadas', icone: AlertCircle, status: ['falhou', 'cancelada'], vazio: 'Nenhum problema. 🎉' },
} as const
type Grupo = keyof typeof GRUPOS

const SITUACAO: Record<Mensagem['status'], [string, 'azul' | 'verde' | 'vermelho' | 'cinza']> = {
  // D85: entregue/lida vêm do WhatsApp; se o paciente desligou a confirmação de leitura, fica em "entregue"
  agendada: ['na fila', 'azul'], enviada: ['✓ enviada', 'cinza'], entregue: ['✓✓ entregue', 'verde'], lida: ['✓✓ lida', 'azul'],
  falhou: ['falhou', 'vermelho'], cancelada: ['cancelada', 'cinza'],
}

/** "hoje", "amanhã", "em 3 dias", "ontem", "há 5 dias" — conta dias de calendário no fuso da clínica. */
function diasAte(iso: string, tz: string): number {
  const dia = (d: Date) => new Date(`${new Intl.DateTimeFormat('en-CA', { timeZone: tz }).format(d)}T12:00:00Z`).getTime()
  return Math.round((dia(new Date(iso)) - dia(new Date())) / 86_400_000)
}

function relativo(dias: number): string {
  if (dias === 0) return 'hoje'
  if (dias === 1) return 'amanhã'
  if (dias === -1) return 'ontem'
  return dias > 0 ? `em ${dias} dias` : `há ${-dias} dias`
}

function Quando({ m, tz }: { m: Mensagem; tz: string }) {
  const naFila = m.status === 'agendada'
  const iso = naFila ? m.scheduled_for : (m.sent_at ?? m.created_at)
  const dias = diasAte(iso, tz)
  const [semana, resto] = dataHora(iso, tz).split(', ')
  const horaTxt = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit', timeZone: tz }).format(new Date(iso))
  const Icone = naFila ? CalendarClock : m.status === 'falhou' || m.status === 'cancelada' ? AlertCircle : Send
  const legenda = naFila ? `sai ${relativo(dias)}` : m.sent_at ? `enviada ${relativo(dias)}` : `criada ${relativo(dias)}`
  const urgente = naFila && dias <= 0
  return (
    <span className="flex w-44 items-center gap-2.5">
      <span className={`grid size-9 shrink-0 place-items-center rounded-xl ${urgente ? 'bg-primary-soft text-primary' : 'bg-surface text-muted ring-1 ring-line'}`}>
        <Icone className="size-4" aria-hidden />
      </span>
      <span className="leading-tight">
        <span className="block text-sm font-medium tabular-nums">
          {semana.replace('.', '')} {resto?.slice(0, 5)} <span className="text-muted">· {horaTxt}</span>
        </span>
        <span className={`block text-xs ${urgente ? 'font-medium text-primary' : 'text-muted'}`}>{legenda}</span>
      </span>
    </span>
  )
}

const PERIODOS = [7, 30, 90] as const

/** Etapa 35 (D130): um cartão por disparo em massa — conferir de relance se saiu e se algo falhou. */
function CartaoDisparo({ d, tz, ativo, onClick }: { d: Disparo; tz: string; ativo: boolean; onClick: () => void }) {
  const pct = (n: number) => `${d.total ? (n / d.total) * 100 : 0}%`
  const dia = (iso: string) => new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', timeZone: tz }).format(new Date(iso))
  const periodo = dia(d.inicio) === dia(d.fim) ? dia(d.inicio) : `${dia(d.inicio)} a ${dia(d.fim)}`
  const Icone = d.tipo === 'aniversario' ? Cake : Megaphone
  return (
    <button type="button" onClick={onClick} aria-pressed={ativo}
      className={`w-64 shrink-0 rounded-2xl p-4 text-left transition ${ativo ? 'bg-primary-soft ring-2 ring-primary' : 'bg-surface ring-1 ring-line hover:ring-primary/40'}`}>
      <span className="flex items-center gap-2">
        <Icone className="size-4 text-primary" aria-hidden />
        <span className="truncate font-medium">{d.titulo}</span>
        <span className="ml-auto text-xs text-muted">{periodo}</span>
      </span>
      <span className="mt-3 flex h-2 overflow-hidden rounded-full bg-surface-muted" aria-hidden>
        <span className="bg-[#1f7a43]" style={{ width: pct(d.entregues) }} />
        <span className="bg-[#86d6a5]" style={{ width: pct(d.enviadas - d.entregues) }} />
        <span className="bg-[#c0362e]" style={{ width: pct(d.falharam) }} />
        <span className="bg-[#8cc3f0]" style={{ width: pct(d.na_fila) }} />
      </span>
      <span className="mt-2 block text-xs text-muted">
        <b className="text-text">{d.enviadas}</b> de {d.total} enviadas · {d.entregues} entregues
        {d.falharam > 0 && <> · <b className="text-[#c0362e] dark:text-[#f3a29b]">{d.falharam} falharam</b></>}
        {d.na_fila > 0 && <> · {d.na_fila} na fila</>}
      </span>
    </button>
  )
}

/** Escolher um cliente: busca pelo nome ou telefone (a lista do período também deixa clicar no nome). */
function BuscaCliente({ onEscolher }: { onEscolher: (c: { id: string; nome: string }) => void }) {
  const { clinica } = useClinica()
  const [texto, setTexto] = useState('')
  const [termo, setTermo] = useState('')
  useEffect(() => { const t = setTimeout(() => setTermo(texto.trim()), 300); return () => clearTimeout(t) }, [texto])
  const q = useQuery({
    queryKey: ['pacientes', clinica.id, 'busca-mensagens', termo],
    queryFn: () => api.get<Paciente[]>(`/clinics/${clinica.id}/patients?busca=${encodeURIComponent(termo)}`),
    enabled: termo.length >= 2,
  })
  const achados = (q.data ?? []).slice(0, 8)
  return (
    <div className="relative">
      <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden />
      <Entrada value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Cliente: nome ou telefone"
        aria-label="Filtrar por cliente" className="!w-64 !py-1.5 pl-9" />
      {termo.length >= 2 && (
        <ul className="absolute right-0 z-20 mt-1 w-72 overflow-hidden rounded-xl bg-surface shadow-lg ring-1 ring-line">
          {q.isLoading ? <li className="px-3 py-2 text-sm text-muted">Buscando…</li>
            : achados.length === 0 ? <li className="px-3 py-2 text-sm text-muted">Ninguém encontrado.</li>
            : achados.map((p) => (
              <li key={p.id}>
                <button type="button" onClick={() => { onEscolher({ id: p.id, nome: p.name ?? telefone(p.phone) }); setTexto(''); setTermo('') }}
                  className="block w-full px-3 py-2 text-left text-sm hover:bg-surface-muted">
                  <span className="font-medium">{p.name ?? 'Sem nome'}</span>
                  <span className="ml-2 text-muted">{telefone(p.phone)}</span>
                </button>
              </li>
            ))}
        </ul>
      )}
    </div>
  )
}

export function Mensagens() {
  const { clinica } = useClinica()
  const pal = useTermos()
  const tz = clinica.timezone
  const [grupo, setGrupo] = useState<Grupo>('fila')
  const [tipo, setTipo] = useState('')
  const [dias, setDias] = useState<number>(7)
  const [cliente, setCliente] = useState<{ id: string; nome: string } | null>(null)
  const [disparo, setDisparo] = useState<Disparo | null>(null)
  const q = useQuery({
    queryKey: ['mensagens', clinica.id, cliente ? `cliente:${cliente.id}` : `dias:${dias}`],
    queryFn: () => api.get<Mensagem[]>(`/clinics/${clinica.id}/outbound?${cliente ? `paciente=${cliente.id}` : `dias=${dias}`}`),
  })
  const qd = useQuery({
    queryKey: ['mensagens', clinica.id, 'disparos', dias],
    queryFn: () => api.get<Disparo[]>(`/clinics/${clinica.id}/outbound/disparos?dias=${dias}`),
    enabled: !cliente,
  })
  const doDisparo = (m: Mensagem) => !disparo
    || (disparo.tipo === 'aniversario' ? m.kind === 'aniversario' : m.kind === 'campanha' && (m.campaign_id ?? null) === disparo.campaign_id)
  const todas = useMemo(() => (q.data ?? []).filter((m) => (!tipo || m.kind === tipo) && doDisparo(m)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [q.data, tipo, disparo])
  const escolherCliente = (c: { id: string; nome: string } | null) => { setCliente(c); setDisparo(null) }
  const escolherDisparo = (d: Disparo) => {
    if (disparo && disparo.tipo === d.tipo && disparo.campaign_id === d.campaign_id) { setDisparo(null); return }
    setDisparo(d)
    setTipo('')
    setGrupo(d.falharam > 0 ? 'problemas' : d.enviadas > 0 ? 'enviadas' : 'fila')
  }
  const doGrupo = (g: Grupo) => todas.filter((m) => (GRUPOS[g].status as readonly string[]).includes(m.status))
  const lista = doGrupo(grupo)
    .slice()
    .sort((a, b) => (grupo === 'fila' ? a.scheduled_for.localeCompare(b.scheduled_for) : (b.sent_at ?? b.created_at).localeCompare(a.sent_at ?? a.created_at)))

  return (
    <>
      <PageHeader titulo="Mensagens" subtitulo={`O que vai sair, o que já saiu e o que não deu certo para os ${pal.clientes}`} />

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div role="tablist" aria-label="Situação das mensagens" className="flex flex-wrap gap-2">
          {(Object.keys(GRUPOS) as Grupo[]).map((g) => {
            const G = GRUPOS[g]
            const n = doGrupo(g).length
            return (
              <button key={g} type="button" role="tab" aria-selected={grupo === g} onClick={() => setGrupo(g)}
                className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm transition ${grupo === g ? 'bg-primary text-primary-contrast' : 'bg-surface text-muted hover:text-text'}`}>
                <G.icone className="size-4" />{G.rotulo}
                <span className={`rounded-full px-2 text-xs font-semibold ${grupo === g ? 'bg-white/25' : 'bg-surface-muted'}`}>{n}</span>
              </button>
            )
          })}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {!cliente && <BuscaCliente onEscolher={escolherCliente} />}
          {!cliente && (
            <label className="flex items-center gap-2 text-sm text-muted">
              Período
              <Seletor value={dias} onChange={(e) => { setDias(Number(e.target.value)); setDisparo(null) }} className="!w-auto !py-1.5">
                {PERIODOS.map((d) => <option key={d} value={d}>Últimos {d} dias</option>)}
              </Seletor>
            </label>
          )}
          <label className="flex items-center gap-2 text-sm text-muted">
            Tipo
            <Seletor value={tipo} onChange={(e) => { setTipo(e.target.value); setDisparo(null) }} className="!w-auto !py-1.5">
              <option value="">Todos</option>
              {Object.entries(TIPO_MENSAGEM).map(([v, [r]]) => <option key={v} value={v}>{r}</option>)}
            </Seletor>
          </label>
        </div>
      </div>

      {cliente && (
        <div className="mb-4 flex flex-wrap items-center gap-3 rounded-2xl bg-primary-soft px-4 py-3 text-sm">
          <span>Tudo o que foi enviado para <b>{cliente.nome}</b>, de qualquer data.</span>
          <button type="button" onClick={() => escolherCliente(null)}
            className="ml-auto inline-flex items-center gap-1 rounded-full bg-surface px-3 py-1 text-xs font-medium ring-1 ring-line hover:text-primary">
            <X className="size-3.5" aria-hidden /> Voltar para todos
          </button>
        </div>
      )}

      {!cliente && (qd.data?.length ?? 0) > 0 && (
        <section className="mb-4" aria-label="Campanhas e aniversários do período">
          <h2 className="mb-2 text-sm font-medium text-muted">Disparos do período <span className="font-normal">· clique para ver as mensagens</span></h2>
          <div className="flex gap-3 overflow-x-auto pb-1">
            {qd.data!.map((d) => (
              <CartaoDisparo key={`${d.tipo}:${d.campaign_id}`} d={d} tz={tz}
                ativo={!!disparo && disparo.tipo === d.tipo && disparo.campaign_id === d.campaign_id}
                onClick={() => escolherDisparo(d)} />
            ))}
          </div>
        </section>
      )}

      <section className="rounded-3xl bg-surface p-2 sm:p-4" aria-live="polite">
        {q.isLoading ? <p className="p-4 text-sm text-muted">Carregando…</p>
          : lista.length === 0 ? <Vazio icone={<Inbox className="size-8" />} texto={GRUPOS[grupo].vazio} />
          : (
            <ul className="divide-y divide-line">
              {lista.map((m) => {
                const [tRot, tCor] = TIPO_MENSAGEM[m.kind] ?? [m.kind, 'cinza']
                const [sRot, sCor] = SITUACAO[m.status]
                return (
                  <li key={m.id}>
                    {/* aberta = um cartão só (linha + mensagem); fechada = só um leve destaque ao passar o mouse */}
                    <details className="group my-1 rounded-2xl transition-colors open:bg-surface-muted/70 open:ring-1 open:ring-line">
                      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-4 gap-y-1 rounded-2xl px-3 py-3 transition-colors hover:bg-surface-muted/50 group-open:hover:bg-transparent">
                        <ChevronRight className="size-4 shrink-0 text-muted transition group-open:rotate-90" aria-hidden />
                        <span className="w-28 shrink-0"><Selo cor={tCor}>{tRot}</Selo></span>
                        <span className="min-w-40 flex-1">
                          {!cliente && m.patient_id ? (
                            <button type="button" title="Ver tudo o que foi enviado para este cliente"
                              onClick={(e) => { e.preventDefault(); escolherCliente({ id: m.patient_id!, nome: m.paciente ?? telefone(m.telefone) }) }}
                              className="font-medium underline-offset-2 hover:text-primary hover:underline">
                              {m.paciente ?? 'Sem nome'}
                            </button>
                          ) : <span className="font-medium">{m.paciente ?? 'Sem nome'}</span>}
                          {m.campanha && <span className="ml-2 text-xs text-muted">· {m.campanha}</span>}
                          <span className="ml-2 text-sm text-muted">{telefone(m.telefone)}</span>
                        </span>
                        <Quando m={m} tz={tz} />
                        <span className="w-24 text-right"><Selo cor={sCor}>{sRot}</Selo></span>
                      </summary>
                      <div className="mx-3 mb-3 ml-11 border-t border-line pt-3 text-sm">
                        <p className="whitespace-pre-line">{m.body}</p>
                        {m.error && <p className="mt-2 text-xs text-muted">Motivo: {m.error}</p>}
                      </div>
                    </details>
                  </li>
                )
              })}
            </ul>
          )}
      </section>

      <details className="mt-6 text-sm text-muted">
        <summary className="cursor-pointer">Ferramentas de teste (só em desenvolvimento)</summary>
        <div className="mt-3"><RelogioTeste /></div>
      </details>
    </>
  )
}
