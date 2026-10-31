"""Paradas (CA05): cadastro de paradas e associação às linhas por sentido. Somente admin."""
from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from src.models import db
from src.models.tracking import LinhaParada, Parada, PARADA_STATUSES, Route, SENTIDOS
from src.routes.viagens import _linha_dict
from src.services.paradas_service import reposicionar
from src.utils.auth import admin_required

paradas_bp = Blueprint('paradas', __name__, url_prefix='/api/admin')


def _texto(data, campo):
    return str(data.get(campo) or '').strip()


def _validar_parada(data, parada=None):
    """(campos, None) ou (None, resposta de erro). Na edição, campos ausentes mantêm o valor."""
    campos = {}
    for campo in ('nome', 'endereco'):
        if campo in data or parada is None:
            valor = _texto(data, campo)
            if not valor:
                return None, (jsonify({'error': f'O campo {campo} é obrigatório'}), 400)
            campos[campo] = valor
    for campo, limite in (('latitude', 90), ('longitude', 180)):
        if campo in data or parada is None:
            try:
                valor = float(data.get(campo))
            except (TypeError, ValueError):
                return None, (jsonify({'error': f'{campo} deve ser um número'}), 400)
            if not -limite <= valor <= limite:
                return None, (jsonify({'error': f'{campo} deve estar entre -{limite} e {limite}'}), 400)
            campos[campo] = valor
    return campos, None


def _linhas_ativas_com(parada: Parada) -> list:
    linhas = (Route.query.join(LinhaParada, LinhaParada.linha_id == Route.id)
              .filter(LinhaParada.parada_id == parada.id, Route.active.is_(True))
              .distinct().all())
    return [{'id': l.id, 'nome': _linha_dict(l)['nome']} for l in linhas]


# ── Paradas ──────────────────────────────────────────────────────────────────

@paradas_bp.route('/paradas', methods=['GET'])
@admin_required
def listar_paradas():
    query = Parada.query.order_by(Parada.nome)
    status = request.args.get('status')
    if status:
        if status not in PARADA_STATUSES:
            return jsonify({'error': f'Status inválido. Use: {", ".join(PARADA_STATUSES)}'}), 400
        query = query.filter_by(status=status)
    busca = (request.args.get('q') or '').strip()
    if busca:
        termo = f'%{busca}%'
        query = query.filter(or_(Parada.nome.ilike(termo), Parada.endereco.ilike(termo)))
    return jsonify([p.to_dict() for p in query.all()])


@paradas_bp.route('/paradas/<int:parada_id>', methods=['GET'])
@admin_required
def obter_parada(parada_id):
    parada = db.session.get(Parada, parada_id)
    if not parada:
        return jsonify({'error': 'Parada não encontrada'}), 404
    return jsonify(parada.to_dict())


@paradas_bp.route('/paradas', methods=['POST'])
@admin_required
def criar_parada():
    campos, erro = _validar_parada(request.get_json() or {})
    if erro:
        return erro
    parada = Parada(**campos)
    db.session.add(parada)
    db.session.commit()
    return jsonify(parada.to_dict()), 201


@paradas_bp.route('/paradas/<int:parada_id>', methods=['PUT'])
@admin_required
def editar_parada(parada_id):
    parada = db.session.get(Parada, parada_id)
    if not parada:
        return jsonify({'error': 'Parada não encontrada'}), 404
    campos, erro = _validar_parada(request.get_json() or {}, parada)
    if erro:
        return erro
    for campo, valor in campos.items():
        setattr(parada, campo, valor)
    db.session.commit()
    return jsonify(parada.to_dict())


@paradas_bp.route('/paradas/<int:parada_id>/desativar', methods=['PATCH'])
@admin_required
def desativar_parada(parada_id):
    parada = db.session.get(Parada, parada_id)
    if not parada:
        return jsonify({'error': 'Parada não encontrada'}), 404
    linhas = _linhas_ativas_com(parada)
    if linhas:  # CA05.5
        return jsonify({'error': 'Parada em uso por linha ativa. Remova-a das linhas antes de desativar.',
                        'linhas': linhas}), 409
    parada.status = 'inativa'
    db.session.commit()
    return jsonify(parada.to_dict())


