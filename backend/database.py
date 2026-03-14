import sqlite3
from contextlib import contextmanager

from werkzeug.security import generate_password_hash

from config import DATABASE_PATH


SEED_PRODUCTS = [
    (
        "Base Líquida Glow",
        "Base",
        "Base líquida com acabamento iluminado.",
        59.9,
        25,
        10,
        "images/base-glow.svg",
        "BASE-GLOW-001",
        "",
        "",
        1,
    ),
    (
        "Paleta Aurora 12 Cores",
        "Olhos",
        "Paleta com 12 tons versáteis para maquiagem.",
        89.9,
        40,
        8,
        "images/paleta-aurora.svg",
        "PALETA-AURORA-012",
        "",
        "",
        1,
    ),
    (
        "Batom Matte Rosé",
        "Lábios",
        "Batom matte de longa duração.",
        34.9,
        15,
        12,
        "images/batom-rose.svg",
        "BATOM-ROSE-001",
        "",
        "",
        1,
    ),
]

DEFAULT_COMPANY_NAME = "Aurora Makes"
DEFAULT_COMPANY_SLUG = "aurora-makes"
DEFAULT_ADMIN_USERNAME = "admin@auroramakes.com"
DEFAULT_ADMIN_EMAIL = "admin@auroramakes.com"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_ADMIN_ROLE = "super_admin"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def _add_column_if_missing(conn, table_name, column_name, definition):
    columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    current_columns = {column["name"] for column in columns}
    if column_name not in current_columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def ensure_default_admin(conn):
    company = conn.execute(
        "SELECT id FROM companies WHERE slug = ? LIMIT 1",
        (DEFAULT_COMPANY_SLUG,),
    ).fetchone()

    if company:
        company_id = int(company["id"])
        conn.execute(
            "UPDATE companies SET name = ?, is_active = 1 WHERE id = ?",
            (DEFAULT_COMPANY_NAME, company_id),
        )
    else:
        cursor = conn.execute(
            "INSERT INTO companies (name, slug, is_active) VALUES (?, ?, 1)",
            (DEFAULT_COMPANY_NAME, DEFAULT_COMPANY_SLUG),
        )
        company_id = int(cursor.lastrowid)

    password_hash = generate_password_hash(DEFAULT_ADMIN_PASSWORD)
    admin_user = conn.execute(
        "SELECT id FROM users WHERE company_id = ? AND LOWER(email) = LOWER(?) LIMIT 1",
        (company_id, DEFAULT_ADMIN_EMAIL),
    ).fetchone()

    if admin_user:
        conn.execute(
            """
            UPDATE users
            SET username = ?,
                email = ?,
                role = ?,
                is_active = 1,
                password_hash = ?
            WHERE id = ?
            """,
            (DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_ROLE, password_hash, int(admin_user["id"])),
        )
        return

    conn.execute(
        """
        INSERT INTO users (company_id, username, email, password_hash, role, is_active)
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        (company_id, DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_EMAIL, password_hash, DEFAULT_ADMIN_ROLE),
    )


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                is_active INTEGER NOT NULL DEFAULT 1,
                last_login_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE,
                UNIQUE(company_id, username),
                UNIQUE(company_id, email)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL DEFAULT 1,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT DEFAULT '',
                price REAL NOT NULL,
                cost REAL NOT NULL DEFAULT 0,
                stock INTEGER NOT NULL DEFAULT 0,
                image_url TEXT DEFAULT '',
                sku TEXT DEFAULT '',
                barcode TEXT DEFAULT '',
                supplier_reference TEXT DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL DEFAULT 1,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                customer_address TEXT NOT NULL,
                total REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                source TEXT NOT NULL DEFAULT 'aurora_makes',
                external_order_id TEXT DEFAULT '',
                payment_status TEXT NOT NULL DEFAULT 'pending',
                payment_method TEXT DEFAULT '',
                shipping_method TEXT DEFAULT '',
                shipping_tracking_code TEXT DEFAULT '',
                shipping_label_url TEXT DEFAULT '',
                shipping_status TEXT NOT NULL DEFAULT 'pending',
                internal_notes TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL DEFAULT 1,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY(product_id) REFERENCES products(id),
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL DEFAULT 1,
                payment_id TEXT NOT NULL UNIQUE,
                order_id INTEGER,
                amount REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                payment_method TEXT DEFAULT '',
                source TEXT NOT NULL DEFAULT 'aurora_makes',
                customer_phone TEXT DEFAULT '',
                raw_payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE SET NULL,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL DEFAULT 1,
                product_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                source TEXT DEFAULT 'manual',
                reference_id TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_id) REFERENCES products(id),
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS product_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL DEFAULT 1,
                product_id INTEGER NOT NULL,
                channel_name TEXT NOT NULL,
                external_product_id TEXT NOT NULL,
                external_sku TEXT DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE,
                UNIQUE(product_id, channel_name, external_product_id)
            )
            """
        )

        conn.execute(
            "INSERT OR IGNORE INTO companies (id, name, slug, is_active) VALUES (1, 'Aurora Makes', 'aurora-makes', 1)"
        )

        # Compatibilidade com bancos antigos
        _add_column_if_missing(conn, "products", "sku", "TEXT DEFAULT ''")
        _add_column_if_missing(conn, "products", "barcode", "TEXT DEFAULT ''")
        _add_column_if_missing(conn, "products", "supplier_reference", "TEXT DEFAULT ''")
        _add_column_if_missing(conn, "products", "company_id", "INTEGER NOT NULL DEFAULT 1")

        _add_column_if_missing(conn, "orders", "source", "TEXT NOT NULL DEFAULT 'aurora_makes'")
        _add_column_if_missing(conn, "orders", "external_order_id", "TEXT DEFAULT ''")
        _add_column_if_missing(conn, "orders", "payment_status", "TEXT NOT NULL DEFAULT 'pending'")
        _add_column_if_missing(conn, "orders", "payment_method", "TEXT DEFAULT ''")
        _add_column_if_missing(conn, "orders", "shipping_method", "TEXT DEFAULT ''")
        _add_column_if_missing(conn, "orders", "shipping_tracking_code", "TEXT DEFAULT ''")
        _add_column_if_missing(conn, "orders", "shipping_label_url", "TEXT DEFAULT ''")
        _add_column_if_missing(conn, "orders", "shipping_status", "TEXT NOT NULL DEFAULT 'pending'")
        _add_column_if_missing(conn, "orders", "internal_notes", "TEXT DEFAULT ''")
        _add_column_if_missing(conn, "orders", "company_id", "INTEGER NOT NULL DEFAULT 1")

        _add_column_if_missing(conn, "stock_movements", "source", "TEXT DEFAULT 'manual'")
        _add_column_if_missing(conn, "stock_movements", "reference_id", "TEXT DEFAULT ''")
        _add_column_if_missing(conn, "stock_movements", "company_id", "INTEGER NOT NULL DEFAULT 1")

        _add_column_if_missing(conn, "order_items", "company_id", "INTEGER NOT NULL DEFAULT 1")
        _add_column_if_missing(conn, "payments", "company_id", "INTEGER NOT NULL DEFAULT 1")
        _add_column_if_missing(conn, "product_channels", "company_id", "INTEGER NOT NULL DEFAULT 1")

        count = conn.execute("SELECT COUNT(*) as total FROM products WHERE company_id = 1").fetchone()["total"]
        if count == 0:
            conn.executemany(
                """
                INSERT INTO products (
                    company_id,
                    name,
                    category,
                    description,
                    price,
                    cost,
                    stock,
                    image_url,
                    sku,
                    barcode,
                    supplier_reference,
                    is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [(1, *product) for product in SEED_PRODUCTS],
            )

        ensure_default_admin(conn)

        conn.commit()
