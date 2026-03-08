from __future__ import annotations

import json
import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import db
from app.telegram_auth import TelegramAuthError, verify_init_data


app = FastAPI(title="NekoGames API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class User(BaseModel):
    id: int
    tg_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class Mode(BaseModel):
    id: int
    name: str
    shots: int
    win_value_min: int


class SessionCreate(BaseModel):
    mode_id: int


class Throw(BaseModel):
    shot_index: int
    dice_value: int
    is_hit: bool


class SessionOut(BaseModel):
    id: int
    status: str
    shots: int
    win_value_min: int
    hits: int
    created_at: str
    finished_at: str | None
    throws: list[Throw]


def _get_init_data(x_telegram_init_data: str | None = Header(default=None)) -> dict[str, str]:
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="initData required")

    try:
        max_age = int(os.getenv("INITDATA_MAX_AGE", "86400"))
        return verify_init_data(x_telegram_init_data, max_age_seconds=max_age)
    except TelegramAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _upsert_user(user_data: dict[str, Any]) -> dict[str, Any]:
    tg_id = int(user_data["id"])
    username = user_data.get("username")
    first_name = user_data.get("first_name")
    last_name = user_data.get("last_name")

    row = db.fetch_one("SELECT * FROM users WHERE tg_id = %s", [tg_id])
    if row:
        db.execute(
            "UPDATE users SET username=%s, first_name=%s, last_name=%s WHERE tg_id=%s",
            [username, first_name, last_name, tg_id],
        )
        row.update({"username": username, "first_name": first_name, "last_name": last_name})
        return row

    db.execute(
        "INSERT INTO users (tg_id, username, first_name, last_name) VALUES (%s, %s, %s, %s)",
        [tg_id, username, first_name, last_name],
    )
    return db.fetch_one("SELECT * FROM users WHERE tg_id = %s", [tg_id])


@app.on_event("startup")
def on_startup() -> None:
    db.init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/modes", response_model=list[Mode])
def list_modes() -> list[dict[str, Any]]:
    return db.fetch_all("SELECT * FROM modes ORDER BY shots ASC")


@app.get("/me", response_model=User)
def me(init_data: dict[str, str] = Depends(_get_init_data)) -> dict[str, Any]:
    user_data = json.loads(init_data["user"])
    return _upsert_user(user_data)


@app.post("/sessions", response_model=SessionOut)
def create_session(payload: SessionCreate, init_data: dict[str, str] = Depends(_get_init_data)) -> dict[str, Any]:
    user_data = json.loads(init_data["user"])
    user = _upsert_user(user_data)

    mode = db.fetch_one("SELECT * FROM modes WHERE id = %s", [payload.mode_id])
    if not mode:
        raise HTTPException(status_code=404, detail="mode not found")

    db.execute(
        """
        INSERT INTO sessions (user_id, mode_id, shots, win_value_min)
        VALUES (%s, %s, %s, %s)
        """,
        [user["id"], mode["id"], mode["shots"], mode["win_value_min"]],
    )
    session = db.fetch_one(
        "SELECT * FROM sessions WHERE user_id=%s ORDER BY id DESC LIMIT 1",
        [user["id"]],
    )
    session["throws"] = []
    return session


@app.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: int, init_data: dict[str, str] = Depends(_get_init_data)) -> dict[str, Any]:
    user_data = json.loads(init_data["user"])
    user = _upsert_user(user_data)

    session = db.fetch_one("SELECT * FROM sessions WHERE id=%s AND user_id=%s", [session_id, user["id"]])
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    throws = db.fetch_all(
        "SELECT shot_index, dice_value, is_hit FROM throws WHERE session_id=%s ORDER BY shot_index ASC",
        [session_id],
    )
    session["throws"] = throws
    return session
