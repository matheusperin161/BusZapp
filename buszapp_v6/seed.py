import sys, os
sys.path.insert(0, os.path.dirname(__file__))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ['DATABASE_URL'] = f"sqlite:///{os.path.join(BASE_DIR, 'src', 'instance', 'app.db')}"

from src.main import create_app
from src.models import db
from src.models.user import User, BusRoute, BusLocation
from src.models.tracking import Route, StopPoint
from werkzeug.security import generate_password_hash

app = create_app()

# Paradas reais de Chapecó por linha
ROUTES_DATA = [
    {
        'route_number': '1',
        'route_name': 'Centro - Zona Norte',
        'origin': 'Terminal Central',
        'destination': 'Bairro Cristo Rei',
        'fare': 4.50,
        'origin_lat': -27.10597, 'origin_lon': -52.61336,
        'dest_lat': -27.08012, 'dest_lon': -52.61850,
        'stops': [
            ('Terminal Central',         -27.10597, -52.61336, 1),
            ('Av. Getúlio Vargas / Cel. Bertaso', -27.10280, -52.61490, 2),
            ('Praça Coronel Bertaso',    -27.09980, -52.61620, 3),
            ('Rua Marechal Deodoro',     -27.09650, -52.61710, 4),
            ('UNOCHAPECÓ',               -27.09310, -52.61800, 5),
            ('Av. Plínio de Nes',        -27.08980, -52.61820, 6),
            ('Bairro São Pedro',         -27.08620, -52.61830, 7),
            ('Cristo Rei - Final',       -27.08012, -52.61850, 8),
        ],
    },
    {
        'route_number': '2',
        'route_name': 'Centro - Efapi',
        'origin': 'Terminal Central',
        'destination': 'Bairro Efapi',
        'fare': 4.50,
        'origin_lat': -27.10597, 'origin_lon': -52.61336,
        'dest_lat': -27.10890, 'dest_lon': -52.64500,
        'stops': [
            ('Terminal Central',         -27.10597, -52.61336, 1),
            ('Av. Getúlio Vargas',        -27.10600, -52.62100, 2),
            ('Rua Uruguai / Av. Atílio Fontana', -27.10610, -52.62800, 3),
            ('UNOCHAPECÓ - Sede',        -27.10600, -52.63200, 4),
            ('Av. Atílio Fontana / Dom Pedro', -27.10650, -52.63700, 5),
            ('Bairro Efapi - Centro',    -27.10750, -52.64100, 6),
            ('Efapi - Final',            -27.10890, -52.64500, 7),
        ],
    },
    {
        'route_number': '3',
        'route_name': 'Circular Centro',
        'origin': 'Terminal Central',
        'destination': 'Terminal Central',
        'fare': 3.50,
        'origin_lat': -27.10597, 'origin_lon': -52.61336,
        'dest_lat':   -27.10597, 'dest_lon': -52.61336,
        'stops': [
            ('Terminal Central',         -27.10597, -52.61336, 1),
            ('Av. Nereu Ramos / XV de Nov.', -27.10400, -52.61500, 2),
            ('Praça Rui Barbosa',        -27.10200, -52.61650, 3),
            ('Av. Marechal Bormann',     -27.10350, -52.61900, 4),
            ('Shopping Pátio Chapecó',   -27.10550, -52.62050, 5),
            ('Av. Getúlio Vargas',       -27.10600, -52.61700, 6),
            ('Terminal Central',         -27.10597, -52.61336, 7),
        ],
    },
    {
        'route_number': '4',
        'route_name': 'Centro - Engenho Braun',
        'origin': 'Terminal Central',
        'destination': 'Engenho Braun',
        'fare': 4.50,
        'origin_lat': -27.10597, 'origin_lon': -52.61336,
        'dest_lat': -27.11500, 'dest_lon': -52.65200,
        'stops': [
            ('Terminal Central',         -27.10597, -52.61336, 1),
            ('Rua Barão do Rio Branco',  -27.10800, -52.61900, 2),
            ('Av. São Pedro',            -27.11000, -52.62500, 3),
            ('Parque das Palmeiras',     -27.11200, -52.63200, 4),
            ('Frigorifico Aurora',       -27.11350, -52.63900, 5),
            ('Engenho Braun - Entrada',  -27.11420, -52.64500, 6),
            ('Engenho Braun - Final',    -27.11500, -52.65200, 7),
        ],
    },
    {
        'route_number': '5',
        'route_name': 'Centro - Jardim América',
        'origin': 'Terminal Central',
        'destination': 'Jardim América',
        'fare': 4.50,
        'origin_lat': -27.10597, 'origin_lon': -52.61336,
        'dest_lat': -27.11800, 'dest_lon': -52.62500,
        'stops': [
            ('Terminal Central',         -27.10597, -52.61336, 1),
            ('Av. Nereu Ramos',          -27.10750, -52.61500, 2),
            ('Rua Otília Daros',         -27.10950, -52.61600, 3),
            ('Av. São Pedro / Bertaso',  -27.11200, -52.61900, 4),
            ('Jardim América - Entrada', -27.11500, -52.62100, 5),
            ('Jardim América - Final',   -27.11800, -52.62500, 6),
        ],
    },
]

with app.app_context():
    db.create_all()

    # Admin
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(
            username='admin', email='admin@buszapp.com',
            password=generate_password_hash('admin123'),
            role='admin', card_balance=100.0
        ))
        print('✓ Admin criado')
    else:
        print('! Admin já existe')

    # Rotas
    for rd in ROUTES_DATA:
        br = BusRoute.query.filter_by(route_number=rd['route_number']).first()
        if not br:
            br = BusRoute(
                route_number=rd['route_number'],
                route_name=rd['route_name'],
                origin=rd['origin'],
                destination=rd['destination'],
                fare=rd['fare'],
            )
            db.session.add(br)
            db.session.flush()
            db.session.add(BusLocation(
                route_id=br.id,
                bus_number=f"{rd['route_number']}01",
                latitude=rd['origin_lat'],
                longitude=rd['origin_lon'],
            ))

        route_name = f"Linha_{rd['route_number']}"
        rt = Route.query.filter_by(route_name=route_name).first()
        if not rt:
            rt = Route(
                route_name=route_name,
                origin_lat=rd['origin_lat'], origin_lon=rd['origin_lon'],
                destination_lat=rd['dest_lat'], destination_lon=rd['dest_lon'],
            )
            db.session.add(rt)
            db.session.flush()
            for name, lat, lng, order in rd['stops']:
                db.session.add(StopPoint(route_id=rt.id, name=name, latitude=lat, longitude=lng, order=order))
            print(f"✓ Linha {rd['route_number']} — {len(rd['stops'])} paradas criadas")
        else:
            print(f"! Linha {rd['route_number']} já existe")

    db.session.commit()
    print('\n✅ Banco populado! Login: admin / admin123')
