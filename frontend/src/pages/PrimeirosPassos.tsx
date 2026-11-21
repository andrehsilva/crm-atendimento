import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Hourglass, LogOut, ShieldCheck } from 'lucide-react'
import { useAviso } from '../components/Aviso'
import { Botao } from '../components/ui'
import { api, type ConfigInicial, type EtapaInicial } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useClinica } from '../lib/clinica'
import { Assistente } from './config/Assistente'
import { Horarios } from './config/Horarios'
import { IaClinica } from './config/IaClinica'
import { Perfil } from './config/Perfil'
import { Procedimentos } from './config/Procedimentos'
import { Profissionais } from './config/Profissionais'

type Codigo = EtapaInicial['codigo']

const AJUDA: Record<Codigo, string> = {
  clinica: 'Nome, endereço, telefone de urgência e o tipo de negócio. O segmento ajusta as palavras e o jeito da assistente.',
  assistente: 'Como a assistente se chama e como ela trata quem escreve. Ajuste também as regras da agenda.',
  aparencia: 'Escolha a cor da clínica e envie a logo (opcional). Se gostar da cor padrão, é só confirmar.',
  horarios: 'Os dias e horários em que a clínica atende. A assistente só marca dentro deles.',
  equipe: 'Os procedimentos que a clínica faz e quem faz cada um. Sem isso a assistente não tem o que marcar.',
  ia: 'A chave de IA da clínica. Salve e clique em "Testar conexão": a etapa só fica pronta com o teste ok.',
}

/** Etapa 10C (D51–D53): enquanto a clínica não conclui os primeiros passos, o painel mostra só isto. */
export function PrimeirosPassos() {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const url = `/clinics/${clinica.id}/config/inicial`
  const chave = ['config', 'inicial', clinica.id]
  const q = useQuery({ queryKey: chave, queryFn: () => api.get<ConfigInicial>(url) })
  const [atual, setAtual] = useState<Codigo | null>(null)

  // Qualquer salvamento dentro das etapas (perfil, horários, chave…) reconfere o que falta
  useEffect(() => qc.getMutationCache().subscribe((ev) => {
    if (ev.type === 'updated' && ev.action.type === 'success') qc.invalidateQueries({ queryKey: chave })
  }), [qc]) // eslint-disable-line react-hooks/exhaustive-deps

  const etapas = q.data?.etapas ?? []
  const aberta = atual ?? etapas.find((e) => !e.ok)?.codigo ?? 'clinica'
  const prontas = etapas.filter((e) => e.ok).length

  const concluir = useMutation({
    mutationFn: () => api.post(`${url}/concluir`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['clinica'] }); aviso.ok('Tudo pronto! O painel está liberado para a equipe.') },
    onError: aviso.erro,
  })
  const confirmarAparencia = useMutation({
    mutationFn: () => api.post<ConfigInicial>(`${url}/aparencia`),
    onSuccess: (e) => { qc.setQueryData(chave, e); setAtual(null) },
    onError: aviso.erro,
  })

  if (!q.data) return <Moldura><p className="text-sm text-muted">Carregando…</p></Moldura>
  const etapa = etapas.find((e) => e.codigo === aberta)!

  return (
    <Moldura>
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Primeiros passos</h1>
        <p className="mt-1 max-w-2xl text-muted">
          Antes de liberar o painel para a equipe, deixe {clinica.name} pronta para atender. {prontas} de {etapas.length} etapas prontas.
        </p>
      </div>
      <div className="grid gap-8 lg:grid-cols-[17rem_1fr]">
        <nav aria-label="Etapas" className="lg:sticky lg:top-6 lg:self-start">
          <ol className="flex flex-col gap-1">
            {etapas.map((e, i) => (
              <li key={e.codigo}>
                <button type="button" onClick={() => setAtual(e.codigo)} aria-current={e.codigo === aberta ? 'step' : undefined}
                  className={`flex w-full items-start gap-3 rounded-2xl px-3 py-2.5 text-left transition ${e.codigo === aberta ? 'bg-surface shadow-sm' : 'hover:bg-surface/60'}`}>
                  <span className={`mt-0.5 grid size-6 shrink-0 place-items-center rounded-full text-xs font-semibold ${e.ok ? 'bg-primary text-primary-contrast' : 'border border-line text-muted'}`}>
                    {e.ok ? <Check className="size-3.5" /> : i + 1}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium">{e.titulo}</span>
                    {!e.ok && e.falta && <span className="block text-xs text-muted">{e.falta}</span>}
                  </span>
                </button>
              </li>
            ))}
          </ol>
          <div className="mt-6 rounded-2xl bg-surface p-4">
            <Botao className="w-full" disabled={!q.data.pode_concluir || concluir.isPending} onClick={() => concluir.mutate()}>
              {concluir.isPending ? 'Concluindo…' : 'Concluir e liberar o painel'}
            </Botao>
            <p className="mt-2 text-xs text-muted">
              {q.data.pode_concluir ? 'Tudo pronto. A equipe passa a usar o painel normalmente.' : 'O botão libera quando as 6 etapas estiverem prontas.'}
            </p>
          </div>
        </nav>

        <section aria-labelledby="etapa-titulo" className="min-w-0">
          <header className="mb-5">
            <h2 id="etapa-titulo" className="text-xl font-semibold">{etapa.titulo}</h2>
            <p className="mt-1 max-w-2xl text-sm text-muted">{AJUDA[etapa.codigo]}</p>
          </header>
          {aberta === 'clinica' && <Perfil podeEditar modo="dados" />}
          {aberta === 'assistente' && <Assistente podeEditar comIa={false} />}
          {aberta === 'aparencia' && (
            <div className="flex flex-col gap-4">
              <Perfil podeEditar modo="aparencia" />
              {!etapa.ok && (
                <div className="flex max-w-5xl flex-wrap items-center justify-between gap-3 rounded-2xl border border-dashed border-line px-4 py-3">
                  <span className="text-sm text-muted">Gostou da cor atual? Pode manter.</span>
                  <Botao variante="secundario" disabled={confirmarAparencia.isPending} onClick={() => confirmarAparencia.mutate()}>
                    Manter esta aparência
                  </Botao>
                </div>
              )}
            </div>
          )}
          {aberta === 'horarios' && <Horarios podeEditar />}
          {aberta === 'equipe' && <div className="flex flex-col gap-6"><Procedimentos podeEditar /><Profissionais podeEditar /></div>}
          {aberta === 'ia' && <div className="max-w-5xl"><IaClinica podeEditar /></div>}
        </section>
      </div>
    </Moldura>
  )
}

