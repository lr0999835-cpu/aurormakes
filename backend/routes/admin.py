from flask import Blueprint, redirect, render_template, request, url_for

from services import (
    create_product,
    delete_product,
    get_product,
    list_products,
    set_product_active,
    update_product,
    update_product_stock,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("")
def admin_home():
    return redirect(url_for("admin.admin_products"))


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
    return render_template("admin/stock.html", products=products)


@admin_bp.post("/stock/<int:product_id>")
def admin_update_stock(product_id):
    stock = request.form.get("stock", 0)
    update_product_stock(product_id, stock)
    return redirect(url_for("admin.admin_stock"))
