"""Autenticação por token Bearer (app mobile), erros JSON e endpoints protegidos."""
from tests.conftest import criar_usuario, login


def token_de(client, email, senha='senha123'):
    res = client.post('/api/auth/login', json={'email': email, 'password': senha, 'client': 'mobile'})
    assert res.status_code == 200, res.get_json()
    return res.get_json()['token']


def bearer(token):
    return {'Authorization': f'Bearer {token}'}


def test_login_web_nao_devolve_token(client, app):
    criar_usuario('ana@teste.com')
    assert 'token' not in login(client, 'ana@teste.com').get_json()


def test_login_mobile_nao_cria_sessao(app):
    criar_usuario('ana@teste.com')
    c = app.test_client()
    token = token_de(c, 'ana@teste.com')
    assert c.get('/api/auth/profile').status_code == 401  # nenhum cookie de sessão ficou
    # logout com cookie de outra sessão e Bearer revoga o token mesmo assim
    login(c, 'ana@teste.com')
    c.post('/api/auth/logout', headers=bearer(token))
    assert app.test_client().get('/api/auth/profile', headers=bearer(token)).status_code == 401


def test_bearer_autentica_sem_cookie(app):
    criar_usuario('ana@teste.com')
    token = token_de(app.test_client(), 'ana@teste.com')
    sem_cookie = app.test_client()
    assert sem_cookie.get('/api/auth/profile').status_code == 401
    res = sem_cookie.get('/api/auth/profile', headers=bearer(token))
    assert res.status_code == 200 and res.get_json()['email'] == 'ana@teste.com'


def test_token_invalido(app):
    c = app.test_client()
    assert c.get('/api/auth/profile', headers=bearer('lixo')).status_code == 401
    assert c.get('/api/auth/profile', headers={'Authorization': 'Basic xyz'}).status_code == 401


def test_logout_e_troca_de_senha_revogam_token(app):
    criar_usuario('ana@teste.com')
    c = app.test_client()
    token = token_de(c, 'ana@teste.com')
    assert app.test_client().post('/api/auth/logout', headers=bearer(token)).status_code == 200
    assert app.test_client().get('/api/auth/profile', headers=bearer(token)).status_code == 401

    token = token_de(app.test_client(), 'ana@teste.com')
    res = app.test_client().put('/api/auth/profile', headers=bearer(token),
                                json={'username': 'ana', 'email': 'ana@teste.com', 'password': 'nova123'})
    assert res.status_code == 200
    assert app.test_client().get('/api/auth/profile', headers=bearer(token)).status_code == 401


def test_bearer_admin_e_motorista(app, admin, client):
    token = token_de(app.test_client(), 'admin@teste.com')
    assert app.test_client().get('/api/admin/drivers', headers=bearer(token)).status_code == 200
    # admin não é motorista
    assert app.test_client().get('/api/viagens/atual', headers=bearer(token)).status_code == 403


def test_api_inexistente_devolve_json_404(client):
    for metodo in ('get', 'post'):
        res = getattr(client, metodo)('/api/nao-existe')
        assert res.status_code in (404, 405)
        assert res.is_json and 'error' in res.get_json()
    assert client.get('/api/nao-existe').status_code == 404


def test_metodo_nao_permitido_em_api_devolve_json(client):
    res = client.delete('/api/routes')
    assert res.status_code == 405 and res.is_json


def test_endpoints_antes_abertos_exigem_login(client, app):
    assert client.post('/api/incidents', json={'driver_id': 1, 'type': 'pane'}).status_code == 401
    assert client.get('/api/incidents').status_code == 401
    assert client.post('/api/incidents/1/resolve').status_code == 401
    assert client.post('/api/admin/populate-routes').status_code == 401
    criar_usuario('ana@teste.com')
    login(client, 'ana@teste.com')
    assert client.post('/api/incidents', json={'type': 'pane'}).status_code == 403
    assert client.get('/api/incidents').status_code == 403


def test_avaliacao_com_valor_invalido_da_400(client, app):
    criar_usuario('ana@teste.com')
    login(client, 'ana@teste.com')
    assert client.post('/api/submit-rating', json={'overall_rating': 'abc'}).status_code == 400
    assert client.post('/api/submit-rating', json={'overall_rating': 4}).status_code == 201
