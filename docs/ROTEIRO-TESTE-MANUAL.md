# Roteiro de teste manual — do zero até o atendimento

Use este roteiro para testar tudo, na ordem, como uma clínica nova faria. Cada passo diz **o que fazer** e **o que deve acontecer** (✔). Marque `[x]` no que passou e anote no fim o que deu errado.

**Antes de começar**
- [ ] Backend e painel rodando: backend em `backend/`, com `uv run uvicorn app.main:app --reload`; painel em `frontend/`, com `npm run dev`.
- [ ] Entrar no painel com **andrehrsilva@gmail.com**, que é o admin geral.
- [ ] Ter à mão: um e-mail para o administrador da clínica nova e outro para a recepção (podem ser apelidos, como `seuemail+admin@gmail.com`).
- [ ] **WhatsApp:** os testes marcados com 📱 precisam de WhatsApp ligado e de números liberados em `ENVIO_SOMENTE_PARA`. Sem WhatsApp, pule esses passos; o resto funciona pelo **chat web** (Demonstração ou botão "Abrir demonstração").

> Dica: deixe a aba do painel aberta numa janela e o chat web noutra, para ver as mudanças em tempo real.

---

## 1. Admin geral: criar a clínica

- [ ] **1.1** Admin geral › Clínicas › **Nova clínica**: nome, telefone da clínica, segmento (odontologia), fuso, e-mail do primeiro administrador.
  ✔ A clínica aparece na lista. Uma **senha provisória** aparece **uma vez**: anote.
- [ ] **1.2** Tente criar outra clínica com o **mesmo telefone**.
  ✔ É recusada (o telefone é a chave da clínica).
- [ ] **1.3** Na clínica criada › **Usuários**: crie um usuário de **recepção**.
  ✔ Aparece a senha provisória. O usuário aparece como "senha provisória".
- [ ] **1.4** **Entrar como** a clínica (suporte).
  ✔ O painel abre na clínica. A ação fica registrada.
- [ ] **1.5** (Opcional) **Suspender** e reativar a clínica.
  ✔ Suspensa, ela não marca nem envia nada.

## 2. Primeiro acesso do administrador da clínica

- [ ] **2.1** Saia e entre com o e-mail do administrador da clínica e a senha provisória.
  ✔ O sistema obriga a **trocar a senha** (mínimo 8 caracteres, com letras e números).
- [ ] **2.2** Esqueci a senha (tela de entrar).
  ✔ Chega o e-mail de redefinição, se o Supabase estiver configurado para e-mail.
- [ ] **2.3** **Primeiros passos:** o painel mostra só a configuração inicial, até concluir.
  ✔ O que faltar vira aviso. Ao concluir, o painel libera para toda a equipe na hora.

## 3. Configurações (como administrador da clínica)

### Perfil
- [ ] **3.1** Nome, telefone de urgência, endereço, "Sobre a clínica" (ex.: "Crianças podem acompanhar os pais").
  ✔ Salva com aviso no canto da tela.
- [ ] **3.2** Aparência: cor e logo. Minha conta: foto e troca de senha.
  ✔ A cor muda o painel. A logo aparece na barra lateral e na tela de entrar.

### Horários
- [ ] **3.3** Segunda a sexta, 08–18, com pausa de 12–13. Sábado fechado.
  ✔ A agenda mostra a pausa hachurada.
- [ ] **3.4** Mude o horário de um dia em que já há consulta marcada (faça depois do 6.1).
  ✔ O sistema lista as consultas que ficam fora. Elas **continuam marcadas**.

### Procedimentos
- [ ] **3.5** Crie: Limpeza (60 min), Restauração (60 min, preço R$ 200), Urgência (60 min, **só recepção**).
  ✔ Aparecem na janela de marcar consulta.

### Profissionais
- [ ] **3.6** Crie a Dra. Ana (faz tudo) e o Dr. Bruno (faz Limpeza e Restauração). Foto, cor e bio.
  ✔ A cor aparece na agenda.
- [ ] **3.7** **Horário** do Dr. Bruno: horário próprio, terça e quinta 08–12, e quinta também 14–18.
  ✔ Faixa fora do horário da clínica ou faixas sobrepostas são recusadas. Na agenda, ele não tem horário livre na segunda.
