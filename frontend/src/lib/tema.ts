export type Tema = 'claro' | 'escuro'

export function temaAtual(): Tema {
  const d = document.documentElement.dataset.theme
  if (d === 'dark') return 'escuro'
  if (d === 'light') return 'claro'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'escuro' : 'claro'
}

export function aplicarTema(t: Tema) {
  document.documentElement.dataset.theme = t === 'escuro' ? 'dark' : 'light'
  try {
    localStorage.setItem('tema', t)
  } catch {
    // navegador sem armazenamento: o tema só não fica salvo
  }
}
