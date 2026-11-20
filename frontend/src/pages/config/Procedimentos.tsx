import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bot, ChevronDown, Pencil, Plus, Trash2, UserRound } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Modal, Selo } from '../../components/ui'
import { api, type ProcedimentoCfg, type ProfissionalCfg } from '../../lib/api'
import { useClinica } from '../../lib/clinica'
import { useTermos } from '../../lib/termos'

type Form = { nome: string; descricao: string; duracao_min: number; preco: string; ativo: boolean; ia_pode_marcar: boolean; profissionais: string[] }
const vazio: Form = { nome: '', descricao: '', duracao_min: 60, preco: '', ativo: true, ia_pode_marcar: true, profissionais: [] }
const reais = (c: number | null) => (c == null ? '' : (c / 100).toFixed(2).replace('.', ','))

/** Imagem 05: lista de procedimentos com liga/desliga, expandir, editar e excluir. */
export function Procedimentos({ podeEditar }: { podeEditar: boolean }) {
  const { clinica } = useClinica()
  const pal = useTermos()
  const aviso = useAviso()
  const qc = useQueryClient()
  const base = `/clinics/${clinica.id}/config`
  const q = useQuery({ queryKey: ['config', 'procedimentos', clinica.id], queryFn: () => api.get<ProcedimentoCfg[]>(`${base}/procedimentos`) })
  const profs = useQuery({ queryKey: ['config', 'profissionais', clinica.id], queryFn: () => api.get<{ profissionais: ProfissionalCfg[] }>(`${base}/profissionais`) })
  const [aberto, setAberto] = useState<string | null>(null)
  const [editando, setEditando] = useState<{ id: string | null; f: Form } | null>(null)
  const [excluir, setExcluir] = useState<ProcedimentoCfg | null>(null)

  const atualizar = () => {
    qc.invalidateQueries({ queryKey: ['config'] })
    qc.invalidateQueries({ queryKey: ['cadastros'] })
  }
  const corpo = (f: Form) => ({ ...f, descricao: f.descricao || null, preco_centavos: f.preco ? Math.round(Number(f.preco.replace(',', '.')) * 100) : null })
  const salvar = useMutation({
    mutationFn: ({ id, f }: { id: string | null; f: Form }) => (id ? api.put(`${base}/procedimentos/${id}`, corpo(f)) : api.post(`${base}/procedimentos`, corpo(f))),
    onSuccess: () => { aviso.ok('Procedimento salvo.'); setEditando(null); atualizar() },
    onError: aviso.erro,
  })
  const alternar = (p: ProcedimentoCfg) => salvar.mutate({ id: p.id, f: { ...paraForm(p), ativo: !p.ativo } })
  const remover = useMutation({
    mutationFn: (id: string) => api.delete<{ resultado: string }>(`${base}/procedimentos/${id}`),
    onSuccess: (r) => { aviso.ok(r.resultado === 'excluido' ? 'Procedimento excluído.' : `Já foi usado em ${pal.atendimentos}: ficou desligado.`); setExcluir(null); atualizar() },
    onError: aviso.erro,
  })

  if (!q.data) return <p className="text-sm text-muted">Carregando…</p>
  const nomeProf = Object.fromEntries((profs.data?.profissionais ?? []).map((p) => [p.id, p.nome]))

  return (
    <div className="max-w-4xl">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted">{q.data.length} procedimentos cadastrados</p>
        {podeEditar && <Botao onClick={() => setEditando({ id: null, f: vazio })}><Plus className="size-4" /> Novo Procedimento</Botao>}
      </div>
      <ul className="flex flex-col gap-3">
        {q.data.map((p) => (
          <li key={p.id} className={`rounded-3xl bg-surface px-5 py-4 ${p.ativo ? '' : 'opacity-60'}`}>
            <div className="flex items-center gap-4">
              <input type="checkbox" role="switch" aria-label={`${p.nome} ativo`} checked={p.ativo} disabled={!podeEditar || salvar.isPending}
                onChange={() => alternar(p)} className="size-4 accent-[var(--primary)]" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2 font-medium">
                  {p.nome}
                  {!p.ia_pode_marcar && <Selo cor="ambar">só a recepção marca</Selo>}
                </div>
                {p.descricao && <p className="truncate text-sm text-muted">{p.descricao}</p>}
              </div>
              <button type="button" aria-label="Detalhes" aria-expanded={aberto === p.id} onClick={() => setAberto(aberto === p.id ? null : p.id)}
                className="rounded-lg p-2 text-muted hover:bg-surface-muted"><ChevronDown className={`size-4 transition ${aberto === p.id ? 'rotate-180' : ''}`} /></button>
              {podeEditar && (
                <>
                  <button type="button" aria-label="Editar" onClick={() => setEditando({ id: p.id, f: paraForm(p) })} className="rounded-lg p-2 text-muted hover:bg-surface-muted"><Pencil className="size-4" /></button>
                  <button type="button" aria-label="Excluir" onClick={() => setExcluir(p)} className="rounded-lg p-2 text-muted hover:bg-surface-muted hover:text-red-600"><Trash2 className="size-4" /></button>
                </>
              )}
            </div>
            {aberto === p.id && (
              <dl className="mt-4 grid gap-2 border-t border-line pt-4 text-sm sm:grid-cols-3">
                <div><dt className="text-muted">Duração</dt><dd>{p.duracao_min} min</dd></div>
                <div><dt className="text-muted">Preço</dt><dd>{p.preco_centavos != null ? `R$ ${reais(p.preco_centavos)}` : '—'}</dd></div>
                <div><dt className="text-muted">{pal.Atendimentos} futur{pal.o}s</dt><dd>{p.consultas_futuras}</dd></div>
                <div className="sm:col-span-3"><dt className="text-muted">Quem faz</dt><dd>{p.profissionais.map((id) => nomeProf[id]).filter(Boolean).join(', ') || 'ninguém (a assistente não oferece)'}</dd></div>
              </dl>
            )}
          </li>
        ))}
      </ul>

      {editando && (
        <Modal titulo={editando.id ? 'Editar procedimento' : 'Novo procedimento'} aberto onFechar={() => setEditando(null)}>
          <FormProcedimento inicial={editando.f} profissionais={profs.data?.profissionais ?? []} enviando={salvar.isPending}
            onCancelar={() => setEditando(null)} onSalvar={(f) => salvar.mutate({ id: editando.id, f })} />
        </Modal>
      )}
      <Modal titulo="Excluir procedimento?" aberto={!!excluir} onFechar={() => setExcluir(null)}>
        <p className="text-sm">Se <strong>{excluir?.nome}</strong> já foi usado em {pal.atendimentos} anteriores, ele só fica desligado (o histórico continua). {pal.Atendimentos} já marcad{pal.o}s não mudam.</p>
        <div className="mt-6 flex justify-end gap-2">
          <Botao variante="fantasma" onClick={() => setExcluir(null)}>Cancelar</Botao>
          <Botao variante="perigo" onClick={() => excluir && remover.mutate(excluir.id)} disabled={remover.isPending}>Excluir</Botao>
        </div>
      </Modal>
    </div>
  )
}

