from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

DATABASE_PATH = Path(os.getenv("AURORA_DB_PATH", BASE_DIR / "aurora_makes.db"))
SECRET_KEY = os.getenv("SECRET_KEY", "aurora-makes-dev-secret")
DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
