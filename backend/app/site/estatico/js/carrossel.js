// Carrossel dos profissionais no site da clínica (Etapa 11). Sem dependências.
// Sem este script o carrossel continua funcionando: dá para arrastar com o dedo (rolagem com "snap").
// Troca sozinho a cada 6 s; para com o mouse em cima, com foco do teclado, ao tocar ou no botão "Pausar";
// não se mexe sozinho se a pessoa pediu "reduzir movimento" no aparelho.
document.querySelectorAll('[data-carrossel]').forEach((raiz) => {
  const trilho = raiz.querySelector('[data-trilho]')
  const total = trilho ? trilho.children.length : 0
  if (total < 2) return
  const pontos = [...raiz.querySelectorAll('[data-ponto]')]
  const pausa = raiz.querySelector('[data-pausa]')
  const reduzir = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  let atual = 0
  let timer = null
  let pausadoPeloUsuario = reduzir

  const marcar = () => pontos.forEach((p, i) => p.setAttribute('aria-current', i === atual ? 'true' : 'false'))
  const ir = (i) => {
    atual = (i + total) % total
    trilho.scrollTo({ left: atual * trilho.clientWidth, behavior: reduzir ? 'auto' : 'smooth' })
    marcar()
  }
  const parar = () => { clearInterval(timer); timer = null }
  const iniciar = () => { if (!pausadoPeloUsuario && !timer) timer = setInterval(() => ir(atual + 1), 6000) }
  const atualizarPausa = () => {
    if (!pausa) return
    pausa.setAttribute('aria-pressed', pausadoPeloUsuario ? 'true' : 'false')
    pausa.textContent = pausadoPeloUsuario ? 'Continuar' : 'Pausar'
  }

  trilho.addEventListener('scroll', () => {
    const i = Math.round(trilho.scrollLeft / trilho.clientWidth)
    if (i !== atual) { atual = i; marcar() }
  }, { passive: true })
  raiz.querySelector('[data-ant]')?.addEventListener('click', () => { ir(atual - 1); parar() })
  raiz.querySelector('[data-prox]')?.addEventListener('click', () => { ir(atual + 1); parar() })
  pontos.forEach((p, i) => p.addEventListener('click', () => { ir(i); parar() }))
  pausa?.addEventListener('click', () => { pausadoPeloUsuario = !pausadoPeloUsuario; atualizarPausa(); pausadoPeloUsuario ? parar() : iniciar() })
  raiz.addEventListener('mouseenter', parar)
  raiz.addEventListener('mouseleave', iniciar)
  raiz.addEventListener('focusin', parar)
  raiz.addEventListener('touchstart', parar, { passive: true })
  document.addEventListener('visibilitychange', () => (document.hidden ? parar() : iniciar()))

  marcar()
  atualizarPausa()
  iniciar()
})
