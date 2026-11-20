import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building, KeyRound, Shapes } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Secao, Seletor } from '../../components/ui'
import { api, type PerfilClinica, type Segmento, type TermosEditaveis, type Usuario } from '../../lib/api'
import { useSegmentos } from '../../lib/termos'
import { useClinica } from '../../lib/clinica'
import { telefone } from '../../lib/formato'
import { problemaSenha } from '../TrocarSenha'

export function Perfil({ podeEditar }: { podeEditar: boolean }) {
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

  return (
    <div className="grid max-w-5xl gap-6 lg:grid-cols-[1fr_22rem]">
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
      <TrocarMinhaSenha />
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
    <Secao titulo="Minha senha" icone={<KeyRound className="size-5" />}>
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
