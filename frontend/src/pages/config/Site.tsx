import { useEffect, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, Globe, Monitor, Smartphone } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Secao, Selo } from '../../components/ui'
import { api, type ProfissionalCfg } from '../../lib/api'
import { CORES_SUGERIDAS, corValida, legivel } from '../../lib/marca'
import { FotoProfissional } from './Profissionais'
import { useClinica } from '../../lib/clinica'

type EstadoSite = {
  template: string
  publicado: boolean
  url: string
  pode_publicar: boolean
  cores: Record<string, string | null>
  cor_clinica: string
  layouts: { id: string; nome: string; descricao: string }[]
}

/** Etapa 11A (D58, D62): o site de apresentação da clínica — layout, prévia e publicação. */
export function Site({ podeEditar }: { podeEditar: boolean }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const base = `/clinics/${clinica.id}/site`
  const chave = ['config', 'site', clinica.id]
  const q = useQuery({ queryKey: chave, queryFn: () => api.get<EstadoSite>(base) })
  const [layout, setLayout] = useState('classico')
  const [celular, setCelular] = useState(false)
  // cor em edição por layout: null = cor da clínica
  const [cores, setCores] = useState<Record<string, string | null>>({})
  useEffect(() => { if (q.data) { setLayout(q.data.template); setCores(q.data.cores) } }, [q.data])

  const salvar = useMutation({
    mutationFn: () => api.put<EstadoSite>(base, { template: layout }),
    onSuccess: (e) => { qc.setQueryData(chave, e); aviso.ok(e.publicado ? 'Layout salvo. O site já mostra o novo layout.' : 'Layout salvo.') },
    onError: aviso.erro,
  })
  const publicar = useMutation({
    mutationFn: (sim: boolean) => api.post<EstadoSite>(`${base}/publicar`, { publicado: sim }),
    onSuccess: (e) => { qc.setQueryData(chave, e); aviso.ok(e.publicado ? 'Site publicado!' : 'Site fora do ar.') },
    onError: aviso.erro,
  })

  const salvarCor = useMutation({
    mutationFn: () => api.put<EstadoSite>(`${base}/cor`, { layout, cor: cores[layout] ?? null }),
    onSuccess: (e) => { qc.setQueryData(chave, e); setCores(e.cores); aviso.ok('Cor salva.') },
    onError: aviso.erro,
  })

  if (!q.data) return <p className="text-sm text-muted">Carregando…</p>
  const e = q.data
  const mudou = layout !== e.template
  const corAtual = cores[layout] ?? null
  const corMudou = (corAtual ?? null) !== (e.cores[layout] ?? null)
  const corOk = !corAtual || legivel(corAtual)
  const nomeLayout = e.layouts.find((l) => l.id === layout)?.nome ?? ''
  const previa = `/api${base}/previa?layout=${layout}${corAtual && corOk ? `&cor=${encodeURIComponent(corAtual)}` : ''}`

  return (
    <div className="grid max-w-6xl gap-6">
      <Secao titulo="Site da clínica" icone={<Globe className="size-5" />}
        acao={e.publicado ? <Selo cor="verde">publicado</Selo> : <Selo cor="ambar">não publicado</Selo>}>
        <p className="max-w-3xl text-sm text-muted">
          Uma página de apresentação montada com os dados que a clínica já cadastrou: nome, logo, cor, sobre, procedimentos,
          equipe, horários e endereço. O botão "Agendar pelo WhatsApp" leva direto para a assistente.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          {e.publicado ? (
            <a href={e.url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-2 break-all text-sm font-medium text-primary underline">
              {e.url} <ExternalLink className="size-4 shrink-0" />
            </a>
          ) : (
            <span className="text-sm text-muted">Endereço depois de publicar: {e.url}</span>
          )}
          {podeEditar && (
            <span className="ml-auto flex gap-2">
              {e.publicado
                ? <Botao variante="secundario" disabled={publicar.isPending} onClick={() => publicar.mutate(false)}>Tirar do ar</Botao>
                : <Botao disabled={!e.pode_publicar || mudou || publicar.isPending} onClick={() => publicar.mutate(true)}
                    title={mudou ? 'Salve o layout antes de publicar' : undefined}>Publicar site</Botao>}
            </span>
          )}
        </div>
        {!e.pode_publicar && <p className="mt-2 text-xs text-muted">Para publicar, conclua antes os Primeiros passos.</p>}
      </Secao>

      <Secao titulo="Layout">
        <fieldset disabled={!podeEditar}>
          <legend className="sr-only">Escolha o layout do site</legend>
          <div className="grid gap-3 md:grid-cols-3">
            {e.layouts.map((l) => (
              <label key={l.id}
                className={`flex cursor-pointer flex-col gap-1 rounded-2xl border p-4 transition has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-primary ${layout === l.id ? 'border-primary bg-primary-soft' : 'border-line hover:border-muted'}`}>
                <span className="flex items-center gap-2 font-medium">
                  <input type="radio" name="layout" value={l.id} checked={layout === l.id} onChange={() => setLayout(l.id)}
                    className="size-4 accent-[var(--primary)]" />
                  {l.nome}
                  {l.id === e.template && <span className="text-xs font-normal text-muted">(atual)</span>}
                </span>
                <span className="text-sm text-muted">{l.descricao}</span>
              </label>
            ))}
          </div>
        </fieldset>
        {podeEditar && mudou && (
          <div className="mt-4 flex justify-end gap-2">
            <Botao variante="fantasma" onClick={() => setLayout(e.template)}>Voltar ao atual</Botao>
            <Botao disabled={salvar.isPending} onClick={() => salvar.mutate()}>{salvar.isPending ? 'Salvando…' : 'Salvar layout'}</Botao>
          </div>
        )}
      </Secao>

      <Secao titulo={`Cor do layout ${nomeLayout}`}>
        <p className="mb-4 max-w-3xl text-sm text-muted">
          Cada layout pode ter a sua cor. Ela vale só para o site; o painel continua com a cor da clínica.
        </p>
        <fieldset disabled={!podeEditar} className="flex flex-wrap items-center gap-3">
          <legend className="sr-only">Cor do layout</legend>
          <BolinhaCor cor={e.cor_clinica} rotulo="Cor da clínica" ativa={!corAtual} onClick={() => setCores({ ...cores, [layout]: null })} destaque />
          {CORES_SUGERIDAS.filter((c) => c.cor !== e.cor_clinica).map((c) => (
            <BolinhaCor key={c.cor} cor={c.cor} rotulo={c.nome} ativa={corAtual === c.cor} onClick={() => setCores({ ...cores, [layout]: c.cor })} />
          ))}
          <label className="flex items-center gap-2 text-sm text-muted">
            <input type="color" value={corAtual ?? e.cor_clinica} onChange={(ev) => setCores({ ...cores, [layout]: ev.target.value })}
              className="size-9 cursor-pointer rounded-full border border-line bg-transparent p-0.5" aria-label="Escolher outra cor" />
            Outra cor
          </label>
          <span className="font-mono text-xs text-muted">{corAtual ?? `${e.cor_clinica} (da clínica)`}</span>
        </fieldset>
        {corAtual && corValida(corAtual) && !corOk && (
          <p role="alert" className="mt-3 text-sm text-red-700 dark:text-red-400">Essa cor é clara demais: o texto branco dos botões ficaria difícil de ler. Escolha um tom mais escuro.</p>
        )}
        {podeEditar && corMudou && (
          <div className="mt-4 flex justify-end gap-2">
            <Botao variante="fantasma" onClick={() => setCores({ ...cores, [layout]: e.cores[layout] ?? null })}>Desfazer</Botao>
            <Botao disabled={!corOk || salvarCor.isPending} onClick={() => salvarCor.mutate()}>{salvarCor.isPending ? 'Salvando…' : 'Salvar cor'}</Botao>
          </div>
        )}
      </Secao>

      <FotosEquipe podeEditar={podeEditar} />

      <Secao titulo="Prévia" acao={
        <div role="group" aria-label="Tamanho da prévia" className="flex gap-1 rounded-xl bg-surface-muted p-1">
          <BotaoTamanho ativo={!celular} onClick={() => setCelular(false)} icone={<Monitor className="size-4" />} rotulo="Computador" />
          <BotaoTamanho ativo={celular} onClick={() => setCelular(true)} icone={<Smartphone className="size-4" />} rotulo="Celular" />
        </div>
      }>
        <div className="flex justify-center rounded-2xl bg-surface-muted p-3">
          <iframe key={previa} title={`Prévia do site no layout ${nomeLayout}`} src={previa}
            className={`h-[720px] rounded-xl border border-line bg-white transition-[width] ${celular ? 'w-[390px]' : 'w-full'}`} />
        </div>
      </Secao>
    </div>
  )
}

function BotaoTamanho({ ativo, onClick, icone, rotulo }: { ativo: boolean; onClick: () => void; icone: ReactNode; rotulo: string }) {
  return (
    <button type="button" aria-pressed={ativo} onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm ${ativo ? 'bg-surface font-medium shadow-sm' : 'text-muted'}`}>
      {icone}{rotulo}
    </button>
  )
}

function BolinhaCor({ cor, rotulo, ativa, onClick, destaque }: { cor: string; rotulo: string; ativa: boolean; onClick: () => void; destaque?: boolean }) {
  return (
    <button type="button" title={rotulo} aria-label={rotulo} aria-pressed={ativa} onClick={onClick}
      className={`grid size-9 place-items-center rounded-full ring-offset-2 ring-offset-surface transition ${ativa ? 'ring-2 ring-text' : ''}`}
      style={{ background: cor }}>
      {destaque && <span className="text-[10px] font-bold text-white">●</span>}
    </button>
  )
}

/** Fotos de quem aparece no site. Com mais de uma pessoa, o site mostra um carrossel que troca sozinho. */
function FotosEquipe({ podeEditar }: { podeEditar: boolean }) {
  const { clinica } = useClinica()
  const base = `/clinics/${clinica.id}/config`
  const q = useQuery({ queryKey: ['config', 'profissionais', clinica.id], queryFn: () => api.get<{ profissionais: ProfissionalCfg[] }>(`${base}/profissionais`) })
  const ativos = (q.data?.profissionais ?? []).filter((p) => p.ativo)
  if (!q.data) return null
  return (
    <Secao titulo="Fotos da equipe">
      <p className="mb-4 max-w-3xl text-sm text-muted">
        {ativos.length > 1
          ? 'Com mais de um profissional, o topo do site vira um carrossel que mostra cada pessoa. Quem tem foto aparece primeiro.'
          : 'A foto aparece em destaque no topo do site.'} A apresentação curta de cada um fica em Configurações › Profissionais.
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        {ativos.map((p) => (
          <div key={p.id}>
            <p className="mb-1 text-sm font-medium">{p.nome}</p>
            {podeEditar
              ? <FotoProfissional id={p.id} base={base} nome={p.nome} versao={p.foto_versao} />
              : <p className="text-sm text-muted">{p.foto_versao ? 'Com foto' : 'Sem foto'}</p>}
          </div>
        ))}
      </div>
    </Secao>
  )
}
