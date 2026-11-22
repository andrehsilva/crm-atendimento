import { useEffect, useState, type CSSProperties } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building, Check, KeyRound, Palette, Shapes } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Secao, Seletor } from '../../components/ui'
import { api, type Aparencia, type PerfilClinica, type Segmento, type TermosEditaveis, type Usuario } from '../../lib/api'
import { useSegmentos } from '../../lib/termos'
import { useClinica } from '../../lib/clinica'
import { telefone } from '../../lib/formato'
import { problemaSenha } from '../TrocarSenha'
import { useAuth } from '../../lib/auth'
import { EnviarImagem, Retrato } from '../../components/Imagem'
import { CORES_SUGERIDAS, corValida, legivel, tons } from '../../lib/marca'

/** modo (10C): 'dados' = dados da clínica e segmento; 'aparencia' = só cor e logo; 'tudo' = a aba Perfil inteira. */
export function Perfil({ podeEditar, modo = 'tudo' }: { podeEditar: boolean; modo?: 'tudo' | 'dados' | 'aparencia' }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const url = `/clinics/${clinica.id}/config/perfil`
  const q = useQuery({ queryKey: ['config', 'perfil', clinica.id], queryFn: () => api.get<PerfilClinica>(url) })
  const segmentos = useSegmentos()
  const [f, setF] = useState({ nome: '', endereco: '', telefone_urgencia: '', sobre: '' })
  const [negocio, setNegocio] = useState<{ segmento: string; termos: TermosEditaveis; lembrete_discreto: boolean }>({
    segmento: 'odontologia', termos: {}, lembrete_discreto: false })
  useEffect(() => {
    if (!q.data) return
    setF({ nome: q.data.nome, endereco: q.data.endereco ?? '', telefone_urgencia: q.data.telefone_urgencia ? telefone(q.data.telefone_urgencia) : '', sobre: q.data.sobre ?? '' })
    setNegocio({ segmento: q.data.segmento, termos: q.data.termos_proprios, lembrete_discreto: q.data.lembrete_discreto })
  }, [q.data])
  const salvar = useMutation({
    mutationFn: () => api.put(url, { ...f, ...negocio }),
    onSuccess: () => {
      aviso.ok('Perfil salvo.')
      qc.invalidateQueries({ queryKey: ['config'] })
      qc.invalidateQueries({ queryKey: ['clinica'] })
    },
    onError: aviso.erro,
  })
  if (!q.data) return <p className="text-sm text-muted">Carregando…</p>
  if (modo === 'aparencia') return <div className="grid gap-6"><AparenciaClinica podeEditar={podeEditar} /></div>

  return (
    <div className={modo === 'tudo' ? 'grid gap-6 lg:grid-cols-[1fr_24rem]' : 'flex flex-col gap-6'}>
      <Secao titulo="Dados da clínica" icone={<Building className="size-5" />}>
        <form onSubmit={(e) => { e.preventDefault(); salvar.mutate() }} className="grid gap-4 sm:grid-cols-2">
          <Campo rotulo="Nome da clínica" ajuda="Aparece no topo da barra lateral e nas mensagens.">
            <Entrada required disabled={!podeEditar} value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} />
          </Campo>
          <Campo rotulo="Telefone da clínica" ajuda="É a chave da clínica; só o admin da plataforma muda.">
            <Entrada disabled value={telefone(q.data.telefone)} />
          </Campo>
          <Campo rotulo="Endereço" ajuda="Vai na mensagem de confirmação.">
            <Entrada disabled={!podeEditar} value={f.endereco} onChange={(e) => setF({ ...f, endereco: e.target.value })} />
          </Campo>
          <Campo rotulo="Telefone de urgência" ajuda="A assistente passa este número em casos urgentes.">
            <Entrada disabled={!podeEditar} value={f.telefone_urgencia} placeholder={telefone(q.data.telefone)}
              onChange={(e) => setF({ ...f, telefone_urgencia: e.target.value })} />
          </Campo>
          <div className="sm:col-span-2">
            <Campo rotulo="Sobre a clínica" ajuda="A assistente usa este texto para tirar dúvidas: convênios, estacionamento, acompanhantes, acessibilidade…">
              <textarea rows={5} maxLength={1500} disabled={!podeEditar} value={f.sobre} onChange={(e) => setF({ ...f, sobre: e.target.value })}
                placeholder="Ex.: Temos estacionamento conveniado na Rua B. Crianças podem acompanhar os pais. Não atendemos convênios."
                className="rounded-xl border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-primary disabled:opacity-60" />
            </Campo>
          </div>
          {podeEditar && (
            <div className="flex justify-end sm:col-span-2">
              <Botao type="submit" disabled={salvar.isPending}>{salvar.isPending ? 'Salvando…' : 'Salvar'}</Botao>
            </div>
          )}
        </form>
      </Secao>
      {modo === 'tudo' && <TrocarMinhaSenha />}
      {modo === 'tudo' && <AparenciaClinica podeEditar={podeEditar} />}
      <SeuNegocio valor={negocio} onMudar={setNegocio} segmentos={segmentos.data ?? []} podeEditar={podeEditar}
        enviando={salvar.isPending} onSalvar={() => salvar.mutate()} />
    </div>
  )
}

