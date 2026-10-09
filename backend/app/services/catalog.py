"""Transactional incident workspace, replay-safe imports and analyst decisions."""
from __future__ import annotations
import json
import uuid
from ..core.db import Database, utcnow
from ..core.errors import AppError
from .normalization import MAX_ROWS


def audit(conn, actor, action, target, detail):
    conn.execute('INSERT INTO audit_log(actor,action,target,detail,created_at) VALUES(?,?,?,?,?)',
                 (actor, action, target, json.dumps(detail, ensure_ascii=False), utcnow()))


def incident(db: Database, id: str) -> dict:
    row = db.query_one('SELECT * FROM incidents WHERE id=?', (id,))
    if row is None:
        raise AppError(404, 'incident_not_found', 'Incident was not found')
    return dict(row)


def create_incident(db: Database, title: str, description: str, actor: str) -> dict:
    id, now = str(uuid.uuid4()), utcnow()
    with db.transaction() as conn:
        conn.execute('INSERT INTO incidents VALUES(?,?,?,?,?,?,?,?)', (id, title.strip(), description.strip(), 'open', 1, actor, now, now))
        audit(conn, actor, 'incident.create', id, {'title': title.strip()})
    return incident(db, id)


def list_incidents(db: Database, limit: int, offset: int) -> dict:
    rows = db.query('''SELECT i.*, (SELECT COUNT(*) FROM events e WHERE e.incident_id=i.id) AS event_count,
        (SELECT COUNT(*) FROM events e WHERE e.incident_id=i.id AND e.review_status='unreviewed') AS unreviewed_count
        FROM incidents i ORDER BY i.updated_at DESC,i.id LIMIT ? OFFSET ?''', (limit, offset))
    return {'items': [dict(row) for row in rows], 'total': db.query_one('SELECT COUNT(*) AS n FROM incidents')['n']}


def update_incident(db: Database, id: str, title: str, description: str, status: str, version: int, actor: str) -> dict:
    with db.transaction() as conn:
        old = conn.execute('SELECT * FROM incidents WHERE id=?', (id,)).fetchone()
        if old is None:
            raise AppError(404, 'incident_not_found', 'Incident was not found')
        if old['version'] != version:
            raise AppError(409, 'version_conflict', 'Incident changed; refresh before saving')
        conn.execute('UPDATE incidents SET title=?,description=?,status=?,version=version+1,updated_at=? WHERE id=?',
                     (title.strip(), description.strip(), status, utcnow(), id))
        audit(conn, actor, 'incident.update', id, {'previous_status': old['status'], 'status': status, 'version': version+1})
    return incident(db, id)


def _event(row) -> dict:
    result = json.loads(row['payload'])
    result.update({key: row[key] for key in ['id', 'incident_id', 'import_id', 'review_status', 'review_note', 'reviewed_by', 'version', 'updated_at']})
    return result


def list_events(db: Database, id: str, limit: int = 200, offset: int = 0,
                source: str = '', review_status: str = '', query: str = '') -> dict:
    incident(db, id)
    clauses, params = ['incident_id=?'], [id]
    if source:
        clauses.append('source=?'); params.append(source)
    if review_status:
        clauses.append('review_status=?'); params.append(review_status)
    if query:
        # instr avoids treating user-supplied '%' and '_' as wildcard operators.
        clauses.append('instr(lower(payload),lower(?)) > 0'); params.append(query)
    where = ' AND '.join(clauses)
    rows = db.query(f'SELECT * FROM events WHERE {where} ORDER BY timestamp,id LIMIT ? OFFSET ?', (*params, limit, offset))
    total = db.query_one(f'SELECT COUNT(*) AS n FROM events WHERE {where}', params)['n']
    return {'items': [_event(row) for row in rows], 'total': total, 'limit': limit, 'offset': offset}


def all_events(db: Database, id: str) -> list[dict]:
    return list_events(db, id, MAX_ROWS)['items']


