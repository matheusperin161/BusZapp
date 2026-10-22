"""Admin routes for managing drivers and vehicles."""
from datetime import date

from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from werkzeug.security import generate_password_hash

from src.models import db
from src.models.user import User, Motorista, Vehicle, CNH_CATEGORIAS
from src.models.tracking import Viagem
from src.utils.auth import admin_required
from src.utils.cpf import cpf_valido, somente_digitos

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

MOTORISTA_REQUIRED_FIELDS = {
    'nome': 'nome',
    'cpf': 'CPF',
    'cnh_numero': 'número da CNH',
    'cnh_categoria': 'categoria da CNH',
    'cnh_validade': 'validade da CNH',
}
VEHICLE_REQUIRED_FIELDS = ('plate', 'model', 'brand', 'year', 'capacity', 'status')
VALID_VEHICLE_STATUSES = ('ativo', 'inativo', 'manutencao')


# ── Drivers ──────────────────────────────────────────────────────────────────

def _texto(data, campo):
    return str(data.get(campo) or '').strip()


def _validar_motorista(data, motorista=None):
    """Valida o payload do cadastro/edição. Retorna (campos, erro, status_http)."""
    faltando = [rotulo for campo, rotulo in MOTORISTA_REQUIRED_FIELDS.items() if not _texto(data, campo)]
    if motorista is None and not _texto(data, 'email'):
        faltando.append('e-mail de acesso')
    if motorista is None and not data.get('senha'):
        faltando.append('senha de acesso')
    if faltando:
        return None, f'Campos obrigatórios ausentes: {", ".join(faltando)}', 400

    cpf = somente_digitos(data['cpf'])
    if not cpf_valido(cpf):
        return None, 'CPF inválido', 400

    categoria = _texto(data, 'cnh_categoria').upper()
    if categoria not in CNH_CATEGORIAS:
        return None, f'Categoria de CNH inválida. Use: {", ".join(CNH_CATEGORIAS)}', 400

    try:
        validade = date.fromisoformat(_texto(data, 'cnh_validade'))
    except ValueError:
        return None, 'Validade da CNH inválida (use AAAA-MM-DD)', 400

    status = _texto(data, 'status') or (motorista.status if motorista else 'ativo')
    if status not in Motorista.VALID_STATUSES:
        return None, f'Status inválido. Use: {", ".join(Motorista.VALID_STATUSES)}', 400

    if data.get('senha') and len(data['senha']) < 6:
        return None, 'A senha deve ter pelo menos 6 caracteres', 400

    campos = {
        'nome': _texto(data, 'nome'),
        'cpf': cpf,
        'cnh_numero': _texto(data, 'cnh_numero'),
        'cnh_categoria': categoria,
        'cnh_validade': validade,
        'telefone': _texto(data, 'telefone') or None,
        'status': status,
        'bus_line': _texto(data, 'bus_line') or None,
        'code': _texto(data, 'code') or None,
        'first_schedule': _texto(data, 'first_schedule') or None,
        'last_schedule': _texto(data, 'last_schedule') or None,
    }

    outro = Motorista.id != motorista.id if motorista else True
    conflitos = [
        (Motorista.query.filter(Motorista.cpf == campos['cpf'], outro).first(), 'CPF já cadastrado'),
        (Motorista.query.filter(Motorista.cnh_numero == campos['cnh_numero'], outro).first(), 'CNH já cadastrada'),
    ]
    if campos['code']:
        conflitos.append((Motorista.query.filter(Motorista.code == campos['code'], outro).first(), 'Código já cadastrado'))
    email = _texto(data, 'email').lower()
    if email:
        outro_usuario = User.id != motorista.usuario_id if motorista else True
        conflitos.append((User.query.filter(User.email == email, outro_usuario).first(), 'E-mail já cadastrado'))
    for existente, msg in conflitos:
        if existente:
            return None, msg, 409

    return campos, None, None


def _username_livre(nome: str) -> str:
    base = nome[:70]
    candidato, n = base, 2
    while User.query.filter_by(username=candidato).first():
        candidato, n = f'{base} ({n})', n + 1
    return candidato


