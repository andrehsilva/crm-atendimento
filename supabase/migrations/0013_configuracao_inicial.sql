-- Etapa 10C (D51–D54): configuração inicial obrigatória.
-- configurada_em: quando o admin concluiu os "Primeiros passos". Depois disso o painel nunca trava de novo (D54).
alter table clinics add column if not exists configurada_em timestamptz;
-- verificada_em: quando a chave salva da clínica passou no "Testar conexão". Trocar chave ou modelo zera.
alter table clinic_ai add column if not exists verificada_em timestamptz;