def import_events(db: Database, id: str, preview: dict, format: str, zone: str, unit: str, actor: str) -> dict:
    if not preview['can_commit'] or preview['errors']:
        raise AppError(422, 'import_has_errors', 'Resolve every invalid row before committing this upload')
    import_id, now = str(uuid.uuid4()), utcnow()
    with db.transaction() as conn:
        case = conn.execute('SELECT status FROM incidents WHERE id=?', (id,)).fetchone()
        if case is None:
            raise AppError(404, 'incident_not_found', 'Incident was not found')
        if case['status'] != 'open':
            raise AppError(409, 'incident_closed', 'Reopen this incident before importing evidence')
        existing = conn.execute('SELECT * FROM imports WHERE incident_id=? AND upload_sha256=? AND default_zone=? AND epoch_unit=?',
                                (id, preview['upload_sha256'], zone, unit)).fetchone()
        if existing is not None:
            return {**dict(existing), 'replayed': True}
        seen = {row['fingerprint'] for row in conn.execute('SELECT fingerprint FROM events WHERE incident_id=?', (id,))}
        additions = [row for row in preview['events'] if row['fingerprint'] not in seen]
        if len(seen) + len(additions) > MAX_ROWS:
            raise AppError(422, 'incident_limit', 'An incident supports at most 10000 unique events')
        duplicates = preview['input_rows'] - len(additions)
        conn.execute('INSERT INTO imports VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                     (import_id, id, preview['upload_sha256'], format, zone, unit, preview['input_rows'], len(additions), duplicates, actor, now))
        for row in additions:
            event_id = str(uuid.uuid4())
            conn.execute('''INSERT INTO events(id,incident_id,import_id,fingerprint,timestamp,source,severity,payload,updated_at)
                            VALUES(?,?,?,?,?,?,?,?,?)''', (event_id, id, import_id, row['fingerprint'], row['timestamp'], row['source'],
                                                         row['severity'], json.dumps(row, ensure_ascii=False), now))
        conn.execute('UPDATE incidents SET updated_at=?,version=version+1 WHERE id=?', (now, id))
        audit(conn, actor, 'evidence.import', id, {'import_id': import_id, 'upload_sha256': preview['upload_sha256'],
                                               'inserted': len(additions), 'duplicates': duplicates})
    return {**dict(db.query_one('SELECT * FROM imports WHERE id=?', (import_id,))), 'replayed': False}


def review_event(db: Database, incident_id: str, event_id: str, status: str, note: str, version: int, actor: str) -> dict:
    with db.transaction() as conn:
        case = conn.execute('SELECT status FROM incidents WHERE id=?', (incident_id,)).fetchone()
        if case is None:
            raise AppError(404, 'incident_not_found', 'Incident was not found')
        if case['status'] != 'open':
            raise AppError(409, 'incident_closed', 'Reopen this incident before changing review decisions')
        row = conn.execute('SELECT * FROM events WHERE id=? AND incident_id=?', (event_id, incident_id)).fetchone()
        if row is None:
            raise AppError(404, 'event_not_found', 'Event was not found in this incident')
        if row['version'] != version:
            raise AppError(409, 'version_conflict', 'Event changed; refresh before saving the decision')
        conn.execute('UPDATE events SET review_status=?,review_note=?,reviewed_by=?,version=version+1,updated_at=? WHERE id=?',
                     (status, note.strip(), actor, utcnow(), event_id))
        audit(conn, actor, 'event.review', incident_id, {'event_id': event_id, 'previous_status': row['review_status'],
                                                     'status': status, 'version': version+1, 'note': note.strip()})
        conn.execute('UPDATE incidents SET updated_at=?,version=version+1 WHERE id=?', (utcnow(), incident_id))
        result = conn.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
    return _event(result)


def delete_incident(db: Database, id: str, actor: str):
    with db.transaction() as conn:
        cursor = conn.execute('DELETE FROM incidents WHERE id=?', (id,))
        if not cursor.rowcount:
            raise AppError(404, 'incident_not_found', 'Incident was not found')
        audit(conn, actor, 'incident.delete', id, {})


def history(db: Database, id: str) -> dict:
    incident(db, id)
    return {'imports': [dict(row) for row in db.query('SELECT * FROM imports WHERE incident_id=? ORDER BY created_at DESC,id', (id,))],
            'audit': [{**dict(row), 'detail': json.loads(row['detail'])} for row in db.query('SELECT * FROM audit_log WHERE target=? ORDER BY id DESC LIMIT 200', (id,))]}
