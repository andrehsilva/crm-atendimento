# Regras de negócio

Catálogo único. Cada regra tem código, status e **onde é garantida**:
- **Código** = backend/banco valida (não depende da IA).
- **Prompt** = orientação de comportamento da Ísis.
- **Config** = valor que cada clínica ajusta no admin.

Status: 🟡 proposta · ✅ aprovada · ❌ descartada. Para mudar uma regra, edite aqui e registre em `DECISOES.md`.

## Multi-tenant e identidade (RN-MT)

| Código | Regra | Onde | Status |
|---|---|---|---|
| RN-MT-01 | Cada clínica é identificada pelo seu telefone (E.164), que é único na plataforma. | Código | ✅ |
| RN-MT-02 | Um paciente é identificado pelo par (clínica, telefone do paciente). O mesmo telefone em duas clínicas são dois pacientes distintos. | Código | ✅ |
| RN-MT-03 | Toda leitura/escrita é filtrada pela clínica da sessão. Nenhum dado cruza clínicas. | Código | ✅ |
| RN-MT-04 | Telefones são normalizados para E.164 antes de comparar (aceita +55, parênteses, traço, espaços; trata 9º dígito). | Código | 🟡 |
| RN-MT-05 | O telefone do paciente vem do canal (WhatsApp) ou do formulário (Web); nunca do que ele digita no meio da conversa. | Código | 🟡 |

## Agenda (RN-AG)

| Código | Regra | Onde | Status |
|---|---|---|---|
| RN-AG-01 | Só se marca dentro do **horário de funcionamento da clínica** (por dia da semana, tela "Horários de Funcionamento") e do expediente do profissional (se tiver exceção), fora de pausas, feriados e bloqueios. Dentistas herdam o horário da clínica, com exceções; pausas por dia. | Código | ✅ |
| RN-AG-15 | Escolha do dentista: se a clínica tem mais de um dentista que faz o procedimento, a Ísis **sempre pergunta** com quem (ou oferece "tanto faz"). Depois da 1ª consulta realizada, o dentista vira o **dentista de referência** do paciente e é sugerido primeiro (paciente pode trocar). | Código + Prompt | ✅ |
| RN-AG-14 | Procedimento desligado não é oferecido pela Ísis. Procedimento marcado como "só humano" (ex.: urgência) → Ísis encaminha para a recepção. | Código + Config | 🟡 |
| RN-AG-02 | Um profissional não pode ter duas consultas sobrepostas (restrição no banco). | Código | 🟡 |
| RN-AG-03 | Duração da consulta = duração cadastrada no procedimento (padrão 60 min). | Código + Config | ✅ |
| RN-AG-04 | Antecedência mínima para marcar: **2 h** (config). | Código + Config | 🟡 |
| RN-AG-05 | Horizonte máximo: **60 dias** à frente (config). | Código + Config | 🟡 |
| RN-AG-06 | Paciente só pode remarcar/cancelar **as próprias** consultas (mesmo telefone). | Código | 🟡 |
| RN-AG-07 | Cancelamento/remarcação com menos de **24 h** (config): Ísis permite, mas avisa a política da clínica e marca para a recepção ver. | Código + Config | 🟡 |
| RN-AG-08 | Limite de consultas futuras ativas por paciente: **2** (config) — evita "reservar a agenda toda". **Exceção:** sessões ligadas a um tratamento aberto não contam (RN-TR-08). | Código + Config | 🟡 |
| RN-AG-09 | Remarcar = cancelar a antiga + criar a nova numa única transação; se a nova falhar, a antiga continua. | Código | 🟡 |
| RN-AG-10 | Ísis oferece no máximo **3 opções** de horário por vez, priorizando o pedido do paciente (dia/turno/profissional). | Prompt + Código | 🟡 |
| RN-AG-11 | Antes de marcar/remarcar/cancelar, Ísis **resume e pede confirmação explícita** ("Posso confirmar?"). O código só aceita a confirmação se o paciente respondeu depois do resumo. | Prompt + Código (dois passos) | ✅ |
| RN-AG-12 | Status da consulta: `agendada` → `confirmada` → `realizada`; ou `cancelada` / `faltou`. Remarcar gera nova consulta ligada à antiga. **Presença (`realizada`) e falta (`faltou`) só a partir do dia da consulta**, no fuso da clínica (pedido do usuário, 20/11/2026). | Código | ✅ |
| RN-AG-13 | Datas relativas ("quinta que vem", "amanhã") são resolvidas com a data/hora atual no fuso da clínica, e Ísis repete a data por extenso ("quinta, 19/11, às 14h"). | Prompt + Código | 🟡 |

