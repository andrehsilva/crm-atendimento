import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, Images, ListChecks, Trash2, Type } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { EnviarImagem } from '../../components/Imagem'
import { Botao, Campo, Entrada, Secao } from '../../components/ui'
import { api } from '../../lib/api'
import { useClinica } from '../../lib/clinica'

type Conteudo = {
  textos: { titulo: string; frase: string; sobre: string }
  secoes: { ordem: string[]; ocultas: string[]; equipe_no_topo: boolean; procedimentos_ocultos: string[] }
  nomes_secoes: Record<string, string>
  padroes: { titulo: string; frase: string | null; sobre: string }
  procedimentos: { id: string; nome: string; visivel: boolean }[]
  galeria: { id: string; legenda: string | null; versao: number }[]
  galeria_max: number
}

/** Etapa 11B: textos, seções (liga/desliga e ordem), procedimentos no site e galeria. Ao salvar, `onSalvo` recarrega a prévia. */
export function SiteConteudo({ podeEditar, onSalvo }: { podeEditar: boolean; onSalvo: () => void }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const base = `/clinics/${clinica.id}/site`
  const chave = ['config', 'site-conteudo', clinica.id]
  const q = useQuery({ queryKey: chave, queryFn: () => api.get<Conteudo>(`${base}/conteudo`) })
  const [textos, setTextos] = useState<Conteudo['textos']>({ titulo: '', frase: '', sobre: '' })
  const [secoes, setSecoes] = useState<Conteudo['secoes'] | null>(null)
  useEffect(() => { if (q.data) { setTextos(q.data.textos); setSecoes(q.data.secoes) } }, [q.data])

  const depois = (c: Conteudo) => { qc.setQueryData(chave, c); onSalvo() }
  const salvar = useMutation({
    mutationFn: () => api.put<Conteudo>(`${base}/conteudo`, { textos, secoes }),
    onSuccess: (c) => { depois(c); aviso.ok('Conteúdo do site salvo.') },
    onError: aviso.erro,
  })

  if (!q.data || !secoes) return null
  const c = q.data
  const mudou = JSON.stringify({ textos, secoes }) !== JSON.stringify({ textos: c.textos, secoes: c.secoes })
  const mover = (i: number, d: number) => {
    const o = [...secoes.ordem]
    ;[o[i], o[i + d]] = [o[i + d], o[i]]
    setSecoes({ ...secoes, ordem: o })
  }
  const alternar = (lista: 'ocultas' | 'procedimentos_ocultos', id: string) =>
    setSecoes({ ...secoes, [lista]: secoes[lista].includes(id) ? secoes[lista].filter((x) => x !== id) : [...secoes[lista], id] })

  return (
    <>
      <Secao titulo="Textos" icone={<Type className="size-5" />}>
        <fieldset disabled={!podeEditar} className="grid gap-4 md:grid-cols-2">
          <Campo rotulo="Título do site" ajuda="Vazio = nome da clínica.">
            <Entrada maxLength={80} value={textos.titulo} placeholder={c.padroes.titulo} onChange={(e) => setTextos({ ...textos, titulo: e.target.value })} />
          </Campo>
          <Campo rotulo="Frase do topo" ajuda={`${textos.frase.length}/200 · Vazio = frase padrão.`}>
            <Entrada maxLength={200} value={textos.frase} placeholder={c.padroes.frase ?? ''} onChange={(e) => setTextos({ ...textos, frase: e.target.value })} />
          </Campo>
          <div className="md:col-span-2">
            <Campo rotulo="Sobre a clínica (no site)" ajuda={`${textos.sobre.length}/1500 · Vazio = o texto de Configurações › Perfil. Evite promessas de resultado e preços promocionais (regras dos conselhos).`}>
              <textarea rows={4} maxLength={1500} value={textos.sobre} placeholder={c.padroes.sobre || 'Conte em poucas linhas quem vocês são e como atendem.'}
                onChange={(e) => setTextos({ ...textos, sobre: e.target.value })}
                className="rounded-xl border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-primary disabled:opacity-60" />
            </Campo>
          </div>
        </fieldset>
      </Secao>

      <Secao titulo="Seções e procedimentos" icone={<ListChecks className="size-5" />}>
        <fieldset disabled={!podeEditar} className="grid gap-8 md:grid-cols-2">
          <div>
            <legend className="mb-1 text-sm font-medium">Seções, na ordem em que aparecem</legend>
            <p className="mb-3 text-xs text-muted">O topo (nome, foto e botão do WhatsApp) fica sempre no começo. Seção sem conteúdo não aparece.</p>
            <ol className="flex flex-col gap-2">
              {secoes.ordem.map((id, i) => (
                <li key={id} className="flex items-center gap-2 rounded-xl border border-line px-3 py-2">
                  <input type="checkbox" checked={!secoes.ocultas.includes(id)} onChange={() => alternar('ocultas', id)}
                    aria-label={`Mostrar ${c.nomes_secoes[id]}`} className="size-4 accent-[var(--primary)]" />
                  <span className={`flex-1 text-sm ${secoes.ocultas.includes(id) ? 'text-muted line-through' : ''}`}>{c.nomes_secoes[id]}</span>
                  <button type="button" disabled={i === 0} onClick={() => mover(i, -1)} aria-label={`Subir ${c.nomes_secoes[id]}`}
                    className="rounded-lg p-1 text-muted hover:bg-surface-muted disabled:opacity-30"><ArrowUp className="size-4" /></button>
                  <button type="button" disabled={i === secoes.ordem.length - 1} onClick={() => mover(i, 1)} aria-label={`Descer ${c.nomes_secoes[id]}`}
                    className="rounded-lg p-1 text-muted hover:bg-surface-muted disabled:opacity-30"><ArrowDown className="size-4" /></button>
                </li>
              ))}
            </ol>
            <label className="mt-4 flex items-start gap-3 text-sm">
              <input type="checkbox" checked={secoes.equipe_no_topo} onChange={(e) => setSecoes({ ...secoes, equipe_no_topo: e.target.checked })}
                className="mt-0.5 size-4 accent-[var(--primary)]" />
              <span>Mostrar a equipe no topo<span className="block text-xs text-muted">Foto e nome de cada profissional (carrossel quando há mais de um).</span></span>
            </label>
          </div>
          <div>
            <legend className="mb-1 text-sm font-medium">Procedimentos que aparecem no site</legend>
            <p className="mb-3 text-xs text-muted">Esconder aqui não muda a agenda nem a assistente.</p>
            <ul className="flex flex-col gap-1.5">
              {c.procedimentos.map((p) => (
                <li key={p.id}>
                  <label className="flex items-center gap-3 text-sm">
                    <input type="checkbox" checked={!secoes.procedimentos_ocultos.includes(p.id)} onChange={() => alternar('procedimentos_ocultos', p.id)}
                      className="size-4 accent-[var(--primary)]" />
                    {p.nome}
                  </label>
                </li>
              ))}
            </ul>
          </div>
        </fieldset>
        {podeEditar && mudou && (
          <div className="mt-5 flex justify-end gap-2">
            <Botao variante="fantasma" onClick={() => { setTextos(c.textos); setSecoes(c.secoes) }}>Desfazer</Botao>
            <Botao disabled={salvar.isPending} onClick={() => salvar.mutate()}>{salvar.isPending ? 'Salvando…' : 'Salvar textos e seções'}</Botao>
          </div>
        )}
      </Secao>

      <Galeria c={c} base={base} podeEditar={podeEditar} onMudou={depois} />
    </>
  )
}

