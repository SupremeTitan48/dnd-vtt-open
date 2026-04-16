from pathlib import Path

from fastapi import FastAPI

from api.http_api import router as api_router, session_service
from app.migrations.status import migration_status

app = FastAPI(title='DND VTT Service')
app.include_router(api_router)


@app.get('/health')
def health() -> dict:
    return {'ok': True}


@app.get('/health/perf')
def health_perf() -> dict:
    return {'ok': True, **session_service.get_visibility_perf_metrics()}


@app.get('/health/ready')
def health_ready() -> dict:
    checks = {'session_store_dir': False, 'event_log_dir': False, 'migration_compatibility': False}
    try:
        store_dir = Path(session_service.store.base_dir)
        store_dir.mkdir(parents=True, exist_ok=True)
        checks['session_store_dir'] = store_dir.is_dir()
    except OSError:
        checks['session_store_dir'] = False
    try:
        events_dir = session_service.store.base_dir / 'events'
        events_dir.mkdir(parents=True, exist_ok=True)
        checks['event_log_dir'] = events_dir.is_dir()
    except OSError:
        checks['event_log_dir'] = False
    migration = migration_status(session_service.sessions)
    checks['migration_compatibility'] = bool(migration.get('compatible', False))
    return {'ok': all(checks.values()), 'checks': checks, 'migration': migration}
