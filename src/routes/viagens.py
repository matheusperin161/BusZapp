"""Viagens e posições: motorista inicia/finaliza viagem e envia GPS; passageiro e admin acompanham."""
from datetime import datetime, timedelta, timezone

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import IntegrityError

from src.models import db
from src.models.user import BusRoute, Vehicle
from src.models.tracking import Posicao, Route, SENTIDOS, Viagem
from src.utils.auth import get_current_user, motorista_required
from src.utils.geo import proxima_parada

viagens_bp = Blueprint('viagens', __name__, url_prefix='/api')

MAX_POSICOES_POR_LOTE = 500
TOLERANCIA_RELOGIO = timedelta(minutes=5)  # posições "do futuro" acima disso são descartadas

_socketio = None


def set_socketio(socket_instance):
    global _socketio
    _socketio = socket_instance


# ── Helpers ──────────────────────────────────────────────────────────────────

def _linha_dict(route: Route) -> dict:
    """Linha com número/nome amigável (vindos de BusRoute, ligada pelo nome 'Linha_<n>')."""
    numero = route.route_name.replace('Linha_', '', 1)
    bus_route = BusRoute.query.filter_by(route_number=numero).first()
    return {
        'id': route.id,
        'numero': numero,
        'nome': bus_route.route_name if bus_route else route.route_name,
        'active': route.active,
    }


def _parse_datetime(valor) -> datetime | None:
    """ISO-8601 → datetime UTC naive (padrão do banco)."""
    if not valor:
        return None
    try:
        dt = datetime.fromisoformat(str(valor).replace('Z', '+00:00'))
    except ValueError:
        return None
    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _viagem_com_posicao(viagem: Viagem) -> dict:
    """Viagem + última posição + próxima parada/estimativa (CA08.6)."""
    data = viagem.to_dict()
    data['linha'] = _linha_dict(viagem.linha)
    ultima = viagem.ultima_posicao()
    data['ultima_posicao'] = ultima.to_dict() if ultima else None
    data['proxima_parada'] = None
    if ultima:
        prox = proxima_parada(ultima.latitude, ultima.longitude, list(viagem.linha.stop_points), viagem.sentido)
        if prox:
            chegada = ultima.registrado_em + timedelta(minutes=prox['eta_min'])
            data['proxima_parada'] = {
                **prox['parada'].to_dict(),
                'distancia_m': round(prox['distancia_m']),
                'eta_min': prox['eta_min'],
                'chegada_estimada': chegada.isoformat(),
            }
    return data


def _pode_gerenciar(viagem: Viagem) -> bool:
    """Dono da viagem ou admin."""
    user = get_current_user()
    if not user:
        return False
    if user.role == 'admin':
        return True
    return user.motorista is not None and user.motorista.id == viagem.motorista_id


def _conflito_ativa(motorista_id: int, veiculo_id: int, ignorar_id: int | None = None):
    """CA08.2 — motorista e veículo só podem ter uma viagem em_andamento."""
    base = Viagem.query.filter_by(status='em_andamento')
    if ignorar_id:
        base = base.filter(Viagem.id != ignorar_id)
    if base.filter_by(motorista_id=motorista_id).first():
        return 'Você já possui uma viagem em andamento. Finalize-a antes de iniciar outra.'
    if base.filter_by(veiculo_id=veiculo_id).first():
        return 'Este veículo já está em uma viagem em andamento.'
    return None


# ── Motorista ────────────────────────────────────────────────────────────────

@viagens_bp.route('/viagens/opcoes', methods=['GET'])
@motorista_required
def opcoes_viagem():
    """CA08.1 — só linhas ativas e veículos ativos."""
    linhas = Route.query.filter_by(active=True).order_by(Route.route_name).all()
    veiculos = Vehicle.query.filter_by(status='ativo').order_by(Vehicle.plate).all()
    ocupados = {v.veiculo_id for v in Viagem.query.filter_by(status='em_andamento').all()}
    return jsonify({
        'linhas': [_linha_dict(l) for l in linhas],
        'veiculos': [
            {'id': v.id, 'plate': v.plate, 'model': v.model, 'em_uso': v.id in ocupados}
            for v in veiculos
        ],
        'sentidos': list(SENTIDOS),
    })


