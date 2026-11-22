import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Megaphone, Plus } from 'lucide-react'
import { useAviso } from './Aviso'
import { Botao, Campo, Entrada, Modal, Secao, Selo } from './ui'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useClinica } from '../lib/clinica'
import { dataHora } from '../lib/formato'
import { useTermos } from '../lib/termos'

type Campanha = {
  id: string; titulo: string; texto: string; publico: string; enviar_em: string; status: 'agendada' | 'cancelada'
  total: number; enviadas: number; na_fila: number; nao_enviadas: number
}
type Dados = { campanhas: Campanha[]; modelos: { id: string; titulo: string; texto: string }[]; publicos: Record<string, string> }

/** Etapa 14A (D69–D72): campanhas escritas pela clínica (Natal, Ano novo, férias…), enviadas aos poucos. */
export function Campanhas() {
  const { clinica } = useClinica()
  const { usuario } = useAuth()
  const aviso = useAviso()
  const qc = useQueryClient()
  const base = `/clinics/${clinica.id}/campanhas`
  const q = useQuery({ queryKey: ['mensagens', 'campanhas', clinica.id], queryFn: () => api.get<Dados>(base) })
  const [nova, setNova] = useState(false)
  const papel = usuario.super_admin ? 'super_admin' : usuario.clinicas.find((c) => c.clinic_id === clinica.id)?.papel
  const admin = papel === 'clinic_admin' || papel === 'super_admin'
  const cancelar = useMutation({
    mutationFn: (id: string) => api.post(`${base}/${id}/cancelar`),
    onSuccess: () => { aviso.ok('Campanha cancelada. O que ainda não saiu foi tirado da fila.'); qc.invalidateQueries({ queryKey: ['mensagens'] }) },
    onError: aviso.erro,
  })
  if (!q.data) return null
  const d = q.data

  return (
    <Secao titulo="Campanhas" icone={<Megaphone className="size-5" />} className="mb-6"
      acao={admin && <Botao onClick={() => setNova(true)}><Plus className="size-4" /> Nova campanha</Botao>}>
      {d.campanhas.length === 0 ? (
        <p className="text-sm text-muted">Nenhuma campanha ainda. Use para Natal, Ano novo, aviso de férias… As mensagens saem aos poucos para não bloquear o número.</p>
      ) : (
        <ul className="flex flex-col divide-y divide-line">
          {d.campanhas.map((c) => {
            const pct = c.total ? Math.round((c.enviadas / c.total) * 100) : 0
            return (
              <li key={c.id} className="flex flex-wrap items-center gap-x-6 gap-y-2 py-3">
                <div className="min-w-48 flex-1">
                  <div className="flex items-center gap-2 font-medium">{c.titulo}
                    {c.status === 'cancelada' ? <Selo cor="vermelho">cancelada</Selo> : c.na_fila === 0 ? <Selo cor="verde">concluída</Selo> : <Selo cor="azul">enviando</Selo>}
                  </div>
                  <p className="text-xs text-muted">{d.publicos[c.publico]} · a partir de {dataHora(c.enviar_em, clinica.timezone)}</p>
                </div>
                <div className="w-56">
                  <div className="mb-1 flex justify-between text-xs text-muted"><span>{c.enviadas} de {c.total} enviadas</span>{c.nao_enviadas > 0 && <span>{c.nao_enviadas} não enviadas</span>}</div>
                  <div role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} aria-label={`Andamento de ${c.titulo}`} className="h-2 overflow-hidden rounded-full bg-surface-muted">
                    <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
                  </div>
                </div>
                {admin && c.status === 'agendada' && c.na_fila > 0 && (
                  <Botao variante="fantasma" disabled={cancelar.isPending} onClick={() => cancelar.mutate(c.id)}>Cancelar</Botao>
                )}
              </li>
            )
          })}
        </ul>
      )}
      {nova && <NovaCampanha d={d} base={base} onFechar={() => setNova(false)} />}
    </Secao>
  )
}

