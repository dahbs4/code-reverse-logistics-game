import os
os.environ['DATABASE_URL']='sqlite:////tmp/reverse-network-test.db'
from fastapi.testclient import TestClient
from backend.main import app
client=TestClient(app)

def test_complete_api_loop():
    assert client.get('/api/health').json()=={'status':'ok'}
    assert len(client.get('/api/scenarios').json())==4
    r=client.post('/api/games',json={'seed':13});assert r.status_code==200
    g=r.json();id=g['id'];assert g['hour']==0 and len(g['routing'])==35
    plan={**g['sites']['IND']['plan'],'dispatch':0}
    a={'sites':{'IND':plan}}
    p=client.post(f'/api/games/{id}/preview',json=a);assert p.status_code==200 and p.json()['hours']==24
    assert client.get(f'/api/games/{id}').json()['hour']==0
    assert client.post(f'/api/games/{id}/action',json=a).status_code==200
    assert client.post(f'/api/games/{id}/save',json={}).json()['saved']
    stepped=client.post(f'/api/games/{id}/step',json={'hours':24}).json()
    assert stepped['hour']==24 and stepped['disposed']>0
    assert stepped['initial']+stepped['generated']==stepped['disposed']+sum(stepped['inventory'].values())
    assert client.post(f'/api/games/{id}/restore',json={}).json()['hour']==0
    assert client.get(f'/api/games/{id}').json()['sites']['IND']['plan']['dispatch']==0
    assert any(x['id']==id for x in client.get('/api/games').json())

def test_validation_and_not_found():
    assert client.get('/api/games/missing').status_code==404
    assert client.post('/api/games',json={'scenario':'missing'}).status_code==422
    g=client.post('/api/games',json={}).json();id=g['id']
    assert client.post(f'/api/games/{id}/step',json={'hours':999}).status_code==422
    p={**g['sites']['EAST']['plan'],'receiving':200,'processing':300}
    assert client.post(f'/api/games/{id}/action',json={'sites':{'EAST':p}}).status_code==422
    assert client.get(f'/api/games/{id}').json()['decisions']==[]
