// Etapa 32 (desempenho): cache do painel no navegador.
//
// - As telas ficam guardadas por mais tempo: voltar ao CRM, Agenda ou Clientes abre na hora e atualiza por trás.
//   Quem avisa que algo mudou é o tempo real (SSE, lib/clinica.tsx); se a conexão cair e voltar, tudo é atualizado.
// - As telas principais também ficam guardadas na ABA do navegador (sessionStorage): recarregar a página já mostra
//   a última versão. Fechar a aba apaga; sair do sistema e entrar com outra conta também apagam.
import { QueryClient } from '@tanstack/react-query'
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister'

const MINUTO = 60_000
const CHAVE = 'isis-cache'
// muda quando o formato dos dados muda (cache antigo é descartado)
export const VERSAO_CACHE = '32.1'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * MINUTO, // o tempo real avisa antes disso quando algo muda
      gcTime: 30 * MINUTO,   // tela guardada mesmo sem ninguém olhando
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

// Só as telas mais usadas vão para a aba do navegador (nada de login, senhas ou relatórios)
const GUARDAR = new Set(['clinicas', 'clinica', 'cadastros', 'kanban', 'dashboard', 'pacientes', 'agenda', 'notificacoes', 'mensagens'])

function armazenamento(): Storage | undefined {
  try {
    return window.sessionStorage
  } catch {
    return undefined // navegador sem acesso ao armazenamento: segue sem guardar
  }
}

export const persister = createSyncStoragePersister({ storage: armazenamento(), key: CHAVE, throttleTime: 1000 })

export const opcoesPersistencia = {
  persister,
  maxAge: 30 * MINUTO,
  buster: VERSAO_CACHE,
  dehydrateOptions: {
    shouldDehydrateQuery: (q: { queryKey: readonly unknown[]; state: { status: string } }) =>
      q.state.status === 'success' && GUARDAR.has(String(q.queryKey[0])),
  },
}

/** Apaga tudo o que o painel guardou (ao sair e ao entrar com outra conta). */
export function limparCache() {
  queryClient.clear()
  try {
    armazenamento()?.removeItem(CHAVE)
  } catch {
    // sem acesso ao armazenamento: nada guardado
  }
}
