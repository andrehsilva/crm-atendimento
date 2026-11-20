import { useState, type FormEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { CartaoAcesso, ErroForm } from '../components/CartaoAcesso'
import { Botao, Campo, Entrada } from '../components/ui'
import { api, type Usuario } from '../lib/api'

export function problemaSenha(nova: string, confirmar: string): string | null {
  if (nova.length < 8) return 'Mínimo de 8 caracteres.'
  if (!/[A-Za-zÀ-ÿ]/.test(nova) || !/\d/.test(nova)) return 'Use letras e números.'
  if (nova !== confirmar) return 'As duas senhas novas não são iguais.'
  return null
}

/** Troca de senha. `obrigatoria`: 1º acesso com senha provisória (D35) — não dá para pular. */
export function TrocarSenha({ obrigatoria = false }: { obrigatoria?: boolean }) {
  const qc = useQueryClient()
  const [atual, setAtual] = useState('')
  const [nova, setNova] = useState('')
  const [confirmar, setConfirmar] = useState('')
  const [mostrar, setMostrar] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
  const problema = problemaSenha(nova, confirmar)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      const u = await api.post<Usuario>('/auth/trocar-senha', { atual, nova })
      qc.setQueryData(['me'], u)
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'Não foi possível trocar a senha.')
    } finally {
      setEnviando(false)
    }
  }

  async function sair() {
    await api.post('/auth/logout').catch(() => undefined)
    qc.setQueryData(['me'], null)
  }

  const tipo = mostrar ? 'text' : 'password'
  return (
    <CartaoAcesso
      titulo={obrigatoria ? 'Crie sua senha' : 'Trocar senha'}
      subtitulo={obrigatoria ? 'Você entrou com uma senha provisória. Escolha uma senha só sua para continuar.' : undefined}
    >
      <form onSubmit={enviar} className="flex flex-col gap-4">
        <Campo rotulo={obrigatoria ? 'Senha provisória' : 'Senha atual'}>
          <Entrada type={tipo} autoComplete="current-password" required value={atual} onChange={(e) => setAtual(e.target.value)} />
        </Campo>
        <Campo rotulo="Nova senha" ajuda="Mínimo de 8 caracteres, com letras e números.">
          <Entrada type={tipo} autoComplete="new-password" required value={nova} onChange={(e) => setNova(e.target.value)} />
        </Campo>
        <Campo rotulo="Confirmar nova senha">
          <Entrada type={tipo} autoComplete="new-password" required value={confirmar} onChange={(e) => setConfirmar(e.target.value)} />
        </Campo>
        <label className="flex items-center gap-2 text-sm text-muted">
          <input type="checkbox" checked={mostrar} onChange={(e) => setMostrar(e.target.checked)} className="size-4 accent-[var(--primary)]" />
          Mostrar senhas
        </label>
        {nova && problema && <p className="text-xs text-muted">{problema}</p>}
        <ErroForm texto={erro} />
        <Botao type="submit" disabled={enviando || !atual || !!problema}>{enviando ? 'Salvando…' : 'Trocar senha'}</Botao>
        {obrigatoria && (
          <button type="button" onClick={sair} className="text-sm text-muted hover:text-text">Sair</button>
        )}
      </form>
    </CartaoAcesso>
  )
}
