import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, KeyRound, XCircle } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Secao, Seletor, Selo } from '../../components/ui'
import { api, type IaClinica as Estado, type ProvedorIa, type TesteIa } from '../../lib/api'
import { useClinica } from '../../lib/clinica'

/** Etapa 10A (D42, D43, D46): provedor, modelo e chave de IA da clínica. A chave só vai, nunca volta. */
export function IaClinica({ podeEditar }: { podeEditar: boolean }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const url = `/clinics/${clinica.id}/config/ia`
  const q = useQuery({ queryKey: ['config', 'ia', clinica.id], queryFn: () => api.get<Estado>(url) })
  const [provedor, setProvedor] = useState<ProvedorIa>('openai')
  const [modelo, setModelo] = useState('')
  const [chave, setChave] = useState('')
  const [teste, setTeste] = useState<TesteIa | null>(null)
  const [confirmarApagar, setConfirmarApagar] = useState(false)

  useEffect(() => {
    if (!q.data) return
    setProvedor(q.data.provedor ?? 'opencode')
    setModelo(q.data.modelo ?? '')
  }, [q.data])

  const depois = (e: Estado) => {
    qc.setQueryData(['config', 'ia', clinica.id], e)
    qc.invalidateQueries({ queryKey: ['clinica'] })
    setChave('')
    setTeste(null)
  }
  const salvar = useMutation({
    mutationFn: () => api.put<Estado>(url, { provedor, modelo: modelo.trim(), chave: chave.trim() || null }),
    onSuccess: (e) => { depois(e); aviso.ok('IA da clínica salva.') },
    onError: aviso.erro,
  })
  const apagar = useMutation({
    mutationFn: () => api.delete<Estado>(`${url}/chave`),
    onSuccess: (e) => { depois(e); setConfirmarApagar(false); aviso.ok('Chave apagada.') },
    onError: aviso.erro,
  })
  const testar = useMutation({
    mutationFn: () => api.post<TesteIa>(`${url}/testar`, { provedor, modelo: modelo.trim(), chave: chave.trim() || null }),
    onSuccess: setTeste,
    onError: aviso.erro,
  })

  if (!q.data) return <p className="text-sm text-muted">Carregando…</p>
  const e = q.data
  const info = e.provedores.find((p) => p.id === provedor)
  const mesmaChave = e.tem_chave && !e.chave_ilegivel && e.provedor === provedor
  const aprovados = info?.modelos_aprovados ?? []
  const aprovado = aprovados.includes(modelo.trim())
  const podeSalvar = !!modelo.trim() && (mesmaChave || chave.trim().length >= 8)

  function enviar(ev: FormEvent) {
    ev.preventDefault()
    if (podeSalvar) salvar.mutate()
  }

  return (
    <Secao titulo="Inteligência artificial" icone={<KeyRound className="size-5" />}
      acao={<Situacao e={e} />}>
      {e.chave_ilegivel && (
        <p role="alert" className="mb-4 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
          A chave salva não pode mais ser lida (a chave-mestra do servidor mudou). Cole a chave de novo.
        </p>
      )}
      <form onSubmit={enviar}>
        <fieldset disabled={!podeEditar} className="grid gap-4 md:grid-cols-3">
          <Campo rotulo="Provedor">
            <Seletor value={provedor} onChange={(ev) => { setProvedor(ev.target.value as ProvedorIa); setTeste(null) }}>
              {e.provedores.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
            </Seletor>
          </Campo>
          <Campo rotulo="Modelo"
            ajuda={!modelo.trim() ? 'Escreva o nome exato do modelo, como aparece no provedor.'
              : aprovado ? 'Aprovado na bateria de testes da plataforma.'
              : 'Ainda não passou na bateria de testes da plataforma. Teste com calma antes de usar com clientes.'}>
            <Entrada list="modelos-aprovados" required maxLength={120} value={modelo} spellCheck={false}
              onChange={(ev) => { setModelo(ev.target.value); setTeste(null) }}
              placeholder={aprovados[0] ?? 'nome-do-modelo'} />
            <datalist id="modelos-aprovados">{aprovados.map((m) => <option key={m} value={m} />)}</datalist>
          </Campo>
          <Campo rotulo="Chave da API" ajuda={info ? `Onde pegar: ${info.onde}.` : undefined}>
            <Entrada type="password" autoComplete="off" spellCheck={false} maxLength={400} value={chave}
              onChange={(ev) => { setChave(ev.target.value); setTeste(null) }}
              placeholder={mesmaChave ? `Salva, termina em ${e.chave_final}. Vazio = manter` : 'Cole a chave aqui'} />
          </Campo>
        </fieldset>

        {teste && (
          <p role="status" className={`mt-4 flex items-center gap-2 text-sm ${teste.ok ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}`}>
            {teste.ok ? <CheckCircle2 className="size-4" /> : <XCircle className="size-4" />}
            {teste.ok ? `Conexão funcionando (${((teste.ms ?? 0) / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} s).` : teste.detalhe}
          </p>
        )}

        {podeEditar && (
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <p className="max-w-xl text-xs text-muted">
              A chave fica guardada criptografada e nunca volta para a tela. O custo das conversas é cobrado na conta da clínica no provedor.
            </p>
            <div className="flex flex-wrap gap-2">
              {e.tem_chave && !confirmarApagar && (
                <Botao type="button" variante="fantasma" onClick={() => setConfirmarApagar(true)}>Apagar chave</Botao>
              )}
              <Botao type="button" variante="secundario" disabled={!podeSalvar || testar.isPending} onClick={() => testar.mutate()}>
                {testar.isPending ? 'Testando…' : 'Testar conexão'}
              </Botao>
              <Botao type="submit" disabled={!podeSalvar || salvar.isPending}>{salvar.isPending ? 'Salvando…' : 'Salvar IA'}</Botao>
            </div>
          </div>
        )}
        {confirmarApagar && (
          <div role="alert" className="mt-3 flex flex-wrap items-center gap-2 rounded-xl border border-line px-3 py-2 text-sm">
            {e.usa_plataforma && e.plataforma.configurada
              ? 'Apagar a chave? A assistente passa a usar a chave da plataforma.'
              : 'Apagar a chave? A assistente fica desligada e as conversas vão direto para a equipe.'}
            <span className="ml-auto flex gap-2">
              <Botao type="button" variante="fantasma" onClick={() => setConfirmarApagar(false)}>Manter</Botao>
              <Botao type="button" variante="perigo" disabled={apagar.isPending} onClick={() => apagar.mutate()}>Apagar</Botao>
            </span>
          </div>
        )}
      </form>
    </Secao>
  )
}

function Situacao({ e }: { e: Estado }) {
  if (e.origem === 'clinica') return <Selo cor="verde">Ligada · chave da clínica (…{e.chave_final})</Selo>
  if (e.origem === 'plataforma') return <Selo cor="azul">Ligada · chave da plataforma</Selo>
  return <Selo cor="ambar">Desligada</Selo>
}

/** Aviso no topo do painel quando a clínica está sem IA (D46). */
export function AvisoIaDesligada() {
  const { clinica } = useClinica()
  if (clinica.ia_ativa !== false) return null
  return (
    <p role="status" className="mb-4 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
      A assistente está desligada: a clínica ainda não tem chave de IA. As conversas vão direto para a equipe.
      O administrador da clínica cadastra a chave em Configurações › Assistente.
    </p>
  )
}
