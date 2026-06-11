"""
db.py — PostgreSQL schema + helper functions
Requires: psycopg2-binary
Env: DATABASE_URL=postgresql://user:pass@host:5432/dbname
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "")

DDL = """
CREATE TABLE IF NOT EXISTS watchlist (
    id          SERIAL PRIMARY KEY,
    ticker      VARCHAR(20) UNIQUE NOT NULL,
    added_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS valuations (
    id                      SERIAL PRIMARY KEY,
    ticker                  VARCHAR(20) NOT NULL,
    calculated_at           TIMESTAMP DEFAULT NOW(),

    -- Inputs (editable overrides)
    current_eps             NUMERIC(12,4),
    eps_growth_rate         NUMERIC(6,4),   -- e.g. 0.15 = 15%
    pe_ratio                NUMERIC(8,2),
    years                   INT DEFAULT 10,
    discount_rate           NUMERIC(6,4) DEFAULT 0.15,
    margin_of_safety        NUMERIC(6,4) DEFAULT 0.50,

    -- Outputs
    future_eps              NUMERIC(12,4),
    future_price            NUMERIC(12,4),
    intrinsic_value         NUMERIC(12,4),
    fair_value              NUMERIC(12,4),
    current_price           NUMERIC(12,4),
    upside_pct              NUMERIC(8,4),   -- (fair_value / current_price - 1)
    verdict                 VARCHAR(20),    -- BUY / HOLD / OVERVALUED

    -- Snapshot of raw yfinance data
    raw_data                JSONB,

    UNIQUE (ticker, calculated_at)
);

CREATE INDEX IF NOT EXISTS idx_valuations_ticker ON valuations(ticker);
CREATE INDEX IF NOT EXISTS idx_valuations_ts     ON valuations(calculated_at DESC);
"""


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()


# ---------- Watchlist ----------

def add_ticker(ticker: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO watchlist (ticker) VALUES (%s) ON CONFLICT DO NOTHING",
                (ticker.upper(),)
            )
        conn.commit()


def remove_ticker(ticker: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM watchlist WHERE ticker = %s", (ticker.upper(),))
            cur.execute("DELETE FROM valuations WHERE ticker = %s", (ticker.upper(),))
        conn.commit()


def get_watchlist() -> list[str]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT ticker FROM watchlist ORDER BY added_at")
            return [r[0] for r in cur.fetchall()]


# ---------- Valuations ----------

def save_valuation(data: dict):
    """
    data keys match valuations columns.
    Upserts on (ticker, calculated_at) — uses NOW() so each run inserts a new row.
    """
    cols = [
        "ticker", "current_eps", "eps_growth_rate", "pe_ratio", "years",
        "discount_rate", "margin_of_safety", "future_eps", "future_price",
        "intrinsic_value", "fair_value", "current_price", "upside_pct",
        "verdict", "raw_data"
    ]
    values = [
        data.get("ticker"),
        data.get("current_eps"),
        data.get("eps_growth_rate"),
        data.get("pe_ratio"),
        data.get("years", 10),
        data.get("discount_rate", 0.15),
        data.get("margin_of_safety", 0.50),
        data.get("future_eps"),
        data.get("future_price"),
        data.get("intrinsic_value"),
        data.get("fair_value"),
        data.get("current_price"),
        data.get("upside_pct"),
        data.get("verdict"),
        json.dumps(data.get("raw_data", {}))
    ]
    placeholders = ", ".join(["%s"] * len(cols))
    col_str = ", ".join(cols)
    sql = f"INSERT INTO valuations ({col_str}) VALUES ({placeholders})"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, values)
        conn.commit()


def get_latest_valuation(ticker: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM valuations
                WHERE ticker = %s
                ORDER BY calculated_at DESC
                LIMIT 1
                """,
                (ticker.upper(),)
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_valuation_history(ticker: str, limit: int = 30) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT calculated_at, current_price, intrinsic_value, fair_value, upside_pct
                FROM valuations
                WHERE ticker = %s
                ORDER BY calculated_at DESC
                LIMIT %s
                """,
                (ticker.upper(), limit)
            )
            return [dict(r) for r in cur.fetchall()]


def get_all_latest_valuations(tickers: list[str]) -> list[dict]:
    if not tickers:
        return []
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (ticker)
                    ticker, current_price, intrinsic_value, fair_value,
                    upside_pct, verdict, calculated_at,
                    current_eps, eps_growth_rate, pe_ratio
                FROM valuations
                WHERE ticker = ANY(%s)
                ORDER BY ticker, calculated_at DESC
                """,
                (tickers,)
            )
            return [dict(r) for r in cur.fetchall()]