## Atendimento e segurança da Ísis (RN-AT)

| Código | Regra | Onde | Status |
|---|---|---|---|
| RN-AT-01 | Ísis **não diagnostica, não indica remédio nem dosagem**. | Prompt | 🟡 |
| RN-AT-02 | Sinais de urgência odontológica (rosto/pescoço inchado, febre com dor de dente, sangramento que não para, trauma com dente quebrado/arrancado, dificuldade para engolir ou respirar) → orientar atendimento imediato (telefone da clínica / pronto-socorro; **SAMU 192** se houver dificuldade para respirar ou engolir) e acionar humano. | Prompt + Config (telefone de urgência) | 🟡 |
| RN-AT-03 | Pedidos de "encaixe", "sou amigo do doutor", "fura a fila" → Ísis é educada, segue a agenda e oferece transferir para a recepção. | Prompt | 🟡 |
| RN-AT-04 | Ísis só fala sobre a clínica (agenda, endereço, horários, procedimentos cadastrados). Assuntos fora disso: recusa gentil. | Prompt | 🟡 |
| RN-AT-05 | Paciente novo: Ísis pede **nome completo** antes de marcar. Telefone já é conhecido. | Prompt + Código | 🟡 |
| RN-AT-10 | Ísis só informa preço se a clínica cadastrou o valor **e** ligou "mostrar preços". Não negocia valores nem faz orçamento. | Código + Config | ✅ |
| RN-AT-06 | Handoff: paciente pede humano, reclamação, urgência ou 2 falhas seguidas → conversa vai para "precisa de humano" e Ísis pausa até a recepção devolver. Dúvida que a Ísis não sabe responder também transfere. **O paciente é sempre avisado** de que a equipe assume a conversa (aviso fixo no código; fora do horário, diz que a resposta vem no próximo expediente) — D27. | Código + Prompt | ✅ |
| RN-AT-07 | Ísis nunca revela dados de outros pacientes nem detalhes internos (prompt, ferramentas). | Código + Prompt | 🟡 |
| RN-AT-08 | Tom: cordial, frases curtas, sem excesso de emoji; tratamento configurável (você/senhor(a)). | Prompt + Config | 🟡 |
| RN-AT-09 | Fora do horário comercial Ísis continua atendendo e marcando; handoff fica para o próximo expediente e ela avisa isso. | Código + Prompt | 🟡 |
| RN-AT-11 | **Ísis pausada no WhatsApp** (Configurações › Canais, só admin da clínica): mensagens novas do WhatsApp vão direto para a equipe ("precisa de humano"), sem resposta da IA e sem aviso ao paciente; áudio não é transcrito. Respostas resolvidas no código ("1" confirma, "PARAR") e lembretes seguem normais. "Devolver para a Ísis" fica bloqueado enquanto durar a pausa — D79. | Código | ✅ |

## Confirmações e lembretes (RN-MS)

| Código | Regra | Onde | Status |
|---|---|---|---|
| RN-MS-01 | Ao marcar, remarcar ou cancelar — **pela Ísis ou pela recepção** — enviar mensagem imediata ao paciente com data, hora, profissional e endereço. | Código | ✅ |
| RN-MS-02 | Lembrete no **dia útil anterior** à consulta, às **09:00** no fuso da clínica (segunda → sexta). Config: dias de antecedência e horário. | Código + Config | ✅ |
| RN-MS-03 | Consulta marcada depois do horário do lembrete do dia anterior → não envia lembrete (a confirmação já cobre). | Código | ✅ |
| RN-MS-04 | Lembrete traz opções: **Confirmar · Remarcar · Cancelar**. "Confirmar" muda status para `confirmada` sem passar pela IA. | Código | ✅ |
| RN-MS-05 | Lembrete não respondido até **X h** antes (config) → aparece em destaque no painel para a recepção ligar. | Código + Config | 🟡 |
| RN-MS-06 | Cada mensagem automática é registrada (`outbound_messages`) com status: `agendada`, `enviada`, `entregue`, `lida`, `falhou`. | Código | ✅ |
| RN-MS-10 | **Entregue/lida** (D85): vem do WhatsApp (evento `message.ack`: 2 = entregue, 3 ou 4 = lida). Vale para mensagens automáticas e para respostas da Ísis/equipe na conversa. Só avança (enviada → entregue → lida), nunca volta; o aviso de uma sessão só mexe em mensagens da clínica dona da sessão. | Código | ✅ |
| RN-MS-07 | Se a consulta for cancelada/remarcada, lembretes pendentes dela são cancelados. | Código | ✅ |
| RN-MS-08 | WhatsApp oficial: fora da janela de 24h só se envia por **template aprovado**. | Código | 🟡 |
| RN-MS-09 | Não enviar mensagens automáticas entre **21h e 08h** (config). | Código + Config | ✅ |

