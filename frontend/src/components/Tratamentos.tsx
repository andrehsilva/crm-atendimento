import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, BellOff, CheckCircle2, CreditCard, Pause, Play, Plus, Sparkles, Stethoscope, Repeat, UserPlus, Wallet, XCircle } from 'lucide-react'
import { api, type MotivoEspera, type TagCliente, type Tratamento, type TratamentosPaciente } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { dataCurta, hora } from '../lib/formato'
import { useAviso } from './Aviso'
import { Botao, Campo, Entrada, Modal, Selo, Seletor, type CorSelo } from './ui'

const MOTIVOS: Record<MotivoEspera, string> = { protetico: 'Protético', exame: 'Exame', cicatrizacao: 'Cicatrização', outro: 'Outro motivo' }

const COR_TAG: Record<TagCliente['codigo'], CorSelo> = {
  novo: 'azul', recorrente: 'roxo', em_tratamento: 'verde', aguardando: 'ambar', particular: 'cinza', convenio: 'rosa',
}
const ICONE_TAG = { novo: UserPlus, recorrente: Repeat, em_tratamento: Play, aguardando: Pause, particular: Wallet, convenio: CreditCard }

/** Etapa 21 (D90): tags automáticas — Novo · Recorrente · Em tratamento · Aguardando. */
export function Tags({ tags, className = '' }: { tags: TagCliente[] | undefined; className?: string }) {
  if (!tags?.length) return null
  return (
    <span className={`inline-flex flex-wrap gap-1 ${className}`}>
      {tags.map((t) => {
        const Icone = ICONE_TAG[t.codigo]
        return <Selo key={t.codigo + (t.procedimento ?? '')} cor={COR_TAG[t.codigo]}><Icone className="size-3" />{t.rotulo}</Selo>
      })}
    </span>
  )
}

const ISO = (d: Date) => d.toISOString().slice(0, 10)
const diaSemana = (iso: string, tz: string) =>
  new Intl.DateTimeFormat('pt-BR', { weekday: 'long', timeZone: tz }).format(new Date(iso)).replace('-feira', '')
const emMeses = (m: number) => { const d = new Date(); d.setMonth(d.getMonth() + m); return ISO(d) }

