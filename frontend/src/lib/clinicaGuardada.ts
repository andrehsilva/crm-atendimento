// Qual clínica fica aberta neste navegador. Separado de clinica.tsx para o login (auth.tsx) usar sem importar o painel.

const CHAVE_CLINICA = 'isis:clinica'

/** Clínica escolhida neste navegador (o super admin troca pelo "Entrar como"). Só conveniência local. */
export function escolherClinica(id: string) {
  try {
    localStorage.setItem(CHAVE_CLINICA, id)
  } catch {
    // navegador sem armazenamento: usa a primeira clínica da lista
  }
}

/** Esquece a clínica escolhida: no próximo acesso o admin da plataforma volta para a clínica de apresentação (D55). */
export function esquecerClinica() {
  try {
    localStorage.removeItem(CHAVE_CLINICA)
  } catch {
    // sem armazenamento: nada guardado
  }
}

export function clinicaGuardada(): string | null {
  try {
    return localStorage.getItem(CHAVE_CLINICA)
  } catch {
    return null
  }
}
