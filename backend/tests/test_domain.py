import csv
import io
import json
import pytest
from backend.app.services.normalization import parse_timestamp, parse_upload, ImportProblem
from backend.app.services.entities import extract_entities
from backend.app.services.analysis import correlate, source_gaps, rate_anomalies
from backend.app.services.export import timeline_csv


def event(id, minute=0, **changes):
    return {'id': id, 'timestamp': f'2026-10-09T10:{minute:02d}:00.000000Z', 'source': 'auth',
            'message': 'Login succeeded', 'actor': 'alice', 'host': '', 'ip': '', **changes}


@pytest.mark.parametrize('value,zone,expected', [
    ('2026-01-01T00:00:00Z', 'UTC', '2026-01-01T00:00:00.000000Z'),
    ('2026-01-01T03:30:00+03:30', 'UTC', '2026-01-01T00:00:00.000000Z'),
    ('2026-01-01T00:00:00', 'America/Los_Angeles', '2026-01-01T08:00:00.000000Z'),
    ('1970-01-01T00:00:00Z', 'UTC', '1970-01-01T00:00:00.000000Z'),
])
def test_timestamp_offsets(value, zone, expected):
    assert parse_timestamp(value, zone) == expected


@pytest.mark.parametrize('value,match', [('2026-11-01T01:30:00', 'ambiguous'), ('2026-03-08T02:30:00', 'gap')])
def test_dst_requires_explicit_offset(value, match):
    with pytest.raises(ImportProblem, match=match):
        parse_timestamp(value, 'America/Los_Angeles')


@pytest.mark.parametrize('value', [True, None, '', 'nan', 'inf', '2026-02-30T00:00:00Z', '1e100'])
def test_invalid_timestamps(value):
    with pytest.raises(ImportProblem):
        parse_timestamp(value)


def test_epoch_units_are_explicit():
    assert parse_timestamp(1000, epoch_unit='milliseconds') == parse_timestamp(1)
    assert parse_timestamp(1000) != parse_timestamp(1000, epoch_unit='milliseconds')


def test_import_replay_has_stable_fingerprint_and_raw_provenance():
    data = json.dumps([{'timestamp': '2026-01-01T00:00:00Z', 'message': 'Login'},
                       {'timestamp': '2026-01-01T00:00:00+00:00', 'message': 'Login'}]).encode()
    report = parse_upload(data, 'json')
    assert report['can_commit'] and report['duplicates'] == 1
    assert len(report['events']) == 1 and len(report['events'][0]['raw_sha256']) == 64


def test_import_partial_errors_prevent_commit():
    report = parse_upload(b'timestamp,message\n2026-01-01T00:00:00Z,Login\nwrong,Invalid\n', 'csv')
    assert not report['can_commit'] and report['errors'][0]['row'] == 2
    assert len(report['events']) == 1


@pytest.mark.parametrize('data,format', [(b'timestamp,timestamp\na,b', 'csv'), (b'{}', 'json'),
                                        (b'[NaN]', 'json'), (b'\xff', 'json'), (b'[]', 'json')])
def test_invalid_documents(data, format):
    with pytest.raises(ImportProblem):
        parse_upload(data, format)


def test_jsonl_and_csv_preserve_multiline_message():
    report = parse_upload(b'timestamp,message\n2026-01-01T00:00:00Z,"hello, world\nnext"', 'csv')
    assert report['events'][0]['message'] == 'hello, world\nnext'
    raw = json.dumps({'timestamp': 0, 'message': 'hello'}).encode()
    assert parse_upload(raw + b'\n', 'jsonl')['can_commit']


def test_entities_reject_invalid_ips_and_normalize_ipv6():
    row = event(1, actor='Alice', host='SERVER.EXAMPLE.', ip='2001:0db8::1',
                message='192.0.2.8 and 999.0.2.8; alice@EXAMPLE.COM')
    entities = {(x['type'], x['value']) for x in extract_entities(row)}
    assert ('ip', '2001:db8::1') in entities and ('ip', '192.0.2.8') in entities
    assert ('ip', '999.0.2.8') not in entities
    assert ('email', 'alice@example.com') in entities and ('host', 'server.example') in entities
    assert ('actor', 'Alice') in entities


def test_correlation_edges_explain_transitive_components():
    rows = [event(1), event(2, 4), event(3, 8), event(4, 9, actor='bob')]
    result = correlate(rows, 300)
    assert result['components'][0]['event_ids'] == [1, 2, 3]
    assert result['components'][0]['duration_seconds'] == 480
    assert result['isolated_events'] == 1
    assert all(edge['entity'] == 'alice' and edge['delta_seconds'] == 240 for edge in result['edges'])


def test_same_entity_outside_window_does_not_link():
    assert correlate([event(1), event(2, 6)], 300)['edges'] == []


def test_correlation_order_is_deterministic_and_ids_are_unique():
    rows = [event(2), event(1), event(3, 1)]
    assert correlate(rows) == correlate(list(reversed(rows)))
    with pytest.raises(ValueError, match='unique'):
        correlate([event(1), event(1)])


def test_gap_is_per_source_and_excludes_exact_threshold():
    rows = [event(1), event(2, 10, source='network'), event(3, 20), event(4, 25)]
    gaps = source_gaps(rows, 300)
    assert len(gaps) == 1 and gaps[0]['seconds'] == 1200 and gaps[0]['source'] == 'auth'


def test_constant_rate_is_not_anomalous_and_burst_is():
    baseline = [event(i, i) for i in range(10)]
    assert not rate_anomalies(baseline)['anomalies']
    burst = baseline + [event(100 + i, 5) for i in range(12)]
    result = rate_anomalies(burst)
    assert len(result['anomalies']) == 1 and result['anomalies'][0]['count'] == 13
    assert result['method'] == 'poisson_scale_fallback'


def test_rate_includes_empty_buckets_and_bounds_sparse_range():
    result = rate_anomalies([event(1), event(2, 9)])
    assert len(result['buckets']) == 10 and result['buckets'][1]['count'] == 0
    assert rate_anomalies([event(1), event(2, 9)], max_buckets=5)['method'] == 'range_too_large'
    assert rate_anomalies([event(1)])['method'] == 'insufficient_data'


@pytest.mark.parametrize('value', [0, -1, float('nan'), float('inf'), True])
def test_analysis_rejects_invalid_thresholds(value):
    with pytest.raises(ValueError):
        correlate([], value)
    with pytest.raises(ValueError):
        source_gaps([], value)
    with pytest.raises(ValueError):
        rate_anomalies([], value)


@pytest.mark.parametrize('formula', ['=1+1', '+1+1', '-1+1', '@SUM(A1)', '  =1', '\tformula'])
def test_csv_neutralizes_formulas_without_mutation(formula):
    row = event(1, message=formula)
    output = list(csv.DictReader(io.StringIO(timeline_csv([row]))))[0]
    assert output['message'] == "'" + formula and row['message'] == formula
