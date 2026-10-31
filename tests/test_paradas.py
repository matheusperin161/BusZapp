"""Paradas (CA05.1 a CA05.5) e compatibilidade com as telas web de rotas."""
from src.models import db
from src.models.tracking import Route


def nova_parada(admin, nome='Praça', **extra):
    dados = {'nome': nome, 'endereco': 'Rua A, 1', 'latitude': -27.1, 'longitude': -52.6, **extra}
    return admin.post('/api/admin/paradas', json=dados)


def test_ca05_1_cadastro_valida_coordenadas(admin):
    assert nova_parada(admin, latitude=91).status_code == 400
    assert nova_parada(admin, longitude='x').status_code == 400
    assert nova_parada(admin, endereco='').status_code == 400
    res = nova_parada(admin)
    assert res.status_code == 201 and res.get_json()['status'] == 'ativa'


def test_listagem_busca_e_edicao(admin):
    pid = nova_parada(admin, 'Terminal').get_json()['id']
    nova_parada(admin, 'Hospital', endereco='Av. Brasil')
    assert [p['nome'] for p in admin.get('/api/admin/paradas?q=brasil').get_json()] == ['Hospital']
    res = admin.put(f'/api/admin/paradas/{pid}', json={'nome': 'Terminal Central'})
    assert res.status_code == 200 and res.get_json()['endereco'] == 'Rua A, 1'
    assert admin.get('/api/admin/paradas/999').status_code == 404


def test_ca05_2_3_associacao_por_sentido_e_ordem(admin, linha):
    pid = nova_parada(admin).get_json()['id']
    url = f'/api/admin/linhas/{linha.id}/paradas'
    assert admin.post(url, json={'parada_id': pid, 'sentido': 'ida', 'ordem': 2}).status_code == 409  # ordem usada
    res = admin.post(url, json={'parada_id': pid, 'sentido': 'ida'})
    assert res.status_code == 201 and res.get_json()['ordem'] == 4
    assert admin.post(url, json={'parada_id': pid, 'sentido': 'ida'}).status_code == 409  # já associada
    assert admin.post(url, json={'parada_id': pid, 'sentido': 'volta', 'ordem': 1,
                                 'tempo_estimado_minutos': 3}).status_code == 201
    assert len(admin.get(f'{url}?sentido=ida').get_json()) == 4
    volta = admin.get(f'{url}?sentido=volta').get_json()
    assert volta[0]['parada']['id'] == pid and volta[0]['tempo_estimado_minutos'] == 3


def test_remover_reordena(admin, linha):
    url = f'/api/admin/linhas/{linha.id}/paradas'
    ida = admin.get(f'{url}?sentido=ida').get_json()
    assert admin.delete(f'{url}/{ida[0]["id"]}').status_code == 200
    restantes = admin.get(f'{url}?sentido=ida').get_json()
    assert [(p['nome'], p['ordem']) for p in restantes] == [('Parada 2', 1), ('Parada 3', 2)]


def test_ca05_5_desativar_parada_em_linha_ativa(admin, linha):
    parada_id = admin.get(f'/api/admin/linhas/{linha.id}/paradas').get_json()[0]['parada']['id']
    res = admin.patch(f'/api/admin/paradas/{parada_id}/desativar')
    assert res.status_code == 409 and res.get_json()['linhas'] == [{'id': linha.id, 'nome': 'Centro - Bairro'}]

    db.session.get(Route, linha.id).active = False
    db.session.commit()
    assert admin.patch(f'/api/admin/paradas/{parada_id}/desativar').get_json()['status'] == 'inativa'
    # parada inativa não entra em linha
    outra = Route(route_name='Linha_2', origin_lat=0, origin_lon=0, destination_lat=0, destination_lon=0)
    db.session.add(outra)
    db.session.commit()
    res = admin.post(f'/api/admin/linhas/{outra.id}/paradas', json={'parada_id': parada_id, 'sentido': 'ida'})
    assert res.status_code == 422
    assert admin.patch(f'/api/admin/paradas/{parada_id}/reativar').get_json()['status'] == 'ativa'


def test_somente_admin(client, linha):
    assert client.get('/api/admin/paradas').status_code == 401


def test_telas_web_continuam_funcionando(admin, linha):
    """admin-rotas.html e acompanhamento.html usam o formato antigo (name/order)."""
    stops = admin.get(f'/api/admin/routes/{linha.id}/stops').get_json()
    assert [(s['name'], s['order']) for s in stops] == [('Parada 1', 1), ('Parada 2', 2), ('Parada 3', 3)]
    # inserir numa ordem ocupada empurra as seguintes
    res = admin.post(f'/api/admin/routes/{linha.id}/stops',
                     json={'name': 'Nova', 'latitude': -27.005, 'longitude': -52.0, 'order': 2})
    assert res.status_code == 201
    nomes = [s['name'] for s in admin.get('/api/route/1').get_json()['stop_points']]
    assert nomes == ['Parada 1', 'Nova', 'Parada 2', 'Parada 3']
    nova = res.get_json()['stop']['id']
    admin.put(f'/api/admin/routes/{linha.id}/stops/{nova}', json={'order': 4, 'name': 'Nova 2'})
    stops = admin.get(f'/api/admin/routes/{linha.id}/stops').get_json()
    assert [(s['name'], s['order']) for s in stops][-1] == ('Nova 2', 4)
    assert admin.delete(f'/api/admin/routes/{linha.id}/stops/{nova}').status_code == 200
    assert len(admin.get(f'/api/admin/routes/{linha.id}/stops').get_json()) == 3


def test_linhas_do_passageiro_tem_nome_e_tempo(client, linha):
    """O app lê nome e tempo_estimado_minutos (antes vinham só name/tempo_ate_proxima_min)."""
    paradas = client.get('/api/linhas').get_json()[0]['paradas']
    assert paradas[0]['nome'] == 'Parada 1' and paradas[0]['tempo_estimado_minutos'] == 4
    assert paradas[0]['name'] == 'Parada 1'


def test_criar_linha_pelo_web_cria_paradas(admin):
    res = admin.post('/api/admin/routes', json={
        'route_number': '7', 'route_name': 'Nova', 'origin': 'A', 'destination': 'B', 'fare': 4,
        'origin_lat': -27, 'origin_lon': -52, 'dest_lat': -27.1, 'dest_lon': -52})
    assert res.status_code == 201
    stops = admin.get(f'/api/admin/routes/{res.get_json()["route_id"]}/stops').get_json()
    assert [s['name'] for s in stops] == ['A', 'B']
