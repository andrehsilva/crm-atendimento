// Cliente da API do backend. Erros de regra chegam como {codigo, mensagem}.

export class ErroApi extends Error {
  codigo: string
  constructor(codigo: string, mensagem: string) {
    super(mensagem)
    this.codigo = codigo
  }
}

export const EVENTO_SESSAO = 'isis:sessao'

async function req<T>(metodo: string, url: string, corpo?: unknown): Promise<T> {
  // Arquivo (logo, foto): vai cru no corpo, com o tipo do próprio arquivo
  const arquivo = corpo instanceof Blob
  const r = await fetch(`/api${url}`, {
    method: metodo,
    headers: corpo ? { 'Content-Type': arquivo ? corpo.type || 'application/octet-stream' : 'application/json' } : undefined,
    body: corpo ? (arquivo ? corpo : JSON.stringify(corpo)) : undefined,
  })
  const dados = await r.json().catch(() => null)
  if (!r.ok) {
    // Sessão vencida ou senha provisória: avisa o ProvedorAuth para mostrar a tela certa
    if (dados?.codigo === 'NAO_AUTENTICADO' || dados?.codigo === 'TROCAR_SENHA') {
      if (!url.startsWith('/auth/')) window.dispatchEvent(new Event(EVENTO_SESSAO))
    }
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
  put: <T>(url: string, corpo: unknown) => req<T>('PUT', url, corpo),
  delete: <T>(url: string) => req<T>('DELETE', url),
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
  segmento: string
  termos: Termos
  cor: string
  logo_versao: number | null
  /** Etapa 10A (D46): false = assistente desligada (clínica sem chave de IA) */
  ia_ativa: boolean
  /** nome que a assistente usa com os clientes (Configurações › Assistente) */
  nome_assistente: string
  /** 10C (D51–D54): false = painel mostra só os "Primeiros passos" */
  configurada: boolean
  /** etapas obrigatórias que faltam (depois de concluída vira só aviso) */
  pendencias: string[]
  /** 10B (D45): gasto do mês x teto; "aviso" aos 80%, "pausada" aos 100% */
  uso_ia: SituacaoUsoIa
  /** D55/D61: clínica de apresentação (onde fica o "Reiniciar demonstração") */
  apresentacao: boolean
}

export type SituacaoUsoIa = { gasto_usd: number; teto_usd: number | null; pct: number | null; nivel: 'ok' | 'aviso' | 'pausada' }
export type UsoIa = {
  situacao: SituacaoUsoIa
  cotacao_brl: number | null
  dias: { dia: string; respostas: number; audio_segundos: number; tokens_entrada: number; tokens_saida: number; custo_usd: number }[]
  meses: { mes: string; respostas: number; tokens: number; custo_usd: number }[]
  sem_preco: { provider: string; model: string }[]
}
export type PrecoModelo = { provider: string; model: string; entrada_usd: number; saida_usd: number; cache_usd: number | null; updated_at: string }
export type Precos = { precos: PrecoModelo[]; cotacao_brl: number | null }

export type EtapaInicial = { codigo: 'clinica' | 'assistente' | 'aparencia' | 'horarios' | 'equipe' | 'ia'; titulo: string; ok: boolean; falta: string | null }
export type ConfigInicial = { concluida: boolean; pode_concluir: boolean; etapas: EtapaInicial[] }

/** Etapa 9B: cor principal e logo da clínica */
export type Aparencia = { cor: string; cor_padrao: string; logo_versao: number | null }

/** Palavras do negócio da clínica (Etapa 9): "dentista/paciente/consulta", "profissional/cliente/atendimento"… */
export type Termos = {
  profissional: string
  profissionais: string
  cliente: string
  clientes: string
  atendimento: string
  atendimentos: string
  genero: 'f' | 'm'
  o: string
  sua: string
  da_sua: string
  uma: string
  nova: string
}
export type TermosEditaveis = Partial<Pick<Termos, 'profissional' | 'profissionais' | 'cliente' | 'clientes' | 'atendimento' | 'atendimentos' | 'genero'>>
export type Segmento = { codigo: string; nome: string; termos: TermosEditaveis; lembrete_discreto: boolean; procedimentos: string[] }

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
  foto_versao: number | null
}

export type Mensagem = {
  id: string
  kind: 'confirmacao' | 'remarcacao' | 'cancelamento' | 'lembrete' | 'aniversario' | 'campanha'
  channel: string
  body: string
  status: 'agendada' | 'enviada' | 'entregue' | 'lida' | 'falhou' | 'cancelada'
  created_at: string
  scheduled_for: string
  sent_at: string | null
  error: string | null
  paciente: string | null
  telefone: string
}

export type Paciente = {
  id: string
  name: string | null
  phone: string
  birth_date: string | null
  drive_url: string | null
  notas: number
  origin: string
  crm_stage: Etapa
  dentista_referencia: string | null
  ultima_consulta: string | null
  proxima_consulta: string | null
  foto_versao: number | null
}

/** Etapa 9C: histórico de observações do cliente e pasta do Drive */
export type NotaCliente = {
  id: string
  texto: string
  autor: string
  criado_em: string
  editado_em: string | null
  pode_editar: boolean
  pode_apagar: boolean
}
export type Observacoes = { drive_url: string | null; notas: NotaCliente[] }

