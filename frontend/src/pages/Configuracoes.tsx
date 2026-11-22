import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { useAuth } from '../lib/auth'
import { useClinica } from '../lib/clinica'
import { Assistente } from './config/Assistente'
import { Canais } from './config/Canais'
import { Convenios } from './config/Convenios'
import { Horarios } from './config/Horarios'
import { Mensagens } from './config/Mensagens'
import { Perfil } from './config/Perfil'
import { Procedimentos } from './config/Procedimentos'
import { Profissionais } from './config/Profissionais'
import { Usuarios } from './config/Usuarios'
import { UsoIa } from './config/UsoIa'
import { Site } from './config/Site'

const ABAS = ['Perfil', 'Horários', 'Procedimentos', 'Profissionais', 'Convênios', 'Assistente', 'Canais', 'Uso da IA', 'Aniversário e campanhas', 'Site', 'Usuários'] as const
type Aba = (typeof ABAS)[number]

/** Spec 07-A: configurações da clínica em abas. Ver: toda a equipe. Mudar: só o administrador da clínica. */
export function Configuracoes() {
  const { usuario } = useAuth()
  const { clinica } = useClinica()
  const papel = usuario.super_admin ? 'super_admin' : usuario.clinicas.find((c) => c.clinic_id === clinica.id)?.papel
  const podeEditar = papel === 'clinic_admin' || papel === 'super_admin'
  const abas = ABAS.filter((a) => a !== 'Usuários' || podeEditar)
  const [busca] = useSearchParams()
  const pedida = abas.find((a) => a === busca.get('aba')) // ?aba=Canais (o sino leva direto para a aba certa)
  const [aba, setAba] = useState<Aba>(pedida ?? 'Perfil')
  useEffect(() => { if (pedida) setAba(pedida) }, [pedida])

  return (
    <>
      <PageHeader titulo="Configurações" subtitulo="Gerencie o perfil, horários e procedimentos da clínica" />
      {!podeEditar && (
        <p className="mb-4 rounded-2xl bg-surface px-4 py-3 text-sm text-muted">Você pode ver as configurações. Para mudar, fale com o administrador da clínica.</p>
      )}
      <div role="tablist" className="mb-6 flex flex-wrap gap-2">
        {abas.map((a) => (
          <button key={a} type="button" role="tab" aria-selected={aba === a} onClick={() => setAba(a)}
            className={`rounded-full px-4 py-1.5 text-sm transition ${aba === a ? 'bg-primary text-primary-contrast' : 'bg-surface text-muted hover:text-text'}`}>
            {a}
          </button>
        ))}
      </div>
      {aba === 'Perfil' && <Perfil podeEditar={podeEditar} />}
      {aba === 'Horários' && <Horarios podeEditar={podeEditar} />}
      {aba === 'Procedimentos' && <Procedimentos podeEditar={podeEditar} />}
      {aba === 'Profissionais' && <Profissionais podeEditar={podeEditar} />}
      {aba === 'Assistente' && <Assistente podeEditar={podeEditar} />}
      {aba === 'Convênios' && <Convenios podeEditar={podeEditar} />}
      {aba === 'Canais' && <Canais podeEditar={podeEditar} />}
      {aba === 'Uso da IA' && <UsoIa podeEditar={podeEditar} />}
      {aba === 'Aniversário e campanhas' && <Mensagens podeEditar={podeEditar} />}
      {aba === 'Site' && <Site podeEditar={podeEditar} />}
      {aba === 'Usuários' && podeEditar && <Usuarios />}
    </>
  )
}
