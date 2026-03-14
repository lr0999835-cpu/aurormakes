from flask import Blueprint, g, jsonify, request

from auth import api_auth_required, tenant_for_request
from services import create_product, delete_product, list_products, update_product

products_bp = Blueprint("products_api", __name__, url_prefix="/api/products")


@products_bp.get("")
@api_auth_required("products:read")
def get_products():
    include_inactive = request.args.get("include_inactive") == "1"
    company_id = g.current_user["company_id"]
    products = list_products(company_id, include_inactive=include_inactive)
    return jsonify([product.to_dict() for product in products])


@products_bp.post("")
@api_auth_required("products:write")
def post_product():
    payload = request.get_json(silent=True) or {}
    company_id = g.current_user["company_id"]

    try:
        product = create_product(company_id, payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(product.to_dict()), 201


@products_bp.put("/<int:product_id>")
@api_auth_required("products:write")
def put_product(product_id):
    payload = request.get_json(silent=True) or {}
    company_id = g.current_user["company_id"]

    try:
        product = update_product(company_id, product_id, payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not product:
        return jsonify({"error": "Produto não encontrado"}), 404

    return jsonify(product.to_dict())


@products_bp.delete("/<int:product_id>")
@api_auth_required("products:write")
def remove_product(product_id):
    company_id = g.current_user["company_id"]
    removed = delete_product(company_id, product_id)

    if not removed:
        return jsonify({"error": "Produto não encontrado"}), 404

    return jsonify({"message": "Produto removido com sucesso"})
