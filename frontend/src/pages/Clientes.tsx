import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FolderOpen, NotebookPen, Pencil, Search, Users } from 'lucide-react'
import { api, type Etapa, type Paciente } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { dataCurta, telefone } from '../lib/formato'
import { useAviso } from '../components/Aviso'
import { PageHeader } from '../components/PageHeader'
import { Botao, Campo, Entrada, Modal, Selo, Vazio, type CorSelo } from '../components/ui'
import { useTermos } from '../lib/termos'
import { EnviarImagem, Retrato } from '../components/Imagem'
import { ModalObservacoes } from '../components/ModalObservacoes'

const ETAPA: Record<Etapa, [string, CorSelo]> = {
  novo_contato: ['Novo contato', 'rosa'],
  agendado: ['Agendado', 'verde'],
  confirmado: ['Confirmado', 'verde'],
  cancelado: ['Cancelado', 'vermelho'],
}

/** Botão de ação da linha: área de toque de 36 px, contorno suave, destaque ao passar o mouse e foco visível. */
const ACAO = 'inline-grid size-9 place-items-center rounded-xl border border-line bg-surface text-muted shadow-sm transition '
  + 'hover:border-primary hover:bg-primary-soft hover:text-primary focus-visible:outline-2 focus-visible:outline-primary'

