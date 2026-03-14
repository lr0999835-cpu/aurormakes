from flask import Blueprint, jsonify, request

from services import create_product, delete_product, list_products, update_product

products_bp = Blueprint("products_api", __name__, url_prefix="/api/products")


@products_bp.get("")
def get_products():
    include_inactive = request.args.get("include_inactive") == "1"
    products = list_products(include_inactive=include_inactive)
    return jsonify([product.to_dict() for product in products])


@products_bp.post("")
def post_product():
    payload = request.get_json(silent=True) or {}

    try:
        product = create_product(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(product.to_dict()), 201


@products_bp.put("/<int:product_id>")
def put_product(product_id):
    payload = request.get_json(silent=True) or {}

    try:
        product = update_product(product_id, payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not product:
        return jsonify({"error": "Produto não encontrado"}), 404

    return jsonify(product.to_dict())


@products_bp.delete("/<int:product_id>")
def remove_product(product_id):
    removed = delete_product(product_id)

    if not removed:
        return jsonify({"error": "Produto não encontrado"}), 404

    return jsonify({"message": "Produto removido com sucesso"})
