import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "")

DDL = """
CREATE TABLE IF NOT EXISTS watchlist (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) UNIQUE NOT NULL,
    added_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS valuations (
    id  SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    calculated_at TIMESTAMP DEFAULT NOW(),

    -- Inputs (editable overrides)
    current_eps  NUMERIC(12,4),
    eps_growth_rate  NUMERIC(6,4),
    pe_ratio NUMERIC(8,2),
    years INT DEFAULT 10,
    discount_rate NUMERIC(6,4) DEFAULT 0.15,
    margin_of_safety NUMERIC(6,4) DEFAULT 0.50,

"""
