"""Authenticated incident APIs. All evidence mutations use transactional services."""
from typing import Literal
from fastapi import APIRouter, Request, UploadFile, File, Form, Query, Response
from pydantic import BaseModel, Field, field_validator
from ..core.auth import authorize
from ..core.errors import AppError
from ..services import catalog
from ..services.normalization import parse_upload, ImportProblem, MAX_BYTES
from ..services.analysis import analyze
from ..services.export import timeline_csv, incident_json
from ..services.advisory import advise

router = APIRouter(prefix='/api', tags=['Incidents'])


class IncidentInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=4000)

    @field_validator('title')
    @classmethod
    def meaningful_title(cls, value):
        if not value.strip(): raise ValueError('Title must contain text')
        return value.strip()


class IncidentUpdate(IncidentInput):
    status: Literal['open', 'closed']
    version: int = Field(ge=1, strict=True)


class ReviewInput(BaseModel):
    status: Literal['unreviewed', 'relevant', 'benign']
    note: str = Field(default='', max_length=4000)
    version: int = Field(ge=1, strict=True)


class AdviceInput(BaseModel):
    external: bool = False
    window_seconds: int = Field(default=300, ge=1, le=86400)
    gap_seconds: int = Field(default=900, ge=1, le=604800)
    bucket_seconds: int = Field(default=60, ge=1, le=86400)


@router.get('/incidents')
def incidents(request: Request, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    authorize(request)
    return catalog.list_incidents(request.app.state.db, limit, offset)


@router.post('/incidents', status_code=201)
def create(request: Request, body: IncidentInput):
    user = authorize(request, 'reviewer')
    return catalog.create_incident(request.app.state.db, body.title, body.description, user['subject'])


@router.get('/incidents/{id}')
def incident(request: Request, id: str):
    authorize(request)
    return catalog.incident(request.app.state.db, id)


@router.patch('/incidents/{id}')
def update(request: Request, id: str, body: IncidentUpdate):
    user = authorize(request, 'reviewer')
    return catalog.update_incident(request.app.state.db, id, body.title, body.description, body.status, body.version, user['subject'])


@router.delete('/incidents/{id}', status_code=204)
def delete(request: Request, id: str):
    user = authorize(request, 'admin')
    catalog.delete_incident(request.app.state.db, id, user['subject'])
    return Response(status_code=204)


@router.post('/incidents/{id}/import')
async def ingest(request: Request, id: str, file: UploadFile = File(...), format: Literal['csv', 'json', 'jsonl'] = Form('csv'),
                 timezone: str = Form('UTC', max_length=100), epoch_unit: Literal['seconds', 'milliseconds'] = Form('seconds'),
                 commit: bool = Form(False)):
    user = authorize(request, 'reviewer')
    catalog.incident(request.app.state.db, id)
    limit = min(request.app.state.settings.max_upload_bytes, MAX_BYTES)
    data = await file.read(limit + 1)
    await file.close()
    if len(data) > limit: raise AppError(413, 'upload_too_large', 'Upload exceeds the configured byte limit')
    try:
        preview = parse_upload(data, format, timezone, epoch_unit)
    except ImportProblem as error:
        raise AppError(422, 'invalid_upload', str(error)) from None
    if not commit:
        return preview
    return catalog.import_events(request.app.state.db, id, preview, format, timezone, epoch_unit, user['subject'])


@router.get('/incidents/{id}/events')
def events(request: Request, id: str, limit: int = Query(200, ge=1, le=1000), offset: int = Query(0, ge=0),
           source: str = Query('', max_length=128), review_status: Literal['', 'unreviewed', 'relevant', 'benign'] = '',
           query: str = Query('', max_length=256)):
    authorize(request)
    return catalog.list_events(request.app.state.db, id, limit, offset, source, review_status, query)


@router.patch('/incidents/{id}/events/{event_id}')
def review(request: Request, id: str, event_id: str, body: ReviewInput):
    user = authorize(request, 'reviewer')
    return catalog.review_event(request.app.state.db, id, event_id, body.status, body.note, body.version, user['subject'])


@router.get('/incidents/{id}/analysis')
def analysis(request: Request, id: str, window_seconds: int = Query(300, ge=1, le=86400),
             gap_seconds: int = Query(900, ge=1, le=604800), bucket_seconds: int = Query(60, ge=1, le=86400)):
    authorize(request)
    return analyze(catalog.all_events(request.app.state.db, id), window_seconds, gap_seconds, bucket_seconds)


@router.get('/incidents/{id}/history')
def history(request: Request, id: str):
    authorize(request)
    return catalog.history(request.app.state.db, id)


@router.get('/incidents/{id}/export')
def export(request: Request, id: str, format: Literal['csv', 'json'] = 'csv'):
    authorize(request)
    case = catalog.incident(request.app.state.db, id)
    rows = catalog.all_events(request.app.state.db, id)
    content = timeline_csv(rows) if format == 'csv' else incident_json(case, rows, analyze(rows))
    return Response(content, media_type='text/csv' if format == 'csv' else 'application/json',
                    headers={'Content-Disposition': f'attachment; filename="incident-{case["id"]}.{format}"',
                             'Cache-Control': 'no-store'})


@router.post('/incidents/{id}/advice')
def advice(request: Request, id: str, body: AdviceInput):
    user = authorize(request, 'reviewer')
    report = analyze(catalog.all_events(request.app.state.db, id), body.window_seconds, body.gap_seconds, body.bucket_seconds)
    result = advise(request.app.state.settings, report, body.external, getattr(request.app.state, 'llm_transport', None))
    with request.app.state.db.transaction() as conn:
        catalog.audit(conn, user['subject'], 'advice.request', id, {'requested_external': body.external, 'mode': result['mode']})
    return result
