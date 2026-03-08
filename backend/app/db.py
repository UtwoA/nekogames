import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

import psycopg2
from psycopg2.extras import RealDictCursor


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


@contextmanager
def get_conn():
    conn = psycopg2.connect(_database_url())
    try:
        yield conn
    finally:
        conn.close()


def init_db(retries: int = 30, delay: float = 1.0) -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    sql = schema_path.read_text(encoding="utf-8")

    last_error: Exception | None = None
    for _ in range(retries):
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                conn.commit()
            return
        except Exception as exc:
            last_error = exc
            time.sleep(delay)

    raise RuntimeError("DB init failed") from last_error


def fetch_all(query: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or [])
            rows = cur.fetchall()
        conn.commit()
    return [dict(row) for row in rows]


def fetch_one(query: str, params: Iterable[Any] | None = None) -> dict[str, Any] | None:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or [])
            row = cur.fetchone()
        conn.commit()
    return dict(row) if row else None


def execute(query: str, params: Iterable[Any] | None = None) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or [])
        conn.commit()
