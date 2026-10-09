"""Portable incident exports with spreadsheet formula neutralization."""
import csv
import io
import json


def cell(value):
    if isinstance(value, str) and (value.startswith(('\t', '\r', '\n')) or value.lstrip().startswith(('=', '+', '-', '@'))):
        return "'" + value
    return value


def timeline_csv(events: list[dict]) -> str:
    fields = ['id', 'timestamp', 'source', 'severity', 'message', 'actor', 'host', 'ip', 'fingerprint', 'review_status']
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(fields)
    for event in sorted(events, key=lambda event: (event['timestamp'], str(event['id']))):
        writer.writerow([cell(event.get(field, '')) for field in fields])
    return stream.getvalue()


def incident_json(incident: dict, events: list[dict], analysis: dict) -> str:
    return json.dumps({'schema_version': '1.0', 'incident': incident, 'events': events, 'analysis': analysis},
                      ensure_ascii=False, indent=2, allow_nan=False)
