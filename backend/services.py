from collections import defaultdict

from database import get_connection
from models import Order, Product


REQUIRED_FIELDS = ["name", "category", "price", "cost", "stock"]
ORDER_STATUSES = ["pending", "paid", "preparing", "ready_to_ship", "shipped", "delivered", "cancelled"]
LOW_STOCK_LIMIT = 3


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
    if not include_inactive:
        query += " WHERE is_active = 1"
    query += " ORDER BY created_at DESC"

    with get_connection() as conn:
        rows = conn.execute(query).fetchall()

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


def create_stock_movement(conn, product_id, movement_type, quantity, notes=""):
    conn.execute(
        """
        INSERT INTO stock_movements (product_id, movement_type, quantity, notes)
        VALUES (?, ?, ?, ?)
        """,
        (int(product_id), movement_type, int(quantity), notes),
    )


def update_product_stock(product_id, stock, notes="Ajuste manual de estoque"):
    stock_value = int(stock)
    if stock_value < 0:
        raise ValueError("Estoque deve ser maior ou igual a 0")

    with get_connection() as conn:
        row = conn.execute("SELECT stock FROM products WHERE id = ?", (product_id,)).fetchone()
        if not row:
            return False

        old_stock = int(row["stock"])
        delta = stock_value - old_stock

        conn.execute(
            "UPDATE products SET stock = ? WHERE id = ?",
            (stock_value, product_id),
        )

        if delta != 0:
            movement = "manual_in" if delta > 0 else "manual_out"
            create_stock_movement(conn, product_id, movement, abs(delta), notes)

        conn.commit()

    return True


def _normalize_order_payload(payload):
    items = payload.get("items") or []
    return {
        "customer_name": (payload.get("customer_name") or "").strip(),
        "customer_phone": (payload.get("customer_phone") or "").strip(),
        "customer_address": (payload.get("customer_address") or "").strip(),
        "items": items,
    }


def create_order(payload):
    data = _normalize_order_payload(payload)

    if not data["customer_name"] or not data["customer_phone"] or not data["customer_address"]:
        raise ValueError("Dados do cliente são obrigatórios")

    if not isinstance(data["items"], list) or not data["items"]:
        raise ValueError("Pedido inválido: carrinho vazio")

    with get_connection() as conn:
        product_ids = [int(item.get("product_id", 0)) for item in data["items"]]
        placeholders = ",".join(["?"] * len(product_ids))
        rows = conn.execute(
            f"SELECT * FROM products WHERE id IN ({placeholders})",
            tuple(product_ids),
        ).fetchall()

        products_by_id = {int(row["id"]): row for row in rows}
        normalized_items = []
        total = 0.0

        for item in data["items"]:
            product_id = int(item.get("product_id", 0))
            quantity = int(item.get("quantity", 0))

            if quantity <= 0:
                raise ValueError("Quantidade inválida")

            product = products_by_id.get(product_id)
            if not product or int(product["is_active"]) != 1:
                raise ValueError(f"Produto inválido: {product_id}")

            if int(product["stock"]) < quantity:
                raise ValueError(f"Estoque insuficiente para {product['name']}")

            price = float(product["price"])
            total += price * quantity
            normalized_items.append({
                "product_id": product_id,
                "name": product["name"],
                "quantity": quantity,
                "price": price,
            })

        order_cursor = conn.execute(
            """
            INSERT INTO orders (customer_name, customer_phone, customer_address, total, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (data["customer_name"], data["customer_phone"], data["customer_address"], total, "pending"),
        )
        order_id = order_cursor.lastrowid

        for item in normalized_items:
            conn.execute(
                """
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)
                """,
                (order_id, item["product_id"], item["quantity"], item["price"]),
            )
            conn.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )
            create_stock_movement(
                conn,
                item["product_id"],
                "order_out",
                item["quantity"],
                f"Baixa automática do pedido #{order_id}",
            )

        conn.commit()

    return get_order(order_id)


def list_orders(limit=None):
    query = "SELECT * FROM orders ORDER BY created_at DESC, id DESC"
    params = ()
    if limit:
        query += " LIMIT ?"
        params = (int(limit),)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return [Order.from_row(row) for row in rows]


def get_order(order_id):
    with get_connection() as conn:
        order_row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order_row:
            return None

        item_rows = conn.execute(
            """
            SELECT oi.*, p.name as product_name
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            WHERE oi.order_id = ?
            ORDER BY oi.id ASC
            """,
            (order_id,),
        ).fetchall()

    order = Order.from_row(order_row).to_dict()
    order["items"] = [
        {
            "id": int(row["id"]),
            "product_id": int(row["product_id"]),
            "product_name": row["product_name"],
            "quantity": int(row["quantity"]),
            "price": float(row["price"]),
        }
        for row in item_rows
    ]
    return order


def update_order_status(order_id, status):
    if status not in ORDER_STATUSES:
        raise ValueError("Status inválido")

    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status, order_id),
        )
        conn.commit()

    if cursor.rowcount == 0:
        return None

    return get_order(order_id)


def list_low_stock_products(limit=20):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM products
            WHERE is_active = 1 AND stock <= ?
            ORDER BY stock ASC, name ASC
            LIMIT ?
            """,
            (LOW_STOCK_LIMIT, int(limit)),
        ).fetchall()

    return [Product.from_row(row) for row in rows]


