import { useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CalendarCheck, CalendarClock, Cake, Hand, Hourglass, Send, X } from 'lucide-react'
import { api, type CardCrm, type Consulta, type Dashboard as Dados } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { dataCurta, hora, telefone, tempoParado } from '../lib/formato'
import { PageHeader } from '../components/PageHeader'
import { ModalConsulta } from '../components/agenda/ModalConsulta'
import { ModalConversa } from '../components/ModalConversa'
import { TIPO_MENSAGEM } from '../components/tipoMensagem'
import { SeloStatus } from '../components/agenda/status'
import { Selo, Secao, Vazio } from '../components/ui'

type Detalhe = 'consultas' | 'confirmacao' | 'esperando' | 'parados' | 'fila'
type Contato = Pick<CardCrm, 'id' | 'name' | 'phone'>

export function Dashboard() {
  const { clinica } = useClinica()
  const tz = clinica.timezone
  const [aberta, setAberta] = useState<Consulta | null>(null)
  const [conversa, setConversa] = useState<Contato | null>(null)
  const [detalhe, setDetalhe] = useState<Detalhe | null>(null)
  const q = useQuery({ queryKey: ['dashboard', clinica.id], queryFn: () => api.get<Dados>(`/clinics/${clinica.id}/dashboard`) })
  const d = q.data

  const alternar = (qual: Detalhe) => setDetalhe((atual) => (atual === qual ? null : qual))
  const card = (qual: Detalhe) => ({ ativo: detalhe === qual, onClick: () => alternar(qual) })

  const listaConsultas = (lista: Consulta[], vazio: string) =>
    !lista.length ? (
      <Vazio icone={<CalendarClock className="size-8" />} texto={vazio} />
    ) : (
      <ul className="divide-y divide-line">
        {lista.map((c) => (
          <li key={c.id}>
            <button type="button" onClick={() => setAberta(c)} className="flex w-full items-center gap-4 py-3 text-left hover:bg-surface-muted/50">
              <span className="w-14 font-semibold">{hora(c.starts_at, tz)}</span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{c.paciente}</span>
                <span className="block truncate text-sm text-muted">{c.procedimento} · {c.profissional}</span>
              </span>
              <SeloStatus status={c.status} />
            </button>
          </li>
        ))}
      </ul>
    )

  function conteudoDetalhe(): { titulo: string; icone: ReactNode; corpo: ReactNode } | null {
    if (!d || !detalhe) return null
    switch (detalhe) {
      case 'consultas':
        return { titulo: 'Consultas de hoje', icone: <CalendarClock className="size-5" />, corpo: listaConsultas(d.consultas_hoje, 'Nenhuma consulta hoje.') }
      case 'confirmacao': {
        const confirmadas = d.consultas_hoje.filter((c) => c.status === 'confirmada' || c.status === 'realizada')
        const pendentes = d.consultas_hoje.filter((c) => c.status === 'agendada')
        return {
          titulo: 'Confirmadas × pendentes',
          icone: <CalendarCheck className="size-5" />,
          corpo: (
            <div className="grid gap-6 lg:grid-cols-2">
              <div>
                <h3 className="mb-1 text-sm font-semibold text-muted">Confirmadas ({confirmadas.length})</h3>
                {listaConsultas(confirmadas, 'Nenhuma confirmada ainda.')}
              </div>
              <div>
                <h3 className="mb-1 text-sm font-semibold text-muted">Pendentes de confirmação ({pendentes.length})</h3>
                {listaConsultas(pendentes, 'Nenhuma pendente.')}
              </div>
            </div>
          ),
        }
      }
      case 'esperando':
        return {
          titulo: 'Esperando uma pessoa',
          icone: <Hand className="size-5" />,
          corpo: !d.esperando.length ? (
            <Vazio icone={<Hand className="size-8" />} texto="Ninguém esperando atendimento." />
          ) : (
            <Lista>
              {d.esperando.map((e) => (
                <Linha key={e.id} onClick={() => setConversa(e)}
                  titulo={e.name ?? telefone(e.phone)}
                  sub={e.ultima_mensagem ?? telefone(e.phone)}
                  lado={<><Selo>{e.channel === 'web' ? 'Chat web' : 'WhatsApp'}</Selo><span className="text-xs text-muted">{tempoParado(e.last_message_at)}</span></>} />
              ))}
            </Lista>
          ),
        }
      case 'parados':
        return {
          titulo: 'Leads parados há mais de 24h',
          icone: <Hourglass className="size-5" />,
          corpo: !d.parados.length ? (
            <Vazio icone={<Hourglass className="size-8" />} texto="Nenhum lead parado." />
          ) : (
            <Lista>
              {d.parados.map((p) => (
                <Linha key={p.id} onClick={() => setConversa(p)}
                  titulo={p.name ?? telefone(p.phone)}
                  sub={p.last_event}
                  lado={<span className="text-xs text-muted">{tempoParado(p.last_activity_at)}</span>} />
              ))}
            </Lista>
          ),
        }
      case 'fila':
        return {
          titulo: 'Mensagens na fila',
          icone: <Send className="size-5" />,
          corpo: !d.fila.length ? (
            <Vazio icone={<Send className="size-8" />} texto="Nenhuma mensagem esperando para sair." />
          ) : (
            <Lista>
              {d.fila.map((m) => {
                const [rotulo, cor] = TIPO_MENSAGEM[m.kind]
                return (
                  <li key={m.id} className="flex items-start gap-4 py-3">
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <Selo cor={cor} className="uppercase tracking-wide">{rotulo}</Selo>
                        <span className="truncate font-medium">{m.paciente ?? telefone(m.phone)}</span>
                      </span>
                      <span className="mt-1 block line-clamp-2 text-sm text-muted">{m.body}</span>
                      {m.error && <span className="mt-1 block text-xs text-[#c0362e]">Tentativa {m.attempts}: {m.error}</span>}
                    </span>
                    <span className="shrink-0 text-xs text-muted">{dataCurta(m.scheduled_for, tz)}, {hora(m.scheduled_for, tz)}</span>
                  </li>
                )
              })}
            </Lista>
          ),
        }
    }
  }

  const aberto = conteudoDetalhe()
  const limite = (lista: unknown[], total: number) =>
    total > lista.length ? <p className="mt-3 text-xs text-muted">Mostrando {lista.length} de {total}.</p> : null

  return (
    <>
      <PageHeader titulo="Dashboard" subtitulo="Resumo do dia da clínica" />
      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Indicador {...card('consultas')} icone={<CalendarClock />} rotulo="Consultas hoje" valor={d?.consultas_hoje.length} />
        <Indicador {...card('confirmacao')} icone={<CalendarCheck />} rotulo="Confirmadas × pendentes" valor={d ? `${d.confirmadas} × ${d.pendentes}` : undefined} />
        <Indicador {...card('esperando')} icone={<Hand />} rotulo="Esperando uma pessoa" valor={d?.precisando_humano} alerta={!!d?.precisando_humano} />
        <Indicador {...card('parados')} icone={<Hourglass />} rotulo="Leads parados +24h" valor={d?.leads_parados} alerta={!!d?.leads_parados} />
        <Indicador {...card('fila')} icone={<Send />} rotulo="Mensagens na fila" valor={d?.mensagens_na_fila} />
      </div>

      {aberto && d && (
        <Secao titulo={aberto.titulo} icone={aberto.icone} className="mb-6"
          acao={
            <button type="button" onClick={() => setDetalhe(null)} aria-label="Fechar detalhes"
              className="grid size-9 place-items-center rounded-xl text-muted hover:bg-surface-muted hover:text-text">
              <X className="size-5" />
            </button>
          }>
          {aberto.corpo}
          {detalhe === 'esperando' && limite(d.esperando, d.precisando_humano)}
          {detalhe === 'parados' && limite(d.parados, d.leads_parados)}
          {detalhe === 'fila' && limite(d.fila, d.mensagens_na_fila)}
        </Secao>
      )}

      <div className="grid gap-6 xl:grid-cols-[2fr_1fr]">
        <Secao titulo="Consultas de hoje" icone={<CalendarClock className="size-5" />}>
          {listaConsultas(d?.consultas_hoje ?? [], 'Nenhuma consulta hoje.')}
        </Secao>
        <Secao titulo="Aniversariantes do dia" icone={<Cake className="size-5" />}>
          {!d?.aniversariantes.length ? (
            <Vazio icone={<Cake className="size-8" />} texto="Ninguém faz aniversário hoje." />
          ) : (
            <ul className="space-y-2">
              {d.aniversariantes.map((a) => (
                <li key={a.id} className="flex items-center justify-between text-sm">
                  <span className="font-medium">🎂 {a.name}</span>
                  <span className="text-muted">{telefone(a.phone)}</span>
                </li>
              ))}
            </ul>
          )}
        </Secao>
      </div>
      <ModalConsulta consulta={aberta} onFechar={() => setAberta(null)} />
      <ModalConversa card={conversa} onFechar={() => setConversa(null)} />
    </>
  )
}

