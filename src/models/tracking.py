from datetime import datetime
from src.models import db


class Route(db.Model):
    __tablename__ = 'route'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    route_name = db.Column(db.String(120), unique=True, nullable=False)
    origin_lat = db.Column(db.Float, nullable=False)
    origin_lon = db.Column(db.Float, nullable=False)
    destination_lat = db.Column(db.Float, nullable=False)
    destination_lon = db.Column(db.Float, nullable=False)
    polyline = db.Column(db.Text, nullable=True)

    stop_points = db.relationship('StopPoint', backref='route', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Route {self.route_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'route_name': self.route_name,
            'origin': f'{self.origin_lat},{self.origin_lon}',
            'destination': f'{self.destination_lat},{self.destination_lon}',
            'polyline': self.polyline,
        }


class StopPoint(db.Model):
    __tablename__ = 'stop_point'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('route.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    order = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<StopPoint {self.name} order={self.order}>'

    def to_dict(self, eta_minutes=None):
        result = {
            'id': self.id,
            'name': self.name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'order': self.order,
        }
        if eta_minutes is not None:
            result['eta_minutes'] = eta_minutes
        return result


class BusSchedule(db.Model):
    """Horário de saída de um ônibus numa rota."""
    __tablename__ = 'bus_schedule'

    id            = db.Column(db.Integer, primary_key=True)
    route_id      = db.Column(db.Integer, db.ForeignKey('route.id', ondelete='CASCADE'), nullable=False)
    departure_time = db.Column(db.String(5), nullable=False)   # "06:30"
    bus_number    = db.Column(db.String(20), nullable=False)
    bus_id        = db.Column(db.Integer, nullable=False, index=True)  # usado no Socket.IO
    period        = db.Column(db.String(20), nullable=True)   # "Manhã", "Tarde", "Noite"
    active        = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'route_id': self.route_id,
            'departure_time': self.departure_time,
            'bus_number': self.bus_number,
            'bus_id': self.bus_id,
            'period': self.period,
            'active': self.active,
        }
