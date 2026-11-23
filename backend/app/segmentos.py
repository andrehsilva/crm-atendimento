"""Segmentos de negócio (Etapa 9, D38–D41).

Cada clínica tem um segmento (odontologia, medicina, ...). O segmento traz as palavras do negócio, os
procedimentos que já vêm prontos, a área de atuação da assistente e os sinais de urgência.
A clínica pode trocar as palavras em Configurações › Perfil (`settings.termos`), por cima do padrão do segmento.

Clínicas criadas antes da Etapa 9 não têm segmento gravado: valem como odontologia.
"""

from dataclasses import dataclass, field

PADRAO = "odontologia"


@dataclass(frozen=True)
class Segmento:
    codigo: str
    nome: str
    tipo_negocio: str  # "uma clínica odontológica" (como a assistente apresenta o lugar)
    termos: dict  # profissional/profissionais/cliente/clientes/atendimento/atendimentos/genero ('f' ou 'm')
    area: str  # do que a assistente pode falar em termos gerais
    nao_e: str  # o que a assistente NÃO é (não diagnostica etc.)
    urgencias: str  # sinais que pedem atendimento imediato ("" = só a regra geral)
    emoji: str  # ícone da linha do procedimento nas mensagens automáticas
    procedimentos: list = field(default_factory=list)  # (nome, descrição, minutos, IA pode marcar?)
    lembrete_discreto: bool = False  # D41: lembrete sem citar o procedimento
    extra_urgencia: str = ""  # orientação adicional (ex.: CVV na psicologia)
    avisos_tratamento: bool = True  # D107: tratamento novo já vem com confirmação/lembrete ligados?


_CONSULTA = {"atendimento": "consulta", "atendimentos": "consultas", "genero": "f"}
_SESSAO = {"atendimento": "sessão", "atendimentos": "sessões", "genero": "f"}
_PACIENTE = {"cliente": "paciente", "clientes": "pacientes"}

