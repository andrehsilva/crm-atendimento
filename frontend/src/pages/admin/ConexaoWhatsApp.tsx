import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Copy, Server } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Secao, Selo } from '../../components/ui'
import { api } from '../../lib/api'

type Conexao = {
  numero_cadastrado: string | null; servidor_proprio: boolean; servidor_url: string | null; chave_final: string | null
  webhook_url: string; webhook_exclusivo: boolean; webhook_pronto: boolean; aviso?: string
}

/** Etapa 16 (D76): número, servidor WAHA (da plataforma ou próprio) e webhook exclusivo de uma clínica. */
export function ConexaoWhatsApp({ id }: { id: string }) {
  const aviso = useAviso()
  const qc = useQueryClient()
  const base = `/admin/clinicas/${id}/whatsapp`
  const chave = ['admin', 'conexao', id]
  const q = useQuery({ queryKey: chave, queryFn: () => api.get<Conexao>(`${base}/conexao`) })
  const [f, setF] = useState({ numero: '', proprio: false, url: '', chave: '' })
  useEffect(() => {
    if (q.data) setF({ numero: q.data.numero_cadastrado ?? '', proprio: q.data.servidor_proprio, url: q.data.servidor_url ?? '', chave: '' })
  }, [q.data])
  const depois = (c: Conexao) => { qc.setQueryData(chave, c); if (c.aviso) aviso.erro(new Error(c.aviso)) }
  const salvar = useMutation({
    mutationFn: () => api.put<Conexao>(`${base}/conexao`, { numero: f.numero || null, url: f.proprio ? f.url : null, chave: f.proprio ? f.chave || null : null }),
    onSuccess: (c) => { depois(c); setF((x) => ({ ...x, chave: '' })); aviso.ok('Conexão salva.') },
    onError: aviso.erro,
  })
  const testar = useMutation({
    mutationFn: () => api.post<{ ok: boolean; sessoes?: string[]; detalhe?: string }>(`${base}/testar`),
    onSuccess: (r) => (r.ok ? aviso.ok(`Servidor respondeu. Sessões: ${r.sessoes?.join(', ') || 'nenhuma'}`) : aviso.erro(new Error(r.detalhe))),
    onError: aviso.erro,
  })
  const exclusivo = useMutation({
    mutationFn: () => api.post<Conexao>(`${base}/webhook-exclusivo`),
    onSuccess: (c) => { depois(c); if (!c.aviso) aviso.ok('Webhook exclusivo criado e apontado no WAHA.') },
    onError: aviso.erro,
  })
  if (!q.data) return null
  const c = q.data

  return (
    <Secao titulo="Conexão desta clínica" icone={<Server className="size-5" />} className="max-w-3xl"
      acao={c.servidor_proprio ? <Selo cor="azul">servidor próprio</Selo> : <Selo>servidor da plataforma</Selo>}>
      <form onSubmit={(e) => { e.preventDefault(); salvar.mutate() }} className="flex flex-col gap-4">
        <Campo rotulo="Número do WhatsApp da clínica" ajuda="Com DDD. Depois de ler o QR, confira se é o mesmo número conectado.">
          <Entrada value={f.numero} placeholder="(11) 91234-5678" onChange={(e) => setF({ ...f, numero: e.target.value })} />
        </Campo>
        <fieldset className="flex flex-col gap-2 text-sm">
          <legend className="mb-1 font-medium">Servidor WAHA</legend>
          <label className="flex items-center gap-2"><input type="radio" checked={!f.proprio} onChange={() => setF({ ...f, proprio: false })} className="size-4 accent-[var(--primary)]" />Usar o servidor da plataforma</label>
          <label className="flex items-center gap-2"><input type="radio" checked={f.proprio} onChange={() => setF({ ...f, proprio: true })} className="size-4 accent-[var(--primary)]" />Servidor próprio desta clínica</label>
        </fieldset>
        {f.proprio && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo rotulo="Endereço do servidor"><Entrada type="url" required value={f.url} placeholder="https://waha.clinica.com.br" onChange={(e) => setF({ ...f, url: e.target.value })} /></Campo>
            <Campo rotulo="Chave da API" ajuda={c.chave_final ? `Salva, termina em ${c.chave_final}. Vazio = manter.` : 'Fica guardada criptografada.'}>
              <Entrada type="password" autoComplete="off" value={f.chave} onChange={(e) => setF({ ...f, chave: e.target.value })} />
            </Campo>
          </div>
        )}
        <div className="flex flex-wrap justify-end gap-2">
          <Botao type="button" variante="secundario" disabled={testar.isPending} onClick={() => testar.mutate()}>Testar conexão</Botao>
          <Botao type="submit" disabled={salvar.isPending}>{salvar.isPending ? 'Salvando…' : 'Salvar'}</Botao>
        </div>
      </form>

      <div className="mt-6 border-t border-line pt-5">
        <p className="text-sm font-medium">Webhook {c.webhook_exclusivo ? <Selo cor="verde">exclusivo</Selo> : <Selo>geral da plataforma</Selo>}</p>
        <div className="mt-2 flex items-center gap-2">
          <code className="min-w-0 flex-1 truncate rounded-xl bg-surface-muted px-3 py-2 text-xs">{c.webhook_url}</code>
          <button type="button" aria-label="Copiar endereço" onClick={() => navigator.clipboard?.writeText(c.webhook_url).then(() => aviso.ok('Endereço copiado.'))}
            className="grid size-9 place-items-center rounded-xl border border-line text-muted hover:text-text"><Copy className="size-4" /></button>
        </div>
        <p className="mt-2 text-xs text-muted">O webhook exclusivo tem segredo próprio e só aceita mensagens da sessão desta clínica.</p>
        <Botao className="mt-3" variante="secundario" disabled={exclusivo.isPending} onClick={() => exclusivo.mutate()}>
          {c.webhook_exclusivo ? 'Gerar novo segredo e apontar' : 'Criar webhook exclusivo e apontar'}
        </Botao>
      </div>
    </Secao>
  )
}