@admin_bp.route('/drivers', methods=['GET'])
@admin_required
def list_drivers():
    """Lista motoristas. Filtros: ?status=ativo|afastado|inativo e ?q= (nome ou CPF)."""
    query = Motorista.query
    status = request.args.get('status', '').strip()
    if status:
        if status not in Motorista.VALID_STATUSES:
            return jsonify({'error': f'Status inválido. Use: {", ".join(Motorista.VALID_STATUSES)}'}), 400
        query = query.filter(Motorista.status == status)

    termo = request.args.get('q', '').strip()
    if termo:
        filtros = [Motorista.nome.ilike(f'%{termo}%')]
        digitos = somente_digitos(termo)
        if digitos:
            filtros.append(Motorista.cpf.like(f'%{digitos}%'))
        query = query.filter(or_(*filtros))

    motoristas = query.order_by(Motorista.nome).all()
    return jsonify([m.to_dict() for m in motoristas])


@admin_bp.route('/drivers', methods=['POST'])
@admin_required
def add_driver():
    data = request.get_json() or {}
    campos, erro, http = _validar_motorista(data)
    if erro:
        return jsonify({'error': erro}), http

    # CA02.4 — todo motorista ganha um acesso de usuário com perfil motorista
    usuario = User(
        username=_username_livre(campos['nome']),
        email=_texto(data, 'email').lower(),
        password=generate_password_hash(data['senha']),
        role='motorista',
        email_verified=True,
    )
    db.session.add(usuario)
    db.session.flush()

    motorista = Motorista(usuario_id=usuario.id, **campos)
    db.session.add(motorista)
    db.session.commit()
    return jsonify({'message': 'Motorista cadastrado com sucesso', 'driver': motorista.to_dict()}), 201


@admin_bp.route('/drivers/<int:driver_id>', methods=['GET'])
@admin_required
def get_driver(driver_id):
    motorista = db.session.get(Motorista, driver_id)
    if not motorista:
        return jsonify({'error': 'Motorista não encontrado'}), 404
    return jsonify(motorista.to_dict())


@admin_bp.route('/drivers/<int:driver_id>', methods=['PUT'])
@admin_required
def edit_driver(driver_id):
    motorista = db.session.get(Motorista, driver_id)
    if not motorista:
        return jsonify({'error': 'Motorista não encontrado'}), 404

    data = request.get_json() or {}
    campos, erro, http = _validar_motorista(data, motorista)
    if erro:
        return jsonify({'error': erro}), http

    for campo, valor in campos.items():
        setattr(motorista, campo, valor)

    usuario = motorista.usuario
    if _texto(data, 'email'):
        usuario.email = _texto(data, 'email').lower()
    if data.get('senha'):
        usuario.password = generate_password_hash(data['senha'])

    db.session.commit()
    return jsonify({'message': 'Motorista atualizado com sucesso', 'driver': motorista.to_dict()}), 200


@admin_bp.route('/drivers/<int:driver_id>', methods=['DELETE'])
@admin_required
def delete_driver(driver_id):
    motorista = db.session.get(Motorista, driver_id)
    if not motorista:
        return jsonify({'error': 'Motorista não encontrado'}), 404

    # CA02.6 — não exclui com viagem em andamento
    if motorista.viagens.filter_by(status='em_andamento').first():
        return jsonify({
            'error': 'Motorista possui viagem em andamento e não pode ser excluído. '
                     'Finalize a viagem antes de excluir.',
            'motivo': 'viagem_em_andamento',
        }), 409
    # Viagens encerradas guardam histórico: nesse caso o caminho é inativar
    if motorista.viagens.first():
        return jsonify({
            'error': 'Motorista possui histórico de viagens e não pode ser excluído. '
                     'Altere o status para inativo.',
            'motivo': 'possui_historico',
        }), 409

    Vehicle.query.filter_by(driver_id=motorista.id).update({'driver_id': None})
    usuario = motorista.usuario
    db.session.delete(motorista)
    db.session.flush()
    if usuario:
        db.session.delete(usuario)
    db.session.commit()
    return jsonify({'message': 'Motorista excluído com sucesso'}), 200


# ── Vehicles ─────────────────────────────────────────────────────────────────

@admin_bp.route('/vehicles', methods=['GET'])
@admin_required
def list_vehicles():
    vehicles = Vehicle.query.order_by(Vehicle.created_at.desc()).all()
    return jsonify([v.to_dict() for v in vehicles])