function NovaCampanha({ d, base, onFechar }: { d: Dados; base: string; onFechar: () => void }) {
  const { clinica } = useClinica()
  const pal = useTermos()
  const aviso = useAviso()
  const qc = useQueryClient()
  const [f, setF] = useState({ titulo: d.modelos[0].titulo, texto: d.modelos[0].texto, publico: 'todos', quando: '' })
  const [previa, setPrevia] = useState<{ total: number; minutos: number } | null>(null)
  useEffect(() => {
    api.post<{ total: number; minutos: number }>(`${base}/previa`, { publico: f.publico }).then(setPrevia).catch(() => setPrevia(null))
  }, [base, f.publico])
  const criar = useMutation({
    mutationFn: () => api.post<{ total: number }>(base, { titulo: f.titulo, texto: f.texto, publico: f.publico, enviar_em: new Date(f.quando).toISOString() }),
    onSuccess: (r) => { aviso.ok(`Campanha criada: ${r.total} mensagens na fila.`); qc.invalidateQueries({ queryKey: ['mensagens'] }); onFechar() },
    onError: aviso.erro,
  })
  const exemplo = f.texto.split('{clinica}').join(clinica.name).split('{nome}').join('Maria')
  const valido = f.titulo.trim() && f.texto.trim() && f.quando && (previa?.total ?? 0) > 0

  return (
    <Modal titulo="Nova campanha" aberto onFechar={onFechar} largura="max-w-2xl">
      <form onSubmit={(e) => { e.preventDefault(); if (valido) criar.mutate() }} className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-2">
          {d.modelos.map((m) => (
            <button key={m.id} type="button" onClick={() => setF({ ...f, titulo: m.titulo, texto: m.texto })}
              className={`rounded-full border px-3 py-1.5 text-sm ${f.titulo === m.titulo ? 'border-primary bg-primary-soft text-primary' : 'border-line text-muted'}`}>{m.titulo}</button>
          ))}
        </div>
        <Campo rotulo="Nome da campanha"><Entrada required maxLength={80} value={f.titulo} onChange={(e) => setF({ ...f, titulo: e.target.value })} /></Campo>
        <Campo rotulo="Mensagem" ajuda={`${f.texto.length}/1000 · {nome} vira o primeiro nome do ${pal.cliente}; {clinica}, o nome da clínica.`}>
          <textarea rows={4} maxLength={1000} required value={f.texto} onChange={(e) => setF({ ...f, texto: e.target.value })}
            className="rounded-xl border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-primary" />
        </Campo>
        <div className="rounded-2xl bg-surface-muted px-4 py-3 text-sm"><span className="block text-xs font-medium text-muted">Como chega no WhatsApp</span>{exemplo}</div>
        <fieldset>
          <legend className="mb-2 text-sm font-medium">Para quem</legend>
          <div className="flex flex-col gap-2">
            {Object.entries(d.publicos).map(([v, r]) => (
              <label key={v} className="flex items-center gap-3 text-sm">
                <input type="radio" name="publico" checked={f.publico === v} onChange={() => setF({ ...f, publico: v })} className="size-4 accent-[var(--primary)]" />{r}
              </label>
            ))}
          </div>
        </fieldset>
        <Campo rotulo="Começar a enviar em"><Entrada type="datetime-local" required value={f.quando} onChange={(e) => setF({ ...f, quando: e.target.value })} /></Campo>
        <p role="status" className="text-sm text-muted">
          {previa === null ? 'Calculando…' : previa.total === 0 ? 'Ninguém recebe com esse público.'
            : `${previa.total} ${previa.total === 1 ? 'pessoa recebe' : 'pessoas recebem'}. As mensagens saem aos poucos (20 a 45 s entre uma e outra, fora do horário de silêncio): cerca de ${previa.minutos < 60 ? `${previa.minutos} min` : `${Math.round(previa.minutos / 6) / 10} h`}. Quem pediu para não receber fica de fora.`}
        </p>
        <div className="flex justify-end gap-2">
          <Botao variante="fantasma" onClick={onFechar}>Cancelar</Botao>
          <Botao type="submit" disabled={!valido || criar.isPending}>{criar.isPending ? 'Criando…' : 'Agendar campanha'}</Botao>
        </div>
      </form>
    </Modal>
  )
}
