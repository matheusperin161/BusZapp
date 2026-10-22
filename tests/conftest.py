import pytest
from werkzeug.security import generate_password_hash

from src.main import create_app
from src.models import db
from src.models.user import User, Vehicle, BusRoute
from src.models.tracking import Route, StopPoint


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def criar_usuario(email, role='user', senha='senha123'):
    user = User(username=email.split('@')[0], email=email, password=generate_password_hash(senha),
                role=role, email_verified=True)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, email, senha='senha123'):
    res = client.post('/api/auth/login', json={'email': email, 'password': senha})
    assert res.status_code == 200, res.get_json()
    return res


@pytest.fixture
def admin(app, client):
    criar_usuario('admin@teste.com', role='admin')
    login(client, 'admin@teste.com')
    return client


@pytest.fixture
def linha(app):
    """Linha 1 com 3 paradas em linha reta (~1,1 km entre elas), 4 min por trecho."""
    db.session.add(BusRoute(route_number='1', route_name='Centro - Bairro', origin='Centro',
                            destination='Bairro', fare=4.5))
    route = Route(route_name='Linha_1', origin_lat=-27.0, origin_lon=-52.0,
                  destination_lat=-27.02, destination_lon=-52.0)
    db.session.add(route)
    db.session.flush()
    for ordem, lat in enumerate((-27.0, -27.01, -27.02), start=1):
        db.session.add(StopPoint(route_id=route.id, name=f'Parada {ordem}', latitude=lat,
                                 longitude=-52.0, order=ordem, tempo_ate_proxima_min=4))
    db.session.commit()
    return route


@pytest.fixture
def veiculos(app):
    lista = [
        Vehicle(plate='AAA1A11', model='Apache', brand='Caio', year=2020, capacity=40, status='ativo'),
        Vehicle(plate='BBB2B22', model='Apache', brand='Caio', year=2020, capacity=40, status='ativo'),
        Vehicle(plate='CCC3C33', model='Apache', brand='Caio', year=2020, capacity=40, status='manutencao'),
    ]
    db.session.add_all(lista)
    db.session.commit()
    return lista
