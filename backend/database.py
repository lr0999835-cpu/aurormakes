import sqlite3
from contextlib import contextmanager

from config import DATABASE_PATH


SEED_PRODUCTS = [
    ("Base Líquida Glow", "Base", "Base líquida com acabamento iluminado.", 59.9, 25, 10, "images/base-glow.svg", 1),
    ("Paleta Aurora 12 Cores", "Olhos", "Paleta com 12 tons versáteis para maquiagem.", 89.9, 40, 8, "images/paleta-aurora.svg", 1),
    ("Batom Matte Rosé", "Lábios", "Batom matte de longa duração.", 34.9, 15, 12, "images/batom-rose.svg", 1),
]


@contextmanager
def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT DEFAULT '',
                price REAL NOT NULL,
                cost REAL NOT NULL DEFAULT 0,
                stock INTEGER NOT NULL DEFAULT 0,
                image_url TEXT DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        count = conn.execute("SELECT COUNT(*) as total FROM products").fetchone()["total"]
        if count == 0:
            conn.executemany(
                """
                INSERT INTO products (name, category, description, price, cost, stock, image_url, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                SEED_PRODUCTS,
            )

        conn.commit()
