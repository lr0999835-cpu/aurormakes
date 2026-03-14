import logging
import os

from flask import Flask, abort, render_template, send_from_directory

from config import DEBUG, PROJECT_ROOT, SECRET_KEY
from database import init_db
from routes.admin import admin_bp
from routes.operations import operations_bp
from routes.products import products_bp


ALLOWED_STATIC_DIRS = {"css", "js", "images"}


def create_app():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    app = Flask(__name__, template_folder="templates")
    app.secret_key = SECRET_KEY
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=not DEBUG,
        PERMANENT_SESSION_LIFETIME=60 * 60 * 8,
    )

    init_db()

    app.register_blueprint(products_bp)
    app.register_blueprint(operations_bp)
    app.register_blueprint(admin_bp)


    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("admin/forbidden.html"), 403

    @app.get("/")
    def home():
        return render_template("store/index.html")

    @app.get("/index.html")
    def home_alias():
        return render_template("store/index.html")

    @app.get("/produtos.html")
    def products_page():
        return render_template("store/produtos.html")

    @app.get("/carrinho.html")
    def cart_page():
        return render_template("store/carrinho.html")

    @app.get("/<path:filename>")
    def static_files(filename):
        folder = filename.split("/", 1)[0]
        if folder not in ALLOWED_STATIC_DIRS:
            abort(404)
        return send_from_directory(PROJECT_ROOT, filename)

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=DEBUG)
