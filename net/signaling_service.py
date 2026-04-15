from fastapi import FastAPI

from api.http_api import router as api_router

app = FastAPI(title='DND VTT Service')
app.include_router(api_router)


@app.get('/health')
def health() -> dict:
    return {'ok': True}
