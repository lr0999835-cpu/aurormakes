from flask import Blueprint, jsonify, request

from services import (
    create_order,
    get_dashboard_data,
    get_sold_products,
    list_low_stock_products,
    list_orders,
    update_order_status,
)

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
    orders = [order.to_dict() for order in list_orders()]
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
