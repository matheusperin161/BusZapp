"""RF23 — gestão de motoristas (CA02.1 a CA02.7)."""
from datetime import date, timedelta

from src.models import db
from src.models.user import User, Motorista
from src.utils.cpf import cpf_valido
from tests.conftest import criar_usuario, login

CPF_A = '529.982.247-25'
CPF_B = '111.444.777-35'


def payload(**extra):
    base = {
        'nome': 'João da Silva',
        'cpf': CPF_A,
        'cnh_numero': '12345678900',
        'cnh_categoria': 'D',
        'cnh_validade': (date.today() + timedelta(days=365)).isoformat(),
        'telefone': '(49) 99999-0000',
        'email': 'joao@teste.com',
        'senha': 'segredo1',
    }
    base.update(extra)
    return base


def test_cpf_digito_verificador():
    assert cpf_valido(CPF_A)
    assert cpf_valido('11144477735')
    assert not cpf_valido('529.982.247-26')
    assert not cpf_valido('111.111.111-11')
    assert not cpf_valido('123')


def test_ca02_1_somente_admin(client, app):
    assert client.get('/api/admin/drivers').status_code == 401
    criar_usuario('passageiro@teste.com')
    login(client, 'passageiro@teste.com')
    assert client.get('/api/admin/drivers').status_code == 403
    assert client.post('/api/admin/drivers', json=payload()).status_code == 403


def test_ca02_2_campos_obrigatorios_e_cpf(admin):
    for campo in ('nome', 'cpf', 'cnh_numero', 'cnh_categoria', 'cnh_validade'):
        res = admin.post('/api/admin/drivers', json=payload(**{campo: ''}))
        assert res.status_code == 400, campo
    res = admin.post('/api/admin/drivers', json=payload(cpf='529.982.247-26'))
    assert res.status_code == 400
    assert res.get_json()['error'] == 'CPF inválido'


def test_ca02_3_cpf_ou_cnh_duplicados(admin):
    assert admin.post('/api/admin/drivers', json=payload()).status_code == 201
    res = admin.post('/api/admin/drivers', json=payload(cnh_numero='999', email='outro@teste.com'))
    assert res.status_code == 409 and 'CPF' in res.get_json()['error']
    res = admin.post('/api/admin/drivers', json=payload(cpf=CPF_B, email='outro@teste.com'))
    assert res.status_code == 409 and 'CNH' in res.get_json()['error']


def test_ca02_4_cria_usuario_motorista_que_consegue_logar(admin, client):
    res = admin.post('/api/admin/drivers', json=payload())
    assert res.status_code == 201
    motorista = db.session.get(Motorista, res.get_json()['driver']['id'])
    usuario = db.session.get(User, motorista.usuario_id)
    assert usuario.role == 'motorista' and usuario.email == 'joao@teste.com'
    assert motorista.cpf == '52998224725'

    client.post('/api/auth/logout')
    res = client.post('/api/auth/login', json={'email': 'joao@teste.com', 'password': 'segredo1'})
    assert res.status_code == 200
    assert res.get_json()['role'] == 'motorista'
    # motorista não acessa o módulo de admin
    assert client.get('/api/admin/drivers').status_code == 403


def test_ca02_5_cnh_vencida_cadastra_e_sinaliza(admin):
    vencida = (date.today() - timedelta(days=1)).isoformat()
    res = admin.post('/api/admin/drivers', json=payload(cnh_validade=vencida))
    assert res.status_code == 201
    lista = admin.get('/api/admin/drivers').get_json()
    assert lista[0]['cnh_vencida'] is True


def test_ca02_6_nao_exclui_com_viagem_em_andamento(admin, client, linha, veiculos):
    driver_id = admin.post('/api/admin/drivers', json=payload()).get_json()['driver']['id']
    client.post('/api/auth/logout')
    login(client, 'joao@teste.com', 'segredo1')
    viagem = client.post('/api/viagens', json={'linha_id': linha.id, 'veiculo_id': veiculos[0].id,
                                               'sentido': 'ida'}).get_json()['viagem']

    client.post('/api/auth/logout')
    login(client, 'admin@teste.com')
    res = client.delete(f'/api/admin/drivers/{driver_id}')
    assert res.status_code == 409
    assert res.get_json()['motivo'] == 'viagem_em_andamento'
    assert 'viagem em andamento' in res.get_json()['error']

    client.post(f'/api/viagens/{viagem["id"]}/finalizar')
    res = client.delete(f'/api/admin/drivers/{driver_id}')
    assert res.status_code == 409 and res.get_json()['motivo'] == 'possui_historico'


def test_exclui_motorista_sem_viagens_remove_acesso(admin):
    driver_id = admin.post('/api/admin/drivers', json=payload()).get_json()['driver']['id']
    assert admin.delete(f'/api/admin/drivers/{driver_id}').status_code == 200
    assert User.query.filter_by(email='joao@teste.com').first() is None


def test_ca02_7_filtro_status_e_busca(admin):
    admin.post('/api/admin/drivers', json=payload())
    admin.post('/api/admin/drivers', json=payload(nome='Maria Souza', cpf=CPF_B, cnh_numero='222',
                                                  email='maria@teste.com', status='afastado'))
    nomes = lambda res: [m['nome'] for m in res.get_json()]
    assert nomes(admin.get('/api/admin/drivers?status=afastado')) == ['Maria Souza']
    assert nomes(admin.get('/api/admin/drivers?q=joão')) == ['João da Silva']
    assert nomes(admin.get('/api/admin/drivers?q=111.444')) == ['Maria Souza']
    assert nomes(admin.get('/api/admin/drivers?q=maria&status=ativo')) == []
    assert admin.get('/api/admin/drivers?status=xyz').status_code == 400


def test_edicao_mantem_unicidade(admin):
    admin.post('/api/admin/drivers', json=payload())
    maria = admin.post('/api/admin/drivers', json=payload(nome='Maria', cpf=CPF_B, cnh_numero='222',
                                                          email='maria@teste.com')).get_json()['driver']
    res = admin.put(f'/api/admin/drivers/{maria["id"]}', json=payload(nome='Maria', cnh_numero='222',
                                                                       email='maria@teste.com', senha=''))
    assert res.status_code == 409
    res = admin.put(f'/api/admin/drivers/{maria["id"]}', json=payload(nome='Maria S.', cpf=CPF_B, cnh_numero='222',
                                                                      email='maria@teste.com', senha='',
                                                                      status='inativo'))
    assert res.status_code == 200 and res.get_json()['driver']['status'] == 'inativo'
