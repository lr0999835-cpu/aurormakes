from flask import Blueprint, jsonify, request
import logging

from services import (
    create_checkout,
    create_order,
    get_dashboard_data,
    get_sold_products,
    list_low_stock_products,
    list_orders,
    register_payment_event,
    update_order_status,
)

logger = logging.getLogger(__name__)

operations_bp = Blueprint("operations_api", __name__, url_prefix="/api")


@operations_bp.post("/orders")
def post_order():
    payload = request.get_json(silent=True) or {}
    try:
        order = create_order(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(order), 201


@operations_bp.get("/orders")
def get_orders():
    orders = [
        order.to_dict()
        for order in list_orders(
            source=request.args.get("source") or None,
            status=request.args.get("status") or None,
            payment_status=request.args.get("payment_status") or None,
            shipping_status=request.args.get("shipping_status") or None,
            customer_phone=request.args.get("customer_phone") or None,
        )
    ]
    return jsonify(orders)


@operations_bp.put("/orders/<int:order_id>/status")
def put_order_status(order_id):
    payload = request.get_json(silent=True) or {}
    try:
        order = update_order_status(order_id, payload.get("status", ""))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not order:
        return jsonify({"error": "Pedido não encontrado"}), 404

    return jsonify(order)


@operations_bp.get("/dashboard")
def get_dashboard():
    return jsonify(get_dashboard_data())


@operations_bp.get("/stock/low")
def get_low_stock():
    return jsonify([product.to_dict() for product in list_low_stock_products()])


@operations_bp.get("/sold-products")
def sold_products():
    return jsonify(get_sold_products())


@operations_bp.post("/checkout")
def post_checkout():
    payload = request.get_json(silent=True) or {}
    payload.setdefault("source", "aurora_makes")

    # unifica desktop/mobile no mesmo caminho de regra de negócio
    device_type = (request.headers.get("X-Device-Type") or payload.get("device_type") or "unknown").strip().lower()
    logger.info("Iniciando checkout. device_type=%s source=%s", device_type, payload.get("source"))

    try:
        order = create_checkout(payload)
    except ValueError as exc:
        logger.warning("Falha de validação no checkout: %s", exc)
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Erro inesperado ao processar checkout")
        return jsonify({"error": "Falha ao processar checkout"}), 500

    return jsonify(order), 201


@operations_bp.post("/payments/webhook")
def payment_webhook():
    payload = request.get_json(silent=True) or {}
    logger.info("Webhook de pagamento recebido. payment_id=%s", payload.get("payment_id") or payload.get("paymentId"))

    try:
        result = register_payment_event(payload)
    except ValueError as exc:
        logger.warning("Webhook inválido: %s", exc)
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Falha ao processar webhook de pagamento")
        return jsonify({"error": "Falha ao processar webhook"}), 500

    return jsonify(result), 200
