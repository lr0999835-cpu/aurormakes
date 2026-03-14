from flask import Blueprint, g, jsonify, request
import logging

from auth import api_auth_required, tenant_for_request
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
    company_id = tenant_for_request()
    if not company_id:
        return jsonify({"error": "Empresa inválida"}), 400
    try:
        order = create_order(company_id, payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(order), 201


@operations_bp.get("/orders")
def get_orders():
    company_id = tenant_for_request()
    if not company_id:
        return jsonify([])
    orders = [
        order.to_dict()
        for order in list_orders(
            company_id,
            source=request.args.get("source") or None,
            status=request.args.get("status") or None,
            payment_status=request.args.get("payment_status") or None,
            shipping_status=request.args.get("shipping_status") or None,
            customer_phone=request.args.get("customer_phone") or None,
        )
    ]
    return jsonify(orders)


@operations_bp.put("/orders/<int:order_id>/status")
@api_auth_required("orders:write")
def put_order_status(order_id):
    payload = request.get_json(silent=True) or {}
    company_id = g.current_user["company_id"]
    try:
        order = update_order_status(company_id, order_id, payload.get("status", ""))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not order:
        return jsonify({"error": "Pedido não encontrado"}), 404

    return jsonify(order)


@operations_bp.get("/dashboard")
def get_dashboard():
    company_id = tenant_for_request()
    if not company_id:
        return jsonify({"error": "Empresa inválida"}), 400
    return jsonify(get_dashboard_data(company_id))


@operations_bp.get("/stock/low")
@api_auth_required("stock:read")
def get_low_stock():
    return jsonify([product.to_dict() for product in list_low_stock_products(g.current_user["company_id"])])


@operations_bp.get("/sold-products")
@api_auth_required("dashboard:read")
def sold_products():
    return jsonify(get_sold_products(g.current_user["company_id"]))


@operations_bp.post("/checkout")
def post_checkout():
    payload = request.get_json(silent=True) or {}
    payload.setdefault("source", "aurora_makes")
    company_id = tenant_for_request()
    if not company_id:
        return jsonify({"error": "Empresa inválida"}), 400

    device_type = (request.headers.get("X-Device-Type") or payload.get("device_type") or "unknown").strip().lower()
    logger.info("Iniciando checkout. device_type=%s source=%s", device_type, payload.get("source"))

    try:
        order = create_checkout(company_id, payload)
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
    company_id = tenant_for_request()
    if not company_id:
        return jsonify({"error": "Empresa inválida"}), 400

    logger.info("Webhook de pagamento recebido. payment_id=%s", payload.get("payment_id") or payload.get("paymentId"))

    try:
        result = register_payment_event(company_id, payload)
    except ValueError as exc:
        logger.warning("Webhook inválido: %s", exc)
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Falha ao processar webhook de pagamento")
        return jsonify({"error": "Falha ao processar webhook"}), 500

    return jsonify(result), 200