- [ ] **3.8** **Folga** da Dra. Ana num dia da semana que vem.
  ✔ O dia fica bloqueado para ela.
- [ ] **3.9** 📱 **Resumo do dia** do Dr. Bruno: ative, informe um número liberado e um horário, confira a **prévia de amanhã** e clique em **"Mandar teste agora"**.
  ✔ Chega a grade do dia, só com o primeiro nome do paciente, o procedimento, ✅ ou ⏳, a pausa e os horários livres.

### Convênios
- [ ] **3.10** Cadastre Amil Dental e Bradesco Dental. Deixe ligado "Perguntar convênio no primeiro contato".
  ✔ Repetido é recusado. Desligar um convênio não apaga o cadastro de ninguém.

### Assistente
- [ ] **3.11** Nome da assistente, tratamento (você ou senhor(a)), "mostrar preços" ligado, áudio ligado.
- [ ] **3.12** Regras: antecedência de 2 h, horizonte de 60 dias, aviso de cancelamento de 24 h, 2 consultas futuras, **2 faltas em 45 dias**, lembrete às 09:00.
- [ ] **3.13** **Jeito da clínica:** "Sempre ofereça primeiro horários de manhã".
  ✔ Até 1.500 caracteres. Não passa por cima das regras.

### Uso da IA
- [ ] **3.14** Chave de IA da clínica (ou a da plataforma) e o botão **Testar**. Teto do mês (ex.: US$ 5).
  ✔ O teste responde "ok". Aos 80% aparece aviso. Aos 100% a assistente pausa e avisa o paciente.

### Aniversário e campanhas
- [ ] **3.15** Aniversário: ative, edite o texto e confira a prévia.
- [ ] **3.16** **Pós-consulta:** ligue (horário 10:00). Desmarque "Urgência" em "procedimentos que recebem".
- [ ] **3.17** **Retorno:** ligue (6 meses, 10:00). Confira os textos do 1º e do 2º convite.
- [ ] **3.18** Campanha: crie uma "Férias" para "todos os clientes" e confira a contagem, o tempo estimado e a prévia. **Cancele** antes de sair.

### Canais
- [ ] **3.19** Toda a equipe vê o status do WhatsApp. 📱 O administrador mostra o **QR code**, reinicia e **pausa ou retoma** a assistente no WhatsApp.
  ✔ Pausada: as mensagens vão direto para a equipe, e o topo do painel avisa.

### Site
- [ ] **3.20** Publique o site, escolha o layout e a cor, monte a galeria (foto, legenda e ordem).
  ✔ A página pública abre com os profissionais e os procedimentos.

### Usuários
- [ ] **3.21** Crie, desative e reative um usuário, e troque o papel.
  ✔ A recepção não vê a aba Usuários e não muda nenhuma configuração (só vê).

---

## 4. Assistente pelo chat web (sem WhatsApp)

Use um telefone **novo** a cada bloco (ex.: 11 90000-0001, 0002…).

- [ ] **4.1 Primeiro contato e convênio:** "Quero marcar uma limpeza" › diga "Amil".
  ✔ Ela pergunta se é **convênio ou particular** antes de marcar. "Amil" vira **Amil Dental**. A tag aparece no CRM.
- [ ] **4.2 Convênio não atendido:** "É Unimed".
  ✔ Ela diz que a clínica não atende e oferece o particular. Aceite e continue.
- [ ] **4.3 Marcar:** escolha dia e turno ("terça de manhã, tanto faz o dentista"), dê o nome completo e confirme.
  ✔ Ela oferece no máximo 3 horários, mostra um **resumo** e só marca depois do seu "sim". Ao fim, diz **quando vem o lembrete**. A consulta aparece na agenda **na hora**, e o sino mostra "Ísis marcou…".
- [ ] **4.4 Dentista com horário próprio:** "Quero com o Dr. Bruno na segunda".
  ✔ Ela explica que ele atende terça e quinta.
- [ ] **4.5 "Vocês me lembram?"**
  ✔ Ela responde com o dia e a hora reais do lembrete daquela consulta.
