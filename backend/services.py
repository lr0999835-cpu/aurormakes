from database import get_connection
from models import Product


REQUIRED_FIELDS = ["name", "category", "price", "cost", "stock"]


def _normalize_payload(payload):
    return {
        "name": (payload.get("name") or "").strip(),
        "category": (payload.get("category") or "").strip(),
        "description": (payload.get("description") or "").strip(),
        "price": float(payload.get("price", 0) or 0),
        "cost": float(payload.get("cost", 0) or 0),
        "stock": int(payload.get("stock", 0) or 0),
        "image_url": (payload.get("image_url") or "").strip(),
        "is_active": 1 if payload.get("is_active", True) else 0,
    }


def validate_product_payload(payload):
    normalized = _normalize_payload(payload)

    for field in REQUIRED_FIELDS:
        if field in ["price", "cost", "stock"]:
            continue
        if not normalized[field]:
            raise ValueError(f"Campo obrigatório: {field}")

    if normalized["price"] < 0 or normalized["cost"] < 0:
        raise ValueError("Preço e custo devem ser maiores ou iguais a 0")

    if normalized["stock"] < 0:
        raise ValueError("Estoque deve ser maior ou igual a 0")

    return normalized


def list_products(include_inactive=False):
    query = "SELECT * FROM products"
    params = []

    if not include_inactive:
        query += " WHERE is_active = 1"

    query += " ORDER BY created_at DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return [Product.from_row(row) for row in rows]


def get_product(product_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    if not row:
        return None

    return Product.from_row(row)


def create_product(payload):
    data = validate_product_payload(payload)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO products (name, category, description, price, cost, stock, image_url, is_active)
            VALUES (:name, :category, :description, :price, :cost, :stock, :image_url, :is_active)
            """,
            data,
        )
        conn.commit()
        product_id = cursor.lastrowid

    return get_product(product_id)


def update_product(product_id, payload):
    if not get_product(product_id):
        return None

    data = validate_product_payload(payload)
    data["id"] = product_id

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE products
            SET name = :name,
                category = :category,
                description = :description,
                price = :price,
                cost = :cost,
                stock = :stock,
                image_url = :image_url,
                is_active = :is_active
            WHERE id = :id
            """,
            data,
        )
        conn.commit()

    return get_product(product_id)


def delete_product(product_id):
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()

    return cursor.rowcount > 0


def set_product_active(product_id, is_active):
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE products SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, product_id),
        )
        conn.commit()

    return cursor.rowcount > 0


def update_product_stock(product_id, stock):
    stock_value = int(stock)
    if stock_value < 0:
        raise ValueError("Estoque deve ser maior ou igual a 0")

    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE products SET stock = ? WHERE id = ?",
            (stock_value, product_id),
        )
        conn.commit()

    return cursor.rowcount > 0