/** Imagem 06: troca de senha com "Mostrar senhas"; o botão só habilita quando está válido. */
function TrocarMinhaSenha() {
  const aviso = useAviso()
  const qc = useQueryClient()
  const [f, setF] = useState({ atual: '', nova: '', confirmar: '' })
  const [mostrar, setMostrar] = useState(false)
  const problema = problemaSenha(f.nova, f.confirmar)
  const trocar = useMutation({
    mutationFn: () => api.post<Usuario>('/auth/trocar-senha', { atual: f.atual, nova: f.nova }),
    onSuccess: (u) => {
      qc.setQueryData(['me'], u)
      setF({ atual: '', nova: '', confirmar: '' })
      aviso.ok('Senha trocada.')
    },
    onError: aviso.erro,
  })
  const tipo = mostrar ? 'text' : 'password'
  return (
    <Secao titulo="Minha conta" icone={<KeyRound className="size-5" />}>
      <MinhaFoto />
      <form onSubmit={(e) => { e.preventDefault(); trocar.mutate() }} className="flex flex-col gap-4">
        <Campo rotulo="Senha atual"><Entrada type={tipo} autoComplete="current-password" value={f.atual} onChange={(e) => setF({ ...f, atual: e.target.value })} /></Campo>
        <Campo rotulo="Nova senha" ajuda="Mínimo de 8 caracteres, com letras e números.">
          <Entrada type={tipo} autoComplete="new-password" value={f.nova} onChange={(e) => setF({ ...f, nova: e.target.value })} />
        </Campo>
        <Campo rotulo="Confirmar nova senha"><Entrada type={tipo} autoComplete="new-password" value={f.confirmar} onChange={(e) => setF({ ...f, confirmar: e.target.value })} /></Campo>
        <label className="flex items-center gap-2 text-sm text-muted">
          <input type="checkbox" checked={mostrar} onChange={(e) => setMostrar(e.target.checked)} className="size-4 accent-[var(--primary)]" />
          Mostrar senhas
        </label>
        {f.nova && problema && <p className="text-xs text-muted">{problema}</p>}
        <Botao type="submit" disabled={trocar.isPending || !f.atual || !!problema}>Trocar senha</Botao>
        <p className="text-xs text-muted">Esqueceu a senha? Use "Esqueci minha senha" na tela de entrar.</p>
      </form>
    </Secao>
  )
}

const CAMPOS_TERMOS: [keyof TermosEditaveis, string][] = [
  ['profissional', 'Quem atende'], ['profissionais', 'Quem atende (plural)'],
  ['cliente', 'Quem é atendido'], ['clientes', 'Quem é atendido (plural)'],
  ['atendimento', 'O horário marcado'], ['atendimentos', 'O horário marcado (plural)'],
]

