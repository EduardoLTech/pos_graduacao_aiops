"""Erros que encerram a execução com código próprio (PRD P5).

As mensagens são escritas aqui, nunca copiadas de exceção de terceiros: texto de exceção pode
carregar o caminho da chave (PRD I2).
"""


class ErroDeUso(Exception):
    """Código 2: parâmetro, chave ou baseline inválido. Nada foi conectado."""

    codigo = 2


class HostInalcancavel(Exception):
    """Código 3: sem conexão, conexão perdida ou chave de host divergente. Sem relatório."""

    codigo = 3
