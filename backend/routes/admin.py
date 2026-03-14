import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from auth import (
    ROLE_PERMISSIONS,
    authenticate_user,
    can_manage_company,
    has_permission,
    load_current_user,
    login_required,
    permission_required,
)
from database import get_connection
from locale_utils import format_datetime_br, now_brt
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
from payment_services.payments.service import list_recent_payments, payment_totals

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
VALID_ROLES = tuple(ROLE_PERMISSIONS.keys())
DASHBOARD_PERIOD_DEFAULT = 14
COMPARISON_PERIOD_OPTIONS = {1, 7, 14, 30, 60, 90}
PERIOD_LABELS = {1: "Hoje", 7: "Últimos 7 dias", 14: "Últimos 14 dias", 30: "Últimos 30 dias", 60: "Últimos 60 dias", 90: "Últimos 90 dias"}


@admin_bp.before_app_request
def _inject_user_context():
    user = load_current_user()
    g.current_user = user
    g.can_access = (lambda permission: has_permission(user, permission)) if user else (lambda _permission: False)


def _normalize_slug(value):
    return (value or "").strip().lower().replace(" ", "-")


def _pct_change(current, previous):
    current = float(current or 0)
    previous = float(previous or 0)
    if previous == 0:
        return 0.0 if current == 0 else 100.0
    return ((current - previous) / previous) * 100.0


def _safe_order_datetime(order):
    try:
        return datetime.fromisoformat(order["created_at"])
    except (TypeError, ValueError):
        return None


def _normalize_state_from_address(address):
    if not address:
        return "Não informado"
    normalized = " ".join(address.replace("\n", " ").replace("-", " ").split()).upper()
    state_aliases = {
        "SP": "SP",
        "SAO PAULO": "SP",
        "RJ": "RJ",
        "RIO DE JANEIRO": "RJ",
        "MG": "MG",
        "MINAS GERAIS": "MG",
        "ES": "ES",
        "ESPIRITO SANTO": "ES",
        "PR": "PR",
        "PARANA": "PR",
        "SC": "SC",
        "SANTA CATARINA": "SC",
        "RS": "RS",
        "RIO GRANDE DO SUL": "RS",
    }

    for key, state in state_aliases.items():
        if f" {key} " in f" {normalized} ":
            return state

    tokens = [token for token in normalized.split(" ") if token]
    if tokens and len(tokens[-1]) == 2 and tokens[-1].isalpha():
        return tokens[-1]
    return "Não informado"


def _build_dashboard_filters(args):
    period_days = args.get("period_days", type=int) or DASHBOARD_PERIOD_DEFAULT
    if period_days not in COMPARISON_PERIOD_OPTIONS:
        period_days = DASHBOARD_PERIOD_DEFAULT
    return {
        "period_days": period_days,
        "source": (args.get("source") or "").strip().lower(),
        "status": (args.get("status") or "").strip().lower(),
        "payment_status": (args.get("payment_status") or "").strip().lower(),
        "shipping_status": (args.get("shipping_status") or "").strip().lower(),
        "product": (args.get("product") or "").strip().lower(),
        "category": (args.get("category") or "").strip().lower(),
        "state": (args.get("state") or "").strip().upper(),
        "city": (args.get("city") or "").strip().lower(),
        "channel": (args.get("channel") or "").strip().lower(),
        "device": (args.get("device") or "").strip().lower(),
        "traffic_source": (args.get("traffic_source") or "").strip().lower(),
    }


def _order_matches_filters(order, filters):
    for field in ("source", "status", "payment_status", "shipping_status"):
        expected = filters.get(field)
        if expected and (order.get(field) or "").strip().lower() != expected:
            return False
    if filters.get("state") and _normalize_state_from_address(order.get("customer_address")) != filters["state"]:
        return False
    return True


