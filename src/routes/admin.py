"""Admin routes for managing drivers and vehicles."""
from flask import Blueprint, jsonify, request

from src.models import db
from src.models.user import Driver, Vehicle
from src.utils.auth import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

DRIVER_REQUIRED_FIELDS = ('name', 'email', 'cpf', 'cnh', 'bus_line', 'code')
VEHICLE_REQUIRED_FIELDS = ('plate', 'model', 'brand', 'year', 'capacity', 'status')
VALID_VEHICLE_STATUSES = ('ativo', 'inativo', 'manutencao')


# ── Drivers ──────────────────────────────────────────────────────────────────

@admin_bp.route('/drivers', methods=['GET'])
@admin_required
def list_drivers():
    drivers = Driver.query.order_by(Driver.created_at.desc()).all()
    return jsonify([d.to_dict() for d in drivers])


@admin_bp.route('/drivers', methods=['POST'])
@admin_required
def add_driver():
    data = request.get_json() or {}
    missing = [f for f in DRIVER_REQUIRED_FIELDS if not data.get(f)]
    if missing:
        return jsonify({'error': f'Campos obrigatórios ausentes: {", ".join(missing)}'}), 400

    if not data.get('password'):
        return jsonify({'error': 'Senha de acesso é obrigatória'}), 400

    conflicts = [
        (Driver.query.filter_by(email=data['email']).first(), 'E-mail já cadastrado'),
        (Driver.query.filter_by(cpf=data['cpf']).first(), 'CPF já cadastrado'),
        (Driver.query.filter_by(cnh=data['cnh']).first(), 'CNH já cadastrada'),
        (Driver.query.filter_by(code=data['code']).first(), 'Código já cadastrado'),
    ]
    for obj, msg in conflicts:
        if obj:
            return jsonify({'error': msg}), 400

    from werkzeug.security import generate_password_hash
    driver = Driver(
        **{f: data[f] for f in DRIVER_REQUIRED_FIELDS},
        password=generate_password_hash(data['password']),
    )
    db.session.add(driver)
    db.session.commit()
    return jsonify({'message': 'Motorista cadastrado com sucesso', 'driver': driver.to_dict()}), 201


@admin_bp.route('/drivers/<int:driver_id>', methods=['GET'])
@admin_required
def get_driver(driver_id):
    driver = db.session.get(Driver, driver_id)
    if not driver:
        return jsonify({'error': 'Motorista não encontrado'}), 404
    return jsonify(driver.to_dict())


@admin_bp.route('/drivers/<int:driver_id>', methods=['PUT'])
@admin_required
def edit_driver(driver_id):
    driver = db.session.get(Driver, driver_id)
    if not driver:
        return jsonify({'error': 'Motorista não encontrado'}), 404

    data = request.get_json() or {}
    missing = [f for f in DRIVER_REQUIRED_FIELDS if not data.get(f)]
    if missing:
        return jsonify({'error': f'Campos obrigatórios ausentes: {", ".join(missing)}'}), 400

    conflicts = [
        (Driver.query.filter(Driver.email == data['email'], Driver.id != driver_id).first(), 'E-mail já cadastrado por outro motorista'),
        (Driver.query.filter(Driver.cpf == data['cpf'], Driver.id != driver_id).first(), 'CPF já cadastrado por outro motorista'),
        (Driver.query.filter(Driver.cnh == data['cnh'], Driver.id != driver_id).first(), 'CNH já cadastrada por outro motorista'),
        (Driver.query.filter(Driver.code == data['code'], Driver.id != driver_id).first(), 'Código já cadastrado por outro motorista'),
    ]
    for obj, msg in conflicts:
        if obj:
            return jsonify({'error': msg}), 400

    for field in DRIVER_REQUIRED_FIELDS:
        setattr(driver, field, data[field])

    # Update password only if provided
    if data.get('password'):
        from werkzeug.security import generate_password_hash
        driver.password = generate_password_hash(data['password'])

    db.session.commit()
    return jsonify({'message': 'Motorista atualizado com sucesso', 'driver': driver.to_dict()}), 200


@admin_bp.route('/drivers/<int:driver_id>', methods=['DELETE'])
@admin_required
def delete_driver(driver_id):
    driver = db.session.get(Driver, driver_id)
    if not driver:
        return jsonify({'error': 'Motorista não encontrado'}), 404
    db.session.delete(driver)
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
        linked_driver = Driver.query.filter_by(bus_line=route_line_str).first() if route_line_str else None
        linked_vehicle = Vehicle.query.filter_by(bus_line=route_line_str).first() if route_line_str else None

        result.append({
            'id': r.id,
            'route_name': r.route_name,
            'origin_lat': r.origin_lat,
            'origin_lon': r.origin_lon,
            'destination_lat': r.destination_lat,
            'destination_lon': r.destination_lon,
            'stop_count': len(stops),
            'stops': [s.to_dict() for s in stops],
            'driver': {'id': linked_driver.id, 'name': linked_driver.name, 'code': linked_driver.code} if linked_driver else None,
            'vehicle': {'id': linked_vehicle.id, 'plate': linked_vehicle.plate, 'model': linked_vehicle.model} if linked_vehicle else None,
        })
    return jsonify(result)


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
        driver = db.session.get(Driver, int(data['driver_id']))
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
    db.session.commit()

    return jsonify({'message': f'Linha {data["route_number"]} criada com sucesso', 'route_id': rt.id}), 201
