-- Etapa 9C: observações do cliente em histórico (D48) e link da pasta do Google Drive (D49).
-- As notas são internas da equipe: a assistente não lê esta tabela.

create table patient_notes (
  id           uuid primary key default gen_random_uuid(),
  clinic_id    uuid not null references clinics(id) on delete cascade,
  patient_id   uuid not null references patients(id) on delete cascade,
  author_id    uuid references app_users(user_id) on delete set null,
  author_name  text not null,                 -- guardado na hora: continua aparecendo se o usuário sair
  body         text not null check (char_length(btrim(body)) between 1 and 5000),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create index patient_notes_paciente on patient_notes (clinic_id, patient_id, created_at desc);
alter table patient_notes enable row level security;

-- Só o link (sem integração): precisa ser uma pasta/arquivo do Google Drive
alter table patients add column drive_url text
  check (drive_url is null or (drive_url ~ '^https://drive\.google\.com/[^\s]*$' and char_length(drive_url) <= 500));

-- O campo antigo "observações" vira a primeira nota do histórico
insert into patient_notes (clinic_id, patient_id, author_name, body, created_at, updated_at)
select clinic_id, id, 'Cadastro', btrim(notes), created_at, created_at
from patients where coalesce(btrim(notes), '') <> '';

update patients set notes = null where notes is not null;
