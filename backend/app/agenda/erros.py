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
    "TRATAMENTO_AGUARDANDO": 409,  # Etapa 21 (RN-TR-04)
    "FALTAS_REPETIDAS": 409,  # RN-AG-16 (D91)
    "CONVENIO_PENDENTE": 409,  # RN-CV-02 (Etapa 22)
    "STATUS_INVALIDO": 409,
    "SERIE_VAZIA": 409,  # Etapa 26: nenhuma data da série coube
    "TEM_CONSULTAS_FUTURAS": 409,  # Etapa 28 (D111): excluir/desativar profissional com consultas marcadas
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
    "LOGO_INVALIDA": 422,
    "LOGO_GRANDE": 413,
    "IA_DESLIGADA": 409,
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
