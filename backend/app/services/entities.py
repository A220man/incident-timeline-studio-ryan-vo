"""Conservative entity extraction; explicit fields and validated message evidence."""
from __future__ import annotations
import ipaddress
import re

IP_CANDIDATE = re.compile(r'(?<![\w:])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])|(?<![\w:])[0-9a-fA-F]*:[0-9a-fA-F:]+(?![\w:])')
EMAIL = re.compile(r'(?<![\w.+-])[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}(?![\w.-])')
HOST = re.compile(r'^[a-zA-Z0-9](?:[a-zA-Z0-9.-]{0,251}[a-zA-Z0-9])?$')


def extract_entities(event: dict) -> list[dict]:
    found = {}

    def add(kind, value, origin):
        if value:
            key = (kind, value)
            found.setdefault(key, {'type': kind, 'value': value, 'origins': []})
            if origin not in found[key]['origins']:
                found[key]['origins'].append(origin)

    actor = str(event.get('actor') or '').strip()
    add('actor', actor, 'actor')  # User identifiers can be case-sensitive.
    host = str(event.get('host') or '').lower().rstrip('.')
    if host and HOST.fullmatch(host) and '..' not in host:
        add('host', host, 'host')
    ip = str(event.get('ip') or '').strip()
    if ip:
        try:
            add('ip', str(ipaddress.ip_address(ip)), 'ip')
        except ValueError:
            pass  # The raw explicit field remains available in the event.
    message = str(event.get('message') or '')
    for candidate in IP_CANDIDATE.findall(message):
        try:
            add('ip', str(ipaddress.ip_address(candidate)), 'message')
        except ValueError:
            continue
    for email in EMAIL.findall(message):
        local, domain = email.rsplit('@', 1)
        add('email', local + '@' + domain.lower(), 'message')
    return [found[key] for key in sorted(found)]


def entity_index(events: list[dict]) -> list[dict]:
    index = {}
    for event in events:
        for entity in extract_entities(event):
            key = (entity['type'], entity['value'])
            record = index.setdefault(key, {'type': key[0], 'value': key[1], 'event_ids': [], 'sources': set()})
            record['event_ids'].append(event['id'])
            record['sources'].add(event['source'])
    return [{**value, 'sources': sorted(value['sources']), 'count': len(value['event_ids'])}
            for _, value in sorted(index.items(), key=lambda item: (-len(item[1]['event_ids']), item[0]))]
