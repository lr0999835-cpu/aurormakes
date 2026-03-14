import json
import logging
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass

from config import (
    MERCADO_PAGO_ACCESS_TOKEN,
    PAYMENT_GATEWAY,
    PAYMENT_GATEWAY_BASE_URL,
    PAYMENT_GATEWAY_TIMEOUT_SECONDS,
    STRIPE_SECRET_KEY,
)

logger = logging.getLogger(__name__)


@dataclass
class GatewayPaymentResponse:
    success: bool
    status: str
    transaction_id: str
    payload: dict
    qr_code_base64: str = ""
    qr_code_text: str = ""
    boleto_url: str = ""
    boleto_barcode: str = ""
    expires_at: str = ""
    error_message: str = ""


class PaymentGateway(ABC):
    @abstractmethod
    def create_payment(self, *, amount_brl: float, description: str, method: str, customer: dict, metadata: dict, card_data: dict | None = None):
        raise NotImplementedError


class MercadoPagoGateway(PaymentGateway):
    def __init__(self, access_token: str, base_url: str | None = None, timeout: int = 15):
        self.access_token = access_token
        self.base_url = base_url or "https://api.mercadopago.com"
        self.timeout = timeout

    def _post(self, endpoint: str, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{endpoint}",
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Idempotency-Key": str(payload.get("external_reference") or payload.get("description") or "aurora-makes"),
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)

    def create_payment(self, *, amount_brl: float, description: str, method: str, customer: dict, metadata: dict, card_data: dict | None = None):
        if not self.access_token:
            return GatewayPaymentResponse(
                success=False,
                status="recusado",
                transaction_id="",
                payload={"error": "missing_access_token"},
                error_message="Gateway Mercado Pago não configurado. Defina MERCADO_PAGO_ACCESS_TOKEN.",
            )

        base_payload = {
            "transaction_amount": round(float(amount_brl), 2),
            "description": description,
            "external_reference": str(metadata.get("order_number") or metadata.get("order_id") or ""),
            "payer": {
                "first_name": customer.get("name", "Cliente"),
                "email": customer.get("email") or "cliente@auroramakes.local",
            },
            "metadata": metadata,
            "notification_url": metadata.get("webhook_url") or "",
        }

        try:
            if method == "pix":
                payload = {**base_payload, "payment_method_id": "pix"}
                result = self._post("/v1/payments", payload)
                point = result.get("point_of_interaction") or {}
                txn = point.get("transaction_data") or {}
                return GatewayPaymentResponse(
                    success=True,
                    status=(result.get("status") or "pending").lower(),
                    transaction_id=str(result.get("id") or ""),
                    payload=result,
                    qr_code_base64=txn.get("qr_code_base64") or "",
                    qr_code_text=txn.get("qr_code") or "",
                    expires_at=result.get("date_of_expiration") or "",
                )

            if method == "boleto":
                payload = {
                    **base_payload,
                    "payment_method_id": "bolbradesco",
                }
                result = self._post("/v1/payments", payload)
                txn = (result.get("transaction_details") or {})
                return GatewayPaymentResponse(
                    success=True,
                    status=(result.get("status") or "pending").lower(),
                    transaction_id=str(result.get("id") or ""),
                    payload=result,
                    boleto_url=txn.get("external_resource_url") or "",
                    boleto_barcode=(result.get("barcode") or ""),
                    expires_at=result.get("date_of_expiration") or "",
                )

            if method == "cartao":
                if not card_data or not card_data.get("token"):
                    return GatewayPaymentResponse(
                        success=False,
                        status="recusado",
                        transaction_id="",
                        payload={},
                        error_message="Token do cartão não informado.",
                    )

                payload = {
                    **base_payload,
                    "token": card_data.get("token"),
                    "installments": int(card_data.get("installments") or 1),
                    "payment_method_id": card_data.get("payment_method_id") or "visa",
                    "issuer_id": card_data.get("issuer_id"),
                    "payer": {
                        **base_payload["payer"],
                        "identification": {
                            "type": card_data.get("document_type") or "CPF",
                            "number": card_data.get("document_number") or "00000000000",
                        },
                    },
                }
                result = self._post("/v1/payments", payload)
                status = (result.get("status") or "rejected").lower()
                mapped = "aprovado" if status == "approved" else "recusado"
                return GatewayPaymentResponse(
                    success=mapped == "aprovado",
                    status=mapped,
                    transaction_id=str(result.get("id") or ""),
                    payload=result,
                )

            return GatewayPaymentResponse(
                success=False,
                status="recusado",
                transaction_id="",
                payload={},
                error_message="Método de pagamento inválido.",
            )
        except urllib.error.HTTPError as exc:
            try:
                details = json.loads(exc.read().decode("utf-8"))
            except Exception:
                details = {"error": str(exc)}
            logger.exception("Falha HTTP no gateway Mercado Pago")
            return GatewayPaymentResponse(
                success=False,
                status="recusado",
                transaction_id="",
                payload=details,
                error_message="Gateway retornou erro ao processar pagamento.",
            )
        except Exception as exc:
            logger.exception("Falha inesperada ao criar pagamento")
            return GatewayPaymentResponse(
                success=False,
                status="recusado",
                transaction_id="",
                payload={"error": str(exc)},
                error_message="Não foi possível processar o pagamento no momento.",
            )


class StripeGateway(PaymentGateway):
    def create_payment(self, *, amount_brl: float, description: str, method: str, customer: dict, metadata: dict, card_data: dict | None = None):
        logger.warning("Stripe gateway não implementado ainda nesta versão.")
        return GatewayPaymentResponse(
            success=False,
            status="recusado",
            transaction_id="",
            payload={"error": "stripe_not_implemented", "has_secret": bool(STRIPE_SECRET_KEY)},
            error_message="Stripe ainda não está habilitado neste deploy.",
        )


def build_gateway() -> PaymentGateway:
    selected = (PAYMENT_GATEWAY or "mercadopago").strip().lower()
    if selected == "stripe":
        return StripeGateway()
    return MercadoPagoGateway(
        access_token=MERCADO_PAGO_ACCESS_TOKEN,
        base_url=PAYMENT_GATEWAY_BASE_URL,
        timeout=PAYMENT_GATEWAY_TIMEOUT_SECONDS,
    )
