from fastapi import FastAPI

app = FastAPI(title="NekoGames API")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
