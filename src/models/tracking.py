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
    active = db.Column(db.Boolean, default=True, server_default=db.true(), nullable=False)

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
            'active': self.active,
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
    # Tempo estimado (min) até a parada seguinte, no sentido de ida
    tempo_ate_proxima_min = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'<StopPoint {self.name} order={self.order}>'

    def to_dict(self, eta_minutes=None):
        result = {
            'id': self.id,
            'name': self.name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'order': self.order,
            'tempo_ate_proxima_min': self.tempo_ate_proxima_min,
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


SENTIDOS = ('ida', 'volta')
VIAGEM_STATUSES = ('planejada', 'em_andamento', 'finalizada', 'cancelada')


class Viagem(db.Model):
    """Viagem de um motorista com um veículo numa linha (RF de rastreamento)."""
    __tablename__ = 'viagens'
    __table_args__ = (
        # Garante no banco: no máximo uma viagem em_andamento por motorista e por veículo
        db.Index('uq_viagem_ativa_motorista', 'motorista_id', unique=True,
                 postgresql_where=db.text("status = 'em_andamento'"),
                 sqlite_where=db.text("status = 'em_andamento'")),
        db.Index('uq_viagem_ativa_veiculo', 'veiculo_id', unique=True,
                 postgresql_where=db.text("status = 'em_andamento'"),
                 sqlite_where=db.text("status = 'em_andamento'")),
    )

    id            = db.Column(db.Integer, primary_key=True)
    linha_id      = db.Column(db.Integer, db.ForeignKey('route.id'), nullable=False, index=True)
    veiculo_id    = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    motorista_id  = db.Column(db.Integer, db.ForeignKey('motoristas.id'), nullable=False)
    sentido       = db.Column(db.String(5), nullable=False)    # ida | volta
    status        = db.Column(db.String(12), default='planejada', nullable=False, index=True)
    iniciada_em   = db.Column(db.DateTime, nullable=True)
    finalizada_em = db.Column(db.DateTime, nullable=True)

    linha     = db.relationship('Route')
    veiculo   = db.relationship('Vehicle')
    motorista = db.relationship('Motorista', backref=db.backref('viagens', lazy='dynamic'))
    posicoes  = db.relationship('Posicao', backref='viagem', lazy='dynamic',
                                order_by='Posicao.registrado_em', cascade='all, delete-orphan')

    def ultima_posicao(self):
        return self.posicoes.order_by(None).order_by(Posicao.registrado_em.desc()).first()

    def to_dict(self):
        return {
            'id': self.id,
            'linha_id': self.linha_id,
            'veiculo_id': self.veiculo_id,
            'motorista_id': self.motorista_id,
            'sentido': self.sentido,
            'status': self.status,
            'iniciada_em': self.iniciada_em.isoformat() if self.iniciada_em else None,
            'finalizada_em': self.finalizada_em.isoformat() if self.finalizada_em else None,
            'veiculo': {'id': self.veiculo.id, 'plate': self.veiculo.plate, 'model': self.veiculo.model} if self.veiculo else None,
            'motorista': {'id': self.motorista.id, 'nome': self.motorista.nome} if self.motorista else None,
        }


class Posicao(db.Model):
    """Posição GPS enviada pelo app do motorista durante a viagem."""
    __tablename__ = 'posicoes'
    __table_args__ = (db.Index('ix_posicoes_viagem_registro', 'viagem_id', 'registrado_em'),)

    id            = db.Column(db.Integer, primary_key=True)
    viagem_id     = db.Column(db.Integer, db.ForeignKey('viagens.id', ondelete='CASCADE'), nullable=False)
    latitude      = db.Column(db.Float, nullable=False)
    longitude     = db.Column(db.Float, nullable=False)
    velocidade    = db.Column(db.Float, nullable=True)   # km/h
    registrado_em = db.Column(db.DateTime, nullable=False)  # hora do dispositivo (UTC)

    def to_dict(self):
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'velocidade': self.velocidade,
            'registrado_em': self.registrado_em.isoformat() if self.registrado_em else None,
        }
