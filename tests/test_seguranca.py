"""Regras de acesso e validação revisadas (incidentes, reset de senha, erros JSON)."""
from src.models import db
from src.models.user import PasswordResetToken
from tests.conftest import criar_usuario, login


def test_rotas_de_admin_e_incidentes_exigem_login(client):
    assert client.post('/api/admin/populate-routes').status_code == 401
    assert client.get('/api/incidents').status_code == 401
    assert client.post('/api/incidents', json={'driver_id': 1, 'type': 'pane'}).status_code == 401
    assert client.post('/api/incidents/1/resolve').status_code == 401


def test_passageiro_nao_registra_incidente(client):
    criar_usuario('p@teste.com')
    login(client, 'p@teste.com')
    assert client.post('/api/incidents', json={'type': 'pane'}).status_code == 403
    assert client.get('/api/incidents').status_code == 403


def test_reset_de_senha_exige_email_do_dono(client):
    criar_usuario('dono@teste.com')
    criar_usuario('outro@teste.com')
    client.post('/api/auth/forgot-password', json={'email': 'dono@teste.com'})
    codigo = PasswordResetToken.query.filter_by(used=False).first().token
    corpo = {'code': codigo, 'new_password': 'nova123', 'confirm_password': 'nova123'}

    assert client.post('/api/auth/reset-password', json=corpo).status_code == 400
    assert client.post('/api/auth/reset-password', json={**corpo, 'email': 'outro@teste.com'}).status_code == 400
    assert client.post('/api/auth/verify-reset-code', json={'code': codigo}).status_code == 400
    assert client.post('/api/auth/reset-password', json={**corpo, 'email': 'dono@teste.com'}).status_code == 200
    login(client, 'dono@teste.com', 'nova123')


def test_avaliacao_com_nota_invalida_retorna_400(client):
    criar_usuario('p@teste.com')
    login(client, 'p@teste.com')
    assert client.post('/api/submit-rating', json={'overall_rating': 'abc'}).status_code == 400
    assert client.post('/api/submit-rating', json={'overall_rating': 5, 'comfort_rating': 9}).status_code == 400
    assert client.post('/api/submit-rating', json={'overall_rating': 5}).status_code == 201


def test_senha_curta_no_perfil_e_cadastro(client):
    assert client.post('/api/auth/register', json={'username': 'x', 'email': 'x@t.com', 'password': '1'}).status_code == 400
    criar_usuario('p@teste.com')
    login(client, 'p@teste.com')
    res = client.put('/api/auth/profile', json={'username': 'p', 'email': 'p@teste.com', 'password': '1'})
    assert res.status_code == 400


def test_api_inexistente_responde_json_404(client):
    res = client.get('/api/nao-existe')
    assert res.status_code == 404
    assert res.is_json
    res = client.delete('/api/routes')
    assert res.status_code == 405 and res.is_json
