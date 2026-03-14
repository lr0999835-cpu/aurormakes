from flask import Flask, send_from_directory

from config import DEBUG, PROJECT_ROOT, SECRET_KEY
from database import init_db
from routes.admin import admin_bp
from routes.products import products_bp


def create_app():
    app = Flask(__name__, template_folder="templates")
    app.secret_key = SECRET_KEY

    init_db()

    app.register_blueprint(products_bp)
    app.register_blueprint(admin_bp)

    @app.get("/")
    def home():
        return send_from_directory(PROJECT_ROOT, "index.html")

    @app.get("/<path:filename>")
    def static_files(filename):
        return send_from_directory(PROJECT_ROOT, filename)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
