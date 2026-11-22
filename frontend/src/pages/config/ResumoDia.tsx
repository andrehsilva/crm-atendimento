import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Sun } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Modal, Selo } from '../../components/ui'
import { api } from '../../lib/api'
import { useClinica } from '../../lib/clinica'

type Resumo = {
  ativo: boolean
  whatsapp: string | null
  hora: string
  ultimo: { dia: string; status: 'enviado' | 'falhou' | 'sem_consulta' | 'pulado'; erro: string | null; enviado_em: string | null } | null
}

const STATUS: Record<NonNullable<Resumo['ultimo']>['status'], [string, 'verde' | 'vermelho' | 'cinza']> = {
  enviado: ['enviado', 'verde'], falhou: ['não saiu', 'vermelho'], sem_consulta: ['sem consulta, não mandou', 'cinza'], pulado: ['não mandou', 'cinza'],
}

/** Etapa 23 (RN-RS, D96–D98): resumo do dia no WhatsApp pessoal do profissional. Só o administrador ativa. */
export function ModalResumoDia({ prof, podeEditar, onFechar }: { prof: { id: string; nome: string } | null; podeEditar: boolean; onFechar: () => void }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const base = `/clinics/${clinica.id}/config/profissionais/${prof?.id}/resumo`
  const q = useQuery({ queryKey: ['config', 'resumo', prof?.id], queryFn: () => api.get<Resumo>(base), enabled: !!prof })
  const previa = useQuery({
    queryKey: ['config', 'resumo', 'previa', prof?.id],
    queryFn: () => api.get<{ dia: string; texto: string | null }>(`${base}/previa`),
    enabled: !!prof,
  })
  const [f, setF] = useState({ ativo: false, whatsapp: '', hora: '07:00' })
  useEffect(() => {
    if (q.data) setF({ ativo: q.data.ativo, whatsapp: q.data.whatsapp ?? '', hora: q.data.hora })
  }, [q.data])

  const salvar = useMutation({
    mutationFn: () => api.put<Resumo>(base, { ativo: f.ativo, whatsapp: f.whatsapp || null, hora: f.hora }),
    onSuccess: (r) => {
      qc.setQueryData(['config', 'resumo', prof?.id], r)
      aviso.ok(r.ativo ? `Resumo do dia ativado: sai às ${r.hora} nos dias com consulta.` : 'Resumo do dia desativado.')
      onFechar()
    },
    onError: aviso.erro,
  })

  const teste = useMutation({
    mutationFn: () => api.post<{ dia: string }>(`${base}/teste`, {}),
    onSuccess: (r) => aviso.ok(`Teste enviado (agenda de ${r.dia.split('-').reverse().slice(0, 2).join('/')}). Confira o WhatsApp do profissional.`),
    onError: aviso.erro,
  })

  const ult = q.data?.ultimo
  const diaPrevia = previa.data?.dia.split('-').reverse().slice(0, 2).join('/')
  return (
    <Modal titulo={`Resumo do dia · ${prof?.nome ?? ''}`} aberto={!!prof} onFechar={onFechar} largura="max-w-2xl">
      <div className="grid gap-5 md:grid-cols-2">
        <fieldset disabled={!podeEditar} className="grid content-start gap-4">
          <p className="text-sm text-muted">
            Logo de manhã, o profissional recebe no WhatsApp <b>pessoal</b> a agenda do dia: horários, primeiro nome dos pacientes,
            procedimentos e quem já confirmou. Sai pelo WhatsApp da clínica.
          </p>
          <label className="flex items-start gap-3 text-sm">
            <input type="checkbox" checked={f.ativo} onChange={(e) => setF({ ...f, ativo: e.target.checked })} className="mt-0.5 size-4 accent-[var(--primary)]" />
            <span>Ativar o resumo do dia
              <span className="block text-xs text-muted">Só ative se o profissional pediu: a mensagem leva nomes de pacientes para o celular pessoal dele.</span>
            </span>
          </label>
          <Campo rotulo="WhatsApp pessoal do profissional">
            <Entrada value={f.whatsapp} onChange={(e) => setF({ ...f, whatsapp: e.target.value })} placeholder="(11) 98765-4321" inputMode="tel" />
          </Campo>
          <Campo rotulo="Horário" ajuda="Só em dias que a clínica abre e que ele tem consulta. Uma vez por dia: mudanças depois aparecem no painel, não geram nova mensagem.">
            <Entrada type="time" value={f.hora} onChange={(e) => setF({ ...f, hora: e.target.value })} />
          </Campo>
          {ult && (
            <p className="text-xs text-muted">
              Último: {ult.dia.split('-').reverse().slice(0, 2).join('/')} <Selo cor={STATUS[ult.status][1]}>{STATUS[ult.status][0]}</Selo>
              {ult.erro && <span className="block">Motivo: {ult.erro}</span>}
            </p>
          )}
        </fieldset>
        <div>
          <p className="mb-2 flex items-center gap-2 text-sm font-medium"><Sun className="size-4 text-primary" />Como fica amanhã{diaPrevia && ` (${diaPrevia})`}</p>
          <div className="rounded-2xl bg-surface-muted p-4">
            {previa.isLoading ? <p className="text-sm text-muted">Carregando…</p>
              : previa.data?.texto
                ? <p className="whitespace-pre-line rounded-2xl rounded-tl-sm bg-surface p-3 text-sm shadow-sm">{previa.data.texto}</p>
                : <p className="text-sm text-muted">Sem consulta amanhã: nesse dia não sai mensagem.</p>}
          </div>
        </div>
      </div>
      {podeEditar && (
        <div className="mt-6 flex flex-wrap justify-end gap-2">
          <Botao variante="secundario" className="mr-auto" disabled={!q.data?.whatsapp || teste.isPending} onClick={() => teste.mutate()}
            title="Manda agora o resumo do próximo dia com consulta, para o número já salvo">
            {teste.isPending ? 'Enviando…' : 'Mandar teste agora'}
          </Botao>
          <Botao variante="fantasma" onClick={onFechar}>Cancelar</Botao>
          <Botao disabled={salvar.isPending || (f.ativo && !f.whatsapp.trim())} onClick={() => salvar.mutate()}>Salvar</Botao>
        </div>
      )}
    </Modal>
  )
}