@admin_bp.route('/vehicles', methods=['POST'])
@admin_required
def add_vehicle():
    data = request.get_json() or {}
    missing = [f for f in VEHICLE_REQUIRED_FIELDS if not data.get(f)]
    if missing:
        return jsonify({'error': f'Campos obrigatórios ausentes: {", ".join(missing)}'}), 400

    if Vehicle.query.filter_by(plate=data['plate']).first():
        return jsonify({'error': 'Placa já cadastrada'}), 400

    try:
        year, capacity = int(data['year']), int(data['capacity'])
    except (TypeError, ValueError):
        return jsonify({'error': 'Ano e capacidade devem ser números inteiros'}), 400

    if data['status'] not in VALID_VEHICLE_STATUSES:
        return jsonify({'error': f'Status inválido. Use: {", ".join(VALID_VEHICLE_STATUSES)}'}), 400

    vehicle = Vehicle(
        plate=data['plate'],
        model=data['model'],
        brand=data['brand'],
        year=year,
        capacity=capacity,
        status=data['status'],
        bus_line=data.get('bus_line'),
        driver_id=data.get('driver_id'),
    )
    db.session.add(vehicle)
    db.session.commit()
    return jsonify({'message': 'Veículo cadastrado com sucesso', 'vehicle': vehicle.to_dict()}), 201


@admin_bp.route('/vehicles/<int:vehicle_id>', methods=['GET'])
@admin_required
def get_vehicle(vehicle_id):
    vehicle = db.session.get(Vehicle, vehicle_id)
    if not vehicle:
        return jsonify({'error': 'Veículo não encontrado'}), 404
    return jsonify(vehicle.to_dict())


@admin_bp.route('/vehicles/<int:vehicle_id>', methods=['PUT'])
@admin_required
def edit_vehicle(vehicle_id):
    vehicle = db.session.get(Vehicle, vehicle_id)
    if not vehicle:
        return jsonify({'error': 'Veículo não encontrado'}), 404

    data = request.get_json() or {}
    missing = [f for f in VEHICLE_REQUIRED_FIELDS if not data.get(f)]
    if missing:
        return jsonify({'error': f'Campos obrigatórios ausentes: {", ".join(missing)}'}), 400

    if Vehicle.query.filter(Vehicle.plate == data['plate'], Vehicle.id != vehicle_id).first():
        return jsonify({'error': 'Placa já cadastrada por outro veículo'}), 400

    try:
        year, capacity = int(data['year']), int(data['capacity'])
    except (TypeError, ValueError):
        return jsonify({'error': 'Ano e capacidade devem ser números inteiros'}), 400

    if data['status'] not in VALID_VEHICLE_STATUSES:
        return jsonify({'error': f'Status inválido. Use: {", ".join(VALID_VEHICLE_STATUSES)}'}), 400

    vehicle.plate = data['plate']
    vehicle.model = data['model']
    vehicle.brand = data['brand']
    vehicle.year = year
    vehicle.capacity = capacity
    vehicle.status = data['status']
    vehicle.bus_line = data.get('bus_line')
    vehicle.driver_id = data.get('driver_id')

    db.session.commit()
    return jsonify({'message': 'Veículo atualizado com sucesso', 'vehicle': vehicle.to_dict()}), 200


@admin_bp.route('/vehicles/<int:vehicle_id>', methods=['DELETE'])
@admin_required
def delete_vehicle(vehicle_id):
    vehicle = db.session.get(Vehicle, vehicle_id)
    if not vehicle:
        return jsonify({'error': 'Veículo não encontrado'}), 404
    if Viagem.query.filter_by(veiculo_id=vehicle.id).first():
        return jsonify({'error': 'Veículo possui viagens registradas e não pode ser excluído. '
                                 'Altere o status para inativo.'}), 409
    db.session.delete(vehicle)
    db.session.commit()
    return jsonify({'message': 'Veículo excluído com sucesso'}), 200


# ── Stop Points Management ────────────────────────────────────────────────────

from src.models.tracking import Route, StopPoint

@admin_bp.route('/routes', methods=['GET'])
@admin_required
def list_routes():
    from src.models.tracking import Route, StopPoint
    routes = Route.query.all()
    result = []
    for r in routes:
        stops = sorted(r.stop_points, key=lambda s: s.order)
        # Find linked driver and vehicle via bus_line name
        from src.models.user import BusRoute as BR
        bus_route = BR.query.filter_by(route_name=r.route_name.replace('Linha_','')).first()
        route_line_str = None
        if bus_route:
            route_line_str = f"{bus_route.route_number} - {bus_route.route_name}"
        linked_driver = Motorista.query.filter_by(bus_line=route_line_str).first() if route_line_str else None
        linked_vehicle = Vehicle.query.filter_by(bus_line=route_line_str).first() if route_line_str else None

        result.append({
            'id': r.id,
            'route_name': r.route_name,
            'origin_lat': r.origin_lat,
            'origin_lon': r.origin_lon,
            'destination_lat': r.destination_lat,
            'destination_lon': r.destination_lon,
            'active': r.active,
            'stop_count': len(stops),
            'stops': [s.to_dict() for s in stops],
            'driver': {'id': linked_driver.id, 'name': linked_driver.nome, 'code': linked_driver.code} if linked_driver else None,
            'vehicle': {'id': linked_vehicle.id, 'plate': linked_vehicle.plate, 'model': linked_vehicle.model} if linked_vehicle else None,
        })
    return jsonify(result)