def get_dashboard_data():
    with get_connection() as conn:
        sales_today = conn.execute(
            "SELECT COUNT(*) as count, COALESCE(SUM(total), 0) as revenue FROM orders WHERE DATE(created_at) = DATE('now')"
        ).fetchone()
        sales_total = conn.execute(
            "SELECT COUNT(*) as count, COALESCE(SUM(total), 0) as revenue FROM orders"
        ).fetchone()
        cost_row = conn.execute(
            """
            SELECT COALESCE(SUM(oi.quantity * p.cost), 0) as total_cost
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            """
        ).fetchone()
        products_sold_row = conn.execute("SELECT COALESCE(SUM(quantity), 0) as qty FROM order_items").fetchone()

        best_sellers_rows = conn.execute(
            """
            SELECT p.name, SUM(oi.quantity) as sold
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            GROUP BY oi.product_id
            ORDER BY sold DESC
            LIMIT 5
            """
        ).fetchall()

        pending_orders = conn.execute("SELECT COUNT(*) as total FROM orders WHERE status = 'pending'").fetchone()["total"]
        ready_orders = conn.execute("SELECT COUNT(*) as total FROM orders WHERE status = 'ready_to_ship'").fetchone()["total"]
        out_of_stock = conn.execute("SELECT COUNT(*) as total FROM products WHERE is_active = 1 AND stock = 0").fetchone()["total"]

        recent = conn.execute("SELECT * FROM orders ORDER BY created_at DESC, id DESC LIMIT 5").fetchall()

    total_revenue = float(sales_total["revenue"])
    total_cost = float(cost_row["total_cost"])

    return {
        "sales_today": int(sales_today["count"]),
        "sales_total_count": int(sales_total["count"]),
        "total_revenue": total_revenue,
        "estimated_profit": total_revenue - total_cost,
        "products_sold": int(products_sold_row["qty"]),
        "best_sellers": [{"name": row["name"], "sold": int(row["sold"])} for row in best_sellers_rows],
        "low_stock_products": [product.to_dict() for product in list_low_stock_products(limit=50)],
        "out_of_stock_products": int(out_of_stock),
        "pending_orders": int(pending_orders),
        "ready_to_ship_orders": int(ready_orders),
        "recent_orders": [Order.from_row(row).to_dict() for row in recent],
    }


def get_sold_products():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.name, SUM(oi.quantity) as quantity, SUM(oi.quantity * oi.price) as revenue
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            GROUP BY p.id, p.name
            ORDER BY quantity DESC
            """
        ).fetchall()

    return [
        {
            "product_id": int(row["id"]),
            "name": row["name"],
            "quantity": int(row["quantity"]),
            "revenue": float(row["revenue"]),
        }
        for row in rows
    ]
