import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Cake } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Secao } from '../../components/ui'
import { api, type ConfigAniversario } from '../../lib/api'
import { useClinica } from '../../lib/clinica'
import { useTermos } from '../../lib/termos'

/** Imagem 04: mensagem de aniversário com prévia (Etapa 6). */
export function Mensagens({ podeEditar }: { podeEditar: boolean }) {
  const { clinica } = useClinica()
  const pal = useTermos()
  const aviso = useAviso()
  const qc = useQueryClient()
  const url = `/clinics/${clinica.id}/mensagens/aniversario`
  const q = useQuery({ queryKey: ['aniversario', clinica.id], queryFn: () => api.get<ConfigAniversario>(url) })

  const [ativo, setAtivo] = useState(false)
  const [texto, setTexto] = useState('')
  const [hora, setHora] = useState('09:00')
  const [previa, setPrevia] = useState('')

  useEffect(() => {
    if (!q.data) return
    setAtivo(q.data.ativo)
    setTexto(q.data.texto)
    setHora(q.data.hora)
    setPrevia(q.data.previa)
  }, [q.data])

  // RN-DP-02: prévia com dados reais, atualizada enquanto digita
  useEffect(() => {
    if (!texto.trim()) return
    const t = setTimeout(() => {
      api.post<{ previa: string }>(`${url}/previa`, { texto }).then((r) => setPrevia(r.previa)).catch(() => undefined)
    }, 400)
    return () => clearTimeout(t)
  }, [texto, url])

  const salvar = useMutation({
    mutationFn: () => api.put<ConfigAniversario>(url, { ativo, texto, hora }),
    onSuccess: () => {
      aviso.ok('Mensagem de aniversário salva.')
      qc.invalidateQueries({ queryKey: ['aniversario'] })
    },
    onError: aviso.erro,
  })

  if (q.isLoading || !q.data) return <p className="text-sm text-muted">Carregando…</p>
  const limite = q.data.limite

  return (
    <div className="grid max-w-5xl gap-6 lg:grid-cols-2">
      <Secao titulo="Mensagem de aniversário" icone={<Cake className="size-5" />}>
        <div className="flex flex-col gap-4">
          <label className="flex items-center gap-3 text-sm">
            <input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} className="size-4 accent-[var(--primary)]" />
            Enviar mensagem no dia do aniversário do {pal.cliente}
          </label>
          <Campo rotulo="Horário de envio" ajuda={`No fuso da clínica. Cada ${pal.cliente} recebe 1 vez por ano.`}>
            <Entrada type="time" value={hora} onChange={(e) => setHora(e.target.value)} className="w-32" />
          </Campo>
          <Campo rotulo="Texto" ajuda={`Use {nome} (primeiro nome) e {clinica}. ${texto.length}/${limite} caracteres.`}>
            <textarea value={texto} maxLength={limite} rows={6} onChange={(e) => setTexto(e.target.value)}
              className="rounded-xl border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-primary" />
          </Campo>
          <p className="text-xs text-muted">
            Quem responder "PARAR" ou "SAIR" deixa de receber. Os lembretes de {pal.atendimento} continuam.
          </p>
          {podeEditar && (
            <div>
              <Botao onClick={() => salvar.mutate()} disabled={salvar.isPending || !texto.trim()}>
                {salvar.isPending ? 'Salvando…' : 'Salvar'}
              </Botao>
            </div>
          )}
        </div>
      </Secao>
      <Secao titulo="Prévia">
        <div className="rounded-2xl bg-surface-muted p-4">
          <p className="max-w-[85%] whitespace-pre-line rounded-2xl rounded-tl-sm bg-surface p-3 text-sm shadow-sm">{previa}</p>
        </div>
        <p className="mt-3 text-xs text-muted">Exemplo com o nome de um {pal.cliente} da clínica.</p>
      </Secao>
    </div>
  )
}
