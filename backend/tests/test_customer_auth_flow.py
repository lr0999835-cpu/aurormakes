import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

tmpdir = tempfile.TemporaryDirectory()
os.environ["AURORA_DB_PATH"] = str(Path(tmpdir.name) / "test.db")

from app import create_app  # noqa: E402


class CustomerAuthFlowTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = create_app()
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_register_login_and_link_order(self):
        register = self.client.post(
            "/api/customer/register",
            json={
                "nome_completo": "Cliente Aurora",
                "email": "cliente@aurora.com",
                "telefone": "21999998888",
                "senha": "senha123",
                "confirmar_senha": "senha123",
                "aceita_marketing": True,
            },
        )
        self.assertEqual(register.status_code, 201)

        duplicate = self.client.post(
            "/api/customer/register",
            json={
                "nome_completo": "Cliente Aurora",
                "email": "cliente@aurora.com",
                "telefone": "21999998888",
                "senha": "senha123",
                "confirmar_senha": "senha123",
            },
        )
        self.assertEqual(duplicate.status_code, 400)

        self.client.post("/api/customer/logout")

        login = self.client.post("/api/customer/login", json={"email": "cliente@aurora.com", "senha": "senha123"})
        self.assertEqual(login.status_code, 200)

        checkout = self.client.post(
            "/api/checkout",
            json={
                "customer_name": "Cliente Aurora",
                "customer_phone": "21999998888",
                "customer_address": "Rua A, 10",
                "items": [{"product_id": 1, "quantity": 1}],
                "payment_method": "pix",
            },
        )
        self.assertEqual(checkout.status_code, 201)

        orders = self.client.get("/api/customer/orders")
        self.assertEqual(orders.status_code, 200)
        orders_list = orders.get_json()
        self.assertGreaterEqual(len(orders_list), 1)
        self.assertTrue(orders_list[0].get("customer_id"))


if __name__ == "__main__":
    unittest.main()
