import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bot, MessageCircle, QrCode, RefreshCw } from 'lucide-react'
import { useAviso } from '../../components/Aviso'
import { Botao, Secao, Selo, type CorSelo } from '../../components/ui'
import { api, type CanalWhatsapp } from '../../lib/api'
import { useClinica } from '../../lib/clinica'
import { telefone } from '../../lib/formato'

/** Situação do WhatsApp em português simples: rótulo, cor do selo e o que fazer. */
const SITUACAO: Record<CanalWhatsapp['situacao'], [string, CorSelo, string]> = {
  conectado: ['Conectado', 'verde', 'Tudo certo: as mensagens chegam e saem normalmente.'],
  qr: ['Esperando o QR code', 'ambar', 'O WhatsApp foi desconectado do celular. Mostre o QR code e leia com o celular da clínica para reconectar.'],
  iniciando: ['Conectando…', 'azul', 'A conexão está sendo iniciada. Isso leva alguns segundos.'],
  parado: ['Desligado', 'vermelho', 'A conexão está parada. Clique em "Reiniciar conexão".'],
  falhou: ['Com problema', 'vermelho', 'A conexão falhou. Clique em "Reiniciar conexão"; se continuar, fale com o suporte.'],
  sem_resposta: ['Sem resposta', 'vermelho', 'Não conseguimos falar com o servidor do WhatsApp agora. Tente de novo em instantes; se continuar, fale com o suporte.'],
  sem_whatsapp: ['Não ligado', 'cinza', 'Esta clínica ainda não tem WhatsApp ligado. Fale com o suporte da plataforma para ativar.'],
  desconhecido: ['Verificando', 'cinza', 'Não deu para saber a situação agora. Clique em "Atualizar".'],
}