def _minutos(valor):
    """Tempo até a próxima parada: número positivo ou None."""
    if valor in (None, ''):
        return None
    minutos = float(valor)
    if minutos <= 0:
        raise ValueError('tempo_ate_proxima_min deve ser positivo')
    return minutos


@admin_bp.errorhandler(ValueError)
def _valor_invalido(e):
    return jsonify({'error': f'Valor inválido: {e}'}), 400


@admin_bp.route('/routes/<int:route_id>', methods=['PATCH'])
@admin_required
def toggle_route(route_id):
    """Ativa/desativa uma linha. Linhas inativas não aparecem para iniciar viagem."""
    route = db.session.get(Route, route_id)
    if not route:
        return jsonify({'error': 'Rota não encontrada'}), 404
    data = request.get_json() or {}
    if not isinstance(data.get('active'), bool):
        return jsonify({'error': 'Informe active: true ou false'}), 400
    route.active = data['active']
    db.session.commit()
    return jsonify({'message': 'Linha atualizada', 'active': route.active})


@admin_bp.route('/routes/<int:route_id>/stops', methods=['GET'])
@admin_required
def list_stops(route_id):
    from src.models.tracking import Route, StopPoint
    route = db.session.get(Route, route_id)
    if not route:
        return jsonify({'error': 'Rota não encontrada'}), 404
    stops = sorted(route.stop_points, key=lambda s: s.order)
    return jsonify([s.to_dict() for s in stops])


@admin_bp.route('/routes/<int:route_id>/stops', methods=['POST'])
@admin_required
def add_stop(route_id):
    from src.models.tracking import Route, StopPoint
    route = db.session.get(Route, route_id)
    if not route:
        return jsonify({'error': 'Rota não encontrada'}), 404
    data = request.get_json() or {}
    missing = [f for f in ('name', 'latitude', 'longitude', 'order') if f not in data]
    if missing:
        return jsonify({'error': f'Campos obrigatórios: {", ".join(missing)}'}), 400
    stop = StopPoint(
        route_id=route_id,
        name=data['name'],
        latitude=float(data['latitude']),
        longitude=float(data['longitude']),
        order=int(data['order']),
        tempo_ate_proxima_min=_minutos(data.get('tempo_ate_proxima_min')),
    )
    db.session.add(stop)
    db.session.commit()
    return jsonify({'message': 'Parada adicionada', 'stop': stop.to_dict()}), 201


@admin_bp.route('/routes/<int:route_id>/stops/<int:stop_id>', methods=['PUT'])
@admin_required
def edit_stop(route_id, stop_id):
    from src.models.tracking import StopPoint
    stop = db.session.get(StopPoint, stop_id)
    if not stop or stop.route_id != route_id:
        return jsonify({'error': 'Parada não encontrada'}), 404
    data = request.get_json() or {}
    stop.name = data.get('name', stop.name)
    stop.latitude = float(data.get('latitude', stop.latitude))
    stop.longitude = float(data.get('longitude', stop.longitude))
    stop.order = int(data.get('order', stop.order))
    if 'tempo_ate_proxima_min' in data:
        stop.tempo_ate_proxima_min = _minutos(data['tempo_ate_proxima_min'])
    db.session.commit()
    return jsonify({'message': 'Parada atualizada', 'stop': stop.to_dict()})


@admin_bp.route('/routes/<int:route_id>/stops/<int:stop_id>', methods=['DELETE'])
@admin_required
def delete_stop(route_id, stop_id):
    from src.models.tracking import StopPoint
    stop = db.session.get(StopPoint, stop_id)
    if not stop or stop.route_id != route_id:
        return jsonify({'error': 'Parada não encontrada'}), 404
    db.session.delete(stop)
    db.session.commit()
    return jsonify({'message': 'Parada removida'})


# ── Create new Route ──────────────────────────────────────────────────────────

