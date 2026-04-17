from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from api.http_api import _ops_state_store, router as api_router, session_service
from app.backup_rate_limit_config import get_backup_rate_limit_config
from app.migrations.status import migration_status

app = FastAPI(title='DND VTT Service')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://127.0.0.1:5173', 'http://localhost:5173', 'null'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(api_router)


@app.get('/health')
def health() -> dict:
    return {'ok': True}


@app.get('/health/perf')
def health_perf() -> dict:
    total, actions = _ops_state_store.get_backup_audit_summary()
    return {
        'ok': True,
        **session_service.get_visibility_perf_metrics(),
        'backup_audit_events_total': total,
        'backup_audit_actions': actions,
    }


@app.get('/health/ops')
def health_ops() -> dict:
    max_operations, window_seconds = get_backup_rate_limit_config()
    total, actions = _ops_state_store.get_backup_audit_summary()
    return {
        'ok': True,
        'active_sessions': len(session_service.sessions),
        'backup_audit_events_total': total,
        'backup_audit_actions': actions,
        'backup_rate_limit_config': {'max_operations': max_operations, 'window_seconds': window_seconds},
    }


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


@app.get('/metrics', response_class=PlainTextResponse)
def metrics() -> str:
    perf = session_service.get_visibility_perf_metrics()
    max_operations, window_seconds = get_backup_rate_limit_config()
    total, actions = _ops_state_store.get_backup_audit_summary()
    lines = [
        f'dnd_vtt_active_sessions {len(session_service.sessions)}',
        f'dnd_vtt_visibility_cache_hits {int(perf.get("visibility_cache_hits", 0))}',
        f'dnd_vtt_visibility_cache_misses {int(perf.get("visibility_cache_misses", 0))}',
        f'dnd_vtt_backup_audit_events_total {total}',
        f'dnd_vtt_backup_rate_limit_max {max_operations}',
        f'dnd_vtt_backup_rate_limit_window_seconds {window_seconds}',
    ]
    for action, count in sorted(actions.items()):
        lines.append(f'dnd_vtt_backup_audit_action_total{{action="{action}"}} {count}')
    return '\n'.join(lines) + '\n'
