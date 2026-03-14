from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

DATABASE_PATH = Path(os.getenv("AURORA_DB_PATH", BASE_DIR / "aurora_makes.db"))
SECRET_KEY = os.getenv("SECRET_KEY", "aurora-makes-dev-secret")
DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

PAYMENT_GATEWAY = os.getenv("PAYMENT_GATEWAY", "mercadopago")
MERCADO_PAGO_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN", "")
PAYMENT_GATEWAY_BASE_URL = os.getenv("PAYMENT_GATEWAY_BASE_URL", "https://api.mercadopago.com")
PAYMENT_GATEWAY_TIMEOUT_SECONDS = int(os.getenv("PAYMENT_GATEWAY_TIMEOUT_SECONDS", "20"))
PAYMENT_WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "")
PAYMENT_WEBHOOK_HEADER = os.getenv("PAYMENT_WEBHOOK_HEADER", "X-Webhook-Secret")
STORE_PUBLIC_URL = os.getenv("STORE_PUBLIC_URL", "http://localhost:5000")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
