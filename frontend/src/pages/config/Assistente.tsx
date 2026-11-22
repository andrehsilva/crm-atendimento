import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bot, CalendarClock, Sparkles } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Secao, Seletor } from '../../components/ui'
import { api, type AssistenteCfg } from '../../lib/api'
import { useClinica } from '../../lib/clinica'
import { useTermos } from '../../lib/termos'
import { IaClinica } from './IaClinica'

/** Nome, tom e regras da agenda (RN marcadas como "Config"). Valem para ações novas. */
export function Assistente({ podeEditar, comIa = true }: { podeEditar: boolean; comIa?: boolean }) {
  const { clinica } = useClinica()
  const pal = useTermos()
  const aviso = useAviso()
  const qc = useQueryClient()
  const url = `/clinics/${clinica.id}/config/assistente`
  const q = useQuery({ queryKey: ['config', 'assistente', clinica.id], queryFn: () => api.get<AssistenteCfg>(url) })
  const [f, setF] = useState<AssistenteCfg | null>(null)
  useEffect(() => { if (q.data) setF(q.data) }, [q.data])
  const salvar = useMutation({
    mutationFn: () => api.put(url, f),
    onSuccess: () => { aviso.ok('Configurações da assistente salvas.'); qc.invalidateQueries({ queryKey: ['config'] }) },
    onError: aviso.erro,
  })
  if (!f) return <p className="text-sm text-muted">Carregando…</p>
  const num = (k: keyof AssistenteCfg) => (e: { target: { value: string } }) => setF({ ...f, [k]: Number(e.target.value) })

  return (
    <div className="grid max-w-5xl gap-6">
      {comIa && <IaClinica podeEditar={podeEditar} />}
      <form onSubmit={(e) => { e.preventDefault(); salvar.mutate() }} className="grid gap-6 lg:grid-cols-2">
        <Secao titulo="Como ela se apresenta" icone={<Bot className="size-5" />}>
          <fieldset disabled={!podeEditar} className="flex flex-col gap-4">
            <Campo rotulo="Nome da assistente"><Entrada required maxLength={40} value={f.nome_assistente} onChange={(e) => setF({ ...f, nome_assistente: e.target.value })} /></Campo>
            <Campo rotulo={`Como trata o ${pal.cliente}`}>
              <Seletor value={f.tratamento} onChange={(e) => setF({ ...f, tratamento: e.target.value as AssistenteCfg['tratamento'] })}>
                <option value="você">Você (mais próximo)</option>
                <option value="senhor(a)">Senhor(a) (mais formal)</option>
              </Seletor>
            </Campo>
            <label className="flex items-start gap-3 text-sm">
              <input type="checkbox" checked={f.mostrar_precos} onChange={(e) => setF({ ...f, mostrar_precos: e.target.checked })} className="mt-0.5 size-4 accent-[var(--primary)]" />
              <span>Informar preços no chat <span className="block text-xs text-muted">Só os preços cadastrados em Procedimentos. Desligado: "a clínica não divulga preços pelo chat".</span></span>
            </label>
            <label className="flex items-start gap-3 text-sm">
              <input type="checkbox" checked={f.aceitar_audio} onChange={(e) => setF({ ...f, aceitar_audio: e.target.checked })} className="mt-0.5 size-4 accent-[var(--primary)]" />
              <span>Aceitar áudios no WhatsApp <span className="block text-xs text-muted">O áudio vira texto e a assistente responde (até 2 min; o custo entra no Uso da IA). Desligado: ela pede para a pessoa escrever.</span></span>
            </label>
          </fieldset>
        </Secao>
        <Secao titulo="Regras da agenda" icone={<CalendarClock className="size-5" />}>
          <fieldset disabled={!podeEditar} className="grid gap-4 sm:grid-cols-2">
            <Campo rotulo="Antecedência mínima (horas)" ajuda="Não marca em cima da hora.">
              <Entrada type="number" min={0} max={168} step={0.5} value={f.antecedencia_min_horas} onChange={num('antecedencia_min_horas')} />
            </Campo>
            <Campo rotulo="Marca até quantos dias à frente">
              <Entrada type="number" min={1} max={365} value={f.horizonte_dias} onChange={num('horizonte_dias')} />
            </Campo>
            <Campo rotulo="Aviso de cancelamento (horas)" ajuda="Cancelar com menos que isso: avisa a política e sinaliza a recepção.">
              <Entrada type="number" min={0} max={168} value={f.aviso_cancelamento_horas} onChange={num('aviso_cancelamento_horas')} />
            </Campo>
            <Campo rotulo={`${pal.Atendimentos} futur${pal.o}s por ${pal.cliente}`}>
              <Entrada type="number" min={1} max={10} value={f.limite_consultas_futuras} onChange={num('limite_consultas_futuras')} />
            </Campo>
            <Campo rotulo="Horário do lembrete" ajuda={`No dia útil anterior ${pal.o === 'a' ? 'à' : 'ao'} ${pal.atendimento}.`}>
              <Entrada type="time" value={f.lembrete_hora} onChange={(e) => setF({ ...f, lembrete_hora: e.target.value })} />
            </Campo>
          </fieldset>
        </Secao>
        <Secao titulo="Jeito da clínica" icone={<Sparkles className="size-5" />} className="lg:col-span-2">
          <p className="mb-3 max-w-3xl text-sm text-muted">
            Diga com suas palavras como a assistente deve atender aqui: o tom, o que oferecer primeiro, o que evitar.
            Ela segue isso sempre que não contrariar as regras de segurança (por exemplo, ela sempre confirma antes de marcar).
          </p>
          <fieldset disabled={!podeEditar}>
            <textarea rows={5} maxLength={1500} value={f.jeito_clinica} onChange={(e) => setF({ ...f, jeito_clinica: e.target.value })}
              aria-label="Jeito da clínica"
              placeholder={'Exemplos:\n- Somos uma clínica infantil: fale de forma leve e acolhedora.\n- Sempre ofereça primeiro a avaliação gratuita.\n- Não marque extração sem uma avaliação antes.'}
              className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-primary disabled:opacity-60" />
            <p className="mt-1 text-right text-xs text-muted">{f.jeito_clinica.length}/1500</p>
          </fieldset>
        </Secao>
        {podeEditar && (
          <div className="flex items-center justify-end gap-3 lg:col-span-2">
            <p className="text-xs text-muted">As mudanças valem para novas ações; {pal.atendimentos} já marcad{pal.o}s não mudam.</p>
            <Botao type="submit" disabled={salvar.isPending}>{salvar.isPending ? 'Salvando…' : 'Salvar'}</Botao>
          </div>
        )}
      </form>
    </div>
  )
}
