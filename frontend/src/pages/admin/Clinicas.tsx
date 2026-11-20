import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, Plus } from 'lucide-react'
import { PageHeader } from '../../components/PageHeader'
import { useAviso } from '../../components/Aviso'
import { Botao, Campo, Entrada, Modal, Seletor, Selo, Vazio } from '../../components/ui'
import { api, type AdminClinica } from '../../lib/api'
import { telefone } from '../../lib/formato'
import { useSegmentos } from '../../lib/termos'
import { SenhaProvisoria } from './SenhaProvisoria'

export const FUSOS = [
  ['America/Sao_Paulo', 'Brasília (SP, RJ, MG, Sul, NE…)'],
  ['America/Manaus', 'Amazonas'],
  ['America/Cuiaba', 'Mato Grosso / MS'],
  ['America/Belem', 'Pará / Amapá'],
  ['America/Fortaleza', 'Ceará / RN / PB'],
  ['America/Recife', 'Pernambuco'],
  ['America/Rio_Branco', 'Acre'],
  ['America/Noronha', 'Fernando de Noronha'],
] as const

export function SeloWhatsapp({ status }: { status: string | null }) {
  if (!status) return <Selo>sem WhatsApp</Selo>
  if (status === 'WORKING') return <Selo cor="verde">conectado</Selo>
  if (status === 'SCAN_QR_CODE') return <Selo cor="ambar">aguardando QR</Selo>
  if (status === 'STARTING') return <Selo cor="azul">iniciando</Selo>
  return <Selo cor="vermelho">{status.toLowerCase()}</Selo>
}

