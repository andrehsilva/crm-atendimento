import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { HeartHandshake, RotateCcw } from 'lucide-react'
import { api } from '../lib/api'
import { useClinica } from '../lib/clinica'
import { useAviso } from './Aviso'
import { Botao, Campo, Entrada, Secao } from './ui'

type Cfg = {
  pos_consulta_ativo: boolean
  pos_consulta_hora: string
  pos_consulta_texto: string
  pos_consulta_excluir: string[]
  retorno_ativo: boolean
  retorno_hora: string
  retorno_meses: number
  retorno_texto: string
  retorno_texto2: string
  previa: { pos_consulta: string; retorno: string; retorno2: string }
}

const area = 'rounded-xl border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-primary'

/** Etapa 25 (RN-AU, D100–D103): pós-consulta e retorno automáticos. Começam desligados; só o administrador muda. */
export function Automacoes({ podeEditar }: { podeEditar: boolean }) {
  const { clinica, cadastros } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const url = `/clinics/${clinica.id}/mensagens/automacoes`
  const q = useQuery({ queryKey: ['automacoes', clinica.id], queryFn: () => api.get<Cfg>(url) })
  const [f, setF] = useState<Omit<Cfg, 'previa'> | null>(null)
  useEffect(() => {
    if (q.data) {
      const { previa: _previa, ...resto } = q.data
      void _previa
      setF(resto)
    }
  }, [q.data])

  const salvar = useMutation({
    mutationFn: () => api.put<Cfg>(url, f),
    onSuccess: (r) => { qc.setQueryData(['automacoes', clinica.id], r); aviso.ok('Automações salvas.') },
    onError: aviso.erro,
  })
  if (!f || !q.data) return null
  const marcar = (id: string, fora: boolean) =>
    setF({ ...f, pos_consulta_excluir: fora ? [...f.pos_consulta_excluir, id] : f.pos_consulta_excluir.filter((x) => x !== id) })

  return (
    <>
      <Secao titulo="Pós-consulta" icone={<HeartHandshake className="size-5" />}>
        <fieldset disabled={!podeEditar} className="space-y-4">
          <label className="flex items-start gap-3 text-sm">
            <input type="checkbox" checked={f.pos_consulta_ativo} onChange={(e) => setF({ ...f, pos_consulta_ativo: e.target.checked })} className="mt-0.5 size-4 accent-[var(--primary)]" />
            <span>Mandar "como você está?" no dia seguinte
              <span className="block text-xs text-muted">Para quem foi marcado como "Compareceu". Se responder com dúvida ou queixa, a assistente atende e chama a equipe se precisar. Quem pediu PARAR não recebe.</span>
            </span>
          </label>
          <Campo rotulo="Horário"><Entrada type="time" value={f.pos_consulta_hora} onChange={(e) => setF({ ...f, pos_consulta_hora: e.target.value })} className="!w-auto" /></Campo>
          <Campo rotulo="Mensagem" ajuda="Use {nome}, {clinica} e {procedimento}.">
            <textarea rows={3} maxLength={1000} value={f.pos_consulta_texto} onChange={(e) => setF({ ...f, pos_consulta_texto: e.target.value })} className={area} />
          </Campo>
          <div>
            <p className="mb-2 text-sm font-medium">Procedimentos que recebem</p>
            <div className="flex flex-wrap gap-x-4 gap-y-2">
              {cadastros.procedimentos.map((p) => (
                <label key={p.id} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={!f.pos_consulta_excluir.includes(p.id)} onChange={(e) => marcar(p.id, !e.target.checked)} />{p.name}
                </label>
              ))}
            </div>
          </div>
          <p className="whitespace-pre-line rounded-2xl bg-surface-muted p-3 text-sm text-muted">Exemplo: {q.data.previa.pos_consulta}</p>
        </fieldset>
      </Secao>

      <Secao titulo="Retorno" icone={<RotateCcw className="size-5" />}>
        <fieldset disabled={!podeEditar} className="space-y-4">
          <label className="flex items-start gap-3 text-sm">
            <input type="checkbox" checked={f.retorno_ativo} onChange={(e) => setF({ ...f, retorno_ativo: e.target.checked })} className="mt-0.5 size-4 accent-[var(--primary)]" />
            <span>Convidar para voltar na data certa
              <span className="block text-xs text-muted">Na data do "volta em" do tratamento concluído, ou depois de X meses sem vir. Só para quem não tem nada marcado nem tratamento aberto. Sem resposta, mais 1 convite 15 dias depois; depois para. Quem pediu PARAR não recebe. Ao ligar, não dispara para o histórico antigo (esses ficam no relatório de recall).</span>
            </span>
          </label>
          <div className="flex flex-wrap gap-4">
            <Campo rotulo="Horário"><Entrada type="time" value={f.retorno_hora} onChange={(e) => setF({ ...f, retorno_hora: e.target.value })} className="!w-auto" /></Campo>
            <Campo rotulo="Meses sem vir" ajuda="Quando não há 'volta em'.">
              <Entrada type="number" min={1} max={36} value={f.retorno_meses} onChange={(e) => setF({ ...f, retorno_meses: Number(e.target.value) })} className="!w-24" />
            </Campo>
          </div>
          <Campo rotulo="1º convite" ajuda="Use {nome} e {clinica}. Quando a pessoa responder, a assistente marca.">
            <textarea rows={3} maxLength={1000} value={f.retorno_texto} onChange={(e) => setF({ ...f, retorno_texto: e.target.value })} className={area} />
          </Campo>
          <Campo rotulo="2º convite (15 dias depois, se não respondeu)">
            <textarea rows={2} maxLength={1000} value={f.retorno_texto2} onChange={(e) => setF({ ...f, retorno_texto2: e.target.value })} className={area} />
          </Campo>
          <p className="whitespace-pre-line rounded-2xl bg-surface-muted p-3 text-sm text-muted">Exemplo: {q.data.previa.retorno}</p>
        </fieldset>
        {podeEditar && <div className="mt-4 flex justify-end"><Botao disabled={salvar.isPending} onClick={() => salvar.mutate()}>Salvar automações</Botao></div>}
      </Secao>
    </>
  )
}
