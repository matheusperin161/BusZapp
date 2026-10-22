"""Validação de CPF por dígito verificador."""
import re


def somente_digitos(valor: str | None) -> str:
    return re.sub(r'\D', '', valor or '')


def cpf_valido(cpf: str | None) -> bool:
    digitos = somente_digitos(cpf)
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d) * peso for d, peso in zip(digitos[:tamanho], range(tamanho + 1, 1, -1)))
        dv = (soma * 10) % 11 % 10
        if dv != int(digitos[tamanho]):
            return False
    return True
