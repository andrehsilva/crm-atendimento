// Cor principal da clínica (Etapa 9B, D40). A partir de UMA cor, calcula os tons usados no tema claro e no escuro.
// O CSS (index.css) lê --marca, --marca-soft, --marca-escuro e --marca-escuro-soft.

export const COR_PADRAO = '#b85c74'
export const CONTRASTE_MINIMO = 3 // mesmo limite do backend (app/aparencia.py)

const BRANCO = '#ffffff'
const FUNDO_ESCURO = '#2a2a2e' // --surface do tema escuro
const BASE_ESCURA = '#1f1f22' // --bg do tema escuro

/** Tons sugeridos: todos legíveis com texto branco e sobre fundo claro. */
export const CORES_SUGERIDAS: { nome: string; cor: string }[] = [
  { nome: 'Rosa (padrão)', cor: '#b85c74' },
  { nome: 'Vinho', cor: '#8e2445' },
  { nome: 'Laranja queimado', cor: '#c2410c' },
  { nome: 'Dourado', cor: '#9a6700' },
  { nome: 'Verde', cor: '#2f7d32' },
  { nome: 'Verde-água', cor: '#0f766e' },
  { nome: 'Azul', cor: '#1f6feb' },
  { nome: 'Roxo', cor: '#6d4fc2' },
  { nome: 'Grafite', cor: '#3f4a5a' },
]

type Rgb = [number, number, number]

const rgb = (hex: string): Rgb => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)) as Rgb
const hex = (c: Rgb) => '#' + c.map((v) => Math.round(v).toString(16).padStart(2, '0')).join('')

export const corValida = (c: string) => /^#[0-9a-fA-F]{6}$/.test(c)

/** Mistura `a` com `b`: peso = quanto de `a` fica. */
function misturar(a: string, b: string, peso: number): string {
  const x = rgb(a)
  const y = rgb(b)
  return hex([0, 1, 2].map((i) => x[i] * peso + y[i] * (1 - peso)) as Rgb)
}

function luminancia(c: string): number {
  const [r, g, b] = rgb(c).map((v) => {
    const s = v / 255
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

export function contraste(a: string, b: string): number {
  const [l1, l2] = [luminancia(a), luminancia(b)].sort((x, y) => y - x)
  return (l1 + 0.05) / (l2 + 0.05)
}

export const legivel = (cor: string) => corValida(cor) && contraste(cor, BRANCO) >= CONTRASTE_MINIMO

/** Os 4 tons da clínica. No escuro a cor é clareada até ficar legível sobre o fundo escuro. */
export function tons(cor: string): Record<string, string> {
  if (!corValida(cor) || cor.toLowerCase() === COR_PADRAO) {
    return { '--marca': COR_PADRAO, '--marca-soft': '#f6e4ea', '--marca-escuro': '#c66c84', '--marca-escuro-soft': '#4a2e37' }
  }
  let escuro = cor
  for (let peso = 0.95; contraste(escuro, FUNDO_ESCURO) < 4 && peso > 0.3; peso -= 0.05) escuro = misturar(cor, BRANCO, peso)
  return {
    '--marca': cor,
    '--marca-soft': misturar(cor, BRANCO, 0.14),
    '--marca-escuro': escuro,
    '--marca-escuro-soft': misturar(escuro, BASE_ESCURA, 0.25),
  }
}

/** Aplica a cor no painel inteiro (null volta para a cor padrão da Ísis). */
export function aplicarMarca(cor: string | null) {
  const raiz = document.documentElement.style
  for (const [k, v] of Object.entries(tons(cor ?? COR_PADRAO))) {
    if (cor) raiz.setProperty(k, v)
    else raiz.removeProperty(k)
  }
}

// ---------------------------------------------------------------- tela de entrar
// A tela de entrar mostra a última clínica usada neste navegador (nome, cor e logo), não a marca da plataforma.
const CHAVE_ENTRADA = 'isis:marca-entrada'
export type MarcaEntrada = { id: string; nome: string; cor: string; logo_versao: number | null }

export function lembrarClinica(m: MarcaEntrada): void {
  try {
    localStorage.setItem(CHAVE_ENTRADA, JSON.stringify(m))
  } catch {
    // navegador sem armazenamento: a tela de entrar fica com a marca padrão
  }
}

export function clinicaLembrada(): MarcaEntrada | null {
  try {
    const m = JSON.parse(localStorage.getItem(CHAVE_ENTRADA) ?? 'null')
    return m && typeof m.id === 'string' && typeof m.nome === 'string' ? m : null
  } catch {
    return null
  }
}
