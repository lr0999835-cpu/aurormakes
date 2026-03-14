from flask import Blueprint, redirect, render_template, request, url_for

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


@admin_bp.get("")
def admin_home():
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.get("/dashboard")
def admin_dashboard():
    metrics = get_dashboard_data()
    sold_products = get_sold_products()
    return render_template("admin/dashboard.html", metrics=metrics, sold_products=sold_products)


@admin_bp.get("/orders")
def admin_orders():
    filters = {
        "source": request.args.get("source", "").strip(),
        "status": request.args.get("status", "").strip(),
        "payment_status": request.args.get("payment_status", "").strip(),
        "shipping_status": request.args.get("shipping_status", "").strip(),
    }

    orders = list_orders(
        source=filters["source"] or None,
        status=filters["status"] or None,
        payment_status=filters["payment_status"] or None,
        shipping_status=filters["shipping_status"] or None,
    )

    selected_id = request.args.get("id")
    selected_order = get_order(int(selected_id)) if selected_id and selected_id.isdigit() else None
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
def admin_order_print(order_id):
    order = get_order(order_id)
    if not order:
        return redirect(url_for("admin.admin_orders"))
    order_items = order.get("items", [])
    return render_template("admin/order_print.html", order=order, order_items=order_items)


@admin_bp.post("/orders/<int:order_id>/status")
def admin_change_order_status(order_id):
    status = request.form.get("status", "")
    update_order_status(order_id, status)
    return redirect(url_for("admin.admin_orders", id=order_id))


@admin_bp.get("/products")
def admin_products():
    products = list_products(include_inactive=True)
    edit_id = request.args.get("edit")
    product_to_edit = get_product(int(edit_id)) if edit_id and edit_id.isdigit() else None
    return render_template(
        "admin/products.html",
        products=products,
        product_to_edit=product_to_edit,
    )


@admin_bp.post("/products")
def admin_create_product():
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

    create_product(payload)
    return redirect(url_for("admin.admin_products"))


@admin_bp.post("/products/<int:product_id>/update")
def admin_update_product(product_id):
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

    update_product(product_id, payload)
    return redirect(url_for("admin.admin_products"))


@admin_bp.post("/products/<int:product_id>/delete")
def admin_delete_product(product_id):
    delete_product(product_id)
    return redirect(url_for("admin.admin_products"))


@admin_bp.post("/products/<int:product_id>/toggle")
def admin_toggle_product(product_id):
    is_active = request.form.get("is_active") == "true"
    set_product_active(product_id, is_active)
    return redirect(url_for("admin.admin_products"))


@admin_bp.get("/stock")
def admin_stock():
    products = list_products(include_inactive=True)
    low_stock = list_low_stock_products(limit=50)
    movements = list_stock_movements(limit=100)
    return render_template("admin/stock.html", products=products, low_stock=low_stock, movements=movements)


@admin_bp.post("/stock/<int:product_id>")
def admin_update_stock(product_id):
    stock = request.form.get("stock", 0)
    notes = request.form.get("notes", "Ajuste manual pelo painel")
    update_product_stock(product_id, stock, notes=notes, source="manual", reference_id="admin_stock")
    return redirect(url_for("admin.admin_stock"))


@admin_bp.get("/channels")
def admin_channels():
    products = list_products(include_inactive=True)
    mappings = get_product_channel_mappings()
    return render_template("admin/channels.html", products=products, mappings=mappings, order_sources=ORDER_SOURCES)


@admin_bp.post("/channels")
def admin_save_channel_mapping():
    save_product_channel_mapping(
        product_id=request.form.get("product_id", 0),
        channel_name=request.form.get("channel_name", ""),
        external_product_id=request.form.get("external_product_id", ""),
        external_sku=request.form.get("external_sku", ""),
        is_active=request.form.get("is_active") == "on",
    )
    return redirect(url_for("admin.admin_channels"))


@admin_bp.get("/integrations")
def admin_integrations():
    return render_template("admin/integrations.html")