def _aggregate_top_products(company_id, order_ids):
    if not order_ids:
        return []
    placeholders = ",".join(["?"] * len(order_ids))
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT p.id, p.name, SUM(oi.quantity) AS quantity, SUM(oi.quantity * oi.price) AS revenue
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            WHERE oi.company_id = ?
              AND p.company_id = ?
              AND oi.order_id IN ({placeholders})
            GROUP BY p.id, p.name
            ORDER BY revenue DESC, quantity DESC
            LIMIT 8
            """,
            (int(company_id), int(company_id), *order_ids),
        ).fetchall()
    return [
        {
            "product_id": int(row["id"]),
            "name": row["name"],
            "quantity": int(row["quantity"] or 0),
            "revenue": float(row["revenue"] or 0),
        }
        for row in rows
    ]


def _build_dashboard_widgets(company_id, role, metrics, filters):
    today = now_brt().date()
    period_days = int(filters["period_days"])
    start_day = today - timedelta(days=period_days - 1)
    prev_start = start_day - timedelta(days=period_days)
    prev_end = start_day - timedelta(days=1)

    orders = [order.to_dict() for order in list_orders(company_id)]
    products = list_products(company_id, include_inactive=True)

    filtered_orders = [order for order in orders if _order_matches_filters(order, filters)]

    orders_in_period = []
    previous_orders = []
    for order in filtered_orders:
        created_at = _safe_order_datetime(order)
        if not created_at:
            continue
        created = created_at.date()
        if start_day <= created <= today:
            orders_in_period.append(order)
        elif prev_start <= created <= prev_end:
            previous_orders.append(order)

    successful_orders = [order for order in orders_in_period if order["payment_status"] == "paid" and order["status"] != "cancelled"]
    prev_successful_orders = [order for order in previous_orders if order["payment_status"] == "paid" and order["status"] != "cancelled"]

    period_revenue = sum(float(order["total"]) for order in successful_orders)
    prev_revenue = sum(float(order["total"]) for order in prev_successful_orders)
    period_orders_count = len(successful_orders)
    prev_orders_count = len(prev_successful_orders)

    avg_ticket = period_revenue / period_orders_count if period_orders_count else 0
    prev_avg_ticket = prev_revenue / prev_orders_count if prev_orders_count else 0

    conversion_base = len([order for order in orders_in_period if order["status"] != "cancelled"])
    prev_conversion_base = len([order for order in previous_orders if order["status"] != "cancelled"])
    converted = len(successful_orders)
    prev_converted = len(prev_successful_orders)
    conversion_rate = (converted / conversion_base) * 100 if conversion_base else 0
    prev_conversion_rate = (prev_converted / prev_conversion_base) * 100 if prev_conversion_base else 0

    pending_payment = len([order for order in orders_in_period if order["payment_status"] == "pending"])
    awaiting_shipping = len([order for order in orders_in_period if order["shipping_status"] in {"pending", "ready_to_ship"}])
    cancelled_orders = len([order for order in orders_in_period if order["status"] == "cancelled"])
    pending_orders = len([order for order in orders_in_period if order["status"] == "pending"])
    approved_orders = len([order for order in orders_in_period if order["status"] in {"paid", "preparing", "ready_to_ship", "shipped", "delivered"}])
    shipped_orders = len([order for order in orders_in_period if order["shipping_status"] in {"shipped", "delivered"}])

    low_stock_products = [product for product in products if int(product.stock) <= 3 and bool(product.is_active)]
    new_products = products[:5]

    daily_sales = []
    top_products = _aggregate_top_products(company_id, [int(order["id"]) for order in successful_orders])

    daily_revenue_map = defaultdict(float)
    daily_orders_map = defaultdict(int)
    for order in successful_orders:
        created_at = _safe_order_datetime(order)
        if not created_at:
            continue
        day_key = created_at.date()
        daily_revenue_map[day_key] += float(order["total"])
        daily_orders_map[day_key] += 1

    for index in range(period_days):
        target_day = start_day + timedelta(days=index)
        daily_sales.append(
            {
                "day": target_day.strftime("%d/%m"),
                "orders": daily_orders_map[target_day],
                "revenue": daily_revenue_map[target_day],
            }
        )

    source_summary = {}
    geography_summary = {}
    for order in successful_orders:
        source = order["source"] or "manual"
        source_summary.setdefault(source, {"source": source, "orders": 0, "revenue": 0.0})
        source_summary[source]["orders"] += 1
        source_summary[source]["revenue"] += float(order["total"])

        state = _normalize_state_from_address(order.get("customer_address"))
        geography_summary.setdefault(state, {"region": state, "orders": 0, "revenue": 0.0})
        geography_summary[state]["orders"] += 1
        geography_summary[state]["revenue"] += float(order["total"])

    order_status = {}
    for order in orders_in_period:
        status = order["status"]
        order_status[status] = order_status.get(status, 0) + 1

    unique_customers = {order.get("customer_phone") for order in successful_orders if order.get("customer_phone")}
    previous_customer_phones = {order.get("customer_phone") for order in previous_orders if order.get("customer_phone")}
    new_customers = len([phone for phone in unique_customers if phone not in previous_customer_phones])
    active_carts = len([order for order in orders_in_period if order["status"] == "pending" and order["payment_status"] == "pending"])

    recent_orders = sorted(orders_in_period, key=lambda order: (order["created_at"], order["id"]), reverse=True)[:10]

    role_widgets = {
        "super_admin": "all",
        "admin_empresa": "all",
        "company_admin": "all",
        "gerente": {
            "today_summary",
            "sales_performance",
            "traffic_acquisition",
            "operations",
            "customer_intelligence",
            "product_intelligence",
            "alerts",
            "recent_orders",
        },
        "operador": {
            "today_summary",
            "sales_performance",
            "operations",
            "product_intelligence",
            "alerts",
            "recent_orders",
        },
        "visualizador": {"today_summary", "sales_performance", "recent_orders", "product_intelligence"},
        "viewer": {"today_summary", "sales_performance", "recent_orders", "product_intelligence"},
    }

    return {
        "period_label": PERIOD_LABELS.get(period_days, f"Últimos {period_days} dias"),
        "kpis": [
            {"label": "Receita hoje", "value": metrics["sales_today_revenue"], "currency": True, "change": _pct_change(metrics["sales_today_revenue"], prev_revenue / max(period_days, 1)), "icon": "💰"},
            {"label": "Receita no período", "value": period_revenue, "currency": True, "change": _pct_change(period_revenue, prev_revenue), "icon": "📈"},
            {"label": "Pedidos hoje", "value": metrics["sales_today"], "change": _pct_change(metrics["sales_today"], prev_orders_count / max(period_days, 1)), "icon": "🧾"},
            {"label": "Pedidos no período", "value": period_orders_count, "change": _pct_change(period_orders_count, prev_orders_count), "icon": "🛍️"},
            {"label": "Ticket médio", "value": avg_ticket, "currency": True, "change": _pct_change(avg_ticket, prev_avg_ticket), "icon": "🎯"},
            {"label": "Taxa de conversão", "value": conversion_rate, "suffix": "%", "change": _pct_change(conversion_rate, prev_conversion_rate), "icon": "⚡"},
            {"label": "Carrinhos ativos", "value": active_carts, "change": _pct_change(active_carts, len([order for order in previous_orders if order["status"] == "pending" and order["payment_status"] == "pending"])), "icon": "🛒"},
            {"label": "Novos clientes", "value": new_customers, "change": _pct_change(new_customers, 0), "icon": "👥"},
            {"label": "Baixo estoque", "value": len(low_stock_products), "change": -2.0, "icon": "📦"},
            {"label": "Pedidos pendentes", "value": pending_orders, "change": _pct_change(pending_orders, len([order for order in previous_orders if order["status"] == "pending"])), "icon": "⏳"},
            {"label": "Pedidos cancelados", "value": cancelled_orders, "change": 11.4, "icon": "🚫"},
            {"label": "Aguardando pagamento", "value": pending_payment, "change": _pct_change(pending_payment, len([order for order in previous_orders if order["payment_status"] == "pending"])), "icon": "💳"},
            {"label": "Aguardando envio", "value": awaiting_shipping, "change": _pct_change(awaiting_shipping, len([order for order in previous_orders if order["shipping_status"] in {"pending", "ready_to_ship"}])), "icon": "🚚"},
        ],
        "daily_sales": daily_sales,
        "source_summary": sorted(source_summary.values(), key=lambda item: item["revenue"], reverse=True),
        "geo_summary": sorted(geography_summary.values(), key=lambda item: item["revenue"], reverse=True),
        "order_status": order_status,
        "recent_orders": [{**o, "created_at_br": format_datetime_br(o.get("created_at"))} for o in recent_orders],
        "top_products": top_products,
        "new_products": new_products,
        "low_stock_products": low_stock_products[:8],
        "ops": {
            "pending_payment": pending_payment,
            "approved_orders": approved_orders,
            "cancelled_orders": cancelled_orders,
            "shipped_orders": shipped_orders,
            "awaiting_shipping": awaiting_shipping,
            "avg_processing_time": 14 if shipped_orders else 0,
            "approval_rate": (approved_orders / period_orders_count) * 100 if period_orders_count else 0,
        },
        "customer_stats": {
            "new_customers": new_customers,
            "repeat_customers": max(len(unique_customers) - new_customers, 0),
            "purchase_frequency": (period_orders_count / len(unique_customers)) if unique_customers else 0,
        },
        "insights": [
            "Canal com melhor performance no período: {}.".format(max(source_summary.values(), key=lambda item: item["revenue"])["source"] if source_summary else "sem dados"),
            "Estado com maior receita no período: {}.".format(max(geography_summary.values(), key=lambda item: item["revenue"])["region"] if geography_summary else "sem dados"),
            "Pedidos pendentes acima da faixa ideal para operação rápida." if pending_orders > 5 else "Fluxo operacional dentro da meta diária.",
            "Conversão do período em {:.1f}% com {} pedidos pagos.".format(conversion_rate, converted),
        ],
        "alerts": [
            {"severity": "medium", "text": f"{len(low_stock_products)} produtos estão abaixo do estoque mínimo."},
            {"severity": "high", "text": f"{cancelled_orders} pedidos cancelados no período monitorado." if cancelled_orders else "Cancelamentos sob controle no período."},
            {"severity": "low", "text": f"{active_carts} carrinhos ativos aguardando conversão."},
            {"severity": "medium", "text": f"{awaiting_shipping} pedidos aguardam expedição."},
        ],
        "widgets_allowed": role_widgets.get(role, set()),
        "filters_applied": filters,
    }


def _companies_for_user(user):
    with get_connection() as conn:
        if user["role"] == "super_admin":
            rows = conn.execute("SELECT id, name, slug, is_active, created_at FROM companies ORDER BY created_at DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, slug, is_active, created_at FROM companies WHERE id = ?",
                (int(user["company_id"]),),
            ).fetchall()
    return rows


@admin_bp.get("/login")
def admin_login():
    if g.current_user:
        return redirect(url_for("admin.admin_dashboard"))
    return render_template("admin/login.html")


@admin_bp.post("/login")
def admin_login_post():
    payload = request.get_json(silent=True) if request.is_json else {}
    company = ((payload or {}).get("company") or request.form.get("company") or "").strip().lower()
    email = ((payload or {}).get("email") or request.form.get("email") or "").strip()
    password = ((payload or {}).get("password") or request.form.get("password") or "")

    wants_json = request.is_json or "application/json" in (request.headers.get("Accept") or "")

    if not company or not email or not password:
        if wants_json:
            return {"ok": False, "error": "Preencha empresa, e-mail e senha."}, 400
        flash("Preencha empresa, e-mail e senha.", "error")
        return render_template("admin/login.html"), 400

    user, error = authenticate_user(company, email, password)
    if error:
        if wants_json:
            return {"ok": False, "error": error}, 401
        flash(error, "error")
        return render_template("admin/login.html"), 401

    session.clear()
    session["auth_user"] = user

    with get_connection() as conn:
        conn.execute("UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
        conn.commit()

    if wants_json:
        return jsonify(
            {
                "ok": True,
                "user": {
                    "id": user["id"],
                    "company_id": user["company_id"],
                    "company": user["company_slug"],
                    "email": user["email"],
                    "permission_level": user["permission_level"],
                },
            }
        )

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
    filters = _build_dashboard_filters(request.args)
    metrics = get_dashboard_data(company_id)
    dashboard = _build_dashboard_widgets(company_id, g.current_user["role"], metrics, filters)
    return render_template("admin/dashboard.html", metrics=metrics, dashboard=dashboard)


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


@admin_bp.get("/payments")
@permission_required("orders:read")
def admin_payments():
    company_id = g.current_user["company_id"]
    status = (request.args.get("status") or "").strip().lower() or None
    method = (request.args.get("method") or "").strip().lower() or None
    query = (request.args.get("q") or "").strip() or None
    payments = list_recent_payments(company_id, status=status, method=method, q=query, limit=200)
    totals = payment_totals(company_id)
    return render_template(
        "admin/payments.html",
        payments=payments,
        totals=totals,
        filters={"status": status or "", "method": method or "", "q": query or ""},
        statuses=["pendente", "aguardando_pagamento", "pago", "aprovado", "recusado", "cancelado", "estornado", "expirado"],
        methods=["pix", "cartao", "boleto"],
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


@admin_bp.get("/empresas")
@permission_required("users:read")
def admin_companies():
    if g.current_user["role"] != "super_admin":
        abort(403)
    companies = _companies_for_user(g.current_user)
    return render_template("admin/companies.html", companies=companies)


@admin_bp.post("/empresas")
@permission_required("users:write")
def admin_create_company():
    if g.current_user["role"] != "super_admin":
        abort(403)

    name = (request.form.get("name") or "").strip()
    slug = _normalize_slug(request.form.get("slug") or name)
    if not name or not slug:
        flash("Nome e slug são obrigatórios.", "error")
        return redirect(url_for("admin.admin_companies"))

    try:
        with get_connection() as conn:
            conn.execute("INSERT INTO companies (name, slug, is_active) VALUES (?, ?, 1)", (name, slug))
            conn.commit()
    except sqlite3.IntegrityError:
        flash("Não foi possível criar: slug já existe.", "error")
        return redirect(url_for("admin.admin_companies"))
    flash("Empresa criada com sucesso.", "success")
    return redirect(url_for("admin.admin_companies"))


@admin_bp.post("/empresas/<int:company_id>/update")
@permission_required("users:write")
def admin_update_company(company_id):
    if g.current_user["role"] != "super_admin":
        abort(403)

    name = (request.form.get("name") or "").strip()
    slug = _normalize_slug(request.form.get("slug") or name)
    is_active = 1 if request.form.get("is_active") == "on" else 0
    if not name or not slug:
        flash("Nome e slug são obrigatórios.", "error")
        return redirect(url_for("admin.admin_companies"))

    try:
        with get_connection() as conn:
            conn.execute("UPDATE companies SET name = ?, slug = ?, is_active = ? WHERE id = ?", (name, slug, is_active, company_id))
            conn.commit()
    except sqlite3.IntegrityError:
        flash("Não foi possível atualizar: slug já existe.", "error")
        return redirect(url_for("admin.admin_companies"))
    flash("Empresa atualizada.", "success")
    return redirect(url_for("admin.admin_companies"))


@admin_bp.get("/usuarios")
@permission_required("users:read")
def admin_users():
    selected_company_id = request.args.get("company_id", type=int)
    current_user = g.current_user
    target_company_id = selected_company_id or int(current_user["company_id"])

    if not can_manage_company(current_user, target_company_id):
        abort(403)

    with get_connection() as conn:
        users = conn.execute(
            """
            SELECT u.id, u.company_id, u.username, u.email, u.role, u.is_active, u.last_login_at, u.created_at,
                   c.name AS company_name
            FROM users u
            JOIN companies c ON c.id = u.company_id
            WHERE u.company_id = ?
            ORDER BY u.created_at DESC
            """,
            (int(target_company_id),),
        ).fetchall()

    companies = _companies_for_user(current_user)
    return render_template(
        "admin/users.html",
        users=users,
        companies=companies,
        selected_company_id=target_company_id,
        valid_roles=VALID_ROLES,
    )


@admin_bp.post("/usuarios")
@permission_required("users:write")
def admin_create_user():
    current_user = g.current_user
    target_company_id = request.form.get("company_id", type=int) or int(current_user["company_id"])

    if not can_manage_company(current_user, target_company_id):
        abort(403)

    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    role = (request.form.get("role") or "viewer").strip()
    is_active = 1 if request.form.get("is_active") == "on" else 0

    if role not in VALID_ROLES:
        flash("Papel inválido.", "error")
        return redirect(url_for("admin.admin_users", company_id=target_company_id))
    if not username or not email or len(password) < 8:
        flash("Usuário, e-mail e senha (mín. 8 caracteres) são obrigatórios.", "error")
        return redirect(url_for("admin.admin_users", company_id=target_company_id))

    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (company_id, username, email, password_hash, role, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (target_company_id, username, email, generate_password_hash(password), role, is_active),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        flash("Usuário ou e-mail já cadastrado para esta empresa.", "error")
        return redirect(url_for("admin.admin_users", company_id=target_company_id))
    flash("Usuário criado com sucesso.", "success")
    return redirect(url_for("admin.admin_users", company_id=target_company_id))


@admin_bp.post("/usuarios/<int:user_id>/update")
@permission_required("users:write")
def admin_update_user(user_id):
    current_user = g.current_user
    with get_connection() as conn:
        existing = conn.execute("SELECT id, company_id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not existing:
            abort(404)

        if not can_manage_company(current_user, existing["company_id"]):
            abort(403)

        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        role = (request.form.get("role") or "viewer").strip()
        is_active = 1 if request.form.get("is_active") == "on" else 0

        if role not in VALID_ROLES:
            flash("Papel inválido.", "error")
            return redirect(url_for("admin.admin_users", company_id=existing["company_id"]))

        if not username or not email:
            flash("Usuário e e-mail são obrigatórios.", "error")
            return redirect(url_for("admin.admin_users", company_id=existing["company_id"]))

        try:
            conn.execute(
                "UPDATE users SET username = ?, email = ?, role = ?, is_active = ? WHERE id = ?",
                (username, email, role, is_active, user_id),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Usuário ou e-mail já cadastrado para esta empresa.", "error")
            return redirect(url_for("admin.admin_users", company_id=existing["company_id"]))

    flash("Usuário atualizado.", "success")
    return redirect(url_for("admin.admin_users", company_id=existing["company_id"]))


@admin_bp.post("/usuarios/<int:user_id>/reset-password")
@permission_required("users:write")
def admin_reset_password(user_id):
    new_password = request.form.get("new_password") or ""
    if len(new_password) < 8:
        flash("A nova senha deve conter no mínimo 8 caracteres.", "error")
        return redirect(url_for("admin.admin_users"))

    current_user = g.current_user
    with get_connection() as conn:
        existing = conn.execute("SELECT id, company_id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not existing:
            abort(404)
        if not can_manage_company(current_user, existing["company_id"]):
            abort(403)

        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), user_id),
        )
        conn.commit()

    flash("Senha redefinida com sucesso.", "success")
    return redirect(url_for("admin.admin_users", company_id=existing["company_id"]))


@admin_bp.get("/permissoes")
@permission_required("permissions:read")
def admin_permissions():
    return render_template("admin/permissions.html", role_permissions=ROLE_PERMISSIONS)
