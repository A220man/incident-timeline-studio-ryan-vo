import json
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.core.config import Settings


@pytest.fixture
def client():
    settings=Settings(environment='test',database_path=':memory:',auth_mode='demo',cookie_secure=False)
    with TestClient(create_app(settings)) as client:
        login=client.post('/api/auth/demo')
        assert login.status_code==200
        client.headers['X-CSRF-Token']=login.json()['csrf_token']
        yield client


def incident(client):
    response=client.post('/api/incidents',json={'title':'Suspicious login','description':'Review collected telemetry'})
    assert response.status_code==201,response.text
    return response.json()


def upload(client,id,rows=None,commit=True):
    rows=rows or [{'timestamp':'2026-10-09T12:00:00Z','message':'Login 192.0.2.1','actor':'alice','severity':'high'},
                  {'timestamp':'2026-10-09T12:01:00Z','message':'File read','actor':'alice'}]
    return client.post(f'/api/incidents/{id}/import',data={'format':'json','commit':str(commit).lower()},
                       files={'file':('events.json',json.dumps(rows).encode(),'application/json')})


def test_full_incident_workflow(client):
    case=incident(client);id=case['id']
    preview=upload(client,id,commit=False).json()
    assert preview['can_commit'] and len(preview['events'])==2
    assert client.get(f'/api/incidents/{id}/events').json()['total']==0
    first=upload(client,id);assert first.status_code==200,first.text
    assert first.json()['inserted']==2
    repeated=upload(client,id).json();assert repeated['replayed'] and repeated['id']==first.json()['id']
    rows=client.get(f'/api/incidents/{id}/events').json()['items'];assert len(rows)==2
    report=client.get(f'/api/incidents/{id}/analysis').json();assert len(report['correlation']['edges'])==1
    item=rows[0]
    reviewed=client.patch(f'/api/incidents/{id}/events/{item["id"]}',json={'status':'relevant','note':'Corroborated with host telemetry','version':item['version']})
    assert reviewed.status_code==200 and reviewed.json()['reviewed_by']=='local-demo'
    stale=client.patch(f'/api/incidents/{id}/events/{item["id"]}',json={'status':'benign','version':item['version']})
    assert stale.status_code==409
    assert client.get(f'/api/incidents/{id}/events',params={'review_status':'relevant'}).json()['total']==1
    exported=client.get(f'/api/incidents/{id}/export?format=json').json()
    assert len(exported['events'])==2 and exported['analysis']['event_count']==2
    advice=client.post(f'/api/incidents/{id}/advice',json={}).json();assert advice['mode']=='local' and advice['items']
    history=client.get(f'/api/incidents/{id}/history').json();assert len(history['imports'])==1
    assert {row['action'] for row in history['audit']} >= {'incident.create','evidence.import','event.review','advice.request'}


def test_invalid_rows_prevent_atomic_import(client):
    id=incident(client)['id']
    response=upload(client,id,[{'timestamp':0,'message':'valid'},{'timestamp':'bad','message':'invalid'}])
    assert response.status_code==422
    assert client.get(f'/api/incidents/{id}/events').json()['total']==0
    assert client.get(f'/api/incidents/{id}/history').json()['imports']==[]


def test_deduplication_across_different_files(client):
    id=incident(client)['id'];assert upload(client,id).json()['inserted']==2
    extra=[{'timestamp':'2026-10-09T12:00:00Z','message':'Login 192.0.2.1','actor':'alice','severity':'high'},
           {'timestamp':'2026-10-09T12:02:00Z','message':'Disconnect'}]
    response=upload(client,id,extra).json();assert response['inserted']==1 and response['duplicates']==1
    assert client.get(f'/api/incidents/{id}/events').json()['total']==3


def test_closed_incident_and_optimistic_metadata(client):
    case=incident(client);id=case['id'];upload(client,id)
    request={'title':case['title'],'description':'Closed','status':'closed','version':case['version']}
    assert client.patch(f'/api/incidents/{id}',json=request).status_code==409
    request['version']=client.get(f'/api/incidents/{id}').json()['version']
    assert client.patch(f'/api/incidents/{id}',json=request).status_code==200
    assert upload(client,id).status_code==409
    row=client.get(f'/api/incidents/{id}/events').json()['items'][0]
    assert client.patch(f'/api/incidents/{id}/events/{row["id"]}',json={'status':'benign','version':row['version']}).status_code==409


def test_event_cannot_be_reviewed_under_another_incident(client):
    a,b=incident(client)['id'],incident(client)['id'];upload(client,a)
    row=client.get(f'/api/incidents/{a}/events').json()['items'][0]
    assert client.patch(f'/api/incidents/{b}/events/{row["id"]}',json={'status':'relevant','version':1}).status_code==404


def test_authentication_csrf_role_and_revocation(client):
    assert client.get('/api/incidents').status_code==200
    csrf=client.headers.pop('X-CSRF-Token')
    assert client.post('/api/incidents',json={'title':'blocked'}).status_code==403
    client.headers['X-CSRF-Token']=csrf
    with client.app.state.db.transaction() as conn:conn.execute('UPDATE sessions SET roles=?',(json.dumps(['viewer']),))
    assert client.post('/api/incidents',json={'title':'blocked'}).status_code==403
    assert client.post('/api/auth/logout').status_code==204
    assert client.get('/api/incidents').status_code==401


def test_delete_cascades_evidence_and_retains_audit(client):
    id=incident(client)['id'];upload(client,id)
    assert client.delete(f'/api/incidents/{id}').status_code==204
    assert client.get(f'/api/incidents/{id}').status_code==404
    assert client.app.state.db.query_one('SELECT COUNT(*) AS n FROM events')['n']==0
    assert client.app.state.db.query_one('SELECT COUNT(*) AS n FROM imports')['n']==0
    assert client.app.state.db.query_one("SELECT COUNT(*) AS n FROM audit_log WHERE action='incident.delete'")['n']==1


def test_literal_search_and_pagination(client):
    id=incident(client)['id'];upload(client,id)
    assert client.get(f'/api/incidents/{id}/events',params={'query':'%'}).json()['total']==0
    a=client.get(f'/api/incidents/{id}/events?limit=1').json()
    b=client.get(f'/api/incidents/{id}/events?limit=1&offset=1').json()
    assert a['total']==b['total']==2 and a['items'][0]['id']!=b['items'][0]['id']


@pytest.mark.parametrize('body',[{'title':' '},{'title':'x'*201},{}])
def test_invalid_incident_metadata(client,body):
    assert client.post('/api/incidents',json=body).status_code==422


def test_no_key_external_advice_is_explicit_failure(client):
    id=incident(client)['id']
    r=client.post(f'/api/incidents/{id}/advice',json={'external':True})
    assert r.status_code==409 and r.json()['error']['code']=='llm_not_configured'
