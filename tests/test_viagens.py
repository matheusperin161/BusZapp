"""Viagens e posições (CA08.1 a CA08.10, exceto os critérios só de app)."""
from datetime import date, datetime, timedelta

import pytest

from src.models import db
from src.models.tracking import Posicao, Route, Viagem
from tests.conftest import criar_usuario, login

CPFS = ['52998224725', '11144477735']


@pytest.fixture
def motoristas(admin, client):
    for i, cpf in enumerate(CPFS):
        res = admin.post('/api/admin/drivers', json={
            'nome': f'Motorista {i}', 'cpf': cpf, 'cnh_numero': f'cnh{i}', 'cnh_categoria': 'D',
            'cnh_validade': (date.today() + timedelta(days=30)).isoformat(),
            'email': f'm{i}@teste.com', 'senha': 'segredo1',
        })
        assert res.status_code == 201
    client.post('/api/auth/logout')
    return ['m0@teste.com', 'm1@teste.com']


def como(client, email, senha='segredo1'):
    client.post('/api/auth/logout')
    login(client, email, senha)
    return client


def iniciar(client, linha, veiculo, sentido='ida'):
    return client.post('/api/viagens', json={'linha_id': linha.id, 'veiculo_id': veiculo.id, 'sentido': sentido})


def test_ca08_1_opcoes_so_ativas(client, motoristas, linha, veiculos):
    inativa = Route(route_name='Linha_9', origin_lat=0, origin_lon=0, destination_lat=0,
                    destination_lon=0, active=False)
    db.session.add(inativa)
    db.session.commit()
    como(client, motoristas[0])
    opcoes = client.get('/api/viagens/opcoes').get_json()
    assert [l['id'] for l in opcoes['linhas']] == [linha.id]
    assert opcoes['linhas'][0]['nome'] == 'Centro - Bairro'
    assert {v['plate'] for v in opcoes['veiculos']} == {'AAA1A11', 'BBB2B22'}
    # backend também recusa linha/veículo inativos
    assert iniciar(client, inativa, veiculos[0]).status_code == 422
    assert iniciar(client, linha, veiculos[2]).status_code == 422
    assert iniciar(client, linha, veiculos[0], sentido='x').status_code == 400


def test_somente_motorista_inicia(client, linha, veiculos, admin):
    assert iniciar(admin, linha, veiculos[0]).status_code == 403


def test_ca08_2_uma_viagem_ativa_por_motorista_e_veiculo(client, motoristas, linha, veiculos):
    como(client, motoristas[0])
    assert iniciar(client, linha, veiculos[0]).status_code == 201
    res = iniciar(client, linha, veiculos[1])
    assert res.status_code == 409 and 'já possui' in res.get_json()['error']

    como(client, motoristas[1])
    res = iniciar(client, linha, veiculos[0])
    assert res.status_code == 409 and 'veículo' in res.get_json()['error']
    assert iniciar(client, linha, veiculos[1]).status_code == 201


def test_indice_unico_barra_corrida(app, motoristas, linha, veiculos):
    from sqlalchemy.exc import IntegrityError
    from src.models.user import Motorista
    m = Motorista.query.first()
    for _ in range(2):
        db.session.add(Viagem(linha_id=linha.id, veiculo_id=veiculos[0].id, motorista_id=m.id,
                              sentido='ida', status='em_andamento', iniciada_em=datetime.utcnow()))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_ca08_3_e_7_posicoes_em_lote_com_horario_do_dispositivo(client, motoristas, linha, veiculos):
    como(client, motoristas[0])
    viagem = iniciar(client, linha, veiculos[0]).get_json()['viagem']
    agora = datetime.utcnow()
    lote = [
        {'latitude': -27.001, 'longitude': -52.0, 'velocidade': 30,
         'registrado_em': (agora + timedelta(seconds=10 * i)).isoformat() + 'Z'}
        for i in range(3)
    ]
    lote.append({'latitude': 999, 'longitude': 0})  # inválida
    res = client.post(f'/api/viagens/{viagem["id"]}/posicoes', json={'posicoes': lote})
    assert res.status_code == 201
    assert res.get_json() == {'aceitas': 3, 'descartadas': 1}
    # posição avulsa (sem lote) também funciona
    assert client.post(f'/api/viagens/{viagem["id"]}/posicoes',
                       json={'latitude': -27.002, 'longitude': -52.0}).status_code == 201
    assert Posicao.query.count() == 4

    como(client, motoristas[1])
    assert client.post(f'/api/viagens/{viagem["id"]}/posicoes',
                       json={'latitude': -27.0, 'longitude': -52.0}).status_code == 404


