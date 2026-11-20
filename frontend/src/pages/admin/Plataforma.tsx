import { useQuery } from '@tanstack/react-query'
import { PageHeader } from '../../components/PageHeader'
import { Secao, Selo } from '../../components/ui'
import { api, type Plataforma } from '../../lib/api'

const sim = (ok: boolean, rotuloOk = 'configurado', rotuloNao = 'não configurado') =>
  ok ? <Selo cor="verde">{rotuloOk}</Selo> : <Selo cor="ambar">{rotuloNao}</Selo>

export function AdminPlataforma() {
  const q = useQuery({ queryKey: ['admin', 'plataforma'], queryFn: () => api.get<Plataforma>('/admin/plataforma') })
  if (q.isLoading || !q.data) return <p className="text-sm text-muted">Carregando…</p>
  const p = q.data
  const linhas: [string, React.ReactNode][] = [
    ['Ambiente', p.ambiente === 'dev' ? <Selo cor="azul">desenvolvimento</Selo> : <Selo cor="verde">{p.ambiente}</Selo>],
    ['Chave da plataforma (IA)', <span key="m">{p.modelo_ia} {sim(p.ia_configurada)}</span>],
    ['Servidor WAHA', <span key="w">{p.waha_servidor ?? '—'} {sim(p.waha_configurado)}</span>],
    ['Webhook assinado (HMAC)', sim(p.webhook_assinado, 'sim', 'não')],
    ['Endereço público do backend', p.endereco_publico ?? <span className="text-muted">— (abra o túnel)</span>],
    ['Mensagens automáticas', sim(p.mensagens_automaticas, 'ligadas', 'desligadas')],
    ['Modo de teste (números liberados)', p.modo_teste_numeros === null ? 'desligado (produção)' : `${p.modo_teste_numeros} número(s)`],
    ['Banco e login (Supabase)', p.supabase ?? '—'],
  ]
  return (
    <>
      <PageHeader titulo="Configurações da plataforma" subtitulo="Somente leitura. Estes valores ficam no backend/.env (as chaves nunca aparecem aqui)." />
      <Secao className="max-w-3xl">
        <dl className="grid grid-cols-[minmax(0,16rem)_1fr] gap-x-6 gap-y-3 text-sm">
          {linhas.map(([r, v]) => (
            <div key={r} className="contents">
              <dt className="text-muted">{r}</dt>
              <dd className="flex flex-wrap items-center gap-2">{v}</dd>
            </div>
          ))}
        </dl>
      </Secao>
    </>
  )
}