/** Etapa 9 (D38, D39, D41): segmento, palavras do negócio e lembrete discreto. */
function SeuNegocio({ valor, onMudar, segmentos, podeEditar, enviando, onSalvar }: {
  valor: { segmento: string; termos: TermosEditaveis; lembrete_discreto: boolean }
  onMudar: (v: { segmento: string; termos: TermosEditaveis; lembrete_discreto: boolean }) => void
  segmentos: Segmento[]
  podeEditar: boolean
  enviando: boolean
  onSalvar: () => void
}) {
  const seg = segmentos.find((s) => s.codigo === valor.segmento)
  const padrao = seg?.termos ?? {}
  const termo = (k: keyof TermosEditaveis) => (e: { target: { value: string } }) => onMudar({ ...valor, termos: { ...valor.termos, [k]: e.target.value } })
  const genero = valor.termos.genero ?? padrao.genero ?? 'f'
  const exemplo = (valor.termos.atendimento || padrao.atendimento || 'consulta')
  return (
    <Secao titulo="Seu negócio" icone={<Shapes className="size-5" />} className="lg:col-span-2">
      <form onSubmit={(e) => { e.preventDefault(); onSalvar() }} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Campo rotulo="Segmento" ajuda="Muda as palavras e o jeito da assistente. Não mexe nos procedimentos já cadastrados.">
          <Seletor disabled={!podeEditar} value={valor.segmento}
            onChange={(e) => {
              const novo = segmentos.find((s) => s.codigo === e.target.value)
              onMudar({ segmento: e.target.value, termos: {}, lembrete_discreto: novo?.lembrete_discreto ?? false })
            }}>
            {segmentos.map((s) => <option key={s.codigo} value={s.codigo}>{s.nome}</option>)}
          </Seletor>
        </Campo>
        {CAMPOS_TERMOS.map(([k, rotulo]) => (
          <Campo key={k} rotulo={rotulo}>
            <Entrada disabled={!podeEditar} maxLength={40} value={valor.termos[k] ?? ''} placeholder={padrao[k] ?? ''} onChange={termo(k)} />
          </Campo>
        ))}
        <Campo rotulo={`Concordância de "${exemplo}"`}>
          <Seletor disabled={!podeEditar} value={genero} onChange={termo('genero')}>
            <option value="f">a {exemplo} · sua {exemplo} · confirmada</option>
            <option value="m">o {exemplo} · seu {exemplo} · confirmado</option>
          </Seletor>
        </Campo>
        <label className="flex items-start gap-2 text-sm sm:col-span-2">
          <input type="checkbox" disabled={!podeEditar} checked={valor.lembrete_discreto}
            onChange={(e) => onMudar({ ...valor, lembrete_discreto: e.target.checked })} className="mt-0.5 size-4 accent-[var(--primary)]" />
          <span>
            Lembretes discretos
            <span className="block text-xs text-muted">Confirmações e lembretes não citam o procedimento, só o dia, a hora e quem atende.</span>
          </span>
        </label>
        <p className="text-xs text-muted sm:col-span-2 lg:col-span-3">
          Campos vazios usam o padrão do segmento (em cinza). As palavras valem nas telas, nas mensagens automáticas e na assistente.
        </p>
        {podeEditar && (
          <div className="flex justify-end sm:col-span-2 lg:col-span-3">
            <Botao type="submit" disabled={enviando}>{enviando ? 'Salvando…' : 'Salvar'}</Botao>
          </div>
        )}
      </form>
    </Secao>
  )
}

/** Foto de perfil de quem está logado (aparece no rodapé da barra lateral). */
function MinhaFoto() {
  const { usuario } = useAuth()
  const aviso = useAviso()
  const qc = useQueryClient()
  const mudar = useMutation({
    mutationFn: (f: File | null) => (f ? api.put<Usuario>('/auth/foto', f) : api.delete<Usuario>('/auth/foto')),
    onSuccess: (u) => qc.setQueryData(['me'], u),
    onError: aviso.erro,
  })
  return (
    <div className="mb-5 flex items-center gap-4 border-b border-line pb-5">
      <Retrato tamanho="size-16" nome={usuario.nome || usuario.email}
        src={usuario.foto_versao ? `/api/auth/foto?v=${usuario.foto_versao}` : null} />
      <div className="space-y-1">
        <EnviarImagem tem={!!usuario.foto_versao} enviando={mudar.isPending} rotulo="Enviar foto"
          onArquivo={(f) => mudar.mutate(f)} onRemover={() => mudar.mutate(null)} onProblema={aviso.erro} />
        <p className="text-xs text-muted">Sua foto de perfil. PNG, JPG ou WebP até 512 KB.</p>
      </div>
    </div>
  )
}

const inicial = (nome: string) => nome.replace(/^Clínica\s+/i, '').charAt(0)