function Galeria({ c, base, podeEditar, onMudou }: { c: Conteudo; base: string; podeEditar: boolean; onMudou: (c: Conteudo) => void }) {
  const aviso = useAviso()
  const enviar = useMutation({ mutationFn: (f: File) => api.post<Conteudo>(`${base}/galeria`, f), onSuccess: onMudou, onError: aviso.erro })
  const apagar = useMutation({ mutationFn: (id: string) => api.delete<Conteudo>(`${base}/galeria/${id}`), onSuccess: onMudou, onError: aviso.erro })
  const legenda = useMutation({
    mutationFn: ({ id, texto }: { id: string; texto: string }) => api.patch<Conteudo>(`${base}/galeria/${id}`, { legenda: texto }),
    onSuccess: onMudou, onError: aviso.erro,
  })
  const ordenar = useMutation({ mutationFn: (ids: string[]) => api.put<Conteudo>(`${base}/galeria-ordem`, { ids }), onSuccess: onMudou, onError: aviso.erro })
  const mover = (i: number, d: number) => {
    const ids = c.galeria.map((g) => g.id)
    ;[ids[i], ids[i + d]] = [ids[i + d], ids[i]]
    ordenar.mutate(ids)
  }
  const cheia = c.galeria.length >= c.galeria_max

  return (
    <Secao titulo="Galeria de fotos" icone={<Images className="size-5" />}
      acao={<span className="text-sm text-muted">{c.galeria.length} de {c.galeria_max}</span>}>
      <p className="mb-4 max-w-3xl text-sm text-muted">
        Fotos do consultório: recepção, salas, fachada. Não use fotos de pacientes nem "antes e depois" (regras dos conselhos).
      </p>
      {c.galeria.length > 0 && (
        <ul className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {c.galeria.map((g, i) => (
            <li key={g.id} className="overflow-hidden rounded-2xl border border-line">
              <img src={`/api${base}/galeria/${g.id}?v=${g.versao}`} alt={g.legenda ?? `Foto ${i + 1}`} className="aspect-[4/3] w-full object-cover" />
              <div className="flex items-center gap-1 p-2">
                <Entrada key={g.legenda ?? ''} defaultValue={g.legenda ?? ''} maxLength={120} placeholder="Legenda (opcional)" disabled={!podeEditar}
                  onBlur={(e) => { if (e.target.value !== (g.legenda ?? '')) legenda.mutate({ id: g.id, texto: e.target.value }) }}
                  className="min-w-0 flex-1 !py-1.5 text-sm" aria-label={`Legenda da foto ${i + 1}`} />
                {podeEditar && (
                  <>
                    <button type="button" disabled={i === 0} onClick={() => mover(i, -1)} aria-label="Mover para antes"
                      className="rounded-lg p-1 text-muted hover:bg-surface-muted disabled:opacity-30"><ArrowUp className="size-4 -rotate-90" /></button>
                    <button type="button" disabled={i === c.galeria.length - 1} onClick={() => mover(i, 1)} aria-label="Mover para depois"
                      className="rounded-lg p-1 text-muted hover:bg-surface-muted disabled:opacity-30"><ArrowDown className="size-4 -rotate-90" /></button>
                    <button type="button" onClick={() => apagar.mutate(g.id)} aria-label={`Apagar foto ${i + 1}`}
                      className="rounded-lg p-1 text-muted hover:bg-surface-muted hover:text-red-600"><Trash2 className="size-4" /></button>
                  </>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      {podeEditar && !cheia && (
        <EnviarImagem tem={false} enviando={enviar.isPending} rotulo="Adicionar foto" onArquivo={(f) => enviar.mutate(f)}
          onRemover={() => undefined} onProblema={aviso.erro} />
      )}
      {cheia && <p className="text-sm text-muted">A galeria está cheia. Apague uma foto para enviar outra.</p>}
    </Secao>
  )
}