/** Etapa 21 (RN-TR): tratamentos do paciente — abrir, pôr em espera, retomar e encerrar. */
export function PainelTratamentos({ pacienteId, compacto = false }: { pacienteId: string; compacto?: boolean }) {
  const { clinica, cadastros } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const tz = clinica.timezone
  const chave = ['tratamentos', clinica.id, pacienteId]
  const q = useQuery({ queryKey: chave, queryFn: () => api.get<TratamentosPaciente>(`/clinics/${clinica.id}/patients/${pacienteId}/tratamentos`) })
  const [novo, setNovo] = useState(false)
  const [espera, setEspera] = useState<Tratamento | null>(null)
  const [retomar, setRetomar] = useState<Tratamento | null>(null)
  const [encerrar, setEncerrar] = useState<Tratamento | null>(null)

  const depois = (r: TratamentosPaciente, msg: string) => {
    qc.setQueryData(chave, r)
    qc.invalidateQueries({ queryKey: ['pacientes'] })
    qc.invalidateQueries({ queryKey: ['kanban'] })
    aviso.ok(msg)
  }

  const editar = useMutation({
    mutationFn: ({ t, dados }: { t: Tratamento; dados: Record<string, unknown>; msg: string }) =>
      api.patch<TratamentosPaciente>(`/clinics/${clinica.id}/tratamentos/${t.id}`, dados),
    onSuccess: (r, v) => { depois(r, v.msg); qc.invalidateQueries({ queryKey: ['mensagens'] }) },
    onError: aviso.erro,
  })

  const lista = q.data?.tratamentos ?? []
  const abertos = lista.filter((t) => t.status === 'em_andamento' || t.status === 'aguardando')
  const encerrados = lista.filter((t) => !abertos.includes(t))

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-sm font-semibold"><Stethoscope className="size-4 text-primary" />Tratamentos</span>
        <Botao variante="fantasma" className="!px-2 !py-1 text-xs" onClick={() => setNovo(true)}><Plus className="size-3.5" />Abrir tratamento</Botao>
      </div>
      {q.isLoading && <p className="text-sm text-muted">Carregando…</p>}
      {!q.isLoading && abertos.length === 0 && (
        <p className="text-sm text-muted">Nenhum tratamento em andamento. Abra um quando o paciente precisar voltar várias vezes.</p>
      )}
      {abertos.map((t) => (
        <div key={t.id} className={`rounded-2xl border p-3 ${t.status === 'aguardando' ? 'border-[#f0c86e] bg-[#fcf1dc]/40 dark:bg-[#43341a]/30' : 'border-line'}`}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="font-medium">{t.procedimento}{t.profissional && <span className="font-normal text-muted"> · {t.profissional}</span>}</div>
              <div className="text-xs text-muted">
                {t.realizadas}{t.sessoes_previstas ? ` de ${t.sessoes_previstas}` : ''} sessões feitas
                {t.intervalo_dias ? ` · a cada ${t.intervalo_dias} dias` : ''}
                {t.proxima_sessao ? ` · próxima ${dataCurta(t.proxima_sessao, tz)} ${hora(t.proxima_sessao, tz)}` : ''}
              </div>
              <div className="mt-1 flex flex-wrap gap-1">
                {t.horario_fixo && t.serie_ate && (
                  <Selo cor="azul"><Repeat className="size-3" />Horário fixo · {diaSemana(t.serie_ate, tz)} {hora(t.serie_ate, tz)}{t.intervalo_dias === 14 ? ' (quinzenal)' : ''}</Selo>
                )}
                {!t.avisos_paciente && <Selo cor="cinza"><BellOff className="size-3" />Sem lembrete</Selo>}
              </div>
            </div>
            {t.status === 'aguardando'
              ? <Selo cor="ambar"><Pause className="size-3" />Aguardando {t.motivo_espera === 'outro' ? (t.motivo_texto ?? 'outro motivo') : MOTIVOS[t.motivo_espera!].toLowerCase()}
                {t.previsao && ` · previsão ${t.previsao.split('-').reverse().slice(0, 2).join('/')}`}</Selo>
              : <Selo cor="verde"><Play className="size-3" />Em andamento</Selo>}
          </div>
          {t.orientacao && (
            <p className="mt-2 flex gap-1.5 text-xs text-muted"><Sparkles className="mt-0.5 size-3 shrink-0" />Recado para a assistente: {t.orientacao}</p>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            {t.status === 'aguardando'
              ? <Botao className="!py-1.5 text-xs" onClick={() => setRetomar(t)}><Play className="size-3.5" />Retomar</Botao>
              : <Botao variante="secundario" className="!py-1.5 text-xs" onClick={() => setEspera(t)}><Pause className="size-3.5" />Aguardar</Botao>}
            <Botao variante="secundario" className="!py-1.5 text-xs" onClick={() => setEncerrar(t)}><CheckCircle2 className="size-3.5" />Encerrar</Botao>
            <Botao variante="fantasma" className="!py-1.5 text-xs" disabled={editar.isPending}
              onClick={() => editar.mutate({ t, dados: { avisos_paciente: !t.avisos_paciente },
                msg: t.avisos_paciente ? 'Lembretes desligados: as sessões deste tratamento não geram mais mensagens automáticas.' : 'Lembretes ligados para as próximas sessões.' })}>
              {t.avisos_paciente ? <><BellOff className="size-3.5" />Desligar lembrete</> : <><Bell className="size-3.5" />Ligar lembrete</>}
            </Botao>
            {t.horario_fixo && (
              <Botao variante="fantasma" className="!py-1.5 text-xs" disabled={editar.isPending}
                onClick={() => editar.mutate({ t, dados: { horario_fixo: false },
                  msg: 'Horário fixo desligado: as sessões já marcadas continuam, mas nenhuma nova é acrescentada.' })}>
                <XCircle className="size-3.5" />Parar horário fixo
              </Botao>
            )}
          </div>
        </div>
      ))}
      {!compacto && encerrados.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer text-muted">Encerrados ({encerrados.length})</summary>
          <ul className="mt-2 space-y-1 text-muted">
            {encerrados.map((t) => (
              <li key={t.id} className="flex items-center gap-2">
                {t.status === 'concluido' ? <CheckCircle2 className="size-3.5 text-[#1f7a43]" /> : <XCircle className="size-3.5" />}
                {t.procedimento} — {t.status === 'concluido' ? 'concluído' : 'interrompido'} em {dataCurta(t.status_desde, tz)}
                {t.volta_em && ` · volta em ${t.volta_em.split('-').reverse().join('/')}`}
              </li>
            ))}
          </ul>
        </details>
      )}

      <ModalNovo aberto={novo} onFechar={() => setNovo(false)} pacienteId={pacienteId}
        procedimentos={cadastros.procedimentos} avisosPadrao={q.data?.avisos_padrao ?? true}
        onFeito={(r) => {
          setNovo(false)
          const s = r.serie
          let msg = 'Tratamento aberto.'
          if (s) {
            msg = `Tratamento aberto com ${s.marcadas} ${s.marcadas === 1 ? 'sessão marcada' : 'sessões marcadas'}.`
            if (s.falhas.length) msg += ` Não couberam: ${s.falhas.map((x) => `${dataCurta(x.inicio, tz)} (${x.motivo})`).join('; ')}`
            qc.invalidateQueries({ queryKey: ['agenda'] })
          }
          depois(r, msg)
        }} />
      <ModalEspera t={espera} onFechar={() => setEspera(null)} onFeito={(r) => { setEspera(null); depois(r, 'Tratamento em espera: a assistente não marca a próxima sessão.') }} />
      <ModalRetomar t={retomar} onFechar={() => setRetomar(null)} onFeito={(r, avisou) => {
        setRetomar(null)
        depois(r, avisou ? 'Tratamento retomado. O paciente vai receber a mensagem para marcar.' : 'Tratamento retomado.')
        if (avisou) qc.invalidateQueries({ queryKey: ['mensagens'] })
      }} />
      <ModalEncerrar t={encerrar} onFechar={() => setEncerrar(null)} onFeito={(r, s) => { setEncerrar(null); depois(r, s === 'concluido' ? 'Tratamento concluído.' : 'Tratamento interrompido.') }} />
    </div>
  )
}

