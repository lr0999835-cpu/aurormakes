import hashlib
import hmac
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from config import PAYMENT_WEBHOOK_HEADER, PAYMENT_WEBHOOK_SECRET, STORE_PUBLIC_URL
from database import get_connection
from payment_services.payments.gateways import build_gateway

logger = logging.getLogger(__name__)
BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")
PAYMENT_STATUSES = {"pendente", "aguardando_pagamento", "pago", "aprovado", "recusado", "cancelado", "estornado", "expirado"}
METHODS = {"pix", "cartao", "boleto"}


def now_iso_brt():
    return datetime.now(BRAZIL_TZ).isoformat(timespec="seconds")


def normalize_payment_status(value: str):
    raw = (value or "").strip().lower()
    map_status = {
        "pending": "pendente",
        "in_process": "aguardando_pagamento",
        "approved": "aprovado",
        "paid": "pago",
        "rejected": "recusado",
        "cancelled": "cancelado",
        "cancelado": "cancelado",
        "refunded": "estornado",
        "charged_back": "estornado",
        "expired": "expirado",
    }
    normalized = map_status.get(raw, raw)
    return normalized if normalized in PAYMENT_STATUSES else "pendente"


def validate_webhook(request):
    if not PAYMENT_WEBHOOK_SECRET:
        return True
    header_value = request.headers.get(PAYMENT_WEBHOOK_HEADER, "")
    expected = PAYMENT_WEBHOOK_SECRET
    if header_value == expected:
        return True

    body = request.get_data(as_text=True) or ""
    digest = hmac.new(expected.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(header_value, digest)


def _payment_row_to_dict(row):
    raw_payload = row["raw_payload"] or "{}"
    try:
        parsed_payload = json.loads(raw_payload)
    except (TypeError, json.JSONDecodeError):
        parsed_payload = {}
    checkout_payload = parsed_payload.get("checkout_payment") if isinstance(parsed_payload, dict) else {}
    if not isinstance(checkout_payload, dict):
        checkout_payload = {}

    amount = float(row["amount"] or 0)
    status = row["status"]
    payment_method = row["payment_method"]
    gateway = row["gateway"]
    return {
        "id": int(row["id"]),
        "order_id": int(row["order_id"]) if row["order_id"] else None,
        "payment_id": row["payment_id"],
        "gateway": gateway,
        "payment_gateway": gateway,
        "transaction_id": row["transaction_id"] or "",
        "payment_method": payment_method,
        "amount": amount,
        "payment_amount": amount,
        "status": status,
        "payment_status": status,
        "payment_payload": checkout_payload,
        "pix_qr_code": row["pix_qr_code"] or "",
        "pix_copy_paste": row["pix_copy_paste"] or "",
        "boleto_barcode": row["boleto_barcode"] or "",
        "boleto_url": row["boleto_url"] or "",
        "expires_at": row["expires_at"] or "",
        "approved_at": row["approved_at"] or "",
        "cancelled_at": row["cancelled_at"] or "",
        "gateway_response": json.loads(row["gateway_response"] or "{}"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_payment_for_order(company_id: int, order: dict, method: str, customer: dict, card_data: dict | None = None, checkout_payment: dict | None = None):
    method = (method or "").strip().lower()
    aliases = {"card": "cartao", "credito": "cartao", "credit_card": "cartao", "boleto_bancario": "boleto"}
    method = aliases.get(method, method)
    if method not in METHODS:
        raise ValueError("Método de pagamento inválido. Use pix, cartao ou boleto.")

    gateway = build_gateway()
    checkout_payment = checkout_payment if isinstance(checkout_payment, dict) else {}
    payment_gateway = str(checkout_payment.get("payment_gateway") or "mercadopago").strip().lower() or "mercadopago"
    metadata = {
        "order_id": order["id"],
        "order_number": f"#{order['id']}",
        "webhook_url": f"{STORE_PUBLIC_URL}/api/payments/webhook",
    }

    gateway_response = gateway.create_payment(
        amount_brl=float(order["total"]),
        description=f"Pedido Aurora Makes #{order['id']}",
        method=method,
        customer=customer,
        metadata=metadata,
        card_data=card_data,
    )

    payment_status = normalize_payment_status(gateway_response.status)
    payment_id = gateway_response.transaction_id or f"local_{order['id']}_{method}"

    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO payments (
                id, company_id, payment_id, order_id, amount, status, payment_method, source,
                customer_phone, raw_payload, gateway, transaction_id, gateway_response,
                webhook_payload, pix_qr_code, pix_copy_paste, boleto_barcode, boleto_url,
                expires_at, approved_at, cancelled_at, created_at, updated_at
            )
            VALUES (
                (SELECT id FROM payments WHERE company_id = ? AND order_id = ?),
                ?, ?, ?, ?, ?, ?, 'aurora_makes', ?, ?, ?, ?, ?, '{}', ?, ?, ?, ?, ?,
                CASE WHEN ? IN ('pago','aprovado') THEN ? ELSE NULL END,
                CASE WHEN ? = 'cancelado' THEN ? ELSE NULL END,
                COALESCE((SELECT created_at FROM payments WHERE company_id = ? AND order_id = ?), ?),
                ?
            )
            """,
            (
                int(company_id), int(order["id"]),
                int(company_id), payment_id, int(order["id"]), float(order["total"]), payment_status,
                method, customer.get("phone") or order.get("customer_phone") or "", json.dumps({"gateway_payload": gateway_response.payload, "checkout_payment": checkout_payment}, ensure_ascii=False),
                payment_gateway, gateway_response.transaction_id, json.dumps(gateway_response.payload, ensure_ascii=False),
                gateway_response.qr_code_base64, gateway_response.qr_code_text, gateway_response.boleto_barcode,
                gateway_response.boleto_url, gateway_response.expires_at,
                payment_status, now_iso_brt(), payment_status, now_iso_brt(),
                int(company_id), int(order["id"]), now_iso_brt(), now_iso_brt(),
            ),
        )
        conn.execute(
            """
            INSERT INTO payment_events (company_id, order_id, payment_id, event_type, status, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(company_id), int(order["id"]), payment_id, "checkout_criado", payment_status,
                json.dumps(gateway_response.payload, ensure_ascii=False), now_iso_brt(),
            ),
        )

        conn.execute(
            """
            UPDATE orders
            SET payment_status = ?,
                payment_method = ?,
                transaction_id = ?,
                approved_at = CASE WHEN ? IN ('pago','aprovado') THEN ? ELSE approved_at END,
                cancelled_at = CASE WHEN ? = 'cancelado' THEN ? ELSE cancelled_at END,
                updated_at = ?
            WHERE company_id = ? AND id = ?
            """,
            (
                payment_status, method, gateway_response.transaction_id,
                payment_status, now_iso_brt(), payment_status, now_iso_brt(), now_iso_brt(),
                int(company_id), int(order["id"]),
            ),
        )
        conn.commit()

        row = conn.execute("SELECT * FROM payments WHERE company_id = ? AND order_id = ?", (int(company_id), int(order["id"]))).fetchone()

    return {
        "success": gateway_response.success,
        "message": gateway_response.error_message or "Pagamento criado com sucesso.",
        "payment": _payment_row_to_dict(row) if row else None,
    }


def process_webhook_event(company_id: int, payload: dict):
    payment_id = str(payload.get("payment_id") or payload.get("data", {}).get("id") or payload.get("id") or "").strip()
    if not payment_id:
        raise ValueError("payment_id é obrigatório no webhook")

    status = normalize_payment_status(payload.get("status") or payload.get("action") or "pendente")
    transaction_id = str(payload.get("transaction_id") or payload.get("id") or payment_id)

    with get_connection() as conn:
        payment = conn.execute(
            "SELECT * FROM payments WHERE company_id = ? AND (payment_id = ? OR transaction_id = ?) ORDER BY id DESC LIMIT 1",
            (int(company_id), payment_id, transaction_id),
        ).fetchone()
        if not payment:
            raise ValueError("Pagamento não encontrado")

        order_id = int(payment["order_id"])
        now = now_iso_brt()
        conn.execute(
            """
            UPDATE payments
            SET status = ?, transaction_id = ?, webhook_payload = ?, updated_at = ?,
                approved_at = CASE WHEN ? IN ('pago','aprovado') THEN ? ELSE approved_at END,
                cancelled_at = CASE WHEN ? IN ('cancelado','estornado') THEN ? ELSE cancelled_at END
            WHERE id = ?
            """,
            (status, transaction_id, json.dumps(payload, ensure_ascii=False), now, status, now, status, now, int(payment["id"])),
        )
        conn.execute(
            """
            UPDATE orders
            SET payment_status = ?, transaction_id = ?,
                status = CASE WHEN ? IN ('pago','aprovado') THEN 'aprovado' WHEN ? IN ('recusado','cancelado','estornado','expirado') THEN 'cancelado' ELSE status END,
                approved_at = CASE WHEN ? IN ('pago','aprovado') THEN ? ELSE approved_at END,
                cancelled_at = CASE WHEN ? IN ('cancelado','estornado') THEN ? ELSE cancelled_at END,
                updated_at = ?
            WHERE company_id = ? AND id = ?
            """,
            (status, transaction_id, status, status, status, now, status, now, now, int(company_id), order_id),
        )
        conn.execute(
            """
            INSERT INTO payment_events (company_id, order_id, payment_id, event_type, status, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (int(company_id), order_id, payment_id, "webhook", status, json.dumps(payload, ensure_ascii=False), now),
        )
        conn.commit()
        result = conn.execute("SELECT * FROM payments WHERE id = ?", (int(payment["id"]),)).fetchone()
    return _payment_row_to_dict(result)


def list_recent_payments(company_id: int, status: str | None = None, method: str | None = None, q: str | None = None, limit: int = 100):
    query = """
    SELECT p.*, o.id as order_number, o.customer_name
    FROM payments p
    LEFT JOIN orders o ON o.id = p.order_id
    WHERE p.company_id = ?
    """
    params = [int(company_id)]
    if status:
        query += " AND p.status = ?"
        params.append(status)
    if method:
        query += " AND p.payment_method = ?"
        params.append(method)
    if q:
        query += " AND (CAST(o.id AS TEXT) = ? OR p.transaction_id = ? OR p.payment_id = ?)"
        params.extend([q, q, q])
    query += " ORDER BY p.updated_at DESC LIMIT ?"
    params.append(int(limit))

    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()

    return [
        {
            **_payment_row_to_dict(row),
            "order_number": int(row["order_number"]) if row["order_number"] else None,
            "customer_name": row["customer_name"] or "",
        }
        for row in rows
    ]


def get_payment_events(company_id: int, order_id: int):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM payment_events WHERE company_id = ? AND order_id = ? ORDER BY id DESC",
            (int(company_id), int(order_id)),
        ).fetchall()
    return [
        {
            "event_type": row["event_type"],
            "status": row["status"],
            "payload": json.loads(row["payload"] or "{}"),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def payment_totals(company_id: int):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT status, payment_method, COALESCE(SUM(amount),0) as total, COUNT(*) as count FROM payments WHERE company_id = ? GROUP BY status, payment_method",
            (int(company_id),),
        ).fetchall()
        paid_today = conn.execute(
            "SELECT COUNT(*) as count FROM payments WHERE company_id = ? AND status IN ('pago','aprovado') AND DATE(approved_at) = DATE('now', '-3 hours')",
            (int(company_id),),
        ).fetchone()
        paid_month = conn.execute(
            "SELECT COUNT(*) as count FROM payments WHERE company_id = ? AND status IN ('pago','aprovado') AND strftime('%Y-%m', approved_at) = strftime('%Y-%m', 'now', '-3 hours')",
            (int(company_id),),
        ).fetchone()

    totals = {"pago": 0, "pendente": 0, "recusado": 0, "cancelado": 0, "metodos": {}}
    for row in rows:
        status = row["status"]
        method = row["payment_method"] or "nao_informado"
        value = float(row["total"] or 0)
        if status in {"pago", "aprovado"}:
            totals["pago"] += value
        elif status in {"pendente", "aguardando_pagamento"}:
            totals["pendente"] += value
        elif status == "recusado":
            totals["recusado"] += value
        elif status in {"cancelado", "estornado", "expirado"}:
            totals["cancelado"] += value
        totals["metodos"].setdefault(method, 0)
        totals["metodos"][method] += value

    totals["pedidos_pagos_hoje"] = int(paid_today["count"] or 0)
    totals["pedidos_pagos_mes"] = int(paid_month["count"] or 0)
    return totals
