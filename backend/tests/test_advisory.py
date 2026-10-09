import json
import httpx
import pytest
from backend.app.services.advisory import advise
from backend.app.services.analysis import analyze
from backend.app.core.config import Settings


@pytest.mark.parametrize('provider',['openai-compatible','anthropic','gemini','ollama'])
def test_adapter_formats_and_aggregate_only_payload(provider):
    config=Settings(environment='test',llm_provider=provider,llm_model='fixture-model',llm_api_key='synthetic-test-value')
    event={'id':'private-event-id','timestamp':'2026-10-09T12:00:00Z','source':'private-source','message':'private-sensitive-log','actor':'private-actor'}
    evidence=analyze([event]);text=json.dumps([{'evidence':'coverage','action':'Review collection completeness.'}])
    def handler(request):
        payload=request.content.decode()
        assert all(value not in payload for value in ['private-sensitive-log','private-event-id','private-source','private-actor'])
        assert 'synthetic-test-value' not in str(request.url)
        if provider=='anthropic':return httpx.Response(200,json={'content':[{'text':text}]})
        if provider=='gemini':return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':text}]}}]})
        return httpx.Response(200,json={'choices':[{'message':{'content':text}}]})
    result=advise(config,evidence,True,httpx.MockTransport(handler))
    assert result['mode']=='external' and result['items'][0]['evidence']=='coverage'


def test_provider_error_cannot_leak_credentials():
    config=Settings(environment='test',llm_provider='openai-compatible',llm_model='fixture',llm_api_key='sensitive-test-value')
    def handler(request):raise httpx.ConnectError('sensitive-test-value',request=request)
    result=advise(config,analyze([]),True,httpx.MockTransport(handler))
    assert result['mode']=='local' and 'warning' in result and 'sensitive-test-value' not in json.dumps(result)


def test_unknown_evidence_reference_falls_back():
    config=Settings(environment='test',llm_provider='ollama',llm_model='fixture')
    def handler(request):return httpx.Response(200,json={'choices':[{'message':{'content':'[{"evidence":"invented","action":"unsupported"}]'}}]})
    result=advise(config,analyze([]),True,httpx.MockTransport(handler))
    assert result['mode']=='local' and result['items'][0]['evidence']=='coverage'