SEGMENTOS: dict[str, Segmento] = {
    s.codigo: s
    for s in [
        Segmento(
            "odontologia", "Odontologia", "uma clínica odontológica",
            {"profissional": "dentista", "profissionais": "dentistas", **_PACIENTE, **_CONSULTA},
            area="saúde bucal",
            nao_e="Você não é dentista: não diagnostica, não indica remédio, dosagem nem tratamento caseiro.",
            urgencias=("rosto ou pescoço inchado, febre com dor de dente, sangramento que não para, dente quebrado ou "
                       "arrancado por pancada, ou dificuldade para engolir ou respirar"),
            emoji="🦷",
            procedimentos=[
                ("Avaliação odontológica geral", "Exame clínico completo, diagnóstico e plano de tratamento.", 60, True),
                ("Limpeza (profilaxia)", "Remoção de tártaro e placa bacteriana, com polimento.", 60, True),
                ("Restauração", "Tratamento de cárie com resina na cor do dente.", 60, True),
                ("Clareamento a laser", "Clareamento dental feito no consultório.", 60, True),
                ("Retorno", "Consulta de acompanhamento após um tratamento.", 30, True),
                ("Atendimento de urgência", "Dor, trauma ou infecção. Encaixe feito pela recepção.", 60, False),
            ],
        ),
        Segmento(
            "medicina", "Medicina", "uma clínica médica",
            {"profissional": "médico(a)", "profissionais": "médicos", **_PACIENTE, **_CONSULTA},
            area="saúde em termos gerais",
            nao_e="Você não é médica: não diagnostica, não interpreta exames, não indica remédio nem dosagem.",
            urgencias=("dor no peito, falta de ar, desmaio, fraqueza ou formigamento de um lado do corpo, fala enrolada, "
                       "sangramento intenso, convulsão ou febre alta que não cede"),
            emoji="🩺",
            procedimentos=[
                ("Primeira consulta", "Primeira vez com o médico: histórico, exame e orientações.", 60, True),
                ("Consulta", "Consulta de rotina.", 30, True),
                ("Retorno", "Acompanhamento após uma consulta.", 30, True),
                ("Avaliação de exames", "Apresentar e discutir resultados de exames.", 30, True),
                ("Atendimento de urgência", "Encaixe feito pela recepção.", 30, False),
            ],
        ),
        Segmento(
            "fisioterapia", "Fisioterapia", "uma clínica de fisioterapia",
            {"profissional": "fisioterapeuta", "profissionais": "fisioterapeutas", **_PACIENTE, **_SESSAO},
            area="fisioterapia e reabilitação em termos gerais",
            nao_e="Você não é fisioterapeuta: não diagnostica, não passa exercícios nem indica remédio.",
            urgencias=("queda com dor forte, perda súbita de força ou de sensibilidade, inchaço intenso, "
                       "dor no peito ou falta de ar"),
            emoji="🩺",
            procedimentos=[
                ("Avaliação fisioterapêutica", "Primeira avaliação e plano de tratamento.", 60, True),
                ("Sessão de fisioterapia", "Sessão do plano de tratamento.", 60, True),
                ("RPG", "Reeducação postural global.", 60, True),
                ("Reavaliação", "Revisão do plano de tratamento.", 30, True),
            ],
        ),
        Segmento(
            "psicologia", "Psicologia", "um consultório de psicologia",
            {"profissional": "psicólogo(a)", "profissionais": "psicólogos", **_PACIENTE, **_SESSAO},
            area="saúde mental apenas de forma geral e acolhedora",
            nao_e=("Você não é psicóloga: não faz terapia pelo chat, não diagnostica e não indica remédio. "
                   "Trate tudo com sigilo e acolhimento; não peça detalhes do motivo do atendimento."),
            urgencias=("pensamentos de se machucar ou de tirar a própria vida, risco para outra pessoa, "
                       "ou crise intensa de pânico ou agitação"),
            extra_urgencia="lembre também do **CVV (188)**, que atende 24 horas por telefone",
            emoji="🗓️",
            lembrete_discreto=True,
            procedimentos=[
                ("Primeira sessão", "Acolhimento e entendimento da demanda.", 60, True),
                ("Sessão de psicoterapia", "Sessão de acompanhamento.", 60, True),
                ("Retorno", "Acompanhamento após uma sessão.", 30, True),
            ],
        ),
        Segmento(
            "psicanalise", "Psicanálise", "um consultório de psicanálise",
            {"profissional": "psicanalista", "profissionais": "psicanalistas", **_PACIENTE, **_SESSAO},
            area="saúde mental apenas de forma geral e acolhedora",
            nao_e=("Você não é psicanalista: não faz análise pelo chat, não diagnostica e não indica remédio. "
                   "Trate tudo com sigilo e acolhimento; não peça detalhes do motivo do atendimento."),
            urgencias=("pensamentos de se machucar ou de tirar a própria vida, risco para outra pessoa, "
                       "ou crise intensa de pânico ou agitação"),
            extra_urgencia="lembre também do **CVV (188)**, que atende 24 horas por telefone",
            emoji="🗓️",
            lembrete_discreto=True,
            avisos_tratamento=False,  # D107: na análise, a agenda é responsabilidade do paciente
            procedimentos=[
                ("Primeira sessão", "Acolhimento e entendimento da demanda.", 60, True),
                ("Sessão de psicanálise", "Sessão de acompanhamento.", 60, True),
                ("Retorno", "Acompanhamento após uma sessão.", 30, True),
            ],
        ),
        Segmento(
            "psiquiatria", "Psiquiatria", "um consultório de psiquiatria",
            {"profissional": "psiquiatra", "profissionais": "psiquiatras", **_PACIENTE, **_CONSULTA},
            area="saúde mental apenas de forma geral e acolhedora",
            nao_e=("Você não é psiquiatra: não avalia sintomas, não diagnostica e não indica ou ajusta remédio. "
                   "Trate tudo com sigilo e acolhimento; não peça detalhes do motivo do atendimento."),
            urgencias=("pensamentos de se machucar ou de tirar a própria vida, risco para outra pessoa, "
                       "ou crise intensa de pânico ou agitação"),
            extra_urgencia="lembre também do **CVV (188)**, que atende 24 horas por telefone",
            emoji="🗓️",
            lembrete_discreto=True,
            procedimentos=[
                ("Primeira consulta psiquiátrica", "Avaliação inicial com o psiquiatra.", 60, True),
                ("Consulta psiquiátrica", "Consulta de acompanhamento.", 30, True),
                ("Retorno psiquiátrico", "Acompanhamento após uma consulta.", 30, True),
            ],
        ),
        Segmento(
            "estetica", "Estética", "uma clínica de estética",
            {"profissional": "profissional", "profissionais": "profissionais",
             "cliente": "cliente", "clientes": "clientes", "atendimento": "atendimento", "atendimentos": "atendimentos",
             "genero": "m"},
            area="estética e bem-estar em termos gerais",
            nao_e="Você não é profissional de saúde: não indica remédio nem tratamento caseiro.",
            urgencias=("reação alérgica, inchaço no rosto, falta de ar, queimadura ou dor intensa depois de um procedimento"),
            emoji="✨",
            procedimentos=[
                ("Avaliação", "Conversa inicial e indicação do tratamento.", 30, True),
                ("Limpeza de pele", "Limpeza profunda com extração.", 60, True),
                ("Drenagem linfática", "Massagem para reduzir inchaço.", 60, True),
                ("Massagem relaxante", "Massagem corporal.", 60, True),
            ],
        ),
        Segmento(
            "outro", "Outro", "um negócio que trabalha com horário marcado",
            {"profissional": "profissional", "profissionais": "profissionais",
             "cliente": "cliente", "clientes": "clientes", "atendimento": "atendimento", "atendimentos": "atendimentos",
             "genero": "m"},
            area="os serviços oferecidos",
            nao_e="Você não dá orientação de saúde, jurídica ou financeira: só informa e cuida da agenda.",
            urgencias="",
            emoji="🗓️",
            procedimentos=[
                ("Atendimento", "Atendimento padrão.", 60, True),
                ("Avaliação", "Primeira conversa.", 30, True),
            ],
        ),
    ]
}

