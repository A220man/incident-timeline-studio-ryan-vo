"""Bounded incident-log import with explicit timestamp and provenance semantics."""
from __future__ import annotations
import csv
import hashlib
import io
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MAX_ROWS = 10000
MAX_BYTES = 5 * 1024 * 1024
SEVERITIES = {'debug', 'info', 'low', 'medium', 'high', 'critical', 'unknown'}


class ImportProblem(ValueError):
    """Invalid evidence; message is safe to show to the importing analyst."""


@dataclass(frozen=True)
class NormalizedEvent:
    fingerprint: str
    timestamp: str
    source: str
    message: str
    severity: str
    actor: str
    host: str
    ip: str
    original_timestamp: str
    row_number: int
    raw_sha256: str

    def to_dict(self):
        return asdict(self)


def parse_timestamp(value: object, default_zone: str = 'UTC', epoch_unit: str = 'seconds') -> str:
    """Return UTC ISO8601. Ambiguous/nonexistent local wall times are rejected.

    Numeric epochs require an explicit unit; never guess units from magnitude.
    A timestamp with a numeric UTC offset needs no zone database interpretation.
    """
    if epoch_unit not in {'seconds', 'milliseconds'}:
        raise ImportProblem('Epoch unit must be seconds or milliseconds')
    try:
        zone = ZoneInfo(default_zone)
    except (ZoneInfoNotFoundError, ValueError):
        raise ImportProblem('Unknown default time zone') from None
    if isinstance(value, bool) or value is None:
        raise ImportProblem('Timestamp is required')
    text = str(value).strip()
    if not text:
        raise ImportProblem('Timestamp is required')
    try:
        number = float(text)
    except ValueError:
        number = None
    try:
        if number is not None:
            if not math.isfinite(number):
                raise ImportProblem('Epoch must be finite')
            stamp = datetime.fromtimestamp(number / (1000 if epoch_unit == 'milliseconds' else 1), timezone.utc)
        else:
            stamp = datetime.fromisoformat(text.replace('Z', '+00:00'))
            if stamp.tzinfo is None:
                candidates = []
                for fold in (0, 1):
                    candidate = stamp.replace(tzinfo=zone, fold=fold)
                    utc = candidate.astimezone(timezone.utc)
                    if utc.astimezone(zone).replace(tzinfo=None) == stamp:
                        candidates.append(utc)
                candidates = list(set(candidates))
                if not candidates:
                    raise ImportProblem('Local timestamp falls in a daylight-saving gap; supply an explicit UTC offset')
                if len(candidates) > 1:
                    raise ImportProblem('Local timestamp is ambiguous; supply an explicit UTC offset')
                stamp = candidates[0]
            stamp = stamp.astimezone(timezone.utc)
    except (ValueError, OverflowError, OSError) as error:
        if isinstance(error, ImportProblem):
            raise
        raise ImportProblem('Invalid ISO8601 timestamp or epoch') from None
    return stamp.isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _text(row: dict, field: str, limit: int, fallback: str = '') -> str:
    value = row.get(field, fallback)
    if value is None:
        return fallback
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise ImportProblem(f'{field} must be text or a number')
    result = str(value).strip()
    if len(result) > limit:
        raise ImportProblem(f'{field} exceeds {limit} characters')
    if '\x00' in result:
        raise ImportProblem(f'{field} contains a null byte')
    return result


def normalize_row(row: dict, row_number: int, default_zone: str, epoch_unit: str) -> NormalizedEvent:
    if not isinstance(row, dict) or any(not isinstance(k, str) for k in row):
        raise ImportProblem('Each event must be an object with named fields')
    stamp = parse_timestamp(row.get('timestamp'), default_zone, epoch_unit)
    source = _text(row, 'source', 128, 'import') or 'import'
    message = _text(row, 'message', 8192)
    if not message:
        raise ImportProblem('message is required')
    severity = _text(row, 'severity', 24, 'unknown').lower() or 'unknown'
    if severity not in SEVERITIES:
        raise ImportProblem('Unrecognized severity: use debug, info, low, medium, high, critical, or unknown')
    actor = _text(row, 'actor', 256)
    host = _text(row, 'host', 256).lower().rstrip('.')
    ip = _text(row, 'ip', 64)
    # The normalized fingerprint deduplicates replayed evidence without discarding
    # severity or entity changes. Raw hash records original content separately.
    canonical = json.dumps([stamp, source, message, severity, actor, host, ip], ensure_ascii=False, separators=(',', ':'))
    raw = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return NormalizedEvent(hashlib.sha256(canonical.encode()).hexdigest(), stamp, source, message,
                           severity, actor, host, ip, str(row['timestamp']), row_number,
                           hashlib.sha256(raw.encode()).hexdigest())


def parse_upload(data: bytes, format: str, default_zone: str = 'UTC', epoch_unit: str = 'seconds') -> dict:
    """Preview an entire bounded import. Invalid rows are reported, never silently lost.

    The API must refuse commit whenever errors are present. Preview deduplicates
    within the upload; the database also enforces unique incident/fingerprint.
    """
    if len(data) > MAX_BYTES:
        raise ImportProblem('Upload exceeds 5 MiB')
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ImportProblem('Upload must be UTF-8') from None
    try:
        if format == 'csv':
            reader = csv.DictReader(io.StringIO(text, newline=''))
            if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ImportProblem('CSV needs unique column names')
            if not {'timestamp', 'message'}.issubset(reader.fieldnames):
                raise ImportProblem('CSV requires timestamp and message columns')
            rows = []
            for row in reader:
                rows.append(row)
                if len(rows) > MAX_ROWS:
                    raise ImportProblem('Import exceeds 10000 rows')
        elif format == 'json':
            rows = json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ImportProblem('JSON numbers must be finite')))
            if not isinstance(rows, list):
                raise ImportProblem('JSON must contain an array of event objects')
        elif format == 'jsonl':
            rows = []
            for line in text.splitlines():
                if line.strip():
                    rows.append(json.loads(line, parse_constant=lambda value: (_ for _ in ()).throw(ImportProblem('JSON numbers must be finite'))))
                if len(rows) > MAX_ROWS:
                    raise ImportProblem('Import exceeds 10000 rows')
        else:
            raise ImportProblem('Format must be csv, json, or jsonl')
    except (json.JSONDecodeError, csv.Error, RecursionError):
        raise ImportProblem('Malformed input document') from None
    if not rows or len(rows) > MAX_ROWS:
        raise ImportProblem('Import must contain between 1 and 10000 events')
    events, errors, seen = [], [], set()
    duplicates = 0
    for i, row in enumerate(rows, 1):
        try:
            event = normalize_row(row, i, default_zone, epoch_unit)
        except ImportProblem as error:
            errors.append({'row': i, 'message': str(error)})
            continue
        except (ValueError, TypeError):
            errors.append({'row': i, 'message': 'Invalid event value'})
            continue
        if event.fingerprint in seen:
            duplicates += 1
        else:
            seen.add(event.fingerprint)
            events.append(event.to_dict())
    return {'events': events, 'errors': errors, 'duplicates': duplicates, 'input_rows': len(rows),
            'upload_sha256': hashlib.sha256(data).hexdigest(), 'can_commit': not errors}