@viagens_bp.route('/viagens/atual', methods=['GET'])
@motorista_required
def viagem_atual():
    viagem = g.motorista.viagens.filter_by(status='em_andamento').first()
    return jsonify({'viagem': _viagem_com_posicao(viagem) if viagem else None})


@viagens_bp.route('/viagens', methods=['POST'])
@motorista_required
def iniciar_viagem():
    motorista = g.motorista
    if motorista.status != 'ativo':
        return jsonify({'error': f'Motorista com status "{motorista.status}" não pode iniciar viagens.'}), 403

    data = request.get_json() or {}
    try:
        linha_id, veiculo_id = int(data.get('linha_id')), int(data.get('veiculo_id'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Informe linha_id e veiculo_id'}), 400
    sentido = data.get('sentido')
    if sentido not in SENTIDOS:
        return jsonify({'error': f'Sentido inválido. Use: {", ".join(SENTIDOS)}'}), 400

    linha = db.session.get(Route, linha_id)
    if not linha or not linha.active:
        return jsonify({'error': 'Linha não encontrada ou inativa'}), 422
    veiculo = db.session.get(Vehicle, veiculo_id)
    if not veiculo or veiculo.status != 'ativo':
        return jsonify({'error': 'Veículo não encontrado ou inativo'}), 422

    conflito = _conflito_ativa(motorista.id, veiculo.id)
    if conflito:
        return jsonify({'error': conflito}), 409

    viagem = Viagem(
        linha_id=linha.id, veiculo_id=veiculo.id, motorista_id=motorista.id,
        sentido=sentido, status='em_andamento', iniciada_em=datetime.utcnow(),
    )
    db.session.add(viagem)
    try:
        db.session.commit()
    except IntegrityError:  # corrida entre duas requisições: o índice único barra
        db.session.rollback()
        return jsonify({'error': 'Motorista ou veículo já está em uma viagem em andamento.'}), 409
    return jsonify({'message': 'Viagem iniciada', 'viagem': _viagem_com_posicao(viagem)}), 201


@viagens_bp.route('/viagens/<int:viagem_id>/posicoes', methods=['POST'])
@motorista_required
def registrar_posicoes(viagem_id):
    """Recebe uma ou várias posições (lote enviado após perda de conexão — CA08.7)."""
    viagem = db.session.get(Viagem, viagem_id)
    if not viagem or viagem.motorista_id != g.motorista.id:
        return jsonify({'error': 'Viagem não encontrada'}), 404
    if viagem.status != 'em_andamento':
        return jsonify({'error': 'Viagem não está em andamento'}), 409

    data = request.get_json() or {}
    itens = data.get('posicoes')
    if itens is None:
        itens = [data]
    if not isinstance(itens, list) or not itens:
        return jsonify({'error': 'Envie posicoes: [{latitude, longitude, ...}]'}), 400
    if len(itens) > MAX_POSICOES_POR_LOTE:
        return jsonify({'error': f'Máximo de {MAX_POSICOES_POR_LOTE} posições por lote'}), 413

    agora = datetime.utcnow()
    aceitas = 0
    for item in itens:
        try:
            lat, lon = float(item['latitude']), float(item['longitude'])
        except (KeyError, TypeError, ValueError):
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        registrado = _parse_datetime(item.get('registrado_em')) or agora
        if registrado < viagem.iniciada_em - TOLERANCIA_RELOGIO or registrado > agora + TOLERANCIA_RELOGIO:
            continue
        velocidade = item.get('velocidade')
        try:
            velocidade = None if velocidade is None else max(0.0, float(velocidade))
        except (TypeError, ValueError):
            velocidade = None
        db.session.add(Posicao(viagem_id=viagem.id, latitude=lat, longitude=lon,
                               velocidade=velocidade, registrado_em=registrado))
        aceitas += 1

    db.session.commit()

    if aceitas and _socketio:
        _socketio.emit('viagem_posicao', _viagem_com_posicao(viagem), namespace='/tracking')
    return jsonify({'aceitas': aceitas, 'descartadas': len(itens) - aceitas}), 201


@viagens_bp.route('/viagens/<int:viagem_id>/finalizar', methods=['POST'])
def finalizar_viagem(viagem_id):
    """CA08.8 — grava finalizada_em; posições deixam de ser aceitas."""
    viagem = db.session.get(Viagem, viagem_id)
    if not viagem or not _pode_gerenciar(viagem):
        return jsonify({'error': 'Viagem não encontrada'}), 404
    if viagem.status != 'em_andamento':
        return jsonify({'error': 'Somente viagens em andamento podem ser finalizadas'}), 409
    viagem.status = 'finalizada'
    viagem.finalizada_em = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Viagem finalizada', 'viagem': viagem.to_dict()})


@viagens_bp.route('/viagens/<int:viagem_id>/cancelar', methods=['POST'])
def cancelar_viagem(viagem_id):
    viagem = db.session.get(Viagem, viagem_id)
    if not viagem or not _pode_gerenciar(viagem):
        return jsonify({'error': 'Viagem não encontrada'}), 404
    if viagem.status not in ('planejada', 'em_andamento'):
        return jsonify({'error': 'Viagem finalizada ou cancelada não pode ser alterada'}), 409
    viagem.status = 'cancelada'
    viagem.finalizada_em = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Viagem cancelada', 'viagem': viagem.to_dict()})


@viagens_bp.route('/viagens/<int:viagem_id>', methods=['PATCH', 'PUT'])
def editar_viagem(viagem_id):
    """Edita sentido/veículo. CA08.9 — viagem finalizada é somente consulta."""
    viagem = db.session.get(Viagem, viagem_id)
    if not viagem or not _pode_gerenciar(viagem):
        return jsonify({'error': 'Viagem não encontrada'}), 404
    if viagem.status in ('finalizada', 'cancelada'):
        return jsonify({'error': f'Viagem {viagem.status} não pode ser editada, apenas consultada.'}), 409

    data = request.get_json() or {}
    if 'sentido' in data:
        if data['sentido'] not in SENTIDOS:
            return jsonify({'error': f'Sentido inválido. Use: {", ".join(SENTIDOS)}'}), 400
        viagem.sentido = data['sentido']
    if 'veiculo_id' in data:
        veiculo = db.session.get(Vehicle, data['veiculo_id'])
        if not veiculo or veiculo.status != 'ativo':
            return jsonify({'error': 'Veículo não encontrado ou inativo'}), 422
        if viagem.status == 'em_andamento':
            conflito = _conflito_ativa(viagem.motorista_id, veiculo.id, ignorar_id=viagem.id)
            if conflito:
                return jsonify({'error': conflito}), 409
        viagem.veiculo_id = veiculo.id
    db.session.commit()
    return jsonify({'message': 'Viagem atualizada', 'viagem': viagem.to_dict()})


@viagens_bp.route('/viagens/<int:viagem_id>', methods=['GET'])
def consultar_viagem(viagem_id):
    viagem = db.session.get(Viagem, viagem_id)
    if not viagem or not _pode_gerenciar(viagem):
        return jsonify({'error': 'Viagem não encontrada'}), 404
    data = _viagem_com_posicao(viagem)
    data['total_posicoes'] = viagem.posicoes.count()
    return jsonify(data)


# ── Passageiro e admin ───────────────────────────────────────────────────────

@viagens_bp.route('/linhas', methods=['GET'])
def listar_linhas():
    """Linhas ativas com paradas (seleção no app do passageiro)."""
    linhas = Route.query.filter_by(active=True).order_by(Route.route_name).all()
    resultado = []
    for linha in linhas:
        item = _linha_dict(linha)
        item['paradas'] = [p.to_dict() for p in sorted(linha.stop_points, key=lambda p: p.order)]
        resultado.append(item)
    return jsonify(resultado)


@viagens_bp.route('/viagens/ativas', methods=['GET'])
def viagens_ativas():
    """CA08.5 — passageiro: ?linha_id=X. CA08.10 — admin: sem filtro, todas as linhas."""
    linha_id = request.args.get('linha_id', type=int)
    query = Viagem.query.filter_by(status='em_andamento')
    if linha_id:
        query = query.filter_by(linha_id=linha_id)
    else:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Usuário não autenticado'}), 401
        if user.role != 'admin':
            return jsonify({'error': 'Informe linha_id'}), 400
    viagens = query.order_by(Viagem.iniciada_em).all()
    return jsonify([_viagem_com_posicao(v) for v in viagens])
