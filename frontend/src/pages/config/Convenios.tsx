import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CreditCard, Plus } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Entrada, Secao, Selo } from '../../components/ui'
import { api, type ConveniosClinica } from '../../lib/api'
import { useClinica } from '../../lib/clinica'

/** Etapa 22 (RN-CV): convênios que a clínica atende. Toda a equipe vê; só o administrador muda. */
export function Convenios({ podeEditar }: { podeEditar: boolean }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const base = `/clinics/${clinica.id}/config/convenios`
  const chave = ['config', 'convenios', clinica.id]
  const q = useQuery({ queryKey: chave, queryFn: () => api.get<ConveniosClinica>(base) })
  const [nome, setNome] = useState('')
  const depois = (r: ConveniosClinica, msg: string) => { qc.setQueryData(chave, r); aviso.ok(msg) }

  const criar = useMutation({
    mutationFn: () => api.post<ConveniosClinica>(base, { nome }),
    onSuccess: (r) => { setNome(''); depois(r, 'Convênio acrescentado.') },
    onError: aviso.erro,
  })
  const ligar = useMutation({
    mutationFn: ({ id, ativo }: { id: string; ativo: boolean }) => api.patch<ConveniosClinica>(`${base}/${id}`, { ativo }),
    onSuccess: (r, v) => depois(r, v.ativo ? 'Convênio religado.' : 'Convênio desligado.'),
    onError: aviso.erro,
  })
  const pergunta = useMutation({
    mutationFn: (perguntar: boolean) => api.put<ConveniosClinica>(`${base}/pergunta`, { perguntar }),
    onSuccess: (r) => depois(r, r.perguntar ? 'A assistente vai perguntar o convênio no primeiro contato.' : 'A assistente não pergunta mais sobre convênio.'),
    onError: aviso.erro,
  })

  if (!q.data) return <p className="text-sm text-muted">Carregando…</p>
  const { perguntar, convenios } = q.data
  const ativos = convenios.filter((c) => c.active)
  const enviar = (e: FormEvent) => { e.preventDefault(); if (nome.trim()) criar.mutate() }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Secao titulo="Convênios atendidos" icone={<CreditCard className="size-5" />}>
        <label className="mb-4 flex items-start gap-3 text-sm">
          <input type="checkbox" checked={perguntar} disabled={!podeEditar || pergunta.isPending}
            onChange={(e) => pergunta.mutate(e.target.checked)} className="mt-0.5 size-4 accent-[var(--primary)]" />
          <span>
            Perguntar "convênio ou particular?" no primeiro contato
            <span className="block text-xs text-muted">Só para quem ainda não veio à clínica. Desligado: a clínica atende só particular.</span>
          </span>
        </label>

        {podeEditar && (
          <form onSubmit={enviar} className="mb-4 flex gap-2">
            <Entrada className="flex-1" value={nome} maxLength={80} onChange={(e) => setNome(e.target.value)} placeholder="Ex.: Unimed, Amil, Bradesco Dental" />
            <Botao type="submit" disabled={!nome.trim() || criar.isPending}><Plus className="size-4" />Acrescentar</Botao>
          </form>
        )}

        {convenios.length === 0 ? (
          <p className="rounded-2xl bg-surface-muted px-4 py-3 text-sm text-muted">
            Nenhum convênio cadastrado. A assistente vai registrar só se a pessoa é de convênio ou particular, sem conferir o nome.
          </p>
        ) : (
          <ul className="divide-y divide-line">
            {convenios.map((c) => (
              <li key={c.id} className="flex items-center justify-between gap-3 py-2.5">
                <span className={c.active ? 'font-medium' : 'text-muted line-through'}>{c.name}</span>
                <span className="flex items-center gap-2">
                  {!c.active && <Selo>desligado</Selo>}
                  {podeEditar && (
                    <Botao variante="fantasma" className="!px-2 !py-1 text-xs" disabled={ligar.isPending}
                      onClick={() => ligar.mutate({ id: c.id, ativo: !c.active })}>
                      {c.active ? 'Desligar' : 'Religar'}
                    </Botao>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Secao>

      <Secao titulo="Como a assistente usa">
        <ul className="list-disc space-y-2 pl-5 text-sm text-muted">
          <li>Só no <b>primeiro contato</b>, antes de marcar, ela pergunta se é convênio ou particular. Quem já veio não é perguntado.</li>
          <li>{ativos.length
            ? <>Se a pessoa disser um convênio, ela confere nesta lista ({ativos.map((c) => c.name).join(', ')}).</>
            : 'Sem lista, ela registra só "convênio" ou "particular".'}</li>
          <li>Convênio que a clínica não atende: ela avisa com gentileza e oferece o particular. Com dúvida ou insistência, passa para a recepção.</li>
          <li>Ela não pede carteirinha. A resposta fica no cadastro do {'paciente'} (a recepção pode mudar em Leads / Clientes) e aparece como tag.</li>
          <li>Desligar um convênio não apaga: quem já tem esse convênio no cadastro continua com ele.</li>
        </ul>
      </Secao>
    </div>
  )
}