type ModoSessoes = 'nao' | 'fixo' | 'numero'

function ModalNovo({ aberto, onFechar, pacienteId, procedimentos, avisosPadrao, onFeito }: {
  aberto: boolean; onFechar: () => void; pacienteId: string
  procedimentos: { id: string; name: string }[]
  avisosPadrao: boolean
  onFeito: (r: TratamentosPaciente) => void
}) {
  const { clinica, cadastros } = useClinica()
  const aviso = useAviso()
  const vazio = { service_id: '', professional_id: '', sessoes: '', orientacao: '', modo: 'nao' as ModoSessoes,
    data: '', hora: '', intervalo: '7', quantas: '8', avisos: null as boolean | null }
  const [f, setF] = useState(vazio)
  const avisos = f.avisos ?? avisosPadrao
  const marcar = f.modo !== 'nao'
  const profissionais = cadastros.profissionais.filter((p) => !f.service_id || p.service_ids.includes(f.service_id))
  const quantas = Number(f.quantas)
  const valido = !!f.service_id && (!marcar || (!!f.professional_id && !!f.data && !!f.hora
    && (f.modo === 'fixo' || (quantas >= 2 && quantas <= 20))))
  const criar = useMutation({
    mutationFn: () => api.post<TratamentosPaciente>(`/clinics/${clinica.id}/patients/${pacienteId}/tratamentos`, {
      service_id: f.service_id, professional_id: f.professional_id || null,
      sessoes_previstas: !marcar && f.sessoes ? Number(f.sessoes) : null,
      intervalo_dias: marcar ? Number(f.intervalo) : null,
      orientacao: f.orientacao.trim() || null, avisos_paciente: avisos,
      serie: marcar ? { inicio: `${f.data}T${f.hora}:00`, sessoes: f.modo === 'numero' ? quantas : null } : null,
    }),
    onSuccess: (r) => { setF(vazio); onFeito(r) },
    onError: aviso.erro,
  })
  const enviar = (e: FormEvent) => { e.preventDefault(); if (valido) criar.mutate() }
  return (
    <Modal titulo="Abrir tratamento" aberto={aberto} onFechar={onFechar}>
      <form onSubmit={enviar} className="grid gap-4">
        <Campo rotulo="Procedimento">
          <Seletor value={f.service_id} onChange={(e) => setF({ ...f, service_id: e.target.value, professional_id: '' })} required>
            <option value="">Escolha…</option>
            {procedimentos.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </Seletor>
        </Campo>
        <Campo rotulo={marcar ? 'Profissional' : 'Profissional (opcional)'}>
          <Seletor value={f.professional_id} onChange={(e) => setF({ ...f, professional_id: e.target.value })} required={marcar}>
            <option value="">{marcar ? 'Escolha…' : 'Qualquer um'}</option>
            {profissionais.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </Seletor>
        </Campo>
        <Campo rotulo="Já marcar as sessões na agenda?">
          <Seletor value={f.modo} onChange={(e) => setF({ ...f, modo: e.target.value as ModoSessoes })}>
            <option value="nao">Não, marco depois</option>
            <option value="fixo">Horário fixo, sem data para terminar</option>
            <option value="numero">Um número de sessões</option>
          </Seletor>
        </Campo>
        {marcar ? (
          <div className="grid gap-3 rounded-2xl bg-surface-muted p-3">
            <div className="grid grid-cols-2 gap-3">
              <Campo rotulo="Primeira sessão">
                <Entrada type="date" value={f.data} min={ISO(new Date())} required onChange={(e) => setF({ ...f, data: e.target.value })} />
              </Campo>
              <Campo rotulo="Horário">
                <Entrada type="time" value={f.hora} step={300} required onChange={(e) => setF({ ...f, hora: e.target.value })} />
              </Campo>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Campo rotulo="Repetir">
                <Seletor value={f.intervalo} onChange={(e) => setF({ ...f, intervalo: e.target.value })}>
                  <option value="7">Toda semana</option>
                  <option value="14">A cada 2 semanas</option>
                </Seletor>
              </Campo>
              {f.modo === 'numero' && (
                <Campo rotulo="Quantas sessões">
                  <Entrada type="number" min={2} max={20} value={f.quantas} onChange={(e) => setF({ ...f, quantas: e.target.value })} />
                </Campo>
              )}
            </div>
            <p className="text-xs text-muted">
              {f.modo === 'fixo'
                ? <>O sistema deixa sempre as <b>próximas 8 sessões</b> marcadas e acrescenta mais uma a cada semana enquanto o tratamento estiver em andamento. Ao encerrar, as sessões futuras saem da agenda.</>
                : 'Cada data passa pelas regras da agenda; as que não couberem (feriado, horário ocupado…) aparecem no aviso.'}
            </p>
          </div>
        ) : (
          <Campo rotulo="Quantas sessões (opcional)">
            <Entrada type="number" min={1} max={100} value={f.sessoes} placeholder="Ex.: 4" onChange={(e) => setF({ ...f, sessoes: e.target.value })} />
          </Campo>
        )}
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" className="mt-0.5" checked={avisos} onChange={(e) => setF({ ...f, avisos: e.target.checked })} />
          <span>
            A assistente manda confirmação e lembrete no dia anterior
            <span className="block text-xs text-muted">
              {avisos ? 'Bom para quem costuma esquecer (ex.: odontologia).' : 'Sem mensagens automáticas das sessões: a agenda fica por conta do paciente (ex.: psicanálise). Remarcações e cancelamentos continuam sendo avisados.'}
            </span>
          </span>
        </label>
        <Campo rotulo="Recado para a assistente (opcional)" ajuda={`${f.orientacao.length}/300`}>
          <textarea value={f.orientacao} maxLength={300} rows={2} placeholder="Ex.: não marcar antes de 10 dias da extração"
            onChange={(e) => setF({ ...f, orientacao: e.target.value })}
            className="rounded-xl border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-primary" />
        </Campo>
        <div className="flex justify-end gap-2">
          <Botao variante="fantasma" onClick={onFechar}>Voltar</Botao>
          <Botao type="submit" disabled={!valido || criar.isPending}>{criar.isPending ? 'Abrindo…' : 'Abrir'}</Botao>
        </div>
      </form>
    </Modal>
  )
}

function ModalEspera({ t, onFechar, onFeito }: { t: Tratamento | null; onFechar: () => void; onFeito: (r: TratamentosPaciente) => void }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const [motivo, setMotivo] = useState<MotivoEspera>('protetico')
  const [texto, setTexto] = useState('')
  const [previsao, setPrevisao] = useState('')
  const salvar = useMutation({
    mutationFn: () => api.post<TratamentosPaciente>(`/clinics/${clinica.id}/tratamentos/${t!.id}/aguardar`,
      { motivo, motivo_texto: motivo === 'outro' ? texto.trim() || null : null, previsao: previsao || null }),
    onSuccess: (r) => { setTexto(''); setPrevisao(''); onFeito(r) },
    onError: aviso.erro,
  })
  return (
    <Modal titulo={`Aguardar · ${t?.procedimento ?? ''}`} aberto={!!t} onFechar={onFechar}>
      <div className="grid gap-4">
        <Campo rotulo="Aguardando o quê?">
          <Seletor value={motivo} onChange={(e) => setMotivo(e.target.value as MotivoEspera)}>
            {Object.entries(MOTIVOS).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
          </Seletor>
        </Campo>
        {motivo === 'outro' && (
          <Campo rotulo="Qual?"><Entrada value={texto} maxLength={120} onChange={(e) => setTexto(e.target.value)} placeholder="Ex.: resultado da tomografia" /></Campo>
        )}
        <Campo rotulo="Previsão (opcional)" ajuda="Se passar dessa data, o sino avisa a equipe. O paciente não recebe nada sozinho.">
          <Entrada type="date" value={previsao} min={ISO(new Date())} onChange={(e) => setPrevisao(e.target.value)} />
        </Campo>
        <p className="rounded-2xl bg-surface-muted px-4 py-3 text-sm text-muted">
          Enquanto aguarda, a assistente <b>não marca</b> a próxima sessão deste tratamento. Se o paciente pedir, ela explica e avisa a equipe. Outros procedimentos seguem normais.
        </p>
        <div className="flex justify-end gap-2">
          <Botao variante="fantasma" onClick={onFechar}>Voltar</Botao>
          <Botao onClick={() => salvar.mutate()} disabled={salvar.isPending || (motivo === 'outro' && !texto.trim())}><Pause className="size-4" />Pôr em espera</Botao>
        </div>
      </div>
    </Modal>
  )
}

function ModalRetomar({ t, onFechar, onFeito }: { t: Tratamento | null; onFechar: () => void; onFeito: (r: TratamentosPaciente, avisou: boolean) => void }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const [texto, setTexto] = useState<string | null>(null)
  const [avisar, setAvisar] = useState(true)
  const previa = useQuery({
    queryKey: ['tratamento', 'retomar', t?.id],
    queryFn: () => api.get<{ texto: string; tem_whatsapp: boolean }>(`/clinics/${clinica.id}/tratamentos/${t!.id}/retomar`),
    enabled: !!t,
  })
  const valor = texto ?? previa.data?.texto ?? ''
  const podeAvisar = previa.data?.tem_whatsapp ?? false
  const salvar = useMutation({
    mutationFn: () => api.post<TratamentosPaciente>(`/clinics/${clinica.id}/tratamentos/${t!.id}/retomar`,
      { texto: valor, avisar_paciente: avisar && podeAvisar }),
    onSuccess: (r) => { setTexto(null); onFeito(r, avisar && podeAvisar) },
    onError: aviso.erro,
  })
  return (
    <Modal titulo={`Retomar · ${t?.procedimento ?? ''}`} aberto={!!t} onFechar={() => { setTexto(null); onFechar() }}>
      <div className="grid gap-4">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={avisar && podeAvisar} disabled={!podeAvisar} onChange={(e) => setAvisar(e.target.checked)} />
          Mandar mensagem pelo WhatsApp convidando a marcar a próxima sessão
        </label>
        {!podeAvisar && previa.data && <p className="text-xs text-muted">A clínica não tem WhatsApp ligado: o tratamento volta a andar, mas ninguém é avisado.</p>}
        {avisar && podeAvisar && (
          <Campo rotulo="Mensagem" ajuda={`${valor.length}/1000 · Quando o paciente responder, a assistente marca a sessão.`}>
            <textarea value={valor} maxLength={1000} rows={4} onChange={(e) => setTexto(e.target.value)}
              className="rounded-xl border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-primary" />
          </Campo>
        )}
        <div className="flex justify-end gap-2">
          <Botao variante="fantasma" onClick={onFechar}>Voltar</Botao>
          <Botao onClick={() => salvar.mutate()} disabled={salvar.isPending || (avisar && podeAvisar && !valor.trim())}><Play className="size-4" />Retomar</Botao>
        </div>
      </div>
    </Modal>
  )
}

function ModalEncerrar({ t, onFechar, onFeito }: { t: Tratamento | null; onFechar: () => void; onFeito: (r: TratamentosPaciente, s: string) => void }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const [status, setStatus] = useState<'concluido' | 'interrompido'>('concluido')
  const [volta, setVolta] = useState(emMeses(6))
  const salvar = useMutation({
    mutationFn: () => api.post<TratamentosPaciente>(`/clinics/${clinica.id}/tratamentos/${t!.id}/encerrar`,
      { status, volta_em: status === 'concluido' && volta ? volta : null }),
    onSuccess: (r) => onFeito(r, status),
    onError: aviso.erro,
  })
  return (
    <Modal titulo={`Encerrar · ${t?.procedimento ?? ''}`} aberto={!!t} onFechar={onFechar}>
      <div className="grid gap-4">
        <Campo rotulo="Como terminou?">
          <Seletor value={status} onChange={(e) => setStatus(e.target.value as 'concluido' | 'interrompido')}>
            <option value="concluido">Concluído</option>
            <option value="interrompido">Interrompido (desistiu, mudou de plano…)</option>
          </Seletor>
        </Campo>
        {status === 'concluido' && (
          <Campo rotulo="Volta em" ajuda="Nessa data o paciente aparece no relatório de recall (chamar de volta).">
            <div className="flex flex-wrap gap-2">
              {[3, 6, 12].map((m) => (
                <Botao key={m} variante={volta === emMeses(m) ? 'primario' : 'secundario'} className="!py-1.5 text-xs" onClick={() => setVolta(emMeses(m))}>{m} meses</Botao>
              ))}
              <Entrada type="date" value={volta} onChange={(e) => setVolta(e.target.value)} className="!py-1.5" />
            </div>
          </Campo>
        )}
        <p className="text-xs text-muted">Encerrado não reabre: se o paciente precisar de novo, abra outro tratamento.{' '}
          {t?.horario_fixo
            ? <b>Como o horário é fixo, as sessões futuras saem da agenda (sem mensagem ao paciente).</b>
            : 'Consultas já marcadas continuam na agenda.'}</p>
        <div className="flex justify-end gap-2">
          <Botao variante="fantasma" onClick={onFechar}>Voltar</Botao>
          <Botao onClick={() => salvar.mutate()} disabled={salvar.isPending}><CheckCircle2 className="size-4" />Encerrar</Botao>
        </div>
      </div>
    </Modal>
  )
}
