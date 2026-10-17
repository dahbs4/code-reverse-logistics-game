import os
os.environ['DATABASE_URL']='sqlite:////tmp/reverse-network-test.db'
from fastapi.testclient import TestClient
from backend.main import app
client=TestClient(app)


def test_weekly_api_loop_and_preview_isolation():
    assert client.get('/api/health').json()=={'status':'ok'}
    g=client.post('/api/games',json={'seed':13}).json();id=g['id']
    assert g['hour']==0 and len(g['weekly_outlook']['weeks'])==52
    plan={'IND':800000,'EAST':420000}
    preview=client.post(f'/api/games/{id}/preview',json=plan)
    assert preview.status_code==200
    assert preview.json()['plan']==plan
    assert client.get(f'/api/games/{id}').json()['weekly_plan']!=plan
    assert client.get(f'/api/games/{id}').json()['hour']==0
    assert client.post(f'/api/games/{id}/action',json=plan).json()['weekly_plan']==plan
    assert client.post(f'/api/games/{id}/save',json={}).json()['saved']
    stepped=client.post(f'/api/games/{id}/step',json={}).json()
    assert stepped['hour']==168 and stepped['disposed']>0
    assert stepped['last_week']['processed']<=sum(plan.values())
    assert stepped['annual_forecast']['weeks'][0]['actual']==stepped['generated']
    assert stepped['initial']+stepped['generated']==stepped['disposed']+sum(stepped['inventory'].values())
    restored=client.post(f'/api/games/{id}/restore',json={}).json()
    assert restored['hour']==0 and restored['weekly_plan']==plan
    assert restored['annual_forecast']==g['annual_forecast']


def test_daily_steps_and_invalid_weekly_plans_are_rejected():
    assert client.get('/api/games/missing').status_code==404
    g=client.post('/api/games',json={}).json();id=g['id']
    for hours in (8,24,999):
        assert client.post(f'/api/games/{id}/step',json={'hours':hours}).status_code==422
    for plan in ({'IND':1000001,'EAST':0},{'IND':0,'EAST':500001},{'IND':-1,'EAST':0},{'sites':{}}):
        assert client.post(f'/api/games/{id}/action',json=plan).status_code==422
    assert client.get(f'/api/games/{id}').json()['decisions']==[]


def test_52_week_api_campaign_and_terminal_controls():
    g=client.post('/api/games',json={}).json();id=g['id']
    for week in range(52):
        g=client.post(f'/api/games/{id}/step',json={}).json()
        assert g['hour']==(week+1)*168
    assert g['terminal']['done']
    assert g['annual_forecast']['remaining_forecast']==0
    assert client.post(f'/api/games/{id}/action',json={'IND':0,'EAST':0}).status_code==409
    assert client.post(f'/api/games/{id}/step',json={}).json()['hour']==8736
