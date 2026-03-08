import asyncio
import json
import os
from contextlib import contextmanager
from typing import Iterable

import psycopg2
from psycopg2.extras import RealDictCursor
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def _env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
WEBAPP_URL = _env("WEBAPP_URL")
DATABASE_URL = _env("DATABASE_URL")


@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


def _fetch_all(query: str, params: Iterable | None = None):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or [])
            rows = cur.fetchall()
        conn.commit()
    return rows


def _fetch_one(query: str, params: Iterable | None = None):
    rows = _fetch_all(query, params)
    return rows[0] if rows else None


def _execute(query: str, params: Iterable | None = None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or [])
        conn.commit()


def claim_sessions(limit: int = 10):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                WITH cte AS (
                    SELECT id
                    FROM sessions
                    WHERE status = 'pending'
                    ORDER BY created_at
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE sessions s
                SET status = 'running'
                FROM cte
                WHERE s.id = cte.id
                RETURNING s.id, s.user_id, s.shots, s.win_value_min
                """,
                [limit],
            )
            rows = cur.fetchall()
        conn.commit()
    return rows


def get_user_tg_id(user_id: int) -> int:
    row = _fetch_one("SELECT tg_id FROM users WHERE id=%s", [user_id])
    if not row:
        raise RuntimeError("user not found")
    return int(row["tg_id"])


def save_throw(session_id: int, shot_index: int, dice_value: int, is_hit: bool) -> None:
    _execute(
        "INSERT INTO throws (session_id, shot_index, dice_value, is_hit) VALUES (%s, %s, %s, %s)",
        [session_id, shot_index, dice_value, is_hit],
    )


def finish_session(session_id: int, status: str, hits: int) -> None:
    _execute(
        "UPDATE sessions SET status=%s, hits=%s, finished_at=NOW() WHERE id=%s",
        [status, hits, session_id],
    )


async def wait_for_db(max_retries: int = 30) -> None:
    for _ in range(max_retries):
        try:
            _fetch_one("SELECT 1")
            _fetch_one("SELECT 1 FROM modes LIMIT 1")
            return
        except Exception:
            await asyncio.sleep(1)
    raise RuntimeError("DB not ready")


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=WEBAPP_URL))],
        ]
    )
    await message.answer(
        "Привет! Нажми кнопку ниже, чтобы открыть мини-приложение.",
        reply_markup=keyboard,
    )


@dp.message(lambda message: message.web_app_data is not None)
async def webapp_data_handler(message):
    raw = message.web_app_data.data
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {"raw": raw}

    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if len(text) > 3500:
        text = text[:3500] + "...(truncated)"

    await message.answer(f"WebApp debug:\n{text}")


async def process_sessions():
    while True:
        sessions = claim_sessions()
        if not sessions:
            await asyncio.sleep(2)
            continue

        for session in sessions:
            session_id = int(session["id"])
            user_id = int(session["user_id"])
            shots = int(session["shots"])
            win_value_min = int(session["win_value_min"])
            tg_id = get_user_tg_id(user_id)

            hits = 0
            for idx in range(1, shots + 1):
                msg = await bot.send_dice(chat_id=tg_id, emoji="🏀")
                value = msg.dice.value
                is_hit = value >= win_value_min
                if is_hit:
                    hits += 1
                save_throw(session_id, idx, value, is_hit)
                await asyncio.sleep(1.5)

            status = "won" if hits == shots else "lost"
            finish_session(session_id, status, hits)

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Вернуться в приложение", web_app=WebAppInfo(url=WEBAPP_URL))],
                ]
            )
            await bot.send_message(
                chat_id=tg_id,
                text=f"Результат: {'победа' if status == 'won' else 'поражение'} ({hits}/{shots})",
                reply_markup=keyboard,
            )


async def main():
    await wait_for_db()
    asyncio.create_task(process_sessions())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
