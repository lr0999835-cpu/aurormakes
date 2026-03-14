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
os.environ["AURORA_DB_PATH"] = str(Path(tmpdir.name) / "test_dashboard.db")

from app import create_app  # noqa: E402


class DashboardBusinessLogicTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = create_app()
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def _post_order(self, customer_phone, total_items=1, status="paid", payment_status="paid", source="aurora_makes", address="Rua A, São Paulo - SP"):
        payload = {
            "customer_name": f"Cliente {customer_phone}",
            "customer_phone": customer_phone,
            "customer_address": address,
            "source": source,
            "status": status,
            "payment_status": payment_status,
            "items": [{"product_id": 1, "quantity": total_items}],
        }
        response = self.client.post("/api/orders", json=payload)
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def _login_admin(self):
        response = self.client.post(
            "/admin/login",
            json={"company": "aurora-makes", "email": "admin@auroramakes.com", "password": "admin123"},
            headers={"Accept": "application/json"},
        )
        self.assertEqual(response.status_code, 200)

    def test_dashboard_api_uses_only_paid_non_cancelled_revenue(self):
        baseline = self.client.get("/api/dashboard").get_json()
        self._post_order("21000000001", payment_status="paid", status="paid")
        self._post_order("21000000002", payment_status="pending", status="pending")
        cancelled = self._post_order("21000000003", payment_status="paid", status="paid")

        from database import get_connection

        with get_connection() as conn:
            conn.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (int(cancelled["id"]),))
            conn.commit()

        dashboard = self.client.get("/api/dashboard").get_json()

        self.assertEqual(dashboard["sales_total_count"], baseline["sales_total_count"] + 1)
        self.assertGreater(dashboard["total_revenue"], 0)
        self.assertGreaterEqual(dashboard["orders_by_source"].get("aurora_makes", 0), 1)

    def test_dashboard_filters_apply_to_widgets_consistently(self):
        self._post_order("21000000011", payment_status="paid", status="paid", source="aurora_makes")
        self._post_order("21000000012", payment_status="paid", status="paid", source="manual")

        self._login_admin()
        response = self.client.get("/admin/dashboard?source=manual")
        self.assertEqual(response.status_code, 200)

        html = response.get_data(as_text=True)
        self.assertIn("Canal: manual", html)
        self.assertIn("Período:", html)

    def test_company_data_isolation_for_dashboard_api(self):
        # tenant 1 default
        self._post_order("21000000021", payment_status="paid", status="paid")

        # create another company and order in tenant 2
        from database import get_connection

        with get_connection() as conn:
            conn.execute("INSERT INTO companies (name, slug, is_active) VALUES ('Other Co', 'other-co', 1)")
            company2 = conn.execute("SELECT id FROM companies WHERE slug = 'other-co'").fetchone()["id"]
            conn.execute(
                "INSERT INTO products (company_id, name, category, description, price, cost, stock, image_url, sku, barcode, supplier_reference, is_active) VALUES (?, 'Prod 2', 'Base', '', 30, 10, 10, '', 'P2', '', '', 1)",
                (int(company2),),
            )
            product2 = conn.execute("SELECT id FROM products WHERE company_id = ? ORDER BY id DESC LIMIT 1", (int(company2),)).fetchone()["id"]
            conn.execute(
                "INSERT INTO orders (company_id, customer_name, customer_phone, customer_address, total, status, source, payment_status, shipping_status) VALUES (?, 'C2', '21999900000', 'Rua B - RJ', 30, 'paid', 'manual', 'paid', 'pending')",
                (int(company2),),
            )
            order2 = conn.execute("SELECT id FROM orders WHERE company_id = ? ORDER BY id DESC LIMIT 1", (int(company2),)).fetchone()["id"]
            conn.execute(
                "INSERT INTO order_items (company_id, order_id, product_id, quantity, price) VALUES (?, ?, ?, 1, 30)",
                (int(company2), int(order2), int(product2)),
            )
            conn.commit()

        tenant1 = self.client.get("/api/dashboard", headers={"X-Company": "aurora-makes"}).get_json()
        tenant2 = self.client.get("/api/dashboard", headers={"X-Company": "other-co"}).get_json()

        self.assertGreaterEqual(tenant1["sales_total_count"], 1)
        self.assertEqual(tenant2["sales_total_count"], 1)


if __name__ == "__main__":
    unittest.main()