/** Configurações › Canais (D79, D80): toda a equipe vê; só o administrador da clínica reconecta e pausa. */
export function Canais({ podeEditar }: { podeEditar: boolean }) {
  const { clinica } = useClinica()
  const aviso = useAviso()
  const qc = useQueryClient()
  const base = `/clinics/${clinica.id}/config/canais/whatsapp`
  const [qr, setQr] = useState(0) // 0 = escondido; outro valor = versão da imagem
  const q = useQuery({
    queryKey: ['canais', clinica.id],
    queryFn: () => api.get<CanalWhatsapp>(base),
    // enquanto não conecta, confere a cada 5 s (assim a tela muda sozinha depois de ler o QR)
    refetchInterval: (x) => (x.state.data?.ligado && x.state.data.situacao !== 'conectado' ? 5000 : false),
  })
  const s = q.data

  // QR na tela: o código do WhatsApp muda a cada ~20 s; conectou, esconde
  useEffect(() => {
    if (!qr) return
    if (s?.situacao === 'conectado') { setQr(0); aviso.ok('WhatsApp conectado!'); return }
    const t = setInterval(() => setQr(Date.now()), 20_000)
    return () => clearInterval(t)
  }, [qr, s?.situacao, aviso])

  const reiniciar = useMutation({
    mutationFn: () => api.post(`${base}/reiniciar`, {}),
    onSuccess: () => { aviso.ok('Reiniciando a conexão…'); qc.invalidateQueries({ queryKey: ['canais'] }) },
    onError: aviso.erro,
  })
  const pausa = useMutation({
    mutationFn: (pausada: boolean) => api.put<CanalWhatsapp>(`${base}/pausa`, { pausada }),
    onSuccess: (r) => {
      qc.setQueryData(['canais', clinica.id], r)
      qc.invalidateQueries({ queryKey: ['clinica'] })
      aviso.ok(r.isis_pausada ? `${clinica.nome_assistente} pausada no WhatsApp.` : `${clinica.nome_assistente} voltou a atender no WhatsApp.`)
    },
    onError: aviso.erro,
  })

  if (!s) return <p className="text-sm text-muted">{q.isError ? 'Não deu para carregar agora.' : 'Carregando…'}</p>
  const [rotulo, cor, explica] = SITUACAO[s.situacao]
  const nome = clinica.nome_assistente

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Secao titulo="WhatsApp" icone={<MessageCircle className="size-5" />}
        acao={<Botao variante="fantasma" onClick={() => q.refetch()} disabled={q.isFetching}>
          <RefreshCw className={`size-4 ${q.isFetching ? 'animate-spin' : ''}`} />Atualizar
        </Botao>}>
        <div className="flex flex-wrap items-center gap-3">
          <Selo cor={cor} className="!text-sm">{rotulo}</Selo>
          {s.numero && <span className="text-lg font-semibold tabular-nums">{telefone(s.numero)}</span>}
        </div>
        <p className="mt-3 text-sm text-muted">{explica}</p>

        {s.ligado && podeEditar && (
          <div className="mt-5 flex flex-wrap gap-2">
            {s.situacao !== 'conectado' && (
              <Botao onClick={() => setQr(qr ? 0 : Date.now())}><QrCode className="size-4" />{qr ? 'Esconder QR code' : 'Mostrar QR code'}</Botao>
            )}
            <Botao variante="secundario" onClick={() => reiniciar.mutate()} disabled={reiniciar.isPending}>
              <RefreshCw className="size-4" />Reiniciar conexão
            </Botao>
          </div>
        )}
        {s.ligado && !podeEditar && s.situacao !== 'conectado' && (
          <p className="mt-4 rounded-2xl bg-surface-muted px-4 py-3 text-sm text-muted">Peça ao administrador da clínica para reconectar.</p>
        )}

        {qr > 0 && (
          <div className="mt-5 flex flex-col items-center gap-3 rounded-2xl bg-surface-muted p-5">
            <img src={`/api${base}/qr?t=${qr}`} alt="QR code para conectar o WhatsApp" className="size-64 rounded-2xl bg-white p-2"
              onError={() => { setQr(0); aviso.erro(new Error('O QR code ainda não está disponível. Espere alguns segundos ou reinicie a conexão.')) }} />
            <ol className="list-decimal space-y-1 pl-5 text-sm text-muted">
              <li>Abra o WhatsApp no celular da clínica.</li>
              <li>Toque em <b>Aparelhos conectados</b> › <b>Conectar aparelho</b>.</li>
              <li>Aponte a câmera para este código. Ele muda sozinho a cada 20 segundos.</li>
            </ol>
          </div>
        )}
      </Secao>

      <Secao titulo={`${nome} no WhatsApp`} icone={<Bot className="size-5" />}
        acao={<Selo cor={s.isis_pausada ? 'ambar' : 'verde'}>{s.isis_pausada ? 'pausada' : 'atendendo'}</Selo>}>
        <p className="text-sm text-muted">
          {s.isis_pausada
            ? `${nome} não está respondendo no WhatsApp. Toda mensagem nova vai direto para a equipe responder pelo painel. Lembretes e confirmações continuam saindo normalmente.`
            : `${nome} responde os pacientes no WhatsApp e passa para a equipe quando precisa.`}
        </p>
        <p className="mt-2 text-xs text-muted">
          Use a pausa em férias ou quando a equipe quiser atender tudo pessoalmente. O paciente não recebe nenhum aviso. O chat do site não é afetado.
        </p>
        {podeEditar ? (
          <Botao className="mt-5" variante={s.isis_pausada ? 'primario' : 'secundario'} disabled={pausa.isPending}
            onClick={() => pausa.mutate(!s.isis_pausada)}>
            {s.isis_pausada ? `Retomar ${nome}` : `Pausar ${nome} no WhatsApp`}
          </Botao>
        ) : (
          <p className="mt-4 text-xs text-muted">Só o administrador da clínica pausa ou retoma.</p>
        )}
      </Secao>
    </div>
  )
}