@paradas_bp.route('/paradas/<int:parada_id>/reativar', methods=['PATCH'])
@admin_required
def reativar_parada(parada_id):
    parada = db.session.get(Parada, parada_id)
    if not parada:
        return jsonify({'error': 'Parada não encontrada'}), 404
    parada.status = 'ativa'
    db.session.commit()
    return jsonify(parada.to_dict())


# ── Paradas de uma linha ─────────────────────────────────────────────────────

@paradas_bp.route('/linhas/<int:linha_id>/paradas', methods=['GET'])
@admin_required
def paradas_da_linha(linha_id):
    linha = db.session.get(Route, linha_id)
    if not linha:
        return jsonify({'error': 'Linha não encontrada'}), 404
    sentido = request.args.get('sentido')
    if sentido and sentido not in SENTIDOS:
        return jsonify({'error': f'Sentido inválido. Use: {", ".join(SENTIDOS)}'}), 400
    sentidos = [sentido] if sentido else list(SENTIDOS)
    return jsonify([a.to_dict() for s in sentidos for a in linha.paradas_ordenadas(s)])


@paradas_bp.route('/linhas/<int:linha_id>/paradas', methods=['POST'])
@admin_required
def associar_parada(linha_id):
    linha = db.session.get(Route, linha_id)
    if not linha:
        return jsonify({'error': 'Linha não encontrada'}), 404
    data = request.get_json() or {}

    sentido = data.get('sentido')
    if sentido not in SENTIDOS:
        return jsonify({'error': f'Sentido inválido. Use: {", ".join(SENTIDOS)}'}), 400
    parada = db.session.get(Parada, data.get('parada_id')) if data.get('parada_id') else None
    if not parada:
        return jsonify({'error': 'Parada não encontrada'}), 404
    if parada.status != 'ativa':
        return jsonify({'error': 'Parada inativa não pode ser associada a uma linha'}), 422

    try:
        ordem = int(data['ordem']) if data.get('ordem') not in (None, '') else None
        tempo = data.get('tempo_estimado_minutos')
        tempo = float(tempo) if tempo not in (None, '') else None
    except (TypeError, ValueError):
        return jsonify({'error': 'ordem e tempo_estimado_minutos devem ser números'}), 400
    if ordem is not None and ordem < 1:
        return jsonify({'error': 'ordem deve ser maior que zero'}), 400
    if tempo is not None and tempo <= 0:
        return jsonify({'error': 'tempo_estimado_minutos deve ser positivo'}), 400

    existentes = LinhaParada.query.filter_by(linha_id=linha.id, sentido=sentido)
    if existentes.filter_by(parada_id=parada.id).first():
        return jsonify({'error': 'Esta parada já está associada à linha neste sentido'}), 409
    if ordem is None:
        ordem = existentes.count() + 1
    elif existentes.filter_by(ordem=ordem).first():  # CA05.3
        return jsonify({'error': f'A ordem {ordem} já está em uso nesta linha/sentido'}), 409

    assoc = LinhaParada(linha_id=linha.id, parada_id=parada.id, sentido=sentido, ordem=ordem,
                        tempo_estimado_minutos=tempo)
    db.session.add(assoc)
    db.session.commit()
    return jsonify(assoc.to_dict()), 201


@paradas_bp.route('/linhas/<int:linha_id>/paradas/<int:assoc_id>', methods=['DELETE'])
@admin_required
def desassociar_parada(linha_id, assoc_id):
    assoc = db.session.get(LinhaParada, assoc_id)
    if not assoc or assoc.linha_id != linha_id:
        return jsonify({'error': 'Associação não encontrada'}), 404
    sentido = assoc.sentido
    db.session.delete(assoc)
    db.session.flush()
    reposicionar(linha_id, sentido)  # as seguintes sobem uma posição
    db.session.commit()
    return jsonify({'message': 'Parada removida da linha'})
