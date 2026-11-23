-- Etapa 30 (D121): o admin geral libera, por clínica, o "Perguntar à assistente". Começa desligado.
alter table clinics add column if not exists pergunte_liberado boolean not null default false;
