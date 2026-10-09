"""Seeded synthetic evaluation of temporal/entity correlation against known pairs.

Scenarios include shared infrastructure, benign bursts and missing telemetry.
Threshold selection uses training seeds only. Held-out results are reported
separately, including an always-separate baseline and false-positive examples.
"""
from __future__ import annotations
import argparse
import itertools
import json
import random
from datetime import datetime, timedelta, timezone
from .analysis import correlate


def scenario(seed: int, campaigns: int = 4) -> tuple[list[dict], dict[str, str]]:
    rng = random.Random(seed)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events, labels = [], {}
    for campaign in range(campaigns):
        actor = f'account-{campaign}'
        base = campaign * 1500 + rng.randrange(0, 120)
        for step in range(5):
            id = f'chain-{campaign}-{step}'
            # Variable spacing sometimes exceeds an otherwise useful window.
            offset = base + step * rng.choice([45, 90, 150, 240])
            events.append({'id': id, 'timestamp': (start + timedelta(seconds=offset)).isoformat().replace('+00:00', 'Z'),
                           'source': ['auth', 'endpoint', 'network'][step % 3], 'actor': actor,
                           'host': 'shared-gateway' if step == 2 else f'host-{campaign}',
                           'ip': '', 'message': f'Synthetic campaign action {step}', 'severity': 'medium'})
            labels[id] = f'campaign-{campaign}'
        for step in range(3):
            id = f'background-{campaign}-{step}'
            events.append({'id': id, 'timestamp': (start + timedelta(seconds=base + rng.randrange(0, 800))).isoformat().replace('+00:00', 'Z'),
                           'source': 'maintenance', 'actor': f'backup-{step}', 'host': f'host-{campaign}',
                           'ip': '', 'message': 'Synthetic independent maintenance', 'severity': 'info'})
            labels[id] = id
    rng.shuffle(events)
    return events, labels


def score(events: list[dict], labels: dict[str, str], window: int | None) -> dict:
    predicted = {}
    if window is None:
        predicted = {event['id']: event['id'] for event in events}
    else:
        for index, component in enumerate(correlate(events, window)['components']):
            for id in component['event_ids']:
                predicted[id] = index
    counts = {'tp': 0, 'fp': 0, 'fn': 0, 'tn': 0}
    errors = []
    for left, right in itertools.combinations(sorted(labels), 2):
        expected = labels[left] == labels[right]
        detected = predicted[left] == predicted[right]
        category = 'tp' if expected and detected else 'fp' if detected else 'fn' if expected else 'tn'
        counts[category] += 1
        if category in {'fp', 'fn'} and len(errors) < 8:
            errors.append({'left': left, 'right': right, 'type': category})
    return {**counts, **metrics(counts), 'examples': errors}


def metrics(counts: dict) -> dict:
    tp, fp, fn = counts['tp'], counts['fp'], counts['fn']
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {'precision': round(precision, 4), 'recall': round(recall, 4),
            'f1': round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0}


def evaluate(seeds: list[int], window: int | None) -> dict:
    totals = dict.fromkeys(['tp', 'fp', 'fn', 'tn'], 0)
    examples = []
    for seed in seeds:
        events, labels = scenario(seed)
        result = score(events, labels, window)
        for key in totals:
            totals[key] += result[key]
        if len(examples) < 8:
            examples.extend({'seed': seed, **example} for example in result['examples'][:8-len(examples)])
    return {**totals, **metrics(totals), 'seeds': seeds, 'examples': examples}


def benchmark(seed: int = 17, count: int = 12) -> dict:
    if count < 2 or count > 100:
        raise ValueError('Scenario count must be between 2 and 100')
    training = list(range(seed, seed + count))
    heldout = list(range(seed + 10000, seed + 10000 + count))
    candidates = [{ 'window_seconds': window, 'result': evaluate(training, window)} for window in [30, 60, 120, 300, 600]]
    best = max(candidates, key=lambda item: (item['result']['f1'], -item['window_seconds']))
    return {'provenance': 'Generated synthetic campaign chains mixed with independent shared-host maintenance; no customer logs.',
            'training': candidates, 'selected_window_seconds': best['window_seconds'],
            'heldout': evaluate(heldout, best['window_seconds']), 'baseline': evaluate(heldout, None),
            'limitations': ['Synthetic labels define related campaigns, not confirmed malicious activity.',
                           'Shared infrastructure causes false positives; sparse telemetry causes false negatives.',
                           'Pairwise metrics weight large components heavily; inspect the error pairs.',
                           'No LLM is called, trained, or scored in this benchmark.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=17)
    parser.add_argument('--count', type=int, default=12)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.seed, args.count), indent=2))