def test_ca08_5_e_6_passageiro_ve_veiculo_proxima_parada_e_eta(client, motoristas, linha, veiculos):
    como(client, motoristas[0])
    viagem = iniciar(client, linha, veiculos[0]).get_json()['viagem']
    # 3/4 do caminho entre a parada 1 (-27.00) e a 2 (-27.01) → falta 1/4 de 4 min
    client.post(f'/api/viagens/{viagem["id"]}/posicoes', json={'latitude': -27.0075, 'longitude': -52.0})

    client.post('/api/auth/logout')
    ativas = client.get(f'/api/viagens/ativas?linha_id={linha.id}').get_json()
    assert len(ativas) == 1
    prox = ativas[0]['proxima_parada']
    assert prox['name'] == 'Parada 2'
    assert prox['eta_min'] == pytest.approx(1.0, abs=0.05)
    assert ativas[0]['ultima_posicao']['latitude'] == -27.0075
    assert client.get('/api/viagens/ativas?linha_id=999').get_json() == []


def test_ca08_6_sentido_volta_inverte_paradas(client, motoristas, linha, veiculos):
    como(client, motoristas[0])
    viagem = iniciar(client, linha, veiculos[0], sentido='volta').get_json()['viagem']
    client.post(f'/api/viagens/{viagem["id"]}/posicoes', json={'latitude': -27.0075, 'longitude': -52.0})
    prox = client.get(f'/api/viagens/{viagem["id"]}').get_json()['proxima_parada']
    assert prox['name'] == 'Parada 1'
    assert prox['eta_min'] == pytest.approx(3.0, abs=0.05)


def test_ca08_8_e_9_finalizar_e_bloquear_edicao(client, motoristas, linha, veiculos):
    como(client, motoristas[0])
    viagem = iniciar(client, linha, veiculos[0]).get_json()['viagem']
    assert client.patch(f'/api/viagens/{viagem["id"]}', json={'sentido': 'volta'}).status_code == 200

    res = client.post(f'/api/viagens/{viagem["id"]}/finalizar')
    assert res.status_code == 200
    assert res.get_json()['viagem']['status'] == 'finalizada'
    assert res.get_json()['viagem']['finalizada_em'] is not None

    assert client.post(f'/api/viagens/{viagem["id"]}/posicoes',
                       json={'latitude': -27.0, 'longitude': -52.0}).status_code == 409
    res = client.patch(f'/api/viagens/{viagem["id"]}', json={'sentido': 'ida'})
    assert res.status_code == 409 and 'apenas consultada' in res.get_json()['error']
    assert client.post(f'/api/viagens/{viagem["id"]}/finalizar').status_code == 409
    assert client.get(f'/api/viagens/{viagem["id"]}').status_code == 200
    assert client.get('/api/viagens/atual').get_json() == {'viagem': None}
    # pode iniciar uma nova depois de finalizar
    assert iniciar(client, linha, veiculos[0]).status_code == 201


def test_ca08_10_admin_ve_todas_as_ativas(client, motoristas, linha, veiculos):
    como(client, motoristas[0])
    iniciar(client, linha, veiculos[0])
    como(client, motoristas[1])
    iniciar(client, linha, veiculos[1])

    assert client.get('/api/viagens/ativas').status_code == 400  # motorista precisa filtrar
    como(client, 'admin@teste.com', 'senha123')
    ativas = client.get('/api/viagens/ativas').get_json()
    assert len(ativas) == 2
    assert client.get('/api/admin/active-trips-count').get_json()['count'] == 2


def test_motorista_afastado_nao_inicia(client, motoristas, linha, veiculos):
    from src.models.user import Motorista
    Motorista.query.filter_by(cpf=CPFS[0]).update({'status': 'afastado'})
    db.session.commit()
    como(client, motoristas[0])
    assert iniciar(client, linha, veiculos[0]).status_code == 403