/** Etapa 9B (D40): logo ao lado do nome da clínica e cor principal do painel. */
function AparenciaClinica({ podeEditar }: { podeEditar: boolean }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const url = `/clinics/${clinica.id}/config/aparencia`
  const q = useQuery({ queryKey: ['config', 'aparencia', clinica.id], queryFn: () => api.get<Aparencia>(url) })
  const [cor, setCor] = useState('')
  useEffect(() => { if (q.data) setCor(q.data.cor) }, [q.data])
  const depois = (a: Aparencia) => {
    qc.setQueryData(['config', 'aparencia', clinica.id], a)
    qc.invalidateQueries({ queryKey: ['clinica'] })
  }
  const salvarCor = useMutation({
    mutationFn: (c: string | null) => api.put<Aparencia>(url, { cor: c }),
    onSuccess: (a) => { depois(a); aviso.ok('Cor salva.') },
    onError: aviso.erro,
  })
  const logo = useMutation({
    mutationFn: (f: File | null) => (f ? api.put<Aparencia>(`/clinics/${clinica.id}/config/logo`, f)
      : api.delete<Aparencia>(`/clinics/${clinica.id}/config/logo`)),
    onSuccess: depois,
    onError: aviso.erro,
  })
  if (!q.data) return null
  const valida = corValida(cor)
  const ok = valida && legivel(cor)
  const mudou = valida && cor.toLowerCase() !== q.data.cor
  const logoSrc = q.data.logo_versao ? `/api/clinics/${clinica.id}/logo?v=${q.data.logo_versao}` : null

  return (
    <Secao titulo="Aparência" icone={<Palette className="size-5" />} className="lg:col-span-2">
      <div className="grid gap-8 lg:grid-cols-[1fr_1.3fr_1fr]">
        <div className="space-y-3">
          <h3 className="text-sm font-medium">Logo</h3>
          <div className="flex items-center gap-4">
            <div className="grid size-20 shrink-0 place-items-center overflow-hidden rounded-2xl border border-line bg-white">
              {logoSrc
                ? <img src={logoSrc} alt="Logo atual" className="size-full object-contain p-1" />
                : <span className="text-2xl font-semibold text-primary">{inicial(clinica.name)}</span>}
            </div>
            <EnviarImagem tem={!!logoSrc} enviando={logo.isPending} rotulo="Enviar logo" desabilitado={!podeEditar}
              onArquivo={(f) => logo.mutate(f)} onRemover={() => logo.mutate(null)} onProblema={aviso.erro} />
          </div>
          <p className="text-xs text-muted">Fica ao lado do nome da clínica, na barra lateral. PNG, JPG ou WebP até 512 KB; quadrada fica melhor.</p>
        </div>

        <div className="space-y-3">
          <h3 className="text-sm font-medium">Cor principal</h3>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Cores sugeridas">
            {CORES_SUGERIDAS.map((c) => {
              const ativa = c.cor === cor.toLowerCase()
              return (
                <button key={c.cor} type="button" role="radio" aria-checked={ativa} title={c.nome} aria-label={c.nome}
                  disabled={!podeEditar} onClick={() => setCor(c.cor)} style={{ background: c.cor }}
                  className={`grid size-9 place-items-center rounded-full text-white outline-offset-2 transition-transform hover:scale-105 disabled:cursor-not-allowed ${ativa ? 'outline-2 outline-text' : ''}`}>
                  {ativa && <Check className="size-4" />}
                </button>
              )
            })}
          </div>
          <div className="flex items-center gap-2">
            <input type="color" aria-label="Escolher outra cor" disabled={!podeEditar} value={valida ? cor.toLowerCase() : '#000000'}
              onChange={(e) => setCor(e.target.value)} className="h-9 w-12 cursor-pointer rounded-lg border border-line bg-surface p-1" />
            <Entrada aria-label="Código da cor" disabled={!podeEditar} value={cor} maxLength={7} className="w-28 font-mono"
              onChange={(e) => setCor(e.target.value.startsWith('#') ? e.target.value : `#${e.target.value}`)} />
          </div>
          {valida && !ok && (
            <p className="text-xs text-red-600 dark:text-red-400">Cor clara demais: textos e botões ficariam difíceis de ler. Escolha um tom mais escuro.</p>
          )}
          {podeEditar && (
            <div className="flex flex-wrap gap-2 pt-1">
              <Botao disabled={!ok || !mudou || salvarCor.isPending} onClick={() => salvarCor.mutate(cor)}>Salvar cor</Botao>
              {q.data.cor !== q.data.cor_padrao && (
                <Botao variante="fantasma" disabled={salvarCor.isPending} onClick={() => salvarCor.mutate(null)}>Voltar à cor padrão</Botao>
              )}
            </div>
          )}
        </div>

        <div className="space-y-3">
          <h3 className="text-sm font-medium">Prévia</h3>
          <div className="marca-escopo space-y-3 rounded-2xl border border-line bg-bg p-4"
            style={tons(valida ? cor.toLowerCase() : q.data.cor) as CSSProperties}>
            <div className="flex items-center gap-2">
              {logoSrc
                ? <img src={logoSrc} alt="" className="size-8 rounded-lg border border-line bg-white object-contain p-0.5" />
                : <span className="grid size-8 place-items-center rounded-lg bg-primary text-sm font-semibold text-primary-contrast">{inicial(clinica.name)}</span>}
              <span className="truncate text-sm font-medium">{clinica.name}</span>
            </div>
            <div className="rounded-xl bg-primary-soft px-3 py-2 text-sm text-primary">Agenda</div>
            <div className="flex items-center gap-2">
              <span className="rounded-xl bg-primary px-3 py-1.5 text-sm font-medium text-primary-contrast">Salvar</span>
              <span className="text-sm text-primary underline">Ver detalhes</span>
            </div>
          </div>
        </div>
      </div>
    </Secao>
  )
}
