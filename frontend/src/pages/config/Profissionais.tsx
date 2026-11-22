import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarOff, Pencil, Plus, Sun, Trash2 } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { EnviarImagem, Retrato } from '../../components/Imagem'
import { Botao, Campo, Entrada, Modal, Selo } from '../../components/ui'
import { api, type ProcedimentoCfg, type ProfissionalCfg } from '../../lib/api'
import { useClinica } from '../../lib/clinica'
import { dataHora } from '../../lib/formato'
import { ModalResumoDia } from './ResumoDia'

type Form = { nome: string; especialidade: string; bio: string; cor: string; ativo: boolean; procedimentos: string[] }
const CORES = ['#B85C74', '#2F80C9', '#2E9E6A', '#C98A1B', '#7A5AC9', '#D0573D']

export function Profissionais({ podeEditar }: { podeEditar: boolean }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const base = `/clinics/${clinica.id}/config`
  const q = useQuery({ queryKey: ['config', 'profissionais', clinica.id], queryFn: () => api.get<{ profissionais: ProfissionalCfg[] }>(`${base}/profissionais`) })
  const servs = useQuery({ queryKey: ['config', 'procedimentos', clinica.id], queryFn: () => api.get<ProcedimentoCfg[]>(`${base}/procedimentos`) })
  const [editando, setEditando] = useState<{ id: string | null; f: Form } | null>(null)
  const [folga, setFolga] = useState<ProfissionalCfg | null>(null)
  const [resumo, setResumo] = useState<{ id: string; nome: string } | null>(null)

  const atualizar = () => {
    qc.invalidateQueries({ queryKey: ['config'] })
    qc.invalidateQueries({ queryKey: ['cadastros'] })
    qc.invalidateQueries({ queryKey: ['agenda'] })
  }
  const salvar = useMutation({
    mutationFn: ({ id, f }: { id: string | null; f: Form }) => {
      const corpo = { ...f, especialidade: f.especialidade || null, bio: f.bio.trim() || null }
      return id ? api.put(`${base}/profissionais/${id}`, corpo) : api.post(`${base}/profissionais`, corpo)
    },
    onSuccess: () => { aviso.ok('Profissional salvo.'); setEditando(null); atualizar() },
    onError: aviso.erro,
  })
  const tirarFolga = useMutation({
    mutationFn: (id: string) => api.delete(`${base}/folgas/${id}`),
    onSuccess: () => { aviso.ok('Folga removida.'); atualizar() },
    onError: aviso.erro,
  })

  if (!q.data) return <p className="text-sm text-muted">Carregando…</p>
  const nomeServ = Object.fromEntries((servs.data ?? []).map((s) => [s.id, s.nome]))
  const paraForm = (p: ProfissionalCfg): Form => ({ nome: p.nome, especialidade: p.especialidade ?? '', bio: p.bio ?? '', cor: p.cor ?? CORES[0], ativo: p.ativo, procedimentos: p.procedimentos })

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted">{q.data.profissionais.filter((p) => p.ativo).length} profissionais ativos</p>
        {podeEditar && <Botao onClick={() => setEditando({ id: null, f: { nome: '', especialidade: '', bio: '', cor: CORES[1], ativo: true, procedimentos: [] } })}><Plus className="size-4" /> Novo profissional</Botao>}
      </div>
      <ul className="flex flex-col gap-3">
        {q.data.profissionais.map((p) => (
          <li key={p.id} className={`rounded-3xl bg-surface px-5 py-4 ${p.ativo ? '' : 'opacity-60'}`}>
            <div className="flex items-start gap-4">
              <span className="shrink-0 rounded-full p-0.5" style={{ background: p.cor ?? '#999' }} title="Cor na agenda">
                <Retrato tamanho="size-12" nome={p.nome} src={p.foto_versao ? `/api${base}/profissionais/${p.id}/foto?v=${p.foto_versao}` : null} />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2 font-medium">
                  {p.nome}
                  {!p.ativo && <Selo>inativo</Selo>}
                  {p.horario_proprio && <Selo cor="azul">horário próprio</Selo>}
                </div>
                {p.especialidade && <p className="text-sm text-muted">{p.especialidade}</p>}
                {p.bio && <p className="mt-1 line-clamp-2 text-sm text-muted">{p.bio}</p>}
                <p className="mt-1 text-sm">{p.procedimentos.map((id) => nomeServ[id]).filter(Boolean).join(' · ') || <span className="text-muted">nenhum procedimento</span>}</p>
                {p.folgas.length > 0 && (
                  <ul className="mt-2 flex flex-wrap gap-2">
                    {p.folgas.map((f) => (
                      <li key={f.id} className="flex items-center gap-1 rounded-xl bg-surface-muted px-2 py-1 text-xs">
                        <CalendarOff className="size-3.5" /> {f.motivo}: {dataHora(f.inicio, clinica.timezone)} → {dataHora(f.fim, clinica.timezone)}
                        {podeEditar && <button type="button" aria-label="Remover folga" onClick={() => tirarFolga.mutate(f.id)} className="ml-1 text-muted hover:text-red-600"><Trash2 className="size-3.5" /></button>}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              {podeEditar && (
                <div className="flex gap-1">
                  <Botao variante="fantasma" onClick={() => setResumo({ id: p.id, nome: p.nome })} title="Agenda do dia no WhatsApp pessoal"><Sun className="size-4" /> Resumo do dia</Botao>
                  <Botao variante="fantasma" onClick={() => setFolga(p)} title="Férias ou folga"><CalendarOff className="size-4" /> Folga</Botao>
                  <button type="button" aria-label="Editar" onClick={() => setEditando({ id: p.id, f: paraForm(p) })} className="rounded-lg p-2 text-muted hover:bg-surface-muted"><Pencil className="size-4" /></button>
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>
      {editando && (
        <Modal titulo={editando.id ? 'Editar profissional' : 'Novo profissional'} aberto onFechar={() => setEditando(null)}>
          {editando.id && <FotoProfissional id={editando.id} base={base} nome={editando.f.nome}
            versao={q.data.profissionais.find((p) => p.id === editando.id)?.foto_versao ?? null} />}
          <FormProfissional inicial={editando.f} servicos={(servs.data ?? []).filter((s) => s.ativo)} enviando={salvar.isPending}
            onCancelar={() => setEditando(null)} onSalvar={(f) => salvar.mutate({ id: editando.id, f })} />
        </Modal>
      )}
      {folga && <NovaFolga p={folga} onFechar={() => setFolga(null)} onFeita={atualizar} />}
      <ModalResumoDia prof={resumo} podeEditar={podeEditar} onFechar={() => setResumo(null)} />
    </div>
  )
}

function FormProfissional({ inicial, servicos, enviando, onSalvar, onCancelar }: {
  inicial: Form; servicos: ProcedimentoCfg[]; enviando: boolean; onSalvar: (f: Form) => void; onCancelar: () => void
}) {
  const [f, setF] = useState(inicial)
  const marcar = (id: string) => setF({ ...f, procedimentos: f.procedimentos.includes(id) ? f.procedimentos.filter((x) => x !== id) : [...f.procedimentos, id] })
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSalvar(f) }} className="flex flex-col gap-4">
      <Campo rotulo="Nome"><Entrada required value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} placeholder="Dra. Ana Lima" /></Campo>
      <Campo rotulo="Especialidade"><Entrada value={f.especialidade} onChange={(e) => setF({ ...f, especialidade: e.target.value })} /></Campo>
      <Campo rotulo="Apresentação curta" ajuda={`Aparece no site da clínica. ${f.bio.length}/400`}>
        <textarea rows={3} maxLength={400} value={f.bio} onChange={(e) => setF({ ...f, bio: e.target.value })}
          placeholder="Ex.: Formada pela USP, atendo adultos e crianças com calma e atenção."
          className="rounded-xl border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-primary" />
      </Campo>
      <fieldset>
        <legend className="mb-2 text-sm font-medium">Cor na agenda</legend>
        <div className="flex gap-2">
          {CORES.map((c) => (
            <button key={c} type="button" aria-label={`Cor ${c}`} aria-pressed={f.cor === c} onClick={() => setF({ ...f, cor: c })}
              className={`size-8 rounded-full ring-offset-2 ring-offset-surface ${f.cor === c ? 'ring-2 ring-text' : ''}`} style={{ background: c }} />
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend className="mb-2 text-sm font-medium">Procedimentos que faz</legend>
        <div className="flex flex-wrap gap-2">
          {servicos.map((s) => (
            <button key={s.id} type="button" aria-pressed={f.procedimentos.includes(s.id)} onClick={() => marcar(s.id)}
              className={`rounded-full border px-3 py-1.5 text-sm ${f.procedimentos.includes(s.id) ? 'border-primary bg-primary-soft text-primary' : 'border-line text-muted'}`}>
              {s.nome}
            </button>
          ))}
        </div>
      </fieldset>
      <label className="flex items-center gap-3 text-sm">
        <input type="checkbox" checked={f.ativo} onChange={(e) => setF({ ...f, ativo: e.target.checked })} className="size-4 accent-[var(--primary)]" />
        Ativo (aparece na agenda e a assistente oferece horários)
      </label>
      <div className="flex justify-end gap-2">
        <Botao variante="fantasma" onClick={onCancelar}>Cancelar</Botao>
        <Botao type="submit" disabled={enviando}>{enviando ? 'Salvando…' : 'Salvar'}</Botao>
      </div>
    </form>
  )
}

function NovaFolga({ p, onFechar, onFeita }: { p: ProfissionalCfg; onFechar: () => void; onFeita: () => void }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const [f, setF] = useState({ inicio: '', fim: '', motivo: 'Férias' })
  const criar = useMutation({
    // dia inteiro: do início do 1º dia ao fim do último, no fuso do navegador (o mesmo da clínica no uso normal)
    mutationFn: () => api.post<{ consultas_no_periodo: number }>(`/clinics/${clinica.id}/config/profissionais/${p.id}/folgas`, {
      inicio: new Date(`${f.inicio}T00:00:00`).toISOString(), fim: new Date(`${f.fim}T23:59:59`).toISOString(), motivo: f.motivo,
    }),
    onSuccess: (r) => {
      aviso.ok(r.consultas_no_periodo ? `Folga salva. Atenção: ${r.consultas_no_periodo} consulta(s) já marcada(s) no período — remarque pela agenda.` : 'Folga salva.')
      onFeita()
      onFechar()
    },
    onError: aviso.erro,
  })
  return (
    <Modal titulo={`Férias ou folga — ${p.nome}`} aberto onFechar={onFechar}>
      <form onSubmit={(e) => { e.preventDefault(); criar.mutate() }} className="flex flex-col gap-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo rotulo="Primeiro dia"><Entrada type="date" required value={f.inicio} onChange={(e) => setF({ ...f, inicio: e.target.value, fim: f.fim || e.target.value })} /></Campo>
          <Campo rotulo="Último dia"><Entrada type="date" required min={f.inicio} value={f.fim} onChange={(e) => setF({ ...f, fim: e.target.value })} /></Campo>
        </div>
        <Campo rotulo="Motivo"><Entrada value={f.motivo} maxLength={120} onChange={(e) => setF({ ...f, motivo: e.target.value })} /></Campo>
        <p className="text-xs text-muted">Nesses dias a assistente não oferece horários com {p.nome}. Consultas já marcadas continuam; você é avisado se houver alguma.</p>
        <div className="flex justify-end gap-2">
          <Botao variante="fantasma" onClick={onFechar}>Cancelar</Botao>
          <Botao type="submit" disabled={criar.isPending || !f.inicio || !f.fim}>Salvar</Botao>
        </div>
      </form>
    </Modal>
  )
}

/** Etapa 11: foto do profissional (aparece no painel e no site). Só para quem já foi salvo. */
export function FotoProfissional({ id, base, nome, versao }: { id: string; base: string; nome: string; versao: number | null }) {
  const aviso = useAviso()
  const qc = useQueryClient()
  const url = `${base}/profissionais/${id}/foto`
  const depois = () => qc.invalidateQueries({ queryKey: ['config'] })
  const enviar = useMutation({ mutationFn: (f: File) => api.put(url, f), onSuccess: () => { aviso.ok('Foto salva.'); depois() }, onError: aviso.erro })
  const remover = useMutation({ mutationFn: () => api.delete(url), onSuccess: () => { aviso.ok('Foto removida.'); depois() }, onError: aviso.erro })
  return (
    <div className="mb-5 flex items-center gap-4 rounded-2xl bg-surface-muted p-3">
      <Retrato tamanho="size-16" nome={nome} src={versao ? `/api${url}?v=${versao}` : null} />
      <div className="flex flex-col gap-1">
        <EnviarImagem tem={!!versao} enviando={enviar.isPending || remover.isPending} rotulo={versao ? 'Trocar foto' : 'Enviar foto'}
          onArquivo={(f) => enviar.mutate(f)} onRemover={() => remover.mutate()} onProblema={aviso.erro} />
        <span className="text-xs text-muted">Foto de rosto, de frente e com boa luz. PNG, JPG ou WebP até 512 KB. Aparece no site.</span>
      </div>
    </div>
  )
}
