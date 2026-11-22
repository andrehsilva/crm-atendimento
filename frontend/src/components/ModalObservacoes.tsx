import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FolderOpen, NotebookPen, Pencil, Trash2 } from 'lucide-react'
import { api, type NotaCliente, type Observacoes, type Paciente } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { telefone } from '../lib/formato'
import { useTermos } from '../lib/termos'
import { useAviso } from './Aviso'
import { Retrato } from './Imagem'
import { EditorTexto, Formatado } from './TextoRico'
import { Botao, Entrada, Modal } from './ui'

const DRIVE = /^https:\/\/drive\.google\.com\/\S*$/

function quando(iso: string, tz: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: tz,
  }).format(new Date(iso))
}

/** Etapa 9C (D48, D49): diário de observações do cliente + botão da pasta no Google Drive. */
export function ModalObservacoes({ paciente, onFechar }: { paciente: Paciente | null; onFechar: () => void }) {
  const { clinica } = useClinica()
  const pal = useTermos()
  const aviso = useAviso()
  const qc = useQueryClient()
  const base = `/clinics/${clinica.id}/patients/${paciente?.id}`
  const chave = ['observacoes', paciente?.id]
  const q = useQuery({ queryKey: chave, queryFn: () => api.get<Observacoes>(`${base}/observacoes`), enabled: !!paciente })
  const [nova, setNova] = useState('')

  const depois = (o: Observacoes) => {
    qc.setQueryData(chave, o)
    qc.invalidateQueries({ queryKey: ['pacientes'] })
  }
  const criar = useMutation({
    mutationFn: () => api.post<Observacoes>(`${base}/observacoes`, { texto: nova }),
    onSuccess: (o) => { depois(o); setNova(''); aviso.ok('Observação salva.') },
    onError: aviso.erro,
  })

  const fechar = () => { setNova(''); onFechar() }
  const nome = paciente?.name ?? (paciente ? telefone(paciente.phone) : '')

  return (
    <Modal titulo={`Observações · ${nome}`} aberto={!!paciente} onFechar={fechar} largura="max-w-2xl">
      {paciente && (
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <Retrato tamanho="size-12" nome={paciente.name}
              src={paciente.foto_versao ? `/api${base}/foto?v=${paciente.foto_versao}` : null} />
            <div className="min-w-0">
              <div className="truncate font-medium">{paciente.name ?? 'Sem nome'}</div>
              <div className="text-sm text-muted">{telefone(paciente.phone)}</div>
            </div>
          </div>

          <PastaDrive url={q.data?.drive_url ?? null} base={base} onSalvo={depois} />

          <form onSubmit={(e) => { e.preventDefault(); if (nova.trim()) criar.mutate() }} className="space-y-2">
            <EditorTexto valor={nova} onMudar={setNova} autoFocus onEnviar={() => nova.trim() && criar.mutate()}
              placeholder={`Nova observação sobre o ${pal.cliente}… (Ctrl+Enter salva)`} />
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs text-muted">Fica guardada com a data e o seu nome. A assistente não lê as observações.</p>
              <Botao type="submit" disabled={!nova.trim() || criar.isPending}>{criar.isPending ? 'Salvando…' : 'Salvar observação'}</Botao>
            </div>
          </form>

          <section aria-label="Histórico de observações">
            {!q.data ? <p className="text-sm text-muted">Carregando…</p>
              : q.data.notas.length === 0 ? (
                <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-line py-8 text-center text-sm text-muted">
                  <NotebookPen className="size-6" />
                  Nenhuma observação ainda. A primeira que você salvar aparece aqui.
                </div>
              ) : (
                <ol className="relative space-y-4 border-l border-line pl-5">
                  {q.data.notas.map((n) => <ItemNota key={n.id} nota={n} base={base} onSalvo={depois} />)}
                </ol>
              )}
          </section>
        </div>
      )}
    </Modal>
  )
}

