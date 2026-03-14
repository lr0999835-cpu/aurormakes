from flask import Flask, abort, render_template, send_from_directory

from config import DEBUG, PROJECT_ROOT, SECRET_KEY
from database import init_db
from routes.admin import admin_bp
from routes.operations import operations_bp
from routes.products import products_bp


ALLOWED_STATIC_DIRS = {"css", "js", "images"}


def create_app():
    app = Flask(__name__, template_folder="templates")
    app.secret_key = SECRET_KEY

    init_db()

    app.register_blueprint(products_bp)
    app.register_blueprint(operations_bp)
    app.register_blueprint(admin_bp)

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
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
