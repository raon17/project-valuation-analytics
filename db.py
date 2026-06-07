import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "valuation_analytics"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "")
}

DDL = """   
CREATE TABLE IF NOT EXISTS watchlist (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) UNIQUE NOT NULL,
    added_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS valuations (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    calculated_at TIMESTAMP DEFAULT NOW(),

    -- Inputs
    current_eps NUMERIC(12,4),
    eps_growth_rate  NUMERIC(6,4),
    pe_ratio NUMERIC(8,2),
    years INT DEFAULT 10,
    discount_rate NUMERIC(6,4) DEFAULT 0.15,
    margin_of_safety NUMERIC(6,4) DEFAULT 0.50,

"""

def get_conn():DATABASE_URL = os.environ.get("DATABASE_URL", "")

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()

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
        conn.commit()
 
def get_watchlist():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT ticker FROM watchlist ORDER BY added_at")
            return [r[0] for r in cur.fetchall()]
 
 