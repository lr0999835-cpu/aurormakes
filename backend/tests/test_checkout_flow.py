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


class CheckoutFlowTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = create_app()
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def _checkout_payload(self, camel_case=False):
        items = [{"productId": 1, "qty": 1}] if camel_case else [{"product_id": 1, "quantity": 1}]
        payload = {
            "customer_name": "Cliente Teste",
            "customer_phone": "21999999999",
            "customer_address": "Rua A",
            "source": "aurora_makes",
            "payment_status": "paid",
            "payment_method": "card",
            "shipping_method": "correios_sedex",
            "shipping_quote_id": "correios-sedex",
            "shipping_eta": "2 a 4 dias úteis",
            "shipping_label": "Correios",
            "customer_address_data": {
                "cep": "20000000",
                "street": "Rua A",
                "number": "10",
                "district": "Centro",
                "city": "Rio de Janeiro",
                "state": "RJ",
            },
            "payment": {
                "payment_method": "cartao",
                "payment_status": "pendente",
                "payment_amount": 49.9,
                "payment_gateway": "mercadopago",
                "transaction_id": "",
                "payment_payload": {"timezone": "America/Sao_Paulo"},
                "created_at": "2026-01-01T10:00:00",
                "updated_at": "2026-01-01T10:00:00"
            },
            "items": items,
        }
        if camel_case:
            payload = {
                "customerName": "Cliente Mobile",
                "customerPhone": "21888888888",
                "customerAddress": "Rua Mobile",
                "source": "aurora_makes",
                "paymentStatus": "paid",
                "paymentMethod": "pix",
                "shippingMethod": "correios_pac",
                "shippingQuoteId": "correios-pac",
                "shippingEta": "5 a 10 dias úteis",
                "shippingLabel": "Correios",
                "items": items,
            }
        return payload

    def test_successful_desktop_purchase_creates_visible_order(self):
        response = self.client.post("/api/checkout", json=self._checkout_payload())
        self.assertEqual(response.status_code, 201)
        order = response.get_json()
        self.assertEqual(order["payment_status"], "paid")
        self.assertEqual(order["shipping_method"], "correios_sedex")
        self.assertEqual(order["shipping_label"], "Correios")
        self.assertEqual(order["shipping_eta"], "2 a 4 dias úteis")
        self.assertEqual(order["customer_address_data"]["state"], "RJ")
        self.assertIn("payment", order)
        self.assertEqual(order["payment"]["payment_method"], "cartao")
        self.assertIn("payment_gateway", order["payment"])
        self.assertIn("payment_payload", order["payment"])

        orders_response = self.client.get("/api/orders", query_string={"customer_phone": "21999999999"})
        self.assertEqual(orders_response.status_code, 200)
        orders = orders_response.get_json()
        self.assertGreaterEqual(len(orders), 1)

        dashboard_response = self.client.get("/api/dashboard")
        self.assertEqual(dashboard_response.status_code, 200)
        dashboard = dashboard_response.get_json()
        self.assertGreaterEqual(dashboard["sales_total_count"], 1)

    def test_successful_mobile_purchase_uses_same_checkout_path(self):
        response = self.client.post(
            "/api/checkout",
            json=self._checkout_payload(camel_case=True),
            headers={"X-Device-Type": "mobile"},
        )
        self.assertEqual(response.status_code, 201)
        order = response.get_json()
        self.assertEqual(order["customer_phone"], "21888888888")

        orders_response = self.client.get("/api/orders", query_string={"customer_phone": "21888888888"})
        orders = orders_response.get_json()
        self.assertGreaterEqual(len(orders), 1)


    def test_checkout_rejects_invalid_shipping_method_for_cep(self):
        payload = self._checkout_payload()
        payload["shipping_method"] = "metodo_inexistente"
        payload["shipping_quote_id"] = "metodo_inexistente"

        response = self.client.post("/api/checkout", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Método de frete inválido", response.get_json()["error"])

    def test_checkout_rejects_shipping_price_tampering(self):
        payload = self._checkout_payload()
        payload["shipping_amount"] = 0.01

        response = self.client.post("/api/checkout", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Valor de frete divergente", response.get_json()["error"])

    def test_shipping_quotes_api_returns_correios_and_partner_options(self):
        response = self.client.post(
            "/api/shipping/quotes",
            json={
                "cep": "01310-100",
                "subtotal": 130,
                "items": [{"product_id": 1, "quantity": 2}],
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        ids = {quote["id"] for quote in payload["quotes"]}
        self.assertIn("correios-pac", ids)
        self.assertIn("correios-sedex", ids)
        self.assertIn("entrega-afiliada", ids)



    def test_checkout_rejects_invalid_contact_data(self):
        payload = self._checkout_payload()
        payload["customer_phone"] = "123"
        payload["customer_email"] = "email-invalido"

        response = self.client.post("/api/checkout", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("e-mail válido", response.get_json()["error"])

    def test_checkout_rejects_invalid_payment_selection(self):
        payload = self._checkout_payload()
        payload["payment_method"] = "criptomoeda"

        response = self.client.post("/api/checkout", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Método de pagamento inválido", response.get_json()["error"])

    def test_payment_config_includes_checkout_login_policy_flag(self):
        response = self.client.get('/api/payments/config')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn('checkout_login_required', payload)

    def test_payment_config_endpoint_exposes_gateway_and_public_key(self):
        response = self.client.get('/api/payments/config')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['gateway'], 'mercadopago')
        self.assertIn('pix', payload['methods'])
        self.assertEqual(payload['currency'], 'BRL')
        self.assertEqual(payload['timezone'], 'America/Sao_Paulo')

    def test_webhook_confirmed_payment_updates_existing_order(self):
        response = self.client.post("/api/orders", json=self._checkout_payload())
        self.assertEqual(response.status_code, 201)
        order = response.get_json()

        webhook_paid = self.client.post(
            "/api/payments/webhook",
            json={
                "payment_id": "pay-1",
                "order_id": order["id"],
                "amount": order["total"],
                "status": "paid",
                "payment_method": "pix",
                "customer_phone": order["customer_phone"],
            },
        )
        self.assertEqual(webhook_paid.status_code, 200)

        orders = self.client.get("/api/orders", query_string={"customer_phone": order["customer_phone"]}).get_json()
        self.assertEqual(orders[0]["payment_status"], "paid")


    def test_webhook_refunded_updates_payment_to_estornado(self):
        response = self.client.post('/api/checkout', json=self._checkout_payload())
        self.assertEqual(response.status_code, 201)
        order = response.get_json()
        payment_id = order.get('payment', {}).get('payment_id')
        self.assertTrue(payment_id)

        webhook_refund = self.client.post(
            '/api/payments/webhook',
            json={
                'payment_id': payment_id,
                'action': 'refunded',
                'transaction_id': payment_id,
            },
        )
        self.assertEqual(webhook_refund.status_code, 200)
        payment = webhook_refund.get_json()
        self.assertEqual(payment['payment_status'], 'estornado')

    def test_webhook_paid_creates_fallback_order_when_missing(self):
        response = self.client.post(
            "/api/payments/webhook",
            json={
                "payment_id": "pay-fallback",
                "amount": 59.9,
                "status": "paid",
                "customer_phone": "21777777777",
                "order": {
                    "customer_name": "Fallback",
                    "customer_phone": "21777777777",
                    "customer_address": "Rua B",
                    "items": [{"product_id": 1, "quantity": 1}],
                    "payment_status": "paid",
                },
            },
        )
        self.assertEqual(response.status_code, 200)

        orders = self.client.get("/api/orders", query_string={"customer_phone": "21777777777"}).get_json()
        self.assertEqual(len(orders), 1)


if __name__ == "__main__":
    unittest.main()