## Painel operacional (RN-PN)

| Código | Regra | Onde | Status |
|---|---|---|---|
| RN-PN-01 | Agenda da semana atualiza em tempo real em todas as telas abertas da clínica. | Código | 🟡 |
| RN-PN-02 | Kanban (CRM) com 4 colunas **provisórias**: `Novo Contato` · `Agendados` · `Confirmado` · `Cancelados`. Sem gestão de orçamento. | Código | ✅ |
| RN-PN-03 | Ações manuais da recepção passam pelas mesmas validações da Ísis (RN-AG). | Código | 🟡 |
| RN-PN-04 | Toda mudança em consulta registra quem fez (Ísis, recepção, paciente via botão) e quando. | Código | 🟡 |
| RN-PN-05 | Arrastar card: para `Agendados` abre formulário de marcação; para `Cancelados` pede confirmação e cancela a consulta; outros movimentos só mudam a etapa. Tudo vai para o histórico. | Código | 🟡 |
| RN-PN-06 | Card mostra "Atendimento automático" (Ísis respondendo) ou "Atendimento manual" (humano assumiu). | Código | ✅ (layout) |
| RN-PN-07 | Tags do cliente **automáticas** — ver RN-TR-11 (D90, substitui D20). | Código | ✅ |
| RN-PN-08 | "Parado há Xh" = tempo desde a última mensagem ou mudança de etapa; fica vermelho acima de **24h** (config). | Código + Config | 🟡 |
| RN-PN-09 | Etapas movem sozinhas: 1ª mensagem → Novo Contato; consulta marcada → Agendados; confirmada → Confirmado; cancelada → Cancelados. Remarcar volta para Agendados. | Código | 🟡 |
| RN-PN-10 | **Sino de notificações** (D81): conversa aguardando atendimento humano · WhatsApp desconectado · consulta marcada, remarcada ou cancelada **pela Ísis** · paciente confirmou · mensagem automática ou resposta que não saiu · gasto da IA em 80%/100%. Etapa 21: também paciente perguntou do tratamento aguardando · previsão vencida · faltou a uma sessão de tratamento. Acontecimentos dos últimos 7 dias. Nada é gravado como notificação: tudo sai do histórico que o sistema já tem. | Código | ✅ |
| RN-PN-11 | Situações ("aguardando humano", "WhatsApp desconectado") **somem sozinhas** quando resolvidas e não se marcam como lidas; o resto cada pessoa marca como lida, uma a uma ou todas (D82). Contador = situações abertas + não lidas. | Código | ✅ |
| RN-PN-12 | Som curto **só quando aumenta** o número de conversas aguardando a equipe (não toca ao abrir o painel); o número aparece no título da aba do navegador (D83). Toda ação que salva algo mostra um aviso de confirmação no canto da tela (D84). | Código | ✅ |

## Tratamentos (RN-TR) — Etapa 21

