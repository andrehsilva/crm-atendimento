// Cliente da API do backend. Erros de regra chegam como {codigo, mensagem}.

export class ErroApi extends Error {
  codigo: string
  constructor(codigo: string, mensagem: string) {
    super(mensagem)
    this.codigo = codigo
  }
}

async function req<T>(metodo: string, url: string, corpo?: unknown): Promise<T> {
  const r = await fetch(`/api${url}`, {
    method: metodo,
    headers: corpo ? { 'Content-Type': 'application/json' } : undefined,
    body: corpo ? JSON.stringify(corpo) : undefined,
  })
  const dados = await r.json().catch(() => null)
  if (!r.ok) {
    if (dados?.codigo) throw new ErroApi(dados.codigo, dados.mensagem)
    const detalhe = Array.isArray(dados?.detail) ? dados.detail.map((d: { msg: string }) => d.msg).join('; ') : dados?.detail
    throw new ErroApi('ERRO', detalhe || `Erro ${r.status}`)
  }
  return dados as T
}

export const api = {
  get: <T>(url: string) => req<T>('GET', url),
  post: <T>(url: string, corpo?: unknown) => req<T>('POST', url, corpo ?? {}),
  patch: <T>(url: string, corpo: unknown) => req<T>('PATCH', url, corpo),
}

// ---------------------------------------------------------------- tipos
export type Clinica = {
  id: string
  name: string
  phone: string
  slug: string
  timezone: string
  address: string | null
  horario: { weekday: number; start_time: string; end_time: string }[]
  pausas: { weekday: number; start_time: string; end_time: string }[]
}

export type Profissional = { id: string; name: string; specialty: string | null; color: string | null; service_ids: string[] }
export type Procedimento = { id: string; name: string; description: string | null; duration_min: number; bookable_by_ai: boolean }
export type Cadastros = { profissionais: Profissional[]; procedimentos: Procedimento[] }

export type StatusConsulta = 'agendada' | 'confirmada' | 'cancelada' | 'realizada' | 'faltou'
export type Consulta = {
  id: string
  status: StatusConsulta
  source: string
  starts_at: string
  ends_at: string
  cancel_reason: string | null
  patient_id: string
  paciente: string | null
  telefone: string
  professional_id: string
  profissional: string
  cor: string | null
  service_id: string
  procedimento: string
}

export type Slot = { professional_id: string; profissional: string; starts_at: string; ends_at: string; preferido: boolean }

export type Etapa = 'novo_contato' | 'agendado' | 'confirmado' | 'cancelado'
export type CardCrm = {
  id: string
  name: string | null
  phone: string
  crm_stage: Etapa
  stage_changed_at: string
  last_event: string
  last_activity_at: string
  created_at: string
  atendimento_manual: boolean
  recorrente: boolean
  consulta_id: string | null
  proxima_consulta: string | null
  procedimento: string | null
}

export type Mensagem = {
  id: string
  kind: 'confirmacao' | 'remarcacao' | 'cancelamento' | 'lembrete' | 'aniversario'
  channel: string
  body: string
  status: 'agendada' | 'enviada' | 'entregue' | 'lida' | 'falhou' | 'cancelada'
  created_at: string
  sent_at: string | null
  paciente: string | null
  telefone: string
}

export type Paciente = {
  id: string
  name: string | null
  phone: string
  birth_date: string | null
  notes: string | null
  origin: string
  crm_stage: Etapa
  dentista_referencia: string | null
  ultima_consulta: string | null
  proxima_consulta: string | null
}

export type Dashboard = {
  hoje: string
  consultas_hoje: Consulta[]
  confirmadas: number
  pendentes: number
  precisando_humano: number
  leads_parados: number
  mensagens_na_fila: number
  aniversariantes: { id: string; name: string; phone: string }[]
}

export type MensagemChat = { id: string; direction: 'in' | 'out'; author: string; content: string; created_at: string }