export function AdminClinicas() {
  const q = useQuery({ queryKey: ['admin', 'clinicas'], queryFn: () => api.get<AdminClinica[]>('/admin/clinicas') })
  const [nova, setNova] = useState(false)
  const [criada, setCriada] = useState<{ email: string; senha: string | null } | null>(null)

  return (
    <>
      <div className="flex items-start justify-between gap-4">
        <PageHeader titulo="Clínicas" subtitulo="Todas as clínicas da plataforma" />
        <Botao onClick={() => setNova(true)}><Plus className="size-4" /> Nova clínica</Botao>
      </div>

      <section className="overflow-hidden rounded-3xl bg-surface">
        {q.isLoading ? (
          <p className="p-6 text-sm text-muted">Carregando…</p>
        ) : !q.data?.length ? (
          <Vazio icone={<Building2 className="size-8" />} texto="Nenhuma clínica ainda." />
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-6 py-3 font-medium">Clínica</th>
                <th className="px-4 py-3 font-medium">Telefone (chave)</th>
                <th className="px-4 py-3 font-medium">WhatsApp</th>
                <th className="px-4 py-3 font-medium">Assistente</th>
                <th className="px-4 py-3 text-right font-medium">Conversas no mês</th>
                <th className="px-4 py-3 text-right font-medium">Usuários</th>
                <th className="px-6 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {q.data.map((c) => (
                <tr key={c.id} className="border-b border-line last:border-0 hover:bg-surface-muted">
                  <td className="px-6 py-4">
                    <Link to={`/admin/clinicas/${c.id}`} className="font-medium hover:text-primary">{c.name}</Link>
                    <div className="text-xs text-muted">/{c.slug}</div>
                  </td>
                  <td className="px-4 py-4 tabular-nums">{telefone(c.phone)}</td>
                  <td className="px-4 py-4"><SeloWhatsapp status={c.whatsapp_sessao ? c.whatsapp_status : null} /></td>
                  <td className="px-4 py-4">{c.nome_assistente}</td>
                  <td className="px-4 py-4 text-right tabular-nums">{c.conversas_mes}</td>
                  <td className="px-4 py-4 text-right tabular-nums">{c.usuarios}</td>
                  <td className="px-6 py-4">{c.status === 'ativa' ? <Selo cor="verde">ativa</Selo> : <Selo cor="vermelho">suspensa</Selo>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {nova && <NovaClinica onFechar={() => setNova(false)} onCriada={(email, senha) => { setNova(false); setCriada({ email, senha }) }} />}
      {criada && <SenhaProvisoria email={criada.email} senha={criada.senha} onFechar={() => setCriada(null)} />}
    </>
  )
}

function NovaClinica({ onFechar, onCriada }: { onFechar: () => void; onCriada: (email: string, senha: string | null) => void }) {
  const qc = useQueryClient()
  const aviso = useAviso()
  const [f, setF] = useState({ nome: '', telefone: '', endereco: '', fuso: 'America/Sao_Paulo', nome_assistente: 'Ísis',
    segmento: 'odontologia', profissional: '', admin_nome: '', admin_email: '' })
  const segmentos = useSegmentos()
  const seg = segmentos.data?.find((s) => s.codigo === f.segmento)
  const mudar = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })

  const criar = useMutation({
    mutationFn: () => api.post<{ admin_email: string; senha_provisoria: string | null }>('/admin/clinicas', {
      ...f, endereco: f.endereco || null, profissional: f.profissional || null, admin_nome: f.admin_nome || null,
    }),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['admin'] })
      qc.invalidateQueries({ queryKey: ['clinicas'] })
      aviso.ok('Clínica criada.')
      onCriada(r.admin_email, r.senha_provisoria)
    },
    onError: aviso.erro,
  })

  function enviar(e: FormEvent) {
    e.preventDefault()
    criar.mutate()
  }

  return (
    <Modal titulo="Nova clínica" aberto onFechar={onFechar} largura="max-w-2xl">
      <form onSubmit={enviar} className="flex flex-col gap-5">
        <fieldset className="grid gap-4 sm:grid-cols-2">
          <legend className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Clínica</legend>
          <Campo rotulo="Segmento" ajuda="Define as palavras, os procedimentos iniciais e o jeito da assistente.">
            <Seletor value={f.segmento} onChange={mudar('segmento')}>
              {(segmentos.data ?? [{ codigo: 'odontologia', nome: 'Odontologia' }]).map((s) => <option key={s.codigo} value={s.codigo}>{s.nome}</option>)}
            </Seletor>
          </Campo>
          <Campo rotulo="Nome"><Entrada required value={f.nome} onChange={mudar('nome')} placeholder="Clínica Sorriso" /></Campo>
          <Campo rotulo="Telefone (WhatsApp)" ajuda="É a chave da clínica: não muda depois.">
            <Entrada required value={f.telefone} onChange={mudar('telefone')} placeholder="(11) 99999-0000" />
          </Campo>
          <Campo rotulo="Endereço"><Entrada value={f.endereco} onChange={mudar('endereco')} placeholder="Rua, número — bairro, cidade" /></Campo>
          <Campo rotulo="Fuso horário">
            <Seletor value={f.fuso} onChange={mudar('fuso')}>
              {FUSOS.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
            </Seletor>
          </Campo>
          <Campo rotulo="Nome da assistente" ajuda={`Como a IA se apresenta aos ${seg?.termos.clientes ?? 'clientes'}.`}>
            <Entrada required value={f.nome_assistente} onChange={mudar('nome_assistente')} />
          </Campo>
          <Campo rotulo={`Primeiro(a) ${seg?.termos.profissional ?? 'profissional'} (opcional)`} ajuda="Faz todos os procedimentos; ajuste depois em Configurações.">
            <Entrada value={f.profissional} onChange={mudar('profissional')} placeholder="Ana Lima" />
          </Campo>
        </fieldset>
        <fieldset className="grid gap-4 sm:grid-cols-2">
          <legend className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Administrador da clínica</legend>
          <Campo rotulo="Nome"><Entrada value={f.admin_nome} onChange={mudar('admin_nome')} /></Campo>
          <Campo rotulo="E-mail" ajuda="Recebe uma senha provisória.">
            <Entrada required type="email" value={f.admin_email} onChange={mudar('admin_email')} />
          </Campo>
        </fieldset>
        <p className="text-xs text-muted">
          Já nasce com horário seg–sex 08–18 (sex até 17), sáb 09–13, almoço 12–13
          {seg ? ` e os procedimentos: ${seg.procedimentos.join(', ')}.` : ' e os procedimentos do segmento.'}
        </p>
        <div className="flex justify-end gap-2">
          <Botao variante="fantasma" onClick={onFechar}>Cancelar</Botao>
          <Botao type="submit" disabled={criar.isPending}>{criar.isPending ? 'Criando…' : 'Criar clínica'}</Botao>
        </div>
      </form>
    </Modal>
  )
}
