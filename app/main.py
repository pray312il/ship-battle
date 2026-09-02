from fastapi import FastAPI
from app.routers import game_route

app = FastAPI(
    title="Battleship"
)

app.include_router(game_route.router)

@app.get("/health")
def healts():
    return {"status" : "OK"}