import { useState, type DragEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Bot, Copy, Hand, Inbox, User } from 'lucide-react'
import { api, type CardCrm, type Etapa } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { dataHora, hojeYmd, horasDesde, partes, telefone, tempoParado } from '../lib/formato'
import { useCelular } from '../lib/celular'
import { useAviso } from '../components/Aviso'
import { PageHeader } from '../components/PageHeader'
import { ModalNovaConsulta, type Previa } from '../components/agenda/ModalNovaConsulta'
import { ModalConversa } from '../components/ModalConversa'
import { Botao, Modal, Selo, type CorSelo } from '../components/ui'
import { Tags } from '../components/Tratamentos'
import { useTermos } from '../lib/termos'

// Colunas provisórias (D19)
const COLUNAS: { etapa: Etapa; titulo: string; cor: CorSelo; bolinha: string }[] = [
  { etapa: 'novo_contato', titulo: 'Novo Contato', cor: 'rosa', bolinha: '#C2547A' },
  { etapa: 'agendado', titulo: 'Agendados', cor: 'verde', bolinha: '#2E9E5B' },
  { etapa: 'confirmado', titulo: 'Confirmado', cor: 'verde', bolinha: '#1F8A4C' },
  { etapa: 'cancelado', titulo: 'Cancelados', cor: 'vermelho', bolinha: '#D9473F' },
]
const PARADO_ALERTA_H = 24 // RN-PN-08

export function Crm() {
  const { clinica } = useClinica()
  const pal = useTermos()
  const aviso = useAviso()
  const [arrastando, setArrastando] = useState<CardCrm | null>(null)
  const [sobre, setSobre] = useState<Etapa | null>(null)
  const [previa, setPrevia] = useState<Previa | undefined>()
  const [cancelar, setCancelar] = useState<CardCrm | null>(null)
  const [aberto, setAberto] = useState<string | null>(null)

  const q = useQuery({ queryKey: ['kanban', clinica.id], queryFn: () => api.get<{ cards: CardCrm[] }>(`/clinics/${clinica.id}/kanban`) })

  const mover = useMutation({
    mutationFn: ({ card, etapa }: { card: CardCrm; etapa: Etapa }) => api.post(`/clinics/${clinica.id}/patients/${card.id}/stage`, { etapa }),
    onSuccess: (_, v) => aviso.ok(`${v.card.name ?? 'Contato'} movido para "${COLUNAS.find((c) => c.etapa === v.etapa)?.titulo ?? v.etapa}".`),
    onError: aviso.erro,
  })
  const confirmar = useMutation({
    mutationFn: (card: CardCrm) => api.post(`/clinics/${clinica.id}/appointments/${card.consulta_id}/status`, { status: 'confirmada' }),
    onSuccess: () => aviso.ok(`${pal.Atendimento} confirmad${pal.o}`),
    onError: aviso.erro,
  })
  const cancelarConsulta = useMutation({
    mutationFn: (card: CardCrm) => api.post(`/clinics/${clinica.id}/appointments/${card.consulta_id}/cancel`, { motivo: 'Cancelado pelo CRM' }),
    onSuccess: () => { aviso.ok(`${pal.Atendimento} cancelad${pal.o}`); setCancelar(null) },
    onError: aviso.erro,
  })

  // RN-PN-05: o que acontece ao soltar um card em cada coluna (no celular: botão "Mover para…")
  function soltar(etapa: Etapa) {
    const card = arrastando
    setArrastando(null)
    setSobre(null)
    if (card) moverPara(card, etapa)
  }
  function moverPara(card: CardCrm, etapa: Etapa) {
    if (card.crm_stage === etapa) return
    if (etapa === 'agendado') {
      setPrevia({ telefone: telefone(card.phone), nome: card.name ?? '' })
    } else if (etapa === 'confirmado') {
      if (card.consulta_id) confirmar.mutate(card)
      else aviso.erro(`Este ${pal.cliente} não tem ${pal.atendimento} futur${pal.o} para confirmar. Arraste para "Agendados" para marcar.`)
    } else if (etapa === 'cancelado' && card.consulta_id) {
      setCancelar(card)
    } else {
      mover.mutate({ card, etapa })
    }
  }

  const cards = q.data?.cards ?? []
  const celular = useCelular()
  const [movendo, setMovendo] = useState<CardCrm | null>(null)
  const modais = (
    <>
      <ModalConversa card={cards.find((c) => c.id === aberto) ?? null} onFechar={() => setAberto(null)} />
      <ModalNovaConsulta aberto={!!previa} previa={previa} onFechar={() => setPrevia(undefined)} />
      <Modal titulo={`Cancelar ${pal.atendimento}?`} aberto={!!cancelar} onFechar={() => setCancelar(null)}>
        {cancelar && (
          <>
            <p className="text-sm">
              Cancelar a consulta de <strong>{cancelar.name}</strong> ({cancelar.procedimento}, {dataHora(cancelar.proxima_consulta!, clinica.timezone)})?
              {pal.Cliente} recebe uma mensagem avisando.
            </p>
            <div className="mt-6 flex justify-end gap-2">
              <Botao variante="fantasma" onClick={() => setCancelar(null)}>Voltar</Botao>
              <Botao variante="perigo" disabled={cancelarConsulta.isPending} onClick={() => cancelarConsulta.mutate(cancelar)}>Cancelar {pal.atendimento}</Botao>
            </div>
          </>
        )}
      </Modal>
      <Modal titulo={`Mover ${movendo?.name ?? 'contato'} para…`} aberto={!!movendo} onFechar={() => setMovendo(null)}>
        {movendo && (
          <div className="flex flex-col gap-2">
            {COLUNAS.filter((c) => c.etapa !== movendo.crm_stage).map((c) => (
              <button key={c.etapa} type="button" onClick={() => { const card = movendo; setMovendo(null); moverPara(card, c.etapa) }}
                className="flex items-center gap-3 rounded-xl border border-line px-4 py-3 text-left active:bg-surface-muted">
                <span className="size-2.5 rounded-full" style={{ background: c.bolinha }} />{c.titulo}
              </button>
            ))}
          </div>
        )}
      </Modal>
    </>
  )

  if (celular) return <><CrmCelular cards={cards} carregando={q.isLoading} onAbrir={setAberto} onMover={setMovendo} />{modais}</>

  return (
    <>
      <PageHeader titulo="CRM" subtitulo="Arraste os leads entre as colunas para atualizar o status do funil" />
      <div className="flex gap-4 overflow-x-auto pb-4">
        {COLUNAS.map((col) => {
          const doCol = cards.filter((c) => c.crm_stage === col.etapa)
          return (
            <section
              key={col.etapa}
              className="flex w-80 shrink-0 flex-col"
              onDragOver={(e: DragEvent) => { e.preventDefault(); setSobre(col.etapa) }}
              onDragLeave={() => setSobre((s) => (s === col.etapa ? null : s))}
              onDrop={() => soltar(col.etapa)}
            >
              <header className="mb-3 flex items-center justify-between px-1">
                <h2 className="flex items-center gap-2 font-semibold">
                  <span className="size-2.5 rounded-full" style={{ background: col.bolinha }} />
                  {col.titulo}
                </h2>
                <span className="grid min-w-6 place-items-center rounded-full bg-surface px-2 text-sm text-muted">{doCol.length}</span>
              </header>
              <div className={`flex min-h-[60vh] flex-1 flex-col gap-3 rounded-3xl p-3 transition ${sobre === col.etapa ? 'bg-primary-soft' : 'bg-surface/60'}`}>
                {doCol.length === 0 && (
                  <div className="flex flex-col items-center gap-2 py-10 text-sm text-muted"><Inbox className="size-7 opacity-60" />Nenhum lead aqui</div>
                )}
                {doCol.map((c) => (
                  <CardLead key={c.id} card={c} cor={col.cor} titulo={col.titulo} tz={clinica.timezone}
                    onDragStart={() => setArrastando(c)} onDragEnd={() => { setArrastando(null); setSobre(null) }}
                    onAbrir={() => setAberto(c.id)} />
                ))}
              </div>
            </section>
          )
        })}
      </div>

      {modais}
    </>
  )
}

