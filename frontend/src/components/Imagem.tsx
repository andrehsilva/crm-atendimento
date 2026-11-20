import { useRef } from 'react'
import { ImageUp, Trash2 } from 'lucide-react'
import { Botao } from './ui'

// Imagens do painel (Etapa 9B): logo da clínica, foto do usuário e foto do lead/cliente.
// O backend confere de novo o tipo e o tamanho; aqui é só para avisar antes de enviar.
const TIPOS_IMAGEM = ['image/png', 'image/jpeg', 'image/webp']
const IMAGEM_MAX = 512 * 1024

function problemaImagem(f: File): string | null {
  if (!TIPOS_IMAGEM.includes(f.type)) return 'Use uma imagem PNG, JPG ou WebP.'
  if (f.size > IMAGEM_MAX) return `A imagem tem ${Math.round(f.size / 1024)} KB; o máximo é 512 KB.`
  return null
}

function iniciaisDe(nome: string | null | undefined): string {
  return (nome || '?').split(/[\s@.]+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase()
}

/** Foto redonda ou, sem foto, as iniciais. */
export function Retrato({ src, nome, tamanho = 'size-9' }: { src: string | null; nome: string | null | undefined; tamanho?: string }) {
  if (src) return <img src={src} alt="" className={`${tamanho} shrink-0 rounded-full object-cover`} />
  return (
    <span aria-hidden className={`grid ${tamanho} shrink-0 place-items-center rounded-full bg-primary-soft text-xs font-medium text-primary`}>
      {iniciaisDe(nome)}
    </span>
  )
}

/** Botões "Enviar" / "Remover" com o seletor de arquivo escondido. */
export function EnviarImagem({ tem, enviando, onArquivo, onRemover, onProblema, rotulo = 'Enviar imagem', desabilitado }: {
  tem: boolean
  enviando: boolean
  onArquivo: (f: File) => void
  onRemover: () => void
  onProblema: (msg: string) => void
  rotulo?: string
  desabilitado?: boolean
}) {
  const ref = useRef<HTMLInputElement>(null)
  return (
    <div className="flex flex-wrap items-center gap-2">
      <input ref={ref} type="file" accept={TIPOS_IMAGEM.join(',')} className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0]
          e.target.value = '' // deixa escolher o mesmo arquivo de novo
          if (!f) return
          const p = problemaImagem(f)
          if (p) onProblema(p)
          else onArquivo(f)
        }} />
      <Botao type="button" variante="fantasma" disabled={enviando || desabilitado} onClick={() => ref.current?.click()}>
        <ImageUp className="size-4" />{enviando ? 'Enviando…' : tem ? 'Trocar' : rotulo}
      </Botao>
      {tem && (
        <Botao type="button" variante="fantasma" disabled={enviando || desabilitado} onClick={onRemover}>
          <Trash2 className="size-4" />Remover
        </Botao>
      )}
    </div>
  )
}