- [ ] **4.6 Remarcar e cancelar:** "Preciso remarcar para quinta" e, depois, "quero cancelar".
  ✔ Resumo antes e confirmação. Remarcar ou cancelar em cima da hora: ela avisa a política. O lembrete velho é cancelado.
- [ ] **4.7 Limite:** marque 2 consultas e peça uma 3ª.
  ✔ Ela explica o limite antes de buscar horários.
- [ ] **4.8 Preço:** "Quanto custa restauração?" e depois "e clareamento?" (não cadastrado).
  ✔ Informa R$ 200 e não inventa o preço do clareamento.
- [ ] **4.9 Dúvida da clínica:** "Posso levar meu filho?"
  ✔ Responde pelo "Sobre a clínica".
- [ ] **4.10 Urgência:** "Meu rosto está inchado e com febre".
  ✔ Orienta procurar atendimento e passa o telefone de urgência. A conversa vai para a equipe, o paciente recebe o aviso fixo, e o sino **toca** "aguardando atendimento humano".
- [ ] **4.11 Pedir pessoa:** "Quero falar com um atendente".
  ✔ Passa para a equipe com aviso. Ela não responde mais até alguém devolver.
- [ ] **4.12 Procedimento só da recepção:** "Quero marcar urgência".
  ✔ Ela não marca e chama a equipe.
- [ ] **4.13 Fora de assunto ou diagnóstico:** "Que remédio tomo para dor?"
  ✔ Não indica remédio.
- [ ] **4.14 Mensagens picadas:** mande "oi", "tudo bem" e "quero marcar" em sequência rápida.
  ✔ Uma resposta só. 📱 No WhatsApp aparece "digitando…".

---

## 5. Painel: recepção (entre com o usuário de recepção)

### Conversas e CRM
- [ ] **5.1** No CRM, abra a conversa do 4.10 › **Assumir conversa** › responda › **Devolver para a assistente**.
  ✔ O selo troca **na hora**, sem recarregar. A resposta aparece. A conversa volta para a assistente.
- [ ] **5.2** Card de alguém **que nunca conversou**: use **"Marcar consulta"** (telefone e nome já preenchidos). 📱 Use também **"Iniciar conversa pelo WhatsApp"**.
  ✔ A conversa iniciada pela equipe começa em atendimento manual.
- [ ] **5.3** Arraste cards entre as colunas.
  ✔ "Agendados" abre a marcação. "Cancelados" pede confirmação. Aparece o aviso "Fulano movido para…".
- [ ] **5.4** Tags no card: Novo, Recorrente, Em tratamento, Aguardando, Particular ou o nome do convênio.

### Agenda
- [ ] **5.5** Marque pela agenda (clique num horário vazio) e veja a consulta com a **etiqueta** "A confirmar". Confirme e veja "Confirmada".
- [ ] **5.6** **Série:** "Repetir", 4 sessões a cada 7 dias, com um dos horários já ocupado.
  ✔ Marca as que cabem e mostra a que não coube, com o motivo. O tratamento é aberto sozinho. Uma **confirmação só**, com as datas, aparece em Mensagens.
- [ ] **5.7** **Presença:** numa consulta de hoje que já passou, o sino mostra "**Registrar presença**". Clique.
  ✔ A agenda abre no dia, com a consulta aberta. Marque **Compareceu** e o aviso some. Com o pós-consulta ligado, aparece em Mensagens › Na fila um "Pós-consulta" para amanhã às 10:00.
- [ ] **5.8** **Faltas:** marque "Faltou" em 2 consultas do mesmo paciente (dentro de 45 dias). Pelo chat, ele pede para marcar.
  ✔ A assistente não marca e passa para a recepção. A recepção marca normalmente.

### Tratamentos
- [ ] **5.9** Leads / Clientes › 🩺 (ou o botão **Tratamento** na conversa) › **Abrir tratamento**: Restauração, 4 sessões, recado "não marcar antes de 10 dias da extração".
  ✔ A tag "Em tratamento" aparece. As sessões não contam no limite de 2.
