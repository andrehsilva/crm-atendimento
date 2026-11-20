import { useQuery } from '@tanstack/react-query'

export type Saude = { status: string; env: string; chat_teste: boolean; banco: { status: string }; ia: { status: string } }

/** Situação do backend (/health): ambiente e se o chat web de teste está ligado. */
export function useSaude() {
  return useQuery({
    queryKey: ['saude'],
    queryFn: async (): Promise<Saude> => {
      const r = await fetch('/health')
      if (!r.ok) throw new Error(String(r.status))
      return r.json()
    },
    staleTime: 60_000,
    retry: false,
  })
}
