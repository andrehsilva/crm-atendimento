// Etapa 33: painel no celular. "Celular" = tela com menos de 768 px (o "md" do Tailwind).
import { useEffect, useState } from 'react'

const CONSULTA = '(max-width: 767px)'

function agora(): boolean {
  return typeof window !== 'undefined' && !!window.matchMedia?.(CONSULTA).matches
}

/** true quando a tela é de celular; acompanha girar o aparelho ou redimensionar a janela. */
export function useCelular(): boolean {
  const [celular, setCelular] = useState(agora)
  useEffect(() => {
    const m = window.matchMedia?.(CONSULTA)
    if (!m) return
    const mudou = () => setCelular(m.matches)
    mudou()
    m.addEventListener('change', mudou)
    return () => m.removeEventListener('change', mudou)
  }, [])
  return celular
}
