-- Etapa 7A: usuários, papéis e registro de ações do admin (D30, D34, D35)
-- A senha fica no Supabase Auth (auth.users). Aqui ficam só o perfil e os papéis.

create table app_users (
  user_id               uuid primary key,          -- id do usuário no Supabase Auth
  email                 text not null unique,
  name                  text,
  must_change_password  boolean not null default false,  -- D35: senha provisória → troca no 1º acesso
  active                boolean not null default true,
  created_at            timestamptz not null default now()
);

-- Dono da plataforma (painel de admin geral)
create table platform_admins (
  user_id     uuid primary key references app_users(user_id) on delete cascade,
  created_at  timestamptz not null default now()
);

-- Quem trabalha em cada clínica
create table clinic_users (
  clinic_id   uuid not null references clinics(id) on delete cascade,
  user_id     uuid not null references app_users(user_id) on delete cascade,
  role        text not null check (role in ('clinic_admin', 'reception')),
  active      boolean not null default true,
  created_at  timestamptz not null default now(),
  primary key (clinic_id, user_id)
);

create index clinic_users_usuario on clinic_users (user_id);

-- Registro de ações sensíveis do admin geral (ex.: "entrar como" a clínica — spec 07)
create table admin_audit (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references app_users(user_id),
  clinic_id   uuid references clinics(id) on delete set null,
  action      text not null,
  detail      jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);

alter table app_users       enable row level security;
alter table platform_admins enable row level security;
alter table clinic_users    enable row level security;
alter table admin_audit     enable row level security;
