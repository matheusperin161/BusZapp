from datetime import datetime
from src.models import db


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)  # 'user' | 'admin'
    card_balance = db.Column(db.Float, default=0.0, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    transactions = db.relationship('Transaction', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    ratings = db.relationship('Rating', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'card_balance': self.card_balance,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Transaction(db.Model):
    __tablename__ = 'transaction'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'recharge' | 'usage'
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Transaction {self.id}: {self.transaction_type} {self.amount}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'transaction_type': self.transaction_type,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class BusRoute(db.Model):
    __tablename__ = 'bus_route'

    id = db.Column(db.Integer, primary_key=True)
    route_number = db.Column(db.String(20), nullable=False)
    route_name = db.Column(db.String(100), nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    fare = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)

    bus_locations = db.relationship('BusLocation', backref='bus_route', lazy='dynamic')

    def __repr__(self):
        return f'<BusRoute {self.route_number}: {self.route_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'route_number': self.route_number,
            'route_name': self.route_name,
            'origin': self.origin,
            'destination': self.destination,
            'fare': self.fare,
            'active': self.active,
        }


class BusLocation(db.Model):
    __tablename__ = 'bus_location'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('bus_route.id'), nullable=True)
    bus_number = db.Column(db.String(20), nullable=True)
    bus_id = db.Column(db.Integer, unique=True, nullable=True, index=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    speed = db.Column(db.Float, default=0.0, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<BusLocation {self.bus_number or self.bus_id}: {self.latitude}, {self.longitude}>'

    def to_dict(self):
        result = {
            'id': self.id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'speed': self.speed,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }
        if self.bus_id is not None:
            result['bus_id'] = self.bus_id
        if self.route_id is not None:
            result['route_id'] = self.route_id
        if self.bus_number:
            result['bus_number'] = self.bus_number
        if self.last_updated:
            result['last_updated'] = self.last_updated.isoformat()
        if self.bus_route:
            result['route'] = self.bus_route.to_dict()
        return result


class Notification(db.Model):
    __tablename__ = 'notification'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Notification {self.id}: {self.title}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'read': self.read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Driver(db.Model):
    __tablename__ = 'driver'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=True)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    cnh = db.Column(db.String(11), unique=True, nullable=False)
    bus_line = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    vehicles = db.relationship('Vehicle', backref='driver', lazy='dynamic')

    def __repr__(self):
        return f'<Driver {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'cpf': self.cpf,
            'cnh': self.cnh,
            'bus_line': self.bus_line,
            'code': self.code,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Rating(db.Model):
    __tablename__ = 'rating'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    overall_rating = db.Column(db.Integer, nullable=False)
    punctuality_rating = db.Column(db.Integer, default=0, nullable=False)
    cleanliness_rating = db.Column(db.Integer, default=0, nullable=False)
    comfort_rating = db.Column(db.Integer, default=0, nullable=False)
    service_rating = db.Column(db.Integer, default=0, nullable=False)
    comments = db.Column(db.Text)
    bus_line = db.Column(db.String(100))
    trip_date = db.Column(db.Date)
    trip_time = db.Column(db.Time)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Rating {self.id}: {self.overall_rating}★ user={self.user_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'overall_rating': self.overall_rating,
            'punctuality_rating': self.punctuality_rating,
            'cleanliness_rating': self.cleanliness_rating,
            'comfort_rating': self.comfort_rating,
            'service_rating': self.service_rating,
            'comments': self.comments,
            'bus_line': self.bus_line,
            'trip_date': self.trip_date.isoformat() if self.trip_date else None,
            'trip_time': self.trip_time.isoformat() if self.trip_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Vehicle(db.Model):
    __tablename__ = 'vehicle'

    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(10), unique=True, nullable=False, index=True)
    model = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='ativo', nullable=False)  # 'ativo' | 'inativo' | 'manutencao'
    bus_line = db.Column(db.String(100))
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    VALID_STATUSES = ('ativo', 'inativo', 'manutencao')

    def __repr__(self):
        return f'<Vehicle {self.plate} - {self.model}>'

    def to_dict(self):
        return {
            'id': self.id,
            'plate': self.plate,
            'model': self.model,
            'brand': self.brand,
            'year': self.year,
            'capacity': self.capacity,
            'status': self.status,
            'bus_line': self.bus_line,
            'driver_id': self.driver_id,
            'driver_name': self.driver.name if self.driver else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class PasswordResetToken(db.Model):
    """Token de redefinição de senha com expiração."""
    __tablename__ = 'password_reset_token'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    token      = db.Column(db.String(100), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used       = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('reset_tokens', lazy='dynamic'))

    def is_valid(self):
        return not self.used and self.expires_at > datetime.utcnow()


class DriverIncident(db.Model):
    """Ocorrência registrada pelo motorista durante o trajeto."""
    __tablename__ = 'driver_incident'

    id         = db.Column(db.Integer, primary_key=True)
    driver_id  = db.Column(db.Integer, db.ForeignKey('driver.id', ondelete='CASCADE'), nullable=False)
    bus_number = db.Column(db.String(20), nullable=True)
    route_id   = db.Column(db.Integer, db.ForeignKey('bus_route.id'), nullable=True)
    type       = db.Column(db.String(30), nullable=False)  # 'atraso' | 'pane' | 'acidente' | 'outro'
    description = db.Column(db.Text, nullable=True)
    status     = db.Column(db.String(20), default='aberto', nullable=False)  # 'aberto' | 'resolvido'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    driver = db.relationship('Driver', backref=db.backref('incidents', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'driver_name': self.driver.name if self.driver else None,
            'bus_number': self.bus_number,
            'route_id': self.route_id,
            'type': self.type,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class EmailVerificationToken(db.Model):
    """Token de verificação de e-mail para novos cadastros."""
    __tablename__ = 'email_verification_token'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    token      = db.Column(db.String(100), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used       = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('verification_tokens', lazy='dynamic'))

    def is_valid(self):
        return not self.used and self.expires_at > datetime.utcnow()
