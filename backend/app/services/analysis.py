"""Explainable temporal correlation, source gaps, and robust event-rate anomalies.

These are triage aids: shared identifiers and unusual rates are evidence for
review, not proof of a compromise or attribution to a person.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
import math
import statistics
from .entities import extract_entities, entity_index


def seconds(value: str) -> float:
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def _positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(name + ' must be finite and positive')


def correlate(events: list[dict], window_seconds: float = 300) -> dict:
    """Build connected components from adjacent appearances of each entity.

    Adjacent edges keep storage linear in extracted entities. A component can
    span longer than the window through an evidence chain; each edge records its
    exact shared identifier and time difference. Unrelated events stay isolated.
    """
    _positive(window_seconds, 'window_seconds')
    ordered = sorted(events, key=lambda event: (event['timestamp'], str(event['id'])))
    ids = [event['id'] for event in ordered]
    if len(set(ids)) != len(ids):
        raise ValueError('Event IDs must be unique')
    parent = {id: id for id in ids}
    rank = dict.fromkeys(ids, 0)

    def root(id):
        while parent[id] != id:
            parent[id] = parent[parent[id]]
            id = parent[id]
        return id

    def union(left, right):
        a, b = root(left), root(right)
        if a == b:
            return
        if rank[a] < rank[b]:
            a, b = b, a
        parent[b] = a
        if rank[a] == rank[b]:
            rank[a] += 1

    previous, edges = {}, []
    for event in ordered:
        timestamp = seconds(event['timestamp'])
        for entity in extract_entities(event):
            key = (entity['type'], entity['value'])
            old = previous.get(key)
            if old and timestamp - old[1] <= window_seconds:
                union(old[0], event['id'])
                edges.append({'from': old[0], 'to': event['id'], 'entity_type': key[0],
                              'entity': key[1], 'delta_seconds': round(timestamp - old[1], 6)})
            previous[key] = (event['id'], timestamp)
    groups = defaultdict(list)
    for event in ordered:
        groups[root(event['id'])].append(event)
    components = []
    for members in groups.values():
        components.append({'event_ids': [e['id'] for e in members], 'size': len(members),
                           'start': members[0]['timestamp'], 'end': members[-1]['timestamp'],
                           'sources': sorted({e['source'] for e in members}),
                           'duration_seconds': seconds(members[-1]['timestamp']) - seconds(members[0]['timestamp'])})
    components.sort(key=lambda group: (-group['size'], group['start'], str(group['event_ids'][0])))
    return {'components': components, 'edges': edges, 'window_seconds': window_seconds,
            'isolated_events': sum(group['size'] == 1 for group in components)}


def source_gaps(events: list[dict], threshold_seconds: float = 900) -> list[dict]:
    """Report internal observed gaps only; no claim about unobserved coverage."""
    _positive(threshold_seconds, 'threshold_seconds')
    sources = defaultdict(list)
    for event in events:
        sources[event['source']].append(event)
    gaps = []
    for source, values in sorted(sources.items()):
        values.sort(key=lambda event: (event['timestamp'], str(event['id'])))
        for previous, current in zip(values, values[1:]):
            duration = seconds(current['timestamp']) - seconds(previous['timestamp'])
            if duration > threshold_seconds:
                gaps.append({'source': source, 'before_event_id': previous['id'], 'after_event_id': current['id'],
                             'start': previous['timestamp'], 'end': current['timestamp'], 'seconds': duration})
    return sorted(gaps, key=lambda gap: (-gap['seconds'], gap['source'], gap['start']))


def rate_anomalies(events: list[dict], bucket_seconds: int = 60, z_threshold: float = 3.5,
                   max_buckets: int = 10000) -> dict:
    """MAD-based rate detector with explicit zero-variance fallback.

    All empty buckets between first and last observed events participate. Fewer
    than five buckets is insufficient evidence. The fallback requires at least
    three excess events and uses sqrt(median+1) as a conservative count scale.
    """
    _positive(bucket_seconds, 'bucket_seconds')
    _positive(z_threshold, 'z_threshold')
    if isinstance(bucket_seconds, bool) or not isinstance(bucket_seconds, int):
        raise ValueError('bucket_seconds must be an integer')
    if not events:
        return {'buckets': [], 'anomalies': [], 'method': 'insufficient_data', 'baseline': None}
    counts = defaultdict(int)
    for event in events:
        counts[math.floor(seconds(event['timestamp']) / bucket_seconds)] += 1
    first, last = min(counts), max(counts)
    if last - first + 1 > max_buckets:
        return {'buckets': [], 'anomalies': [], 'method': 'range_too_large', 'baseline': None,
                'message': 'Increase the bucket size or narrow the incident time range'}
    values = [counts[index] for index in range(first, last + 1)]
    median = statistics.median(values)
    mad = statistics.median(abs(value - median) for value in values)
    enough = len(values) >= 5
    scale = 1.4826 * mad if mad else math.sqrt(median + 1)
    rows = []
    for index, value in enumerate(values, first):
        score = (value - median) / scale
        anomalous = enough and value - median >= 3 and score >= z_threshold
        rows.append({'start': datetime.fromtimestamp(index * bucket_seconds, timezone.utc).isoformat().replace('+00:00', 'Z'),
                     'count': value, 'score': round(score, 4), 'anomalous': anomalous})
    return {'buckets': rows, 'anomalies': [row for row in rows if row['anomalous']],
            'method': 'robust_mad' if enough and mad else 'poisson_scale_fallback' if enough else 'insufficient_data',
            'baseline': {'median': median, 'mad': mad, 'scale': scale, 'bucket_seconds': bucket_seconds,
                         'z_threshold': z_threshold, 'sample_size': len(values)}}


def analyze(events: list[dict], window_seconds: float = 300, gap_seconds: float = 900,
            bucket_seconds: int = 60) -> dict:
    return {'event_count': len(events), 'entities': entity_index(events),
            'correlation': correlate(events, window_seconds), 'gaps': source_gaps(events, gap_seconds),
            'rates': rate_anomalies(events, bucket_seconds),
            'limitations': ['Correlation does not establish causality.',
                           'Gaps only describe the supplied evidence, not source availability.',
                           'Burst scores use within-incident statistics and can be biased by incomplete collection.']}