CHAVES_TERMOS = ("profissional", "profissionais", "cliente", "clientes", "atendimento", "atendimentos", "genero")


def segmento_de(settings: dict | None) -> Segmento:
    codigo = (settings or {}).get("segmento") or PADRAO
    return SEGMENTOS.get(codigo, SEGMENTOS[PADRAO])


def termos(settings: dict | None) -> dict:
    """Palavras da clínica: padrão do segmento + o que a clínica ajustou. Inclui as concordâncias prontas."""
    seg = segmento_de(settings)
    proprios = (settings or {}).get("termos") or {}
    t = {k: (str(proprios.get(k)).strip() if proprios.get(k) else seg.termos[k]) for k in CHAVES_TERMOS}
    if t["genero"] not in ("f", "m"):
        t["genero"] = seg.termos["genero"]
    f = t["genero"] == "f"
    t.update({
        "o": "a" if f else "o",  # confirmad{o}
        "sua": "sua" if f else "seu",
        "da_sua": "da sua" if f else "do seu",
        "uma": "uma" if f else "um",
        "nova": "nova" if f else "novo",
    })
    return t


def lembrete_discreto(settings: dict | None) -> bool:
    s = settings or {}
    return bool(s["lembrete_discreto"]) if s.get("lembrete_discreto") is not None else segmento_de(s).lembrete_discreto


def avisos_tratamento(settings: dict | None) -> bool:
    """D107: padrão do 'a assistente manda confirmação e lembrete' ao abrir um tratamento."""
    return segmento_de(settings).avisos_tratamento


def cap(texto: str) -> str:
    return texto[:1].upper() + texto[1:]


def publico() -> list[dict]:
    """Lista para as telas (admin geral e Perfil)."""
    return [
        {"codigo": s.codigo, "nome": s.nome, "termos": s.termos, "lembrete_discreto": s.lembrete_discreto,
         "procedimentos": [p[0] for p in s.procedimentos]}
        for s in SEGMENTOS.values()
    ]
