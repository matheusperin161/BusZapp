"""Real-time bus tracking routes and Socket.IO handlers."""
from datetime import datetime
from flask import Blueprint, jsonify, request

from src.models import db
from src.models.user import BusLocation
from src.models.tracking import Route, StopPoint, BusSchedule
from src.utils.geo import calculate_speed, find_next_stops_with_eta
from src.config import GOOGLE_API_KEY

tracking_bp = Blueprint('tracking', __name__, url_prefix='/api')

_socketio = None


def set_socketio(socket_instance):
    global _socketio
    _socketio = socket_instance


def register_socketio_handlers(socket_instance):
    socket_instance.on_event('connect', lambda: print('Client connected'), namespace='/tracking')
    socket_instance.on_event('disconnect', lambda: print('Client disconnected'), namespace='/tracking')


def _get_route_by_number(route_number: str) -> Route | None:
    """Fetch route by its route_number string (e.g. '1', '2')."""
    return Route.query.filter_by(route_name=f'Linha_{route_number}').first()


@tracking_bp.route('/update_location', methods=['POST'])
def update_location():
    data = request.get_json() or {}
    if not all(k in data for k in ('bus_id', 'latitude', 'longitude')):
        return jsonify({'error': 'bus_id, latitude e longitude são obrigatórios'}), 400

    bus_location = BusLocation.query.filter_by(bus_id=data['bus_id']).first()
    speed_kmh = 0.0

    if bus_location:
        time_diff = (datetime.utcnow() - bus_location.timestamp).total_seconds()
        if time_diff > 0:
            speed_kmh = calculate_speed(
                bus_location.latitude, bus_location.longitude,
                data['latitude'], data['longitude'], time_diff)
        bus_location.latitude = data['latitude']
        bus_location.longitude = data['longitude']
        bus_location.speed = speed_kmh
    else:
        # Try to find route by bus_id prefix
        bus_id_str = str(data['bus_id'])
        route = None
        for rn in ['1', '2', '3', '4', '5']:
            if bus_id_str.startswith(rn):
                route = _get_route_by_number(rn)
                if route:
                    break
        bus_location = BusLocation(
            bus_id=data['bus_id'],
            route_id=route.id if route else None,
            bus_number=data.get('bus_number', 'N/A'),
            latitude=data['latitude'],
            longitude=data['longitude'],
            speed=speed_kmh,
        )
        db.session.add(bus_location)

    db.session.commit()

    # Find which route this bus belongs to via schedule
    schedule = BusSchedule.query.filter_by(bus_id=data['bus_id']).first()
    route = None
    if schedule:
        route = db.session.get(Route, schedule.route_id)
    elif bus_location.route_id:
        route = db.session.get(Route, bus_location.route_id)

    if route and _socketio:
        stops = find_next_stops_with_eta(
            data['latitude'], data['longitude'],
            speed_kmh if speed_kmh > 0 else 30.0, route)
        location_data = bus_location.to_dict()
        if stops:
            first = stops[0]
            location_data['next_stop'] = first['stop'].to_dict(eta_minutes=first['eta_minutes'])
            location_data['distance_to_stop'] = first['distance_meters']
        _socketio.emit('location_update', location_data, namespace='/tracking')

    return jsonify({'success': True, 'data': bus_location.to_dict()}), 200


@tracking_bp.route('/route/<route_number>', methods=['GET'])
def get_route(route_number):
    """Return stop points for a given route_number string."""
    route = _get_route_by_number(str(route_number))
    if not route:
        return jsonify({'error': f'Rota {route_number} não encontrada. Rode o seed.py.'}), 404

    stop_points = [sp.to_dict() for sp in sorted(route.stop_points, key=lambda sp: sp.order)]
    return jsonify({'stop_points': stop_points, 'route_id': route.id}), 200


@tracking_bp.route('/route/<int:route_number>/schedules', methods=['GET'])
def get_schedules(route_number):
    route = _get_route_by_number(str(route_number))
    if not route:
        return jsonify([]), 200

    schedules = BusSchedule.query.filter_by(route_id=route.id, active=True)\
        .order_by(BusSchedule.departure_time).all()

    if not schedules:
        defaults = [
            ('06:00', f'{route_number}01', int(f'{route_number}101'), 'Manhã'),
            ('07:30', f'{route_number}02', int(f'{route_number}102'), 'Manhã'),
            ('09:00', f'{route_number}03', int(f'{route_number}103'), 'Manhã'),
            ('12:00', f'{route_number}04', int(f'{route_number}104'), 'Tarde'),
            ('14:30', f'{route_number}05', int(f'{route_number}105'), 'Tarde'),
            ('17:00', f'{route_number}06', int(f'{route_number}106'), 'Tarde'),
            ('18:30', f'{route_number}07', int(f'{route_number}107'), 'Noite'),
            ('20:00', f'{route_number}08', int(f'{route_number}108'), 'Noite'),
        ]
        for dep, bnum, bid, period in defaults:
            db.session.add(BusSchedule(
                route_id=route.id,
                departure_time=dep,
                bus_number=bnum,
                bus_id=bid,
                period=period,
            ))
        db.session.commit()
        schedules = BusSchedule.query.filter_by(route_id=route.id, active=True)\
            .order_by(BusSchedule.departure_time).all()

    return jsonify([s.to_dict() for s in schedules])