function paraForm(p: ProcedimentoCfg): Form {
  return { nome: p.nome, descricao: p.descricao ?? '', duracao_min: p.duracao_min, preco: reais(p.preco_centavos), ativo: p.ativo, ia_pode_marcar: p.ia_pode_marcar, profissionais: p.profissionais }
}

function FormProcedimento({ inicial, profissionais, enviando, onSalvar, onCancelar }: {
  inicial: Form; profissionais: ProfissionalCfg[]; enviando: boolean; onSalvar: (f: Form) => void; onCancelar: () => void
}) {
  const [f, setF] = useState(inicial)
  const marcar = (id: string) => setF({ ...f, profissionais: f.profissionais.includes(id) ? f.profissionais.filter((x) => x !== id) : [...f.profissionais, id] })
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSalvar(f) }} className="flex flex-col gap-4">
      <Campo rotulo="Nome"><Entrada required value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} /></Campo>
      <Campo rotulo="Descrição curta" ajuda="A assistente usa para explicar o procedimento.">
        <Entrada value={f.descricao} maxLength={300} onChange={(e) => setF({ ...f, descricao: e.target.value })} />
      </Campo>
      <div className="grid gap-4 sm:grid-cols-2">
        <Campo rotulo="Duração (min)"><Entrada type="number" min={5} max={480} step={5} required value={f.duracao_min} onChange={(e) => setF({ ...f, duracao_min: Number(e.target.value) })} /></Campo>
        <Campo rotulo="Preço (opcional)" ajuda="Só aparece no chat se a clínica liga 'mostrar preços' na aba Assistente.">
          <Entrada inputMode="decimal" placeholder="0,00" value={f.preco} onChange={(e) => setF({ ...f, preco: e.target.value.replace(/[^\d,]/g, '') })} />
        </Campo>
      </div>
      <label className="flex items-start gap-3 text-sm">
        <input type="checkbox" checked={f.ia_pode_marcar} onChange={(e) => setF({ ...f, ia_pode_marcar: e.target.checked })} className="mt-0.5 size-4 accent-[var(--primary)]" />
        <span><Bot className="mr-1 inline size-4" />A assistente pode marcar sozinha <span className="block text-xs text-muted">Desligue para casos que exigem a recepção (ex.: urgência).</span></span>
      </label>
      <fieldset>
        <legend className="mb-2 text-sm font-medium">Quem faz</legend>
        <div className="flex flex-wrap gap-2">
          {profissionais.filter((p) => p.ativo).map((p) => (
            <button key={p.id} type="button" aria-pressed={f.profissionais.includes(p.id)} onClick={() => marcar(p.id)}
              className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm ${f.profissionais.includes(p.id) ? 'border-primary bg-primary-soft text-primary' : 'border-line text-muted'}`}>
              <UserRound className="size-3.5" /> {p.nome}
            </button>
          ))}
          {!profissionais.length && <p className="text-sm text-muted">Cadastre profissionais na aba Profissionais.</p>}
        </div>
      </fieldset>
      <div className="flex justify-end gap-2">
        <Botao variante="fantasma" onClick={onCancelar}>Cancelar</Botao>
        <Botao type="submit" disabled={enviando}>{enviando ? 'Salvando…' : 'Salvar'}</Botao>
      </div>
    </form>
  )
}