- [ ] **5.10** **Aguardar** › Protético, com previsão para amanhã. Pelo chat, o paciente pede para marcar a próxima sessão.
  ✔ A assistente não marca. Explica que a clínica entra em contato, e o sino mostra "Fulano quer marcar…". Uma **limpeza**, ela marca normalmente.
- [ ] **5.11** Deixe a previsão vencer (ou ajuste a data no passado).
  ✔ O sino mostra "a previsão era…".
- [ ] **5.12** **Retomar**, editando o texto. 📱 O paciente recebe o convite e, ao responder, a assistente marca. Sem WhatsApp, confira o "Tratamento" em Mensagens › Na fila.
- [ ] **5.13** **Encerrar** › Concluído › volta em 6 meses.
  ✔ O tratamento aparece em "Encerrados".

### Clientes
- [ ] **5.14** Edite o cadastro: nome, nascimento, **convênio**, foto, observações e pasta do Drive.
  ✔ As tags atualizam. O filtro por tag funciona.

### Mensagens
- [ ] **5.15** As abas Na fila, Enviadas e Não enviadas, e o filtro por tipo.
  ✔ A data aparece com ícone e "sai amanhã" ou "em N dias". 📱 Os selos ✓ enviada, ✓✓ entregue e ✓✓ lida mudam sozinhos.
- [ ] **5.16** 📱 Na conversa, as respostas mostram ✓, ✓✓ e ✓✓ azul quando o paciente lê.

### Sino e avisos
- [ ] **5.17** O sino conta e lista: aguardando humano (com som), o que a assistente marcou, remarcou ou cancelou, confirmações, mensagem que não saiu, presença, tratamento e gasto da IA. O número aparece também no título da aba.
- [ ] **5.18** **Marcar todas como lidas.** Depois entre com outro usuário.
  ✔ Para ele, as notificações continuam não lidas. As de "situação" não somem marcando como lidas: só quando o problema é resolvido.
- [ ] **5.19** Toda ação que salva mostra o aviso de confirmação no canto da tela.

### Dashboard e relatórios (administrador)
- [ ] **5.20** Dashboard: agenda do dia e filtro por profissional.
- [ ] **5.21** Relatórios: baixe cada planilha (recall, atendimentos, produção, faltas, cadastro, aniversariantes, desempenho da assistente).
  ✔ O recall não traz quem está em tratamento e usa o "volta em".

---

## 6. 📱 WhatsApp (quando estiver ligado)

- [ ] **6.1** Admin geral › clínica › WhatsApp: ligar a sessão, **Testar conexão**, apontar o webhook (ou o webhook exclusivo).
- [ ] **6.2** Repita o bloco 4 pelo WhatsApp, incluindo **áudio** (vira texto) e **imagem sem legenda** (a assistente pede para escrever).
- [ ] **6.3** Lembrete: marque para amanhã e, no dia, responda **"1"** ao lembrete.
  ✔ A consulta fica confirmada sem IA, e o sino mostra a confirmação.
- [ ] **6.4** Responda **"PARAR"**.
  ✔ Ele não recebe mais aniversário, campanha, pós-consulta nem retorno. Confirmação e lembrete continuam.
- [ ] **6.5** Nada sai entre 21h e 08h (silêncio).
- [ ] **6.6** **Modo de teste:** número fora de `ENVIO_SOMENTE_PARA` não recebe nada, e a mensagem aparece em "Não enviadas" com o motivo.
- [ ] **6.7** Derrube a sessão (desconecte o celular).
  ✔ O sino mostra "WhatsApp desconectado". A aba Canais mostra o QR para reconectar.

---

## 7. Isolamento e segurança (rápido)

- [ ] **7.1** Com o usuário de recepção, tente abrir o endereço de outra clínica (troque o id na barra).
  ✔ "Sem acesso".
- [ ] **7.2** A recepção não muda configurações (os campos ficam travados), não dispara campanha e não baixa relatórios.
- [ ] **7.3** Saia, entre de novo e deixe o painel aberto por mais de 1 hora.
  ✔ A sessão renova sozinha.

---

## Anotações do teste

| Passo | O que aconteceu | Gravidade (bloqueia / incomoda / detalhe) |
|---|---|---|
| | | |