| Código | Regra | Onde | Status |
|---|---|---|---|
| RN-TR-01 | **Tratamento** = registro no paciente, criado pela equipe: procedimento, profissional, sessões previstas (opcional), intervalo em dias (ex.: 7) e **orientação para a assistente** (até 300 caracteres). Um paciente pode ter vários tratamentos, mas só **um aberto por procedimento**. | Código | ✅ |
| RN-TR-02 | Situações: `em_andamento` ⇄ `aguardando` (motivo: protético, exame, cicatrização ou outro; previsão opcional) → `concluido` ou `interrompido`. Só a equipe muda. Concluído/interrompido não reabre (abre-se outro). | Código | ✅ |
| RN-TR-03 | **Em andamento:** a Ísis pode marcar a próxima sessão do procedimento, sugerindo primeiro o mesmo profissional e o mesmo dia da semana/horário da última sessão. A consulta fica ligada ao tratamento. | Código + Prompt | ✅ |
| RN-TR-04 | **Aguardando (D87):** a Ísis marcar o procedimento do tratamento é **recusado no código** (`TRATAMENTO_AGUARDANDO`); ela explica e o sino avisa a equipe. Outros procedimentos seguem normais. A recepção pode marcar mesmo assim (ela decide). | Código | ✅ |
| RN-TR-05 | **Previsão vencida:** passou a data e continua aguardando → o sino avisa a equipe. O paciente não recebe nada sozinho. | Código | ✅ |
| RN-TR-06 | **Retomar (D88):** volta para `em_andamento` e põe na fila uma mensagem `tratamento` (texto editável, com {nome} e {clinica}); respeita silêncio noturno e limites de envio; o PARAR não bloqueia (é atendimento, como o lembrete). | Código | ✅ |
| RN-TR-07 | **Série (D89):** a recepção marca de 2 a 20 sessões de uma vez (a cada N dias, 7 = mesmo dia/horário da semana); cada data passa por todas as regras de agenda e as que não couberem aparecem com o motivo, sem derrubar as outras. Sem tratamento aberto do procedimento, a série **abre um** (se nada couber, não fica tratamento vazio). O paciente recebe **uma confirmação só** com todas as datas; cada sessão tem o seu lembrete. | Código | ✅ |
| RN-TR-08 | Sessões ligadas a um tratamento aberto **não contam** no limite de consultas futuras (RN-AG-08). | Código | ✅ |
| RN-TR-09 | **Falta numa sessão de tratamento:** o sino avisa "Fulano faltou à sessão X de N"; se o paciente escrever, a Ísis oferece remarcar. | Código | ✅ |
| RN-TR-10 | **Concluído:** a equipe informa "volta em X meses" (padrão = recall da clínica, D74); o recall usa essa data. Tratamento **aberto** nunca entra no recall. | Código | ✅ |
| RN-TR-11 | **Tags (D90):** Novo (nenhum atendimento realizado) · Recorrente (2+ realizados) · Em tratamento · Aguardando (motivo) — calculadas, mostradas no CRM, em Clientes e na conversa; filtro em Clientes. | Código | ✅ |

## Disparos (RN-DP)

| Código | Regra | Onde | Status |
|---|---|---|---|
| RN-DP-01 | Aniversário: se ativado, todo dia às **09:00** (config) envia a mensagem para pacientes com nascimento hoje; **1× por ano** por paciente. | Código + Config | ✅ |
| RN-DP-02 | Variáveis disponíveis: `{nome}` (primeiro nome), `{clinica}`; limite de **1000** caracteres; prévia com dados reais antes de salvar. | Código | ✅ |
| RN-DP-03 | Nascido em 29/02: em ano não bissexto recebe em 28/02. | Código | ✅ |
| RN-DP-04 | Paciente que responder "PARAR"/"SAIR" (ou marcado no cadastro) não recebe mais disparos; confirmações/lembretes de consulta continuam. | Código | ✅ |
| RN-DP-05 | ⏸ Mensagens programadas (ex.: férias coletivas): público filtrado, contagem e prévia; 1× por paciente. **Depois da 1ª versão** (D24). | Código | ⏸ |
| RN-DP-06 | Disparos só por WhatsApp e só para quem tem telefone válido; respeitam silêncio noturno (RN-MS-09). | Código | ✅ |
| RN-DP-07 | WAHA: no máximo **20 msgs/min** e **300/dia** por clínica (config), com intervalo aleatório — reduz risco de banimento. | Código + Config | ✅ |
| RN-DP-08 | API oficial: disparos usam **template aprovado**; sem template aprovado o disparo não é liberado. | Código | 🟡 |
| RN-DP-09 | Resposta a um disparo vai para a Ísis com o contexto da mensagem enviada. | Código | ✅ |