function ItemNota({ nota, base, onSalvo }: { nota: NotaCliente; base: string; onSalvo: (o: Observacoes) => void }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const [editando, setEditando] = useState<string | null>(null)
  const [confirmar, setConfirmar] = useState(false)
  const salvar = useMutation({
    mutationFn: () => api.patch<Observacoes>(`${base}/observacoes/${nota.id}`, { texto: editando }),
    onSuccess: (o) => { onSalvo(o); setEditando(null); aviso.ok('Observação atualizada.') },
    onError: aviso.erro,
  })
  const apagar = useMutation({
    mutationFn: () => api.delete<Observacoes>(`${base}/observacoes/${nota.id}`),
    onSuccess: (o) => { onSalvo(o); aviso.ok('Observação apagada.') },
    onError: aviso.erro,
  })

  return (
    <li className="relative">
      <span aria-hidden className="absolute -left-[1.6rem] top-1.5 size-2.5 rounded-full bg-primary ring-4 ring-surface" />
      <div className="mb-1 flex flex-wrap items-baseline gap-x-2 text-xs text-muted">
        <span className="font-medium text-text">{nota.autor}</span>
        <time dateTime={nota.criado_em}>{quando(nota.criado_em, clinica.timezone)}</time>
        {nota.editado_em && <span title={`Editada em ${quando(nota.editado_em, clinica.timezone)}`}>(editada)</span>}
        <span className="ml-auto flex gap-1">
          {nota.pode_editar && editando === null && (
            <button type="button" aria-label="Corrigir observação" onClick={() => setEditando(nota.texto)}
              className="rounded-md p-1 hover:bg-surface-muted hover:text-text"><Pencil className="size-3.5" /></button>
          )}
          {nota.pode_apagar && editando === null && (
            <button type="button" aria-label="Apagar observação" onClick={() => setConfirmar(true)}
              className="rounded-md p-1 hover:bg-surface-muted hover:text-text"><Trash2 className="size-3.5" /></button>
          )}
        </span>
      </div>
      {editando !== null ? (
        <div className="space-y-2">
          <EditorTexto valor={editando} onMudar={setEditando} autoFocus onEnviar={() => editando.trim() && salvar.mutate()} />
          <div className="flex justify-end gap-2">
            <Botao variante="fantasma" onClick={() => setEditando(null)}>Cancelar</Botao>
            <Botao disabled={!editando.trim() || salvar.isPending} onClick={() => salvar.mutate()}>Salvar correção</Botao>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl bg-surface-muted px-4 py-3"><Formatado texto={nota.texto} /></div>
      )}
      {confirmar && (
        <div role="alert" className="mt-2 flex flex-wrap items-center gap-2 rounded-xl border border-line px-3 py-2 text-sm">
          Apagar esta observação? Não dá para desfazer.
          <span className="ml-auto flex gap-2">
            <Botao variante="fantasma" onClick={() => setConfirmar(false)}>Manter</Botao>
            <Botao disabled={apagar.isPending} onClick={() => apagar.mutate()}>Apagar</Botao>
          </span>
        </div>
      )}
    </li>
  )
}

function PastaDrive({ url, base, onSalvo }: { url: string | null; base: string; onSalvo: (o: Observacoes) => void }) {
  const aviso = useAviso()
  const [editando, setEditando] = useState(false)
  const [valor, setValor] = useState('')
  const salvar = useMutation({
    mutationFn: (u: string | null) => api.put<Observacoes>(`${base}/drive`, { url: u }),
    onSuccess: (o, u) => { onSalvo(o); setEditando(false); setValor(''); aviso.ok(u ? 'Pasta do Drive salva.' : 'Pasta do Drive removida.') },
    onError: aviso.erro,
  })
  const valido = DRIVE.test(valor.trim())

  if (url && !editando) {
    return (
      <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-line px-4 py-3">
        <FolderOpen className="size-5 text-primary" />
        <span className="text-sm font-medium">Pasta no Google Drive</span>
        <span className="ml-auto flex gap-2">
          <a href={url} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-contrast hover:opacity-90">
            Abrir pasta no Drive
          </a>
          <Botao variante="fantasma" onClick={() => { setValor(url); setEditando(true) }}>Alterar</Botao>
        </span>
      </div>
    )
  }
  return (
    <form onSubmit={(e) => { e.preventDefault(); if (valido) salvar.mutate(valor.trim()) }}
      className="space-y-2 rounded-2xl border border-dashed border-line px-4 py-3">
      <label htmlFor="drive-url" className="flex items-center gap-2 text-sm font-medium">
        <FolderOpen className="size-5 text-muted" />Pasta no Google Drive
      </label>
      <div className="flex flex-wrap gap-2">
        <Entrada id="drive-url" type="url" className="min-w-0 flex-1" value={valor} onChange={(e) => setValor(e.target.value)}
          placeholder="https://drive.google.com/drive/folders/…" />
        <Botao type="submit" disabled={!valido || salvar.isPending}>Salvar link</Botao>
        {url && <Botao variante="fantasma" onClick={() => salvar.mutate(null)}>Remover link</Botao>}
        {editando && <Botao variante="fantasma" onClick={() => setEditando(false)}>Cancelar</Botao>}
      </div>
      <p className="text-xs text-muted">
        {valor.trim() && !valido ? 'O link precisa começar com https://drive.google.com/'
          : 'Crie a pasta no seu Drive, copie o link e cole aqui. Quem pode abrir a pasta é definido no próprio Drive.'}
      </p>
    </form>
  )
}