function CardLead({ card, cor, titulo, tz, onDragStart, onDragEnd, onAbrir }: {
  card: CardCrm; cor: CorSelo; titulo: string; tz: string; onDragStart: () => void; onDragEnd: () => void; onAbrir: () => void
}) {
  const clinicaId = useClinica().clinica.id
  const parado = horasDesde(card.last_activity_at) >= PARADO_ALERTA_H
  const dias = Math.floor(horasDesde(card.created_at) / 24)
  return (
    <article draggable onDragStart={onDragStart} onDragEnd={onDragEnd} onClick={onAbrir} title="Clique para ver a conversa"
      className="cursor-grab rounded-2xl bg-surface p-4 shadow-sm ring-1 ring-line active:cursor-grabbing">
      <div className="mb-3 flex flex-col items-end gap-1.5">
        {card.atendimento_manual
          ? <Selo cor="ambar"><Hand className="size-3" />Atendimento manual</Selo>
          : <Selo><Bot className="size-3" />Atendimento automático</Selo>}
        <Tags tags={card.tags} className="justify-end" />
      </div>
      <div className="flex items-center gap-3">
        {card.foto_versao
          ? <img src={`/api/clinics/${clinicaId}/patients/${card.id}/foto?v=${card.foto_versao}`} alt="" className="size-9 shrink-0 rounded-full object-cover" />
          : <span className="grid size-9 shrink-0 place-items-center rounded-full bg-primary-soft text-primary"><User className="size-4" /></span>}
        <div className="min-w-0">
          <div className="truncate font-semibold">{card.name ?? 'Sem nome'}</div>
          <div className="text-xs text-muted">{telefone(card.phone)}</div>
        </div>
      </div>
      {card.procedimento && (
        <p className="mt-2 text-sm text-muted">{card.procedimento} · {dataHora(card.proxima_consulta!, tz)}</p>
      )}
      <div className="mt-3 border-t border-line pt-3">
        <div className="flex items-center justify-between">
          <Selo cor={cor}>{titulo}</Selo>
          <span className="text-xs text-muted" title="Tempo desde o primeiro contato">⏱ {dias}d</span>
        </div>
        {parado && <Selo cor="vermelho" className="mt-1.5">Parado {tempoParado(card.last_activity_at)}</Selo>}
        <button type="button" onClick={(e) => { e.stopPropagation(); navigator.clipboard?.writeText(card.last_event) }} title="Copiar último evento"
          className="mt-1.5 flex items-center gap-1 rounded bg-surface-muted px-1.5 py-0.5 font-mono text-[11px] text-muted hover:text-text">
          {card.last_event}<Copy className="size-3" />
        </button>
      </div>
    </article>
  )
}

/** Etapa 33: CRM no celular — só o nome e o status de cada contato, filtro "Hoje" já ligado.
 *  Tocar no nome abre a conversa; tocar no status abre "Mover para…" (no lugar de arrastar). */
function CrmCelular({ cards, carregando, onAbrir, onMover }: {
  cards: CardCrm[]; carregando: boolean; onAbrir: (id: string) => void; onMover: (c: CardCrm) => void
}) {
  const { clinica } = useClinica()
  const tz = clinica.timezone
  const [soHoje, setSoHoje] = useState(true)
  const hoje = hojeYmd(tz)
  // "Hoje" = consulta marcada para hoje ou conversa/movimento hoje
  const ehDeHoje = (c: CardCrm) =>
    (!!c.proxima_consulta && partes(c.proxima_consulta, tz).ymd === hoje) || partes(c.last_activity_at, tz).ymd === hoje
  const ordem = (c: CardCrm) => COLUNAS.findIndex((x) => x.etapa === c.crm_stage)
  const lista = (soHoje ? cards.filter(ehDeHoje) : cards).slice().sort((a, b) => ordem(a) - ordem(b))

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight">CRM</h1>
        <div className="flex rounded-xl bg-surface p-1 text-sm" role="group" aria-label="Período">
          {([true, false] as const).map((v) => (
            <button key={String(v)} type="button" onClick={() => setSoHoje(v)} aria-pressed={soHoje === v}
              className={`rounded-lg px-3 py-1.5 ${soHoje === v ? 'bg-primary text-primary-contrast' : 'text-muted'}`}>
              {v ? 'Hoje' : 'Todos'}
            </button>
          ))}
        </div>
      </div>
      {carregando && <p className="py-8 text-center text-sm text-muted">Carregando…</p>}
      {!carregando && lista.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-12 text-center text-sm text-muted">
          <Inbox className="size-7 opacity-60" />
          {soHoje ? <>Nenhum contato hoje.<button type="button" className="text-primary" onClick={() => setSoHoje(false)}>Ver todos</button></> : 'Nenhum lead aqui'}
        </div>
      )}
      <ul className="flex flex-col divide-y divide-line rounded-2xl bg-surface">
        {lista.map((c) => {
          const col = COLUNAS.find((x) => x.etapa === c.crm_stage)!
          return (
            <li key={c.id} className="flex items-center gap-3 px-4 py-3">
              <button type="button" onClick={() => onAbrir(c.id)}
                className={`min-w-0 flex-1 truncate text-left font-medium ${c.name ? '' : 'text-muted'}`}>
                {c.name ?? telefone(c.phone)}
              </button>
              <button type="button" onClick={() => onMover(c)} aria-label={`Status: ${col.titulo}. Tocar para mover`}>
                <Selo cor={col.cor}>{col.titulo}</Selo>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