@admin_bp.route('/routes', methods=['POST'])
@admin_required
def create_route():
    from src.models.tracking import Route, StopPoint
    from src.models.user import BusRoute
    data = request.get_json() or {}
    missing = [f for f in ('route_number', 'route_name', 'origin', 'destination', 'fare',
                            'origin_lat', 'origin_lon', 'dest_lat', 'dest_lon') if not str(data.get(f,'')).strip()]
    if missing:
        return jsonify({'error': f'Campos obrigatórios: {", ".join(missing)}'}), 400

    if BusRoute.query.filter_by(route_number=str(data['route_number'])).first():
        return jsonify({'error': f'Linha {data["route_number"]} já existe'}), 400

    try:
        fare = float(data['fare'])
        origin_lat = float(data['origin_lat'])
        origin_lon = float(data['origin_lon'])
        dest_lat = float(data['dest_lat'])
        dest_lon = float(data['dest_lon'])
    except (ValueError, TypeError):
        return jsonify({'error': 'Valores numéricos inválidos'}), 400

    # Create BusRoute (shown in linha selection)
    br = BusRoute(
        route_number=str(data['route_number']),
        route_name=data['route_name'],
        origin=data['origin'],
        destination=data['destination'],
        fare=fare,
    )
    db.session.add(br)

    # Create Route (used for tracking/stops)
    rt = Route(
        route_name=f"Linha_{data['route_number']}",
        origin_lat=origin_lat, origin_lon=origin_lon,
        destination_lat=dest_lat, destination_lon=dest_lon,
    )
    db.session.add(rt)
    db.session.flush()

    # Link driver and vehicle to the route if provided
    if data.get('driver_id'):
        driver = db.session.get(Motorista, int(data['driver_id']))
        if driver:
            driver.bus_line = f"{data['route_number']} - {data['route_name']}"

    if data.get('vehicle_id'):
        vehicle = db.session.get(Vehicle, int(data['vehicle_id']))
        if vehicle:
            vehicle.bus_line = f"{data['route_number']} - {data['route_name']}"

    # Auto-create origin and destination as first stops
    db.session.add(StopPoint(route_id=rt.id, name=data['origin'],
                              latitude=origin_lat, longitude=origin_lon, order=1))
    db.session.add(StopPoint(route_id=rt.id, name=data['destination'],
                              latitude=dest_lat, longitude=dest_lon, order=2))

    # Auto-create default departure schedules so the schedules page works immediately
    from src.routes.tracking import _create_default_schedules
    _create_default_schedules(rt.id, str(data['route_number']))

    db.session.commit()

    return jsonify({'message': f'Linha {data["route_number"]} criada com sucesso', 'route_id': rt.id}), 201


# ── Active trips count (for the stats counter) ───────────────────────────────

@admin_bp.route('/active-trips-count', methods=['GET'])
@admin_required
def active_trips_count():
    from src.models.user import DriverTrip
    from datetime import datetime
    today = datetime.utcnow().date()
    legado = DriverTrip.query.filter_by(trip_date=today).filter(
        DriverTrip.ended_at.is_(None)
    ).count()
    viagens = Viagem.query.filter_by(status='em_andamento').count()
    return jsonify({'count': legado + viagens})


# ── Admin reports ─────────────────────────────────────────────────────────────

@admin_bp.route('/ratings', methods=['GET'])
@admin_required
def list_all_ratings():
    from src.models.user import Rating
    from sqlalchemy.orm import joinedload
    driver_id_map = {d.id: d for d in Motorista.query.all()}
    ratings = (
        Rating.query
        .options(joinedload(Rating.user), joinedload(Rating.driver))
        .order_by(Rating.created_at.desc())
        .limit(500)
        .all()
    )
    result = []
    for r in ratings:
        item = r.to_dict()
        d = driver_id_map.get(r.driver_id)
        item['driver_name'] = d.nome if d else None
        item['driver_code'] = d.code if d else None
        item['username'] = r.user.username if r.user else None
        result.append(item)
    return jsonify(result)


@admin_bp.route('/all-transactions', methods=['GET'])
@admin_required
def list_all_transactions():
    from src.models.user import Transaction, User
    from sqlalchemy.orm import joinedload
    txs = (
        Transaction.query
        .options(joinedload(Transaction.user))
        .order_by(Transaction.created_at.desc())
        .limit(1000)
        .all()
    )
    result = []
    for tx in txs:
        item = tx.to_dict()
        item['username'] = tx.user.username if tx.user else None
        result.append(item)
    return jsonify(result)


