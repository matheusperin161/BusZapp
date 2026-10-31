"""Cartão de transporte (CA06): app em /api/cartoes e telas web em /api/card, /api/recharge..."""
import pytest

from src.models import db
from src.models.user import BusRoute
from tests.conftest import criar_usuario, login


@pytest.fixture
def ana(app, client):
    criar_usuario('ana@teste.com')
    login(client, 'ana@teste.com')
    return client


def cadastrar(client, numero='12345678', **extra):
    return client.post('/api/cartoes', json={'numero': numero, **extra})


def test_cadastro_e_listagem(ana):
    assert ana.get('/api/cartoes').get_json() == []
    res = cadastrar(ana, '1234 5678 9012', titular='Ana', tipo='estudante')
    assert res.status_code == 201
    cartao = res.get_json()
    assert cartao['numero'] == '123456789012' and cartao['saldo_centavos'] == 0 and cartao['status'] == 'ativo'
    assert [c['id'] for c in ana.get('/api/cartoes').get_json()] == [cartao['id']]


def test_validacoes_de_cadastro(ana):
    assert cadastrar(ana, '1234').status_code == 400
    assert cadastrar(ana, tipo='vip').status_code == 400
    assert cadastrar(ana).status_code == 201
    assert cadastrar(ana, '87654321').status_code == 409  # um cartão por usuário


def test_numero_unico_e_dono(ana, app):
    cartao = cadastrar(ana).get_json()
    outro = app.test_client()
    criar_usuario('bia@teste.com')
    login(outro, 'bia@teste.com')
    assert cadastrar(outro).status_code == 409
    assert outro.get(f'/api/cartoes/{cartao["id"]}').status_code == 403
    assert outro.post(f'/api/cartoes/{cartao["id"]}/recarga', json={'valor_centavos': 100}).status_code == 403
    assert outro.get('/api/cartoes/999').status_code == 404


def test_recarga_extrato_e_bloqueio(ana):
    cid = cadastrar(ana).get_json()['id']
    assert ana.post(f'/api/cartoes/{cid}/recarga', json={'valor_centavos': 4.5}).status_code == 400
    res = ana.post(f'/api/cartoes/{cid}/recarga', json={'valor_centavos': 1050, 'payment_method': 'pix'})
    assert res.status_code == 201 and res.get_json()['cartao']['saldo_centavos'] == 1050
    extrato = ana.get(f'/api/cartoes/{cid}/transacoes').get_json()
    assert extrato['total'] == 1 and extrato['itens'][0]['amount'] == 10.5

    assert ana.post(f'/api/cartoes/{cid}/bloquear').status_code == 200
    assert ana.post(f'/api/cartoes/{cid}/bloquear').status_code == 409
    assert ana.post(f'/api/cartoes/{cid}/recarga', json={'valor_centavos': 100}).status_code == 409
    assert ana.post('/api/recharge', json={'amount': 5, 'payment_method': 'pix'}).status_code == 409


def test_web_e_app_veem_o_mesmo_cartao(ana):
    # web: recarrega antes de cadastrar o cartão (como já acontecia)
    assert ana.post('/api/recharge', json={'amount': 10, 'payment_method': 'pix'}).status_code == 200
    assert ana.get('/api/balance').get_json() == {'balance': 10.0}
    # app: cadastra o número no mesmo cartão e mantém o saldo
    cartao = cadastrar(ana).get_json()
    assert cartao['saldo_centavos'] == 1000
    # web enxerga o cadastro feito pelo app e não deixa cadastrar outro
    info = ana.get('/api/card/info').get_json()
    assert info['card_number'] == '12345678' and info['card_balance'] == 10.0
    res = ana.post('/api/card/register', json={'card_number': '99999999', 'holder_name': 'Ana', 'card_type': 'normal'})
    assert res.status_code == 409
    assert ana.get('/api/auth/profile').get_json()['card_balance'] == 10.0


def test_cadastro_pelo_web(ana):
    res = ana.post('/api/card/register', json={'card_number': '111.222', 'holder_name': 'Ana', 'card_type': 'idoso'})
    assert res.status_code == 200
    assert ana.get('/api/cartoes').get_json()[0]['tipo'] == 'idoso'


def test_uso_do_transporte_debita_sem_negativar(ana):
    db.session.add(BusRoute(route_number='1', route_name='Centro', origin='A', destination='B', fare=4.5))
    db.session.commit()
    rota = BusRoute.query.first()
    assert ana.post('/api/use-transport', json={'route_id': rota.id}).status_code == 400  # sem cartão
    ana.post('/api/recharge', json={'amount': 5, 'payment_method': 'pix'})
    res = ana.post('/api/use-transport', json={'route_id': rota.id})
    assert res.status_code == 200 and res.get_json()['new_balance'] == 0.5
    assert ana.post('/api/use-transport', json={'route_id': rota.id}).status_code == 400
    tipos = [t['transaction_type'] for t in ana.get('/api/transactions').get_json()]
    assert sorted(tipos) == ['recharge', 'usage']


def test_admin_lista_e_ajusta(ana, app):
    cadastrar(ana)
    adm = app.test_client()
    criar_usuario('admin@teste.com', role='admin')
    login(adm, 'admin@teste.com')
    assert ana.get('/api/admin/cartoes').status_code == 403
    lista = adm.get('/api/admin/cartoes?status=ativo').get_json()
    assert len(lista) == 1 and lista[0]['usuario']['email'] == 'ana@teste.com'

    usuario = lista[0]['usuario']['id']
    assert adm.put(f'/api/admin/users/{usuario}/card', json={'card_balance': 3}).status_code == 200
    assert adm.get('/api/admin/users/cards').get_json()[0]['card_balance'] == 3.0
    ajuste = ana.get('/api/transactions').get_json()[0]
    assert ajuste['transaction_type'] == 'ajuste' and ajuste['amount'] == 3.0
