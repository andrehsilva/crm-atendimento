"""Erros de regra da agenda. Cada um tem um código estável (a Ísis e o painel usam o código)."""

# código -> status HTTP
STATUS_HTTP = {
    "CLINICA_NAO_ENCONTRADA": 404,
    "CONSULTA_NAO_ENCONTRADA": 404,
    "PROCEDIMENTO_NAO_ENCONTRADO": 404,
    "PROFISSIONAL_NAO_ENCONTRADO": 404,
    "CLINICA_SUSPENSA": 403,
    "NAO_E_SUA": 403,
    "SO_HUMANO": 403,
    "HORARIO_OCUPADO": 409,
    "LIMITE_CONSULTAS": 409,
    "STATUS_INVALIDO": 409,
    "FORA_DO_HORARIO": 422,
    "ANTECEDENCIA": 422,
    "HORIZONTE": 422,
    "PROFISSIONAL_NAO_FAZ": 422,
    "PROCEDIMENTO_INATIVO": 422,
    "NOME_OBRIGATORIO": 422,
    "TELEFONE_INVALIDO": 422,
    "DADOS_INVALIDOS": 422,
    "ENVIO_FALHOU": 502,
    "NAO_AUTENTICADO": 401,
    "SEM_ACESSO": 403,
    "TROCAR_SENHA": 403,
    "SENHA_FRACA": 422,
}


class AgendaError(Exception):
    def __init__(self, codigo: str, mensagem: str):
        assert codigo in STATUS_HTTP, codigo
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem

    @property
    def status_http(self) -> int:
        return STATUS_HTTP[self.codigo]
