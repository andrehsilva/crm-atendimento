import { useState, type FormEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { CartaoAcesso, ErroForm } from '../components/CartaoAcesso'
import { Botao, Campo, Entrada } from '../components/ui'
import { api, type Usuario } from '../lib/api'

/** Tela de entrar (D34) + "Esqueci minha senha". */
export function Login({ aviso }: { aviso?: string }) {
  const qc = useQueryClient()
  const [modo, setModo] = useState<'entrar' | 'esqueci'>('entrar')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [mostrar, setMostrar] = useState(false)
  const [erro, setErro] = useState<string | null>(aviso ?? null)
  const [ok, setOk] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function entrar(e: FormEvent) {
    e.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      const u = await api.post<Usuario>('/auth/login', { email, senha })
      qc.setQueryData(['me'], u)
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'Não foi possível entrar.')
    } finally {
      setEnviando(false)
    }
  }

  async function esqueci(e: FormEvent) {
    e.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      const r = await api.post<{ mensagem: string }>('/auth/esqueci', { email })
      setOk(r.mensagem)
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'Não foi possível enviar.')
    } finally {
      setEnviando(false)
    }
  }

  if (modo === 'esqueci') {
    return (
      <CartaoAcesso titulo="Esqueci minha senha" subtitulo="Enviaremos um link para você criar uma nova senha.">
        <form onSubmit={esqueci} className="flex flex-col gap-4">
          <Campo rotulo="E-mail">
            <Entrada type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Campo>
          <ErroForm texto={erro} />
          {ok && <p role="status" className="rounded-xl bg-primary-soft px-3 py-2 text-sm text-primary">{ok}</p>}
          <Botao type="submit" disabled={enviando || !email}>{enviando ? 'Enviando…' : 'Enviar link'}</Botao>
          <button type="button" onClick={() => { setModo('entrar'); setOk(null); setErro(null) }} className="text-sm text-muted hover:text-text">
            Voltar para entrar
          </button>
        </form>
      </CartaoAcesso>
    )
  }

  return (
    <CartaoAcesso titulo="Entrar" subtitulo="Use o e-mail e a senha do seu acesso ao painel.">
      <form onSubmit={entrar} className="flex flex-col gap-4">
        <Campo rotulo="E-mail">
          <Entrada type="email" autoComplete="username" required autoFocus value={email} onChange={(e) => setEmail(e.target.value)} />
        </Campo>
        <Campo rotulo="Senha">
          <Entrada type={mostrar ? 'text' : 'password'} autoComplete="current-password" required value={senha}
            onChange={(e) => setSenha(e.target.value)} />
        </Campo>
        <label className="flex items-center gap-2 text-sm text-muted">
          <input type="checkbox" checked={mostrar} onChange={(e) => setMostrar(e.target.checked)} className="size-4 accent-[var(--primary)]" />
          Mostrar senha
        </label>
        <ErroForm texto={erro} />
        <Botao type="submit" disabled={enviando || !email || !senha}>{enviando ? 'Entrando…' : 'Entrar'}</Botao>
        <button type="button" onClick={() => { setModo('esqueci'); setErro(null) }} className="text-sm text-muted hover:text-text">
          Esqueci minha senha
        </button>
      </form>
    </CartaoAcesso>
  )
}
