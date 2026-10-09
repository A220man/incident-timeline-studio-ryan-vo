"""Grounded triage advice from aggregate evidence, with a deterministic fallback."""
from __future__ import annotations
import json
import httpx
from ..core.errors import AppError


def evidence_summary(analysis: dict) -> dict:
    return {'coverage': {'event_count': analysis['event_count'], 'entity_count': len(analysis['entities'])},
            'correlation': {'components': len(analysis['correlation']['components']),
                            'isolated_events': analysis['correlation']['isolated_events'],
                            'edge_count': len(analysis['correlation']['edges']),
                            'window_seconds': analysis['correlation']['window_seconds']},
            'gaps': {'count': len(analysis['gaps']), 'longest_seconds': max((gap['seconds'] for gap in analysis['gaps']), default=0)},
            'rates': {'anomalies': len(analysis['rates']['anomalies']), 'method': analysis['rates']['method']}}


def local_advice(evidence: dict) -> list[dict]:
    rows = []
    if evidence['gaps']['count']:
        rows.append({'evidence': 'gaps', 'action': 'Compare the observed gaps with source retention and collection schedules before treating them as missing telemetry.'})
    if evidence['rates']['anomalies']:
        rows.append({'evidence': 'rates', 'action': 'Inspect events in flagged buckets and compare them with normal source volume; a burst alone does not establish malicious activity.'})
    if evidence['correlation']['edge_count']:
        rows.append({'evidence': 'correlation', 'action': 'Review each shared entity and its time difference. Shared hosts, service accounts, or NAT addresses can connect unrelated events.'})
    if not rows:
        rows.append({'evidence': 'coverage', 'action': 'Review event coverage and provenance. Absence of a correlation or anomaly does not establish that the incident is benign.'})
    return rows


def _parse(text: str, evidence: dict) -> list[dict]:
    if text.startswith('```'):
        text = text.strip().split('\n', 1)[1].rsplit('```', 1)[0]
    data = json.loads(text)
    if not isinstance(data, list) or not 1 <= len(data) <= 8:
        raise ValueError('Expected one to eight advice items')
    for item in data:
        if not isinstance(item, dict) or item.get('evidence') not in evidence:
            raise ValueError('Unknown evidence reference')
        if not isinstance(item.get('action'), str) or not 1 <= len(item['action']) <= 1000:
            raise ValueError('Invalid action')
    return [{'evidence': item['evidence'], 'action': item['action']} for item in data]


def advise(settings, analysis: dict, external: bool, transport=None) -> dict:
    evidence = evidence_summary(analysis)
    result = {'mode': 'local', 'evidence': evidence, 'items': local_advice(evidence),
              'limitations': 'Advice is a review aid, not a verdict. No actions are executed.'}
    if not external:
        return result
    if settings.llm_provider != 'ollama' and not settings.llm_api_key:
        raise AppError(409, 'llm_not_configured', 'Configure LLM_API_KEY before requesting external advice')
    if not settings.llm_model:
        raise AppError(409, 'llm_not_configured', 'Configure LLM_MODEL before requesting external advice')
    prompt = ('Return a JSON array with 1-8 objects containing evidence and action. Evidence must be one of '
              'coverage, correlation, gaps, rates. Recommend cautious next investigation steps grounded ONLY in these '
              'aggregate measurements. Do not claim a breach, attribute an actor, or invent events. '
              'Do not emit commands or instructions to modify systems. Measurements: ' + json.dumps(evidence))
    provider, key = settings.llm_provider, settings.llm_api_key
    headers = {'Content-Type': 'application/json'}
    if provider in {'openai-compatible', 'openai', 'ollama'}:
        base = settings.llm_base_url or ('http://127.0.0.1:11434/v1' if provider == 'ollama' else 'https://api.openai.com/v1')
        url = base.rstrip('/') + '/chat/completions'
        if key: headers['Authorization'] = 'Bearer ' + key
        body = {'model': settings.llm_model, 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 1200}
    elif provider == 'anthropic':
        url = 'https://api.anthropic.com/v1/messages'
        headers.update({'x-api-key': key, 'anthropic-version': '2023-06-01'})
        body = {'model': settings.llm_model, 'max_tokens': 1200, 'messages': [{'role': 'user', 'content': prompt}]}
    elif provider == 'gemini':
        from urllib.parse import quote
        url = 'https://generativelanguage.googleapis.com/v1beta/models/' + quote(settings.llm_model, safe='') + ':generateContent'
        headers['x-goog-api-key'] = key
        body = {'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'maxOutputTokens': 1200}}
    else:
        raise AppError(409, 'llm_not_configured', 'Unrecognized LLM_PROVIDER')
    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds, transport=transport, follow_redirects=False, trust_env=False) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            raw = response.json()
        if provider == 'anthropic':
            text = ''.join(part.get('text', '') for part in raw['content'])
        elif provider == 'gemini':
            text = ''.join(part.get('text', '') for part in raw['candidates'][0]['content']['parts'])
        else:
            text = raw['choices'][0]['message']['content']
        result.update(mode='external', items=_parse(text, evidence))
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, AttributeError):
        result['warning'] = 'External advice was unavailable or invalid. Local recommendations are shown.'
    return result
