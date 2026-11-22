import { useEffect, useRef, useState, type ComponentType } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  AlertCircle, Bell, CalendarCheck, CalendarClock, CalendarPlus, CalendarX, CheckCheck, Gauge, Headset, Hourglass,
  PauseCircle, UserCheck, UserX, WifiOff,
} from 'lucide-react'
import { api, type Notificacao, type Notificacoes } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { useAviso } from './Aviso'
import { ModalConversa } from './ModalConversa'

const ICONE: Record<Notificacao['tipo'], ComponentType<{ className?: string }>> = {
  humano: Headset, whatsapp: WifiOff, marcada: CalendarPlus, remarcada: CalendarClock, cancelada: CalendarX,
  confirmada: CalendarCheck, falhou: AlertCircle, resposta_falhou: AlertCircle, ia: Gauge,
  tratamento_pedido: PauseCircle, tratamento_previsao: Hourglass, faltou_sessao: UserX, presenca: UserCheck,
}

/** "agora", "há 5 min", "há 2 h", "há 3 dias" */
function haQuanto(iso: string): string {
  const min = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60_000))
  if (min < 1) return 'agora'
  if (min < 60) return `há ${min} min`
  const h = Math.round(min / 60)
  if (h < 24) return `há ${h} h`
  const d = Math.round(h / 24)
  return d === 1 ? 'ontem' : `há ${d} dias`
}

/** D83: som curto (dois bipes) gerado no navegador — sem arquivo de áudio. */
function tocarSom() {
  try {
    const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    const ctx = new Ctx()
    ;[0, 0.18].forEach((atraso, i) => {
      const osc = ctx.createOscillator()
      const vol = ctx.createGain()
      osc.frequency.value = i === 0 ? 880 : 1175
      vol.gain.setValueAtTime(0.0001, ctx.currentTime + atraso)
      vol.gain.exponentialRampToValueAtTime(0.15, ctx.currentTime + atraso + 0.02)
      vol.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + atraso + 0.15)
      osc.connect(vol).connect(ctx.destination)
      osc.start(ctx.currentTime + atraso)
      osc.stop(ctx.currentTime + atraso + 0.16)
    })
    setTimeout(() => ctx.close(), 600)
  } catch {
    // navegador sem áudio (ou bloqueado até a primeira interação): fica só o contador
  }
}

