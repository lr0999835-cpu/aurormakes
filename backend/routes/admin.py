from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from auth import (
    authenticate_user,
    has_permission,
    load_current_user,
    login_required,
    permission_required,
)
from database import get_connection
from services import (
    ORDER_SOURCES,
    ORDER_STATUSES,
    PAYMENT_STATUSES,
    SHIPPING_STATUSES,
    create_product,
    delete_product,
    get_dashboard_data,
    get_order,
    get_product,
    get_product_channel_mappings,
    get_sold_products,
    list_low_stock_products,
    list_orders,
    list_products,
    list_stock_movements,
    save_product_channel_mapping,
    set_product_active,
    update_order_status,
    update_product,
    update_product_stock,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_app_request
def _inject_user_context():
    user = load_current_user()
    g.current_user = user
    g.can_access = (lambda permission: has_permission(user, permission)) if user else (lambda _permission: False)


@admin_bp.get("/login")
def admin_login():
    if g.current_user:
        return redirect(url_for("admin.admin_dashboard"))
    return render_template("admin/login.html")


@admin_bp.post("/login")
def admin_login_post():
    company = (request.form.get("company") or "").strip().lower()
    login = (request.form.get("login") or "").strip()
    password = request.form.get("password") or ""

    if not company or not login or not password:
        flash("Preencha empresa, usuário/e-mail e senha.", "error")
        return render_template("admin/login.html"), 400

    user, error = authenticate_user(company, login, password)
    if error:
        flash(error, "error")
        return render_template("admin/login.html"), 401

    session.clear()
    session["auth_user"] = user

    with get_connection() as conn:
        conn.execute("UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
        conn.commit()

    next_url = request.args.get("next") or request.form.get("next")
    if next_url and next_url.startswith("/admin"):
        return redirect(next_url)
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.post("/logout")
@login_required
def admin_logout():
    session.clear()
    flash("Sessão encerrada com sucesso.", "success")
    return redirect(url_for("admin.admin_login"))


@admin_bp.get("")
@login_required
def admin_home():
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.get("/dashboard")
@permission_required("dashboard:read")
def admin_dashboard():
    company_id = g.current_user["company_id"]
    metrics = get_dashboard_data(company_id)
    sold_products = get_sold_products(company_id)
    return render_template("admin/dashboard.html", metrics=metrics, sold_products=sold_products)


@admin_bp.get("/orders")
@permission_required("orders:read")
def admin_orders():
    company_id = g.current_user["company_id"]
    filters = {
        "source": request.args.get("source", "").strip(),
        "status": request.args.get("status", "").strip(),
        "payment_status": request.args.get("payment_status", "").strip(),
        "shipping_status": request.args.get("shipping_status", "").strip(),
    }

    orders = list_orders(
        company_id,
        source=filters["source"] or None,
        status=filters["status"] or None,
        payment_status=filters["payment_status"] or None,
        shipping_status=filters["shipping_status"] or None,
    )

    selected_id = request.args.get("id")
    selected_order = get_order(company_id, int(selected_id)) if selected_id and selected_id.isdigit() else None
    selected_order_items = selected_order.get("items", []) if selected_order else []
    return render_template(
        "admin/orders.html",
        orders=orders,
        selected_order=selected_order,
        selected_order_items=selected_order_items,
        statuses=ORDER_STATUSES,
        order_sources=ORDER_SOURCES,
        payment_statuses=PAYMENT_STATUSES,
        shipping_statuses=SHIPPING_STATUSES,
        filters=filters,
    )


@admin_bp.get("/orders/<int:order_id>/print")
@permission_required("orders:read")
def admin_order_print(order_id):
    company_id = g.current_user["company_id"]
    order = get_order(company_id, order_id)
    if not order:
        return redirect(url_for("admin.admin_orders"))
    order_items = order.get("items", [])
    return render_template("admin/order_print.html", order=order, order_items=order_items)


@admin_bp.post("/orders/<int:order_id>/status")
@permission_required("orders:write")
def admin_change_order_status(order_id):
    company_id = g.current_user["company_id"]
    status = request.form.get("status", "")
    update_order_status(company_id, order_id, status)
    return redirect(url_for("admin.admin_orders", id=order_id))


@admin_bp.get("/products")
@permission_required("products:read")
def admin_products():
    company_id = g.current_user["company_id"]
    products = list_products(company_id, include_inactive=True)
    edit_id = request.args.get("edit")
    product_to_edit = get_product(company_id, int(edit_id)) if edit_id and edit_id.isdigit() else None
    return render_template(
        "admin/products.html",
        products=products,
        product_to_edit=product_to_edit,
    )


@admin_bp.post("/products")
@permission_required("products:write")
def admin_create_product():
    company_id = g.current_user["company_id"]
    payload = {
        "name": request.form.get("name"),
        "category": request.form.get("category"),
        "description": request.form.get("description"),
        "price": request.form.get("price"),
        "cost": request.form.get("cost"),
        "stock": request.form.get("stock"),
        "image_url": request.form.get("image_url"),
        "sku": request.form.get("sku"),
        "barcode": request.form.get("barcode"),
        "supplier_reference": request.form.get("supplier_reference"),
        "is_active": request.form.get("is_active") == "on",
    }

    create_product(company_id, payload)
    return redirect(url_for("admin.admin_products"))


@admin_bp.post("/products/<int:product_id>/update")
@permission_required("products:write")
def admin_update_product(product_id):
    company_id = g.current_user["company_id"]
    payload = {
        "name": request.form.get("name"),
        "category": request.form.get("category"),
        "description": request.form.get("description"),
        "price": request.form.get("price"),
        "cost": request.form.get("cost"),
        "stock": request.form.get("stock"),
        "image_url": request.form.get("image_url"),
        "sku": request.form.get("sku"),
        "barcode": request.form.get("barcode"),
        "supplier_reference": request.form.get("supplier_reference"),
        "is_active": request.form.get("is_active") == "on",
    }

    update_product(company_id, product_id, payload)
    return redirect(url_for("admin.admin_products"))


@admin_bp.post("/products/<int:product_id>/delete")
@permission_required("products:write")
def admin_delete_product(product_id):
    company_id = g.current_user["company_id"]
    delete_product(company_id, product_id)
    return redirect(url_for("admin.admin_products"))


@admin_bp.post("/products/<int:product_id>/toggle")
@permission_required("products:write")
def admin_toggle_product(product_id):
    company_id = g.current_user["company_id"]
    is_active = request.form.get("is_active") == "true"
    set_product_active(company_id, product_id, is_active)
    return redirect(url_for("admin.admin_products"))


@admin_bp.get("/stock")
@permission_required("stock:read")
def admin_stock():
    company_id = g.current_user["company_id"]
    products = list_products(company_id, include_inactive=True)
    low_stock = list_low_stock_products(company_id, limit=50)
    movements = list_stock_movements(company_id, limit=100)
    return render_template("admin/stock.html", products=products, low_stock=low_stock, movements=movements)


@admin_bp.post("/stock/<int:product_id>")
@permission_required("stock:write")
def admin_update_stock(product_id):
    company_id = g.current_user["company_id"]
    stock = request.form.get("stock", 0)
    notes = request.form.get("notes", "Ajuste manual pelo painel")
    update_product_stock(company_id, product_id, stock, notes=notes, source="manual", reference_id="admin_stock")
    return redirect(url_for("admin.admin_stock"))


@admin_bp.get("/channels")
@permission_required("channels:read")
def admin_channels():
    company_id = g.current_user["company_id"]
    products = list_products(company_id, include_inactive=True)
    mappings = get_product_channel_mappings(company_id)
    return render_template("admin/channels.html", products=products, mappings=mappings, order_sources=ORDER_SOURCES)


@admin_bp.post("/channels")
@permission_required("channels:write")
def admin_save_channel_mapping():
    company_id = g.current_user["company_id"]
    save_product_channel_mapping(
        company_id=company_id,
        product_id=request.form.get("product_id", 0),
        channel_name=request.form.get("channel_name", ""),
        external_product_id=request.form.get("external_product_id", ""),
        external_sku=request.form.get("external_sku", ""),
        is_active=request.form.get("is_active") == "on",
    )
    return redirect(url_for("admin.admin_channels"))


@admin_bp.get("/integrations")
@permission_required("integrations:read")
def admin_integrations():
    return render_template("admin/integrations.html")


@admin_bp.get("/usuarios")
@permission_required("users:read")
def admin_users():
    company_id = g.current_user["company_id"]
    with get_connection() as conn:
        users = conn.execute(
            "SELECT id, username, email, role, is_active, last_login_at, created_at FROM users WHERE company_id = ? ORDER BY created_at DESC",
            (int(company_id),),
        ).fetchall()
    return render_template("admin/users.html", users=users)
