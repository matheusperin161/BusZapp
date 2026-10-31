"""Ordem das paradas de uma linha/sentido."""
from src.models.tracking import LinhaParada


def reposicionar(linha_id: int, sentido: str, assoc: LinhaParada | None = None, nova_ordem: int | None = None):
    """Renumera 1..n as paradas da linha/sentido; se `assoc` vier, ela é colocada em `nova_ordem`
    (as seguintes andam uma posição). Sem `assoc`, só fecha buracos (após remover uma parada)."""
    demais = [a for a in (LinhaParada.query
                          .filter_by(linha_id=linha_id, sentido=sentido)
                          .order_by(LinhaParada.ordem, LinhaParada.id))
              if a is not assoc]
    if assoc is not None:
        posicao = max(0, min(len(demais), (nova_ordem or len(demais) + 1) - 1))
        demais.insert(posicao, assoc)
    for i, item in enumerate(demais, start=1):
        item.ordem = i
