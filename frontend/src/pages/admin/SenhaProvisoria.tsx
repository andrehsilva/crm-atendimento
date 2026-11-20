import { useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { Botao, Modal } from '../../components/ui'

/** Mostra a senha provisória UMA vez (D35). Depois de fechar, não dá para ver de novo. */
export function SenhaProvisoria({ email, senha, onFechar }: { email: string; senha: string | null; onFechar: () => void }) {
  const [copiado, setCopiado] = useState(false)
  return (
    <Modal titulo="Acesso criado" aberto onFechar={onFechar}>
      {senha ? (
        <div className="flex flex-col gap-4 text-sm">
          <p>Envie estes dados para a pessoa por um canal seguro. No 1º acesso ela cria a própria senha.</p>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 rounded-2xl bg-surface-muted p-4">
            <dt className="text-muted">E-mail</dt>
            <dd className="font-medium">{email}</dd>
            <dt className="text-muted">Senha provisória</dt>
            <dd className="flex items-center gap-2 font-mono text-base font-semibold tracking-wide">
              {senha}
              <button type="button" aria-label="Copiar senha" className="rounded-lg p-1 text-muted hover:bg-surface hover:text-text"
                onClick={() => navigator.clipboard?.writeText(senha).then(() => setCopiado(true)).catch(() => undefined)}>
                {copiado ? <Check className="size-4 text-green-600" /> : <Copy className="size-4" />}
              </button>
            </dd>
          </dl>
          <p className="rounded-xl bg-primary-soft px-3 py-2 text-primary">Anote agora: esta senha não aparece de novo.</p>
        </div>
      ) : (
        <p className="text-sm">
          <strong>{email}</strong> já tinha acesso ao sistema, então foi só ligado a esta clínica. A senha continua a mesma.
        </p>
      )}
      <div className="mt-6 flex justify-end">
        <Botao onClick={onFechar}>Entendi</Botao>
      </div>
    </Modal>
  )
}