@admin_bp.route('/recharge-chart', methods=['GET'])
@admin_required
def recharge_chart():
    from src.models.user import Transaction, User
    from sqlalchemy.orm import joinedload
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=30)
    txs = (
        Transaction.query
        .options(joinedload(Transaction.user))
        .filter(Transaction.transaction_type == 'recharge', Transaction.created_at >= since)
        .order_by(Transaction.created_at.desc())
        .all()
    )
    result = []
    for tx in txs:
        item = tx.to_dict()
        item['username'] = tx.user.username if tx.user else None
        result.append(item)
    return jsonify(result)


# ── User Cards ────────────────────────────────────────────────────────────────

VALID_CARD_TYPES = ('cidadao', 'normal', 'estudante', 'idoso', 'acompanhante', 'carteiro', 'colaborador', 'pcd')

@admin_bp.route('/users/cards', methods=['GET'])
@admin_required
def list_user_cards():
    from src.models.user import User
    users = User.query.filter_by(role='user').order_by(User.username).all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'card_number': u.card_number,
        'card_holder': u.card_holder,
        'card_type': u.card_type,
        'card_balance': u.card_balance,
        'email_verified': u.email_verified,
    } for u in users])


@admin_bp.route('/users/<int:user_id>/card', methods=['PUT'])
@admin_required
def edit_user_card(user_id):
    from src.models.user import User
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    data = request.get_json() or {}
    if 'card_number' in data:
        user.card_number = data['card_number'] or None
    if 'card_holder' in data:
        user.card_holder = data['card_holder'] or None
    if 'card_type' in data:
        ct = data['card_type']
        if ct and ct not in VALID_CARD_TYPES:
            return jsonify({'error': f'Tipo inválido. Use: {", ".join(VALID_CARD_TYPES)}'}), 400
        user.card_type = ct or None
    if 'card_balance' in data:
        try:
            user.card_balance = float(data['card_balance'])
        except (TypeError, ValueError):
            return jsonify({'error': 'Saldo inválido'}), 400
    db.session.commit()
    return jsonify({'message': 'Cartão atualizado com sucesso'})


@admin_bp.route('/all-bus-locations', methods=['GET'])
@admin_required
def list_all_bus_locations():
    from src.models.user import BusLocation, DriverTrip
    from datetime import datetime, timedelta
    from sqlalchemy import func

    now = datetime.utcnow()
    today = now.date()
    gps_cutoff = now - timedelta(minutes=15)

    # Encerra automaticamente trips de dias anteriores que ficaram abertas
    DriverTrip.query.filter(
        DriverTrip.trip_date < today,
        DriverTrip.ended_at.is_(None),
    ).update({'ended_at': now}, synchronize_session=False)
    db.session.commit()

    # Ônibus que transmitiram GPS nos últimos 15 min — critério principal
    # (independente de DriverTrip aberta, para suportar testes com 1 conta)
    latest_ids = (
        db.session.query(func.max(BusLocation.id))
        .filter(BusLocation.timestamp >= gps_cutoff)
        .filter(BusLocation.bus_number.isnot(None))
        .group_by(BusLocation.bus_number)
        .all()
    )
    loc_ids = [row[0] for row in latest_ids if row[0] is not None]
    if not loc_ids:
        return jsonify([])

    locations = BusLocation.query.filter(BusLocation.id.in_(loc_ids)).all()

    # Monta mapa bus_number -> trip mais recente do dia para enriquecer a rota
    all_today_trips = (
        DriverTrip.query
        .filter_by(trip_date=today)
        .filter(DriverTrip.bus_number.isnot(None))
        .order_by(DriverTrip.started_at.desc())
        .all()
    )
    # Pega a trip mais recente por bus_number (aberta ou não)
    trip_by_bus = {}
    for t in all_today_trips:
        if t.bus_number not in trip_by_bus:
            trip_by_bus[t.bus_number] = t

    result = []
    for loc in locations:
        d = loc.to_dict()
        if not d.get('route'):
            trip = trip_by_bus.get(loc.bus_number)
            if trip and trip.bus_line:
                parts = trip.bus_line.split(' - ', 1)
                route_number = parts[0].strip()
                route_name = parts[1].strip() if len(parts) > 1 else trip.bus_line
                d['route'] = {
                    'route_number': route_number,
                    'route_name': route_name,
                }
        result.append(d)
    return jsonify(result)
