-- Etapa 11A (ajuste): cor própria para cada layout do site (vazio = cor da clínica).
-- Ex.: {"moderno": "#0f766e", "acolhedor": "#b85c74"}
alter table clinic_sites add column if not exists cores jsonb not null default '{}'::jsonb;
