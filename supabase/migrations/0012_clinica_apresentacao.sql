-- D55: clínica de apresentação da plataforma (hoje a Clínica Rodrigues, endereço /demo).
-- O admin da plataforma entra sempre por ela e só nela aparece o botão "Admin geral". No máximo uma.
alter table clinics add column if not exists apresentacao boolean not null default false;
create unique index if not exists clinics_uma_apresentacao on clinics ((true)) where apresentacao;
update clinics set apresentacao = true
where slug = 'demo' and not exists (select 1 from clinics where apresentacao);
