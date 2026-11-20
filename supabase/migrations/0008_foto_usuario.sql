-- Etapa 9B: foto de perfil de cada usuário do painel (mesmas regras da logo: PNG/JPG/WebP até 512 KB).

create table user_photos (
  user_id     uuid primary key references app_users(user_id) on delete cascade,
  mime        text not null check (mime in ('image/png', 'image/jpeg', 'image/webp')),
  data        bytea not null check (octet_length(data) <= 524288),
  updated_at  timestamptz not null default now()
);

alter table user_photos enable row level security;