function Lista({ children }: { children: ReactNode }) {
  return <ul className="divide-y divide-line">{children}</ul>
}

function Linha({ titulo, sub, lado, onClick }: { titulo: string; sub: string; lado: ReactNode; onClick: () => void }) {
  return (
    <li>
      <button type="button" onClick={onClick} className="flex w-full items-center gap-4 py-3 text-left hover:bg-surface-muted/50">
        <span className="min-w-0 flex-1">
          <span className="block truncate font-medium">{titulo}</span>
          <span className="block truncate text-sm text-muted">{sub}</span>
        </span>
        <span className="flex shrink-0 items-center gap-2">{lado}</span>
      </button>
    </li>
  )
}

function Indicador({ icone, rotulo, valor, alerta, ativo, onClick }: {
  icone: ReactNode; rotulo: string; valor?: number | string; alerta?: boolean; ativo: boolean; onClick: () => void
}) {
  return (
    <button type="button" onClick={onClick} aria-pressed={ativo} aria-label={`${rotulo}: ver detalhes`}
      className={`rounded-3xl bg-surface p-5 text-left transition hover:-translate-y-0.5 hover:shadow-md focus-visible:outline-2 focus-visible:outline-primary ${ativo ? 'ring-2 ring-primary' : ''}`}>
      <span className={`mb-3 grid size-10 place-items-center rounded-xl [&>svg]:size-5 ${alerta ? 'bg-[#fce8e6] text-[#c0362e]' : 'bg-primary-soft text-primary'}`}>{icone}</span>
      <div className="text-2xl font-bold">{valor ?? '—'}</div>
      <div className="text-sm text-muted">{rotulo}</div>
    </button>
  )
}