/** Etapa 19 (D81–D83): sino com contador no topo do painel. */
export function Sino() {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const navegar = useNavigate()
  const [aberto, setAberto] = useState(false)
  const [conversa, setConversa] = useState<NonNullable<Notificacao['paciente']> | null>(null)
  const caixa = useRef<HTMLDivElement>(null)
  const base = `/clinics/${clinica.id}/notificacoes`
  const q = useQuery({
    queryKey: ['notificacoes', clinica.id],
    queryFn: () => api.get<Notificacoes>(base),
    refetchInterval: 60_000, // o tempo real cobre quase tudo; isto pega o resto (ex.: gasto da IA)
  })
  const dados = q.data
  const contador = dados?.contador ?? 0

  // número no título da aba: "(2) Clínica Rodrigues · Painel"
  useEffect(() => {
    document.title = `${contador ? `(${contador}) ` : ''}${clinica.name} · Painel`
  }, [contador, clinica.name])

  // som só quando aumenta o número de conversas aguardando a equipe (não toca ao abrir o painel)
  const anterior = useRef<number | null>(null)
  useEffect(() => {
    if (dados === undefined) return
    if (anterior.current !== null && dados.aguardando > anterior.current) tocarSom()
    anterior.current = dados.aguardando
  }, [dados])

  // fecha ao clicar fora ou apertar Esc
  useEffect(() => {
    if (!aberto) return
    const fora = (e: MouseEvent) => { if (caixa.current && !caixa.current.contains(e.target as Node)) setAberto(false) }
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setAberto(false) }
    document.addEventListener('mousedown', fora)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', fora); document.removeEventListener('keydown', esc) }
  }, [aberto])

  const lidas = useMutation({
    mutationFn: (chaves: string[] | null) => api.post<Notificacoes>(`${base}/lidas`, { chaves }),
    onSuccess: (r, chaves) => {
      qc.setQueryData(['notificacoes', clinica.id], r)
      if (chaves === null) aviso.ok('Todas marcadas como lidas.')
    },
    onError: aviso.erro,
  })

  function abrir(n: Notificacao) {
    if (!n.situacao && !n.lida) lidas.mutate([n.chave])
    setAberto(false)
    // conversa e tratamentos (Etapa 21) abrem a janela do paciente, onde ficam o tratamento e o botão Retomar
    const naConversa = ['humano', 'resposta_falhou', 'tratamento_pedido', 'tratamento_previsao']
    if (naConversa.includes(n.tipo) && n.paciente) return setConversa(n.paciente)
    const destino: Partial<Record<Notificacao['tipo'], string>> = {
      whatsapp: '/configuracoes?aba=Canais', ia: '/configuracoes?aba=Uso da IA', falhou: '/mensagens',
      marcada: '/agenda', remarcada: '/agenda', cancelada: '/agenda', confirmada: '/agenda',
    }
    if (n.dia) return navegar(`/agenda?dia=${n.dia}${n.consulta_id ? `&consulta=${n.consulta_id}` : ''}`)
    const para = destino[n.tipo]
    if (para) navegar(para)
  }

  const itens = dados?.itens ?? []
  const naoLidas = itens.some((i) => !i.situacao && !i.lida)

  return (
    <div ref={caixa} className="relative">
      <button type="button" onClick={() => setAberto((a) => !a)} aria-expanded={aberto}
        aria-label={contador ? `Notificações: ${contador} pedindo atenção` : 'Notificações'}
        className="relative grid size-9 place-items-center rounded-full bg-surface text-muted hover:text-text">
        <Bell className="size-4" />
        {contador > 0 && (
          <span className={`absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full px-1 text-[11px] font-semibold text-white ${
            dados?.aguardando ? 'bg-red-500' : 'bg-primary'}`}>
            {contador > 99 ? '99+' : contador}
          </span>
        )}
      </button>

      {aberto && (
        <div role="dialog" aria-label="Notificações"
          className="absolute right-0 top-11 z-50 w-[min(26rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-line bg-surface shadow-xl">
          <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
            <span className="font-semibold">Notificações</span>
            {naoLidas && (
              <button type="button" onClick={() => lidas.mutate(null)} disabled={lidas.isPending}
                className="flex items-center gap-1.5 text-xs text-muted hover:text-text">
                <CheckCheck className="size-3.5" />Marcar todas como lidas
              </button>
            )}
          </div>
          <ul className="max-h-[70vh] divide-y divide-line overflow-y-auto">
            {q.isLoading && <li className="px-4 py-6 text-center text-sm text-muted">Carregando…</li>}
            {!q.isLoading && itens.length === 0 && (
              <li className="flex flex-col items-center gap-2 px-4 py-10 text-center text-sm text-muted">
                <Bell className="size-6" />Nada pedindo atenção agora.
              </li>
            )}
            {itens.map((n) => {
              const Icone = ICONE[n.tipo]
              const urgente = n.situacao
              const apagada = !n.situacao && n.lida
              return (
                <li key={n.chave}>
                  <button type="button" onClick={() => abrir(n)}
                    className={`flex w-full gap-3 px-4 py-3 text-left hover:bg-surface-muted ${urgente ? 'bg-[#fce8e6]/50 dark:bg-[#4a2220]/40' : ''}`}>
                    <span className={`grid size-9 shrink-0 place-items-center rounded-xl ${
                      urgente ? 'bg-[#fce8e6] text-[#c0362e] dark:bg-[#4a2220] dark:text-[#f3a29b]' : 'bg-primary-soft text-primary'} ${apagada ? 'opacity-50' : ''}`}>
                      <Icone className="size-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className={`block text-sm ${apagada ? 'text-muted' : 'font-medium'}`}>{n.titulo}</span>
                      {n.texto && <span className="block truncate text-xs text-muted">{n.texto}</span>}
                      <span className="mt-0.5 block text-[11px] text-muted">{haQuanto(n.quando)}</span>
                    </span>
                    {!n.situacao && !n.lida && <span className="mt-1.5 size-2 shrink-0 rounded-full bg-primary" aria-label="não lida" />}
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      )}
      <ModalConversa card={conversa} onFechar={() => setConversa(null)} />
    </div>
  )
}
