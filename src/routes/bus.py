"""Bus routes, notifications, and ratings."""
from datetime import datetime
from flask import Blueprint, jsonify, request, session
from sqlalchemy import func

from src.models import db
from src.models.user import BusRoute, BusLocation, Notification, Rating
from src.utils.auth import login_required

bus_bp = Blueprint('bus', __name__, url_prefix='/api')


# ── Bus Routes ──────────────────────────────────────────────────────────────

@bus_bp.route('/routes', methods=['GET'])
def get_bus_routes():
    routes = BusRoute.query.filter_by(active=True).all()
    return jsonify([r.to_dict() for r in routes])


@bus_bp.route('/bus-locations/<int:route_id>', methods=['GET'])
def get_bus_locations(route_id):
    locations = BusLocation.query.filter_by(route_id=route_id).all()
    return jsonify([loc.to_dict() for loc in locations])


@bus_bp.route('/admin/populate-routes', methods=['POST'])
def populate_routes():
    if BusRoute.query.count() > 0:
        return jsonify({'message': 'Rotas já existem no banco de dados'}), 200

    sample_routes = [
        BusRoute(route_number='001', route_name='Centro - Zona Norte', origin='Centro', destination='Zona Norte', fare=4.50),
        BusRoute(route_number='002', route_name='Centro - Zona Sul', origin='Centro', destination='Zona Sul', fare=4.50),
        BusRoute(route_number='003', route_name='Zona Leste - Centro', origin='Zona Leste', destination='Centro', fare=4.50),
        BusRoute(route_number='004', route_name='Zona Oeste - Centro', origin='Zona Oeste', destination='Centro', fare=4.50),
        BusRoute(route_number='005', route_name='Circular Shopping', origin='Terminal Central', destination='Shopping Center', fare=3.50),
    ]
    db.session.add_all(sample_routes)
    db.session.flush()

    sample_locations = [
        BusLocation(route_id=sample_routes[0].id, bus_number='1001', latitude=-23.5505, longitude=-46.6333),
        BusLocation(route_id=sample_routes[0].id, bus_number='1002', latitude=-23.5515, longitude=-46.6343),
        BusLocation(route_id=sample_routes[1].id, bus_number='2001', latitude=-23.5525, longitude=-46.6353),
        BusLocation(route_id=sample_routes[1].id, bus_number='2002', latitude=-23.5535, longitude=-46.6363),
        BusLocation(route_id=sample_routes[2].id, bus_number='3001', latitude=-23.5545, longitude=-46.6373),
    ]
    db.session.add_all(sample_locations)
    db.session.commit()

    return jsonify({'message': 'Rotas e localizações criadas com sucesso'}), 201


# ── Notifications ────────────────────────────────────────────────────────────

@bus_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    notifications = (
        Notification.query
        .filter_by(user_id=session['user_id'])
        .order_by(Notification.created_at.desc())
        .all()
    )
    return jsonify([n.to_dict() for n in notifications])


# ── Ratings ──────────────────────────────────────────────────────────────────

@bus_bp.route('/submit-rating', methods=['POST'])
@login_required
def submit_rating():
    data = request.get_json() or {}
    overall_rating = data.get('overall_rating')

    if not overall_rating or not (1 <= int(overall_rating) <= 5):
        return jsonify({'error': 'Avaliação geral é obrigatória e deve estar entre 1 e 5'}), 400

    sub_ratings = {
        'punctuality_rating': data.get('punctuality_rating', 0),
        'cleanliness_rating': data.get('cleanliness_rating', 0),
        'comfort_rating': data.get('comfort_rating', 0),
        'service_rating': data.get('service_rating', 0),
    }
    for key, val in sub_ratings.items():
        if not (0 <= int(val) <= 5):
            return jsonify({'error': 'Todas as avaliações devem estar entre 0 e 5'}), 400

    trip_date = None
    trip_time = None
    if data.get('trip_date'):
        try:
            trip_date = datetime.strptime(data['trip_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de data inválido. Use YYYY-MM-DD'}), 400
    if data.get('trip_time'):
        try:
            trip_time = datetime.strptime(data['trip_time'], '%H:%M').time()
        except ValueError:
            return jsonify({'error': 'Formato de hora inválido. Use HH:MM'}), 400

    rating = Rating(
        user_id=session['user_id'],
        overall_rating=int(overall_rating),
        **{k: int(v) for k, v in sub_ratings.items()},
        comments=data.get('comments', ''),
        bus_line=data.get('bus_line', ''),
        trip_date=trip_date,
        trip_time=trip_time,
    )

    try:
        db.session.add(rating)
        db.session.commit()
        return jsonify({'message': 'Avaliação enviada com sucesso', 'rating': rating.to_dict()}), 201
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro ao salvar avaliação'}), 500


@bus_bp.route('/ratings', methods=['GET'])
@login_required
def get_user_ratings():
    ratings = (
        Rating.query
        .filter_by(user_id=session['user_id'])
        .order_by(Rating.created_at.desc())
        .all()
    )
    return jsonify([r.to_dict() for r in ratings])


@bus_bp.route('/ratings/stats', methods=['GET'])
def get_ratings_stats():
    total = Rating.query.count()
    if total == 0:
        return jsonify({k: 0 for k in [
            'total_ratings', 'average_overall', 'average_punctuality',
            'average_cleanliness', 'average_comfort', 'average_service',
        ]})

    avgs = db.session.query(
        func.avg(Rating.overall_rating).label('overall'),
        func.avg(Rating.punctuality_rating).label('punctuality'),
        func.avg(Rating.cleanliness_rating).label('cleanliness'),
        func.avg(Rating.comfort_rating).label('comfort'),
        func.avg(Rating.service_rating).label('service'),
    ).first()

    return jsonify({
        'total_ratings': total,
        'average_overall': round(avgs.overall or 0, 2),
        'average_punctuality': round(avgs.punctuality or 0, 2),
        'average_cleanliness': round(avgs.cleanliness or 0, 2),
        'average_comfort': round(avgs.comfort or 0, 2),
        'average_service': round(avgs.service or 0, 2),
    })
