import { useClinica } from './clinica'
import { useQuery } from '@tanstack/react-query'
import { api, type Segmento, type Termos } from './api'

const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1)

const PADRAO: Termos = {
  profissional: 'profissional', profissionais: 'profissionais', cliente: 'cliente', clientes: 'clientes',
  atendimento: 'atendimento', atendimentos: 'atendimentos', genero: 'm', o: 'o', sua: 'seu', da_sua: 'do seu', uma: 'um', nova: 'novo',
}

/**
 * Palavras do negócio da clínica (Etapa 9). Ex.: `t.Atendimento` = "Consulta" / "Sessão" / "Atendimento";
 * `t.o` faz a concordância: `${t.Atendimento} confirmad${t.o}`.
 */
export function useTermos() {
  const { clinica } = useClinica()
  const t = clinica.termos ?? PADRAO
  return {
    ...t,
    Profissional: cap(t.profissional),
    Profissionais: cap(t.profissionais),
    Cliente: cap(t.cliente),
    Clientes: cap(t.clientes),
    Atendimento: cap(t.atendimento),
    Atendimentos: cap(t.atendimentos),
    Nova: cap(t.nova),
    Uma: cap(t.uma),
    nenhuma: t.genero === 'f' ? 'nenhuma' : 'nenhum',
    Nenhuma: t.genero === 'f' ? 'Nenhuma' : 'Nenhum',
    /** "1 consulta" / "3 sessões" */
    contar: (n: number) => `${n} ${n === 1 ? t.atendimento : t.atendimentos}`,
  }
}

export type Palavras = ReturnType<typeof useTermos>

/** Segmentos disponíveis (odontologia, medicina, …) para os formulários. */
export function useSegmentos() {
  return useQuery({ queryKey: ['segmentos'], queryFn: () => api.get<Segmento[]>('/segmentos'), staleTime: Infinity })
}
