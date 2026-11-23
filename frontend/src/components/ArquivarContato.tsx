import { useState } from 'react'
import { createPortal } from 'react-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Archive, ArchiveRestore, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useClinica } from '../lib/clinica'
import { telefone } from '../lib/formato'
import { useAviso } from './Aviso'
import { Botao, Modal } from './ui'

type Contato = { id: string; name: string | null; phone: string }

/** Mesmo botão de ação das linhas de Clientes (36 px, contorno suave). */
const ACAO = 'inline-grid size-9 place-items-center rounded-xl border border-line bg-surface text-muted shadow-sm transition '
  + 'hover:border-primary hover:bg-primary-soft hover:text-primary focus-visible:outline-2 focus-visible:outline-primary disabled:opacity-50'

/** Etapa 29 (D112–D114): arquivar (toda a equipe) e excluir de vez (só admin, só quem nunca teve consulta). */
export function AcoesArquivo({ contato, arquivado = false, temConsultas, compacto = false, onFeito }: {
  contato: Contato
  arquivado?: boolean
  /** undefined = não sabemos (o servidor confere ao excluir) */
  temConsultas?: boolean
  compacto?: boolean
  onFeito?: (acao: 'arquivado' | 'desarquivado' | 'excluido') => void
}) {
  const { clinica } = useClinica()
  const { usuario } = useAuth()
  const aviso = useAviso()
  const qc = useQueryClient()
  const [confirmar, setConfirmar] = useState<'arquivar' | 'excluir' | null>(null)
  const papel = usuario.super_admin ? 'super_admin' : usuario.clinicas.find((c) => c.clinic_id === clinica.id)?.papel
  const admin = papel === 'clinic_admin' || papel === 'super_admin'
  const base = `/clinics/${clinica.id}/patients/${contato.id}`
  const nome = contato.name ?? telefone(contato.phone)

  const atualizar = () => ['kanban', 'pacientes', 'dashboard', 'notificacoes'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }))
  const acao = useMutation({
    mutationFn: (a: 'arquivar' | 'desarquivar' | 'excluir') =>
      a === 'excluir' ? api.delete(base) : api.post(`${base}/${a}`),
    onSuccess: (_r, a) => {
      setConfirmar(null)
      atualizar()
      const feito = a === 'arquivar' ? 'arquivado' : a === 'desarquivar' ? 'desarquivado' : 'excluido'
      aviso.ok(feito === 'arquivado' ? `${nome} arquivado: saiu do CRM e da lista. Se escrever de novo, volta sozinho.`
        : feito === 'desarquivado' ? `${nome} voltou para as listas.` : `${nome} excluído de vez.`)
      onFeito?.(feito)
    },
    onError: (e) => { setConfirmar(null); aviso.erro(e) },
  })

  const podeExcluir = admin && temConsultas !== true
  return (
    <>
      {compacto ? (
        // Na tabela de Clientes: só ícone, no mesmo estilo dos botões vizinhos (observações, tratamento, editar)
        <>
          {arquivado
            ? <button type="button" title="Desarquivar (voltar para as listas)" aria-label={`Desarquivar ${nome}`} className={ACAO}
                disabled={acao.isPending} onClick={() => acao.mutate('desarquivar')}><ArchiveRestore className="size-[18px]" strokeWidth={1.75} /></button>
            : <button type="button" title="Arquivar (tirar do CRM e da lista)" aria-label={`Arquivar ${nome}`} className={ACAO}
                onClick={() => setConfirmar('arquivar')}><Archive className="size-[18px]" strokeWidth={1.75} /></button>}
          {podeExcluir && (
            <button type="button" title="Excluir de vez" aria-label={`Excluir ${nome}`} className={`${ACAO} hover:!border-red-500 hover:!bg-red-50 hover:!text-red-600`}
              onClick={() => setConfirmar('excluir')}><Trash2 className="size-[18px]" strokeWidth={1.75} /></button>
          )}
        </>
      ) : (
        <>
          {arquivado
            ? <Botao variante="secundario" disabled={acao.isPending} onClick={() => acao.mutate('desarquivar')}><ArchiveRestore className="size-4" />Desarquivar</Botao>
            : <Botao variante="secundario" onClick={() => setConfirmar('arquivar')}><Archive className="size-4" />Arquivar</Botao>}
          {podeExcluir && (
            <Botao variante="secundario" className="text-red-600" onClick={() => setConfirmar('excluir')}><Trash2 className="size-4" />Excluir</Botao>
          )}
        </>
      )}
      {/* fora da tabela: dentro da célula o texto herdava "não quebrar linha" e a janela saía cortada */}
      {confirmar && createPortal(
      <Modal titulo={confirmar === 'excluir' ? `Excluir · ${nome}` : `Arquivar · ${nome}`} aberto onFechar={() => setConfirmar(null)}>
        <div className="grid gap-4 text-sm">
          {confirmar === 'excluir'
            ? <p>Apaga <b>de vez</b> o contato, a conversa e as mensagens. Não dá para desfazer. Só funciona para quem nunca teve consulta.</p>
            : <p>O contato sai do CRM e da lista de {'clientes'}; os dados ficam guardados (filtro "Arquivados" em Clientes). Se ele mandar mensagem de novo, volta sozinho como "Novo contato".</p>}
          <div className="flex justify-end gap-2">
            <Botao variante="fantasma" onClick={() => setConfirmar(null)}>Voltar</Botao>
            <Botao disabled={acao.isPending} onClick={() => acao.mutate(confirmar!)} className={confirmar === 'excluir' ? '!bg-red-600' : ''}>
              {confirmar === 'excluir' ? <><Trash2 className="size-4" />Excluir de vez</> : <><Archive className="size-4" />Arquivar</>}
            </Botao>
          </div>
        </div>
      </Modal>, document.body)}
    </>
  )
}
