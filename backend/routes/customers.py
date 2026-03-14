from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from auth import customer_login_required, load_current_customer, tenant_for_request
from customer_services import (
    authenticate_customer,
    create_customer,
    create_customer_address,
    get_customer_by_id,
    list_customer_addresses,
    update_customer_profile,
)
from services import list_orders

customers_bp = Blueprint("customers", __name__)


def _customer_session_payload(customer):
    return {
        "id": customer["id"],
        "company_id": customer["company_id"],
        "nome_completo": customer["nome_completo"],
        "email": customer["email"],
    }


@customers_bp.get("/api/customer/session")
def customer_session():
    customer = load_current_customer()
    if not customer:
        return jsonify({"authenticated": False})
    profile = get_customer_by_id(customer["company_id"], customer["id"])
    return jsonify({"authenticated": True, "customer": profile})


@customers_bp.post("/api/customer/register")
def customer_register():
    payload = request.get_json(silent=True) or {}
    company_id = tenant_for_request()
    if not company_id:
        return jsonify({"error": "Empresa inválida."}), 400
    try:
        customer = create_customer(company_id, payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    session["customer_user"] = _customer_session_payload(customer)
    return jsonify({"message": "Conta criada com sucesso!", "customer": customer}), 201


@customers_bp.post("/api/customer/login")
def customer_login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip()
    senha = payload.get("senha") or ""
    company_id = tenant_for_request()
    if not company_id:
        return jsonify({"error": "Empresa inválida."}), 400

    customer = authenticate_customer(company_id, email, senha)
    if not customer:
        return jsonify({"error": "E-mail ou senha inválidos."}), 401

    session["customer_user"] = _customer_session_payload(customer)
    return jsonify({"message": "Login realizado com sucesso.", "customer": customer})


@customers_bp.post("/api/customer/logout")
def customer_logout():
    session.pop("customer_user", None)
    return jsonify({"message": "Sessão encerrada."})


@customers_bp.get("/api/customer/account")
def customer_account_get():
    customer = load_current_customer()
    if not customer:
        return jsonify({"error": "Não autenticado."}), 401
    profile = get_customer_by_id(customer["company_id"], customer["id"])
    return jsonify(profile)


@customers_bp.put("/api/customer/account")
def customer_account_update():
    customer = load_current_customer()
    if not customer:
        return jsonify({"error": "Não autenticado."}), 401
    payload = request.get_json(silent=True) or {}
    try:
        profile = update_customer_profile(customer["company_id"], customer["id"], payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    session["customer_user"] = _customer_session_payload(profile)
    return jsonify({"message": "Dados atualizados com sucesso.", "customer": profile})


@customers_bp.get("/api/customer/addresses")
def customer_addresses_get():
    customer = load_current_customer()
    if not customer:
        return jsonify({"error": "Não autenticado."}), 401
    return jsonify(list_customer_addresses(customer["company_id"], customer["id"]))


@customers_bp.post("/api/customer/addresses")
def customer_addresses_post():
    customer = load_current_customer()
    if not customer:
        return jsonify({"error": "Não autenticado."}), 401

    payload = request.get_json(silent=True) or {}
    try:
        address = create_customer_address(customer["company_id"], customer["id"], payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"message": "Endereço salvo com sucesso.", "address": address}), 201


@customers_bp.get("/api/customer/orders")
def customer_orders_get():
    customer = load_current_customer()
    if not customer:
        return jsonify({"error": "Não autenticado."}), 401

    orders = [
        order.to_dict()
        for order in list_orders(customer["company_id"], customer_id=customer["id"])
    ]
    return jsonify(orders)


@customers_bp.get("/conta/entrar")
def customer_login_page():
    if load_current_customer():
        return redirect(url_for("customers.customer_account_page"))
    return render_template("store/customer_login.html")


@customers_bp.get("/conta/criar")
def customer_register_page():
    if load_current_customer():
        return redirect(url_for("customers.customer_account_page"))
    return render_template("store/customer_register.html")


@customers_bp.get("/minha-conta")
@customer_login_required
def customer_account_page():
    return render_template("store/customer_account.html")


@customers_bp.get("/meus-pedidos")
@customer_login_required
def customer_orders_page():
    return render_template("store/customer_orders.html")


@customers_bp.get("/meus-enderecos")
@customer_login_required
def customer_addresses_page():
    return render_template("store/customer_addresses.html")


@customers_bp.get("/conta/sair")
def customer_logout_page():
    session.pop("customer_user", None)
    return redirect(url_for("customers.customer_login_page"))