export function Clientes() {
  const { clinica } = useClinica()
  const pal = useTermos()
  const tz = clinica.timezone
  const [busca, setBusca] = useState('')
  const [termo, setTermo] = useState('')
  const [editando, setEditando] = useState<Paciente | null>(null)
  const [notas, setNotas] = useState<Paciente | null>(null)

  useEffect(() => {
    const t = setTimeout(() => setTermo(busca.trim()), 300)
    return () => clearTimeout(t)
  }, [busca])

  const q = useQuery({
    queryKey: ['pacientes', clinica.id, termo],
    queryFn: () => api.get<Paciente[]>(`/clinics/${clinica.id}/patients${termo ? `?busca=${encodeURIComponent(termo)}` : ''}`),
  })

  return (
    <>
      <PageHeader titulo="Leads / Clientes" subtitulo={`${pal.Clientes} e contatos`} />
      <div className="rounded-3xl bg-surface p-5">
        <div className="relative mb-4 max-w-sm">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
          <Entrada className="w-full pl-9" placeholder="Buscar por nome ou telefone" value={busca} onChange={(e) => setBusca(e.target.value)} />
        </div>
        {!q.data?.length ? (
          <Vazio icone={<Users className="size-8" />} texto={q.isLoading ? 'Carregando…' : `Nenhum ${pal.cliente} encontrado.`} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-muted">
                <tr className="border-b border-line">
                  <th className="py-2 pr-4 font-medium">Nome</th>
                  <th className="py-2 pr-4 font-medium">Telefone</th>
                  <th className="py-2 pr-4 font-medium">Etapa</th>
                  <th className="py-2 pr-4 font-medium">Nascimento</th>
                  <th className="py-2 pr-4 font-medium">Próxim{pal.o} {pal.atendimento}</th>
                  <th className="py-2 pr-4 font-medium">{pal.Profissional} de referência</th>
                  <th className="py-2 pr-4 font-medium">Origem</th>
                  <th />
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {q.data.map((p) => {
                  const [rot, cor] = ETAPA[p.crm_stage]
                  return (
                    <tr key={p.id}>
                      <td className="py-2.5 pr-4 font-medium">
                        <span className="flex items-center gap-3">
                          <Retrato nome={p.name} src={p.foto_versao ? `/api/clinics/${clinica.id}/patients/${p.id}/foto?v=${p.foto_versao}` : null} />
                          {p.name ?? <span className="text-muted">sem nome</span>}
                        </span>
                      </td>
                      <td className="py-2.5 pr-4">{telefone(p.phone)}</td>
                      <td className="py-2.5 pr-4"><Selo cor={cor}>{rot}</Selo></td>
                      <td className="py-2.5 pr-4">{p.birth_date ? p.birth_date.split('-').reverse().join('/') : '—'}</td>
                      <td className="py-2.5 pr-4">{p.proxima_consulta ? dataCurta(p.proxima_consulta, tz) : '—'}</td>
                      <td className="py-2.5 pr-4">{p.dentista_referencia ?? '—'}</td>
                      <td className="py-2.5 pr-4 capitalize">{p.origin}</td>
                      <td className="whitespace-nowrap py-2.5 pl-4 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          {p.drive_url && (
                            <a href={p.drive_url} target="_blank" rel="noopener noreferrer" title="Abrir pasta no Google Drive"
                              aria-label={`Abrir pasta no Drive de ${p.name ?? ''}`} className={ACAO}>
                              <FolderOpen className="size-[18px]" strokeWidth={1.75} />
                            </a>
                          )}
                          <button type="button" title={p.notas ? `Observações (${p.notas})` : 'Observações'} aria-label={`Observações de ${p.name ?? ''}`}
                            onClick={() => setNotas(p)} className={`relative ${ACAO}`}>
                            <NotebookPen className="size-[18px]" strokeWidth={1.75} />
                            {p.notas > 0 && (
                              <span className="absolute -right-1.5 -top-1.5 grid min-w-5 place-items-center rounded-full bg-primary px-1 text-[11px] font-semibold leading-5 text-primary-contrast ring-2 ring-surface">
                                {p.notas}
                              </span>
                            )}
                          </button>
                          <button type="button" title="Editar cadastro" aria-label={`Editar ${p.name ?? ''}`} onClick={() => setEditando(p)} className={ACAO}>
                            <Pencil className="size-[18px]" strokeWidth={1.75} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <ModalEditar paciente={editando} onFechar={() => setEditando(null)} />
      <ModalObservacoes paciente={notas} onFechar={() => setNotas(null)} />
    </>
  )
}

function ModalEditar({ paciente, onFechar }: { paciente: Paciente | null; onFechar: () => void }) {
  const { clinica } = useClinica()
  const pal = useTermos()
  const aviso = useAviso()
  const [nome, setNome] = useState('')
  const [nasc, setNasc] = useState('')
  const [foto, setFoto] = useState<number | null>(null)
  const qc = useQueryClient()
  useEffect(() => {
    setNome(paciente?.name ?? '')
    setNasc(paciente?.birth_date ?? '')
    setFoto(paciente?.foto_versao ?? null)
  }, [paciente])
  const urlFoto = `/clinics/${clinica.id}/patients/${paciente?.id}/foto`
  const mudarFoto = useMutation({
    mutationFn: (f: File | null) => (f ? api.put<{ foto_versao: number | null }>(urlFoto, f) : api.delete<{ foto_versao: null }>(urlFoto)),
    onSuccess: (r) => {
      setFoto(r.foto_versao)
      qc.invalidateQueries({ queryKey: ['pacientes'] })
      qc.invalidateQueries({ queryKey: ['kanban'] })
    },
    onError: aviso.erro,
  })

  const salvar = useMutation({
    mutationFn: () => api.patch(`/clinics/${clinica.id}/patients/${paciente!.id}`, { name: nome || null, birth_date: nasc || null }),
    onSuccess: () => { aviso.ok(`${pal.Cliente} atualizado`); onFechar() },
    onError: aviso.erro,
  })

  return (
    <Modal titulo={`Editar ${pal.cliente}`} aberto={!!paciente} onFechar={onFechar}>
      <div className="space-y-4">
        <div className="flex items-center gap-4">
          <Retrato tamanho="size-16" nome={nome || paciente?.name} src={foto ? `/api${urlFoto}?v=${foto}` : null} />
          <div className="space-y-1">
            <EnviarImagem tem={!!foto} enviando={mudarFoto.isPending} rotulo="Enviar foto"
              onArquivo={(f) => mudarFoto.mutate(f)} onRemover={() => mudarFoto.mutate(null)} onProblema={aviso.erro} />
            <p className="text-xs text-muted">PNG, JPG ou WebP até 512 KB.</p>
          </div>
        </div>
        <p className="text-sm text-muted">Telefone: {paciente && telefone(paciente.phone)} (é a chave do {pal.cliente} e não muda)</p>
        <Campo rotulo="Nome completo"><Entrada value={nome} onChange={(e) => setNome(e.target.value)} /></Campo>
        <Campo rotulo="Data de nascimento" ajuda="Usada na mensagem de aniversário"><Entrada type="date" value={nasc} onChange={(e) => setNasc(e.target.value)} /></Campo>
      </div>
      <div className="mt-6 flex justify-end gap-2">
        <Botao variante="fantasma" onClick={onFechar}>Cancelar</Botao>
        <Botao disabled={salvar.isPending} onClick={() => salvar.mutate()}>Salvar</Botao>
      </div>
    </Modal>
  )
}
