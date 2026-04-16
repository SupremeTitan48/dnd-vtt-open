from fastapi import FastAPI

from api.http_api import router as api_router, session_service

app = FastAPI(title='DND VTT Service')
app.include_router(api_router)


@app.get('/health')
def health() -> dict:
    return {'ok': True}


@app.get('/health/perf')
def health_perf() -> dict:
    return {'ok': True, **session_service.get_visibility_perf_metrics()}