export type Dashboard = {
  hoje: string
  consultas_hoje: Consulta[]
  confirmadas: number
  pendentes: number
  precisando_humano: number
  leads_parados: number
  mensagens_na_fila: number
  esperando: { id: string; name: string | null; phone: string; channel: 'web' | 'whatsapp'; last_message_at: string; ultima_mensagem: string | null }[]
  parados: { id: string; name: string | null; phone: string; last_event: string; last_activity_at: string }[]
  fila: { id: string; kind: Mensagem['kind']; body: string; scheduled_for: string; attempts: number; error: string | null; paciente: string | null; phone: string }[]
  aniversariantes: { id: string; name: string; phone: string }[]
}

export type MensagemChat = { id: string; direction: 'in' | 'out'; author: string; content: string; created_at: string }

export type Relogio = {
  agora: string
  simulado: boolean
  adiantado_min: number
  proximo_lembrete: string | null
  envio_automatico: boolean
}

export type ConfigAniversario = { ativo: boolean; texto: string; hora: string; previa: string; limite: number }

export type Usuario = {
  id: string
  email: string
  nome: string | null
  super_admin: boolean
  trocar_senha: boolean
  foto_versao: number | null
  clinicas: { clinic_id: string; papel: 'clinic_admin' | 'reception' }[]
}

// ---------------------------------------------------------------- admin geral (7B)
export type AdminClinica = {
  id: string
  /** D55: clínica de apresentação da plataforma (no máximo uma) */
  apresentacao: boolean
  name: string
  phone: string
  slug: string
  status: 'ativa' | 'suspensa'
  timezone: string
  address: string | null
  created_at: string
  nome_assistente: string
  whatsapp_sessao: string | null
  whatsapp_status: string | null
  whatsapp_numero: string | null
  conversas_mes: number
  usuarios: number
}

export type UsuarioClinica = {
  id: string
  email: string
  nome: string | null
  papel: 'clinic_admin' | 'reception'
  ativo: boolean
  senha_provisoria: boolean
}

export type SessaoWaha = { sessao: string; status: string; numero: string | null; webhooks: string[]; clinic_id: string | null; clinica: string | null }

export type StatusWhatsapp =
  | { ligado: false }
  | { ligado: true; sessao: string; status: string; numero: string | null; ativo: boolean; webhooks?: string[]; webhook_ok?: boolean; webhook_esperado?: string | null; erro?: string }

export type UsoClinica = {
  id: string
  name: string
  status: string
  conversas: number
  mensagens_recebidas: number
  respostas_ia: number
  tempo_medio_s: number | null
  falhas_ia: number
  automaticas_enviadas: number
  consultas_pela_ia: number
  tokens_ia: number
  custo_clinica_usd: number
  custo_plataforma_usd: number
}

export type Plataforma = {
  ambiente: string
  modelo_ia: string
  ia_configurada: boolean
  waha_servidor: string | null
  waha_configurado: boolean
  webhook_assinado: boolean
  endereco_publico: string | null
  mensagens_automaticas: boolean
  modo_teste_numeros: number | null
  supabase: string | null
  transcricao_configurada: boolean
}

// ---------------------------------------------------------------- configurações da clínica (7C)
export type PerfilClinica = {
  nome: string; telefone: string; endereco: string | null; slug: string; telefone_urgencia: string | null; sobre: string | null
  segmento: string; termos: Termos; termos_proprios: TermosEditaveis; termos_do_segmento: TermosEditaveis; lembrete_discreto: boolean
}
export type PausaDia = { inicio: string; fim: string }
export type DiaHorario = { weekday: number; nome: string; ativo: boolean; inicio: string; fim: string; pausas: PausaDia[] }
export type Horarios = { dias: DiaHorario[]; profissionais_com_horario_proprio: string[] }
export type ConsultaAfetada = { id: string; quando: string; paciente: string | null; profissional: string }
export type ProcedimentoCfg = {
  id: string
  nome: string
  descricao: string | null
  duracao_min: number
  preco_centavos: number | null
  ativo: boolean
  ia_pode_marcar: boolean
  profissionais: string[]
  consultas_futuras: number
}
export type Folga = { id: string; professional_id: string | null; inicio: string; fim: string; motivo: string | null }
export type ProfissionalCfg = {
  id: string
  nome: string
  especialidade: string | null
  /** Etapa 11: aparecem no site da clínica */
  bio: string | null
  foto_versao: number | null
  cor: string | null
  ativo: boolean
  procedimentos: string[]
  horario_proprio: boolean
  folgas: Folga[]
}
/** Etapa 10A: IA da clínica. A chave nunca vem do servidor, só os 4 últimos caracteres. */
export type ProvedorIa = 'google' | 'openai' | 'opencode' | 'openrouter'
export type IaClinica = {
  provedor: ProvedorIa | null
  modelo: string | null
  tem_chave: boolean
  chave_final: string | null
  usa_plataforma: boolean
  atualizado_em: string | null
  origem: 'clinica' | 'plataforma' | null
  chave_ilegivel: boolean
  modelo_aprovado: boolean
  plataforma: { configurada: boolean; modelo: string | null }
  provedores: { id: ProvedorIa; nome: string; onde: string; modelos_aprovados: string[] }[]
}
export type TesteIa = { ok: boolean; ms?: number; resposta?: string; detalhe?: string }

export type AssistenteCfg = {
  nome_assistente: string
  tratamento: 'você' | 'senhor(a)'
  mostrar_precos: boolean
  aceitar_audio: boolean
  antecedencia_min_horas: number
  horizonte_dias: number
  aviso_cancelamento_horas: number
  limite_consultas_futuras: number
  lembrete_hora: string
}
