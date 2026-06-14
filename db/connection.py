from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"))

def init_db():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vmi_scores (
                id               SERIAL PRIMARY KEY,
                ticker           VARCHAR(10) NOT NULL,
                run_at           TIMESTAMP DEFAULT NOW(),
                quality_score    INT,
                valuation_score  INT,
                momentum_score   INT,
                total_score      INT,
                decision         VARCHAR(20),
                dcf_value        NUMERIC(10,2),
                current_price    NUMERIC(10,2),
                margin_of_safety NUMERIC(6,2),
                raw_data         JSONB
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id        SERIAL PRIMARY KEY,
                ticker    VARCHAR(10) UNIQUE NOT NULL,
                added_at  TIMESTAMP DEFAULT NOW(),
                notes     TEXT
            )
        """))
        conn.commit()