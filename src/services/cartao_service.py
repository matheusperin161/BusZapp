"""Saldo do cartão: crédito e débito atômicos (UPDATE condicional, sem corrida entre requisições)."""
from src.models import db
from src.models.user import Cartao, Transaction


def cartao_do_usuario(user, criar: bool = False) -> Cartao | None:
    """Cartão do usuário; com criar=True cria um sem número (recarga pelo web antes do cadastro)."""
    if user.cartao is None and criar:
        db.session.add(Cartao(usuario_id=user.id))
        db.session.flush()
        db.session.refresh(user)
    return user.cartao


def _movimentar(cartao: Cartao, centavos: int, tipo: str, descricao: str, filtro) -> Transaction | None:
    linhas = (Cartao.query
              .filter(Cartao.id == cartao.id, *filtro)
              .update({Cartao.saldo_centavos: Cartao.saldo_centavos + centavos}, synchronize_session=False))
    if not linhas:
        db.session.rollback()
        return None
    transacao = Transaction(user_id=cartao.usuario_id, cartao_id=cartao.id, amount=centavos / 100,
                            transaction_type=tipo, description=descricao)
    db.session.add(transacao)
    db.session.commit()
    db.session.refresh(cartao)
    return transacao


def creditar(cartao: Cartao, centavos: int, descricao: str, tipo: str = 'recharge') -> Transaction | None:
    """Soma ao saldo; None se o cartão estiver bloqueado."""
    return _movimentar(cartao, centavos, tipo, descricao, [Cartao.status == 'ativo'])


def debitar(cartao: Cartao, centavos: int, descricao: str, tipo: str = 'usage') -> Transaction | None:
    """Desconta do saldo; None se bloqueado ou com saldo insuficiente."""
    return _movimentar(cartao, -centavos, tipo, descricao,
                       [Cartao.status == 'ativo', Cartao.saldo_centavos >= centavos])
