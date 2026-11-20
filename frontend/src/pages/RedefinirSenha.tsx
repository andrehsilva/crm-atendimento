import { useMemo, useState, type FormEvent } from 'react'
import { CartaoAcesso, ErroForm } from '../components/CartaoAcesso'
import { Botao, Campo, Entrada } from '../components/ui'
import { api } from '../lib/api'
import { problemaSenha } from './TrocarSenha'

/** Página aberta pelo link do e-mail "Esqueci minha senha". O Supabase manda o token depois do # na URL. */
export function RedefinirSenha() {
  const token = useMemo(() => {
    const p = new URLSearchParams(window.location.hash.replace(/^#/, ''))
    return p.get('access_token')
  }, [])
  const erroLink = useMemo(() => {
    const p = new URLSearchParams(window.location.hash.replace(/^#/, ''))
    return p.get('error_description')
  }, [])
  const [nova, setNova] = useState('')
  const [confirmar, setConfirmar] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [pronto, setPronto] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const problema = problemaSenha(nova, confirmar)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      await api.post('/auth/redefinir', { access_token: token, nova })
      setPronto(true)
      window.history.replaceState(null, '', '/redefinir-senha') // tira o token da barra de endereço
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'Não foi possível salvar.')
    } finally {
      setEnviando(false)
    }
  }

  if (pronto) {
    return (
      <CartaoAcesso titulo="Senha criada ✅" subtitulo="Agora é só entrar com o seu e-mail e a nova senha.">
        <a href="/" className="block rounded-xl bg-primary px-4 py-2 text-center text-sm font-medium text-primary-contrast">Ir para o login</a>
      </CartaoAcesso>
    )
  }
  if (!token) {
    return (
      <CartaoAcesso titulo="Link inválido" subtitulo={erroLink ?? 'Este link expirou ou já foi usado. Peça um novo em "Esqueci minha senha".'}>
        <a href="/" className="block rounded-xl bg-primary px-4 py-2 text-center text-sm font-medium text-primary-contrast">Voltar</a>
      </CartaoAcesso>
    )
  }
  return (
    <CartaoAcesso titulo="Criar nova senha">
      <form onSubmit={enviar} className="flex flex-col gap-4">
        <Campo rotulo="Nova senha" ajuda="Mínimo de 8 caracteres, com letras e números.">
          <Entrada type="password" autoComplete="new-password" required value={nova} onChange={(e) => setNova(e.target.value)} />
        </Campo>
        <Campo rotulo="Confirmar nova senha">
          <Entrada type="password" autoComplete="new-password" required value={confirmar} onChange={(e) => setConfirmar(e.target.value)} />
        </Campo>
        {nova && problema && <p className="text-xs text-muted">{problema}</p>}
        <ErroForm texto={erro} />
        <Botao type="submit" disabled={enviando || !!problema}>{enviando ? 'Salvando…' : 'Salvar nova senha'}</Botao>
      </form>
    </CartaoAcesso>
  )
}