/** Para quem não é administrador: espera o admin terminar (D52). Libera sozinha quando ele concluir (tempo real). */
export function AguardandoConfiguracao() {
  const { clinica } = useClinica()
  return (
    <Moldura>
      <div className="mx-auto mt-16 flex max-w-md flex-col items-center gap-3 text-center">
        <span className="grid size-12 place-items-center rounded-2xl bg-primary-soft text-primary"><Hourglass className="size-6" /></span>
        <h1 className="text-2xl font-semibold">A clínica está sendo configurada</h1>
        <p className="text-muted">
          O administrador de {clinica.name} está terminando a configuração inicial. Assim que ele concluir, o painel abre aqui sozinho.
        </p>
      </div>
    </Moldura>
  )
}

function Moldura({ children }: { children: ReactNode }) {
  const { clinica } = useClinica()
  const { usuario, sair } = useAuth()
  return (
    <div className="min-h-full bg-bg">
      <header className="flex items-center justify-between gap-4 px-6 py-4 sm:px-10">
        <div className="flex min-w-0 items-center gap-3">
          {clinica.logo_versao ? (
            <img src={`/api/clinics/${clinica.id}/logo?v=${clinica.logo_versao}`} alt="" className="size-9 rounded-xl object-contain" />
          ) : (
            <span aria-hidden className="grid size-9 place-items-center rounded-xl bg-primary font-semibold text-primary-contrast">
              {clinica.name.charAt(0).toUpperCase()}
            </span>
          )}
          <span className="truncate font-semibold">{clinica.name}</span>
        </div>
        <div className="flex items-center gap-2">
          {usuario.super_admin && (
            <Link to="/admin" className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-muted hover:bg-surface hover:text-text">
              <ShieldCheck className="size-4" /> Admin geral
            </Link>
          )}
          <button type="button" onClick={sair} className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-muted hover:bg-surface hover:text-text">
            <LogOut className="size-4" /> Sair
          </button>
        </div>
      </header>
      <main className="px-6 pb-16 pt-4 sm:px-10">{children}</main>
    </div>
  )
}

/** D54: depois de concluída, o que deixar de estar pronto vira só um aviso (o painel não trava de novo). */
export function AvisoPendencias() {
  const { clinica } = useClinica()
  // a falta de IA já tem o aviso próprio (assistente desligada)
  const itens = clinica.pendencias.filter((p) => !(p === 'Inteligência artificial' && !clinica.ia_ativa))
  if (!clinica.configurada || itens.length === 0) return null
  return (
    <p role="status" className="mb-4 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
      Falta configurar: {itens.join(', ')}. Ajuste em <Link to="/configuracoes" className="font-medium underline">Configurações</Link>.
    </p>
  )
}
