import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routers import game_route

logger = logging.getLogger("app")

app = FastAPI(
    title="Battleship"
)

app.include_router(game_route.router)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url)
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})

@app.get("/health")
def healts():
    return {"status" : "OK"}