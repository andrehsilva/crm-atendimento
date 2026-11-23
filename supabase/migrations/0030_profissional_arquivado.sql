-- Etapa 28 (D110/D111): excluir profissional. Sem histórico → apaga de vez; com histórico → arquiva
-- (fica inativo e some da lista; consultas antigas, relatórios e conversas continuam com o nome dele).
alter table professionals add column if not exists archived_at timestamptz;
