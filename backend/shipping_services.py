import os
from dataclasses import asdict, dataclass
from typing import Any


BRAZILIAN_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB",
    "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


@dataclass
class ShippingQuote:
    id: str
    method_code: str
    provider: str
    method_name: str
    shipping_label: str
    shipping_eta: str
    estimate_min_days: int
    estimate_max_days: int
    shipping_price: float
    badge: str
    currency: str = "BRL"

    def to_dict(self):
        return asdict(self)


def normalize_cep(value: str) -> str:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    return digits[:8]


def is_valid_cep(value: str) -> bool:
    cep = normalize_cep(value)
    return len(cep) == 8 and cep != "00000000"


def _dynamic_rate(base: float, cep: str, subtotal: float, package_weight_kg: float) -> float:
    distance_factor = (int(cep[0]) + int(cep[1])) * 0.22
    weight_factor = max(0.0, package_weight_kg - 0.3) * 2.8
    subtotal_discount = min(4.0, subtotal * 0.01)
    return round(max(0.0, base + distance_factor + weight_factor - subtotal_discount), 2)


def _estimate_weight_kg(items: list[dict[str, Any]]) -> float:
    total_quantity = 0
    for item in items:
        try:
            total_quantity += int(item.get("quantity", 0) or 0)
        except (TypeError, ValueError):
            continue
    if total_quantity <= 0:
        return 0.3
    return round(total_quantity * 0.35, 2)


def calculate_shipping_quotes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    cep = normalize_cep(payload.get("cep") or "")
    if not is_valid_cep(cep):
        raise ValueError("CEP inválido. Informe um CEP brasileiro no formato 00000-000.")

    subtotal = float(payload.get("subtotal") or 0)
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    package_weight_kg = float(payload.get("package_weight_kg") or _estimate_weight_kg(items))

    custom_affiliate_label = (os.environ.get("AFFILIATE_SHIPPING_LABEL") or "Envio parceiro Aurora").strip()

    correios_pac = ShippingQuote(
        id="correios-pac",
        method_code="correios_pac",
        provider="correios",
        method_name="Correios PAC",
        shipping_label="Correios",
        shipping_eta="5 a 10 dias úteis",
        estimate_min_days=5,
        estimate_max_days=10,
        shipping_price=_dynamic_rate(15.9, cep, subtotal, package_weight_kg),
        badge="Melhor custo-benefício",
    )
    correios_sedex = ShippingQuote(
        id="correios-sedex",
        method_code="correios_sedex",
        provider="correios",
        method_name="Correios SEDEX",
        shipping_label="Correios",
        shipping_eta="2 a 4 dias úteis",
        estimate_min_days=2,
        estimate_max_days=4,
        shipping_price=_dynamic_rate(27.9, cep, subtotal, package_weight_kg),
        badge="Mais rápido",
    )
    affiliate = ShippingQuote(
        id="entrega-afiliada",
        method_code="affiliate_partner",
        provider="affiliate",
        method_name=custom_affiliate_label,
        shipping_label=custom_affiliate_label,
        shipping_eta="3 a 7 dias úteis",
        estimate_min_days=3,
        estimate_max_days=7,
        shipping_price=_dynamic_rate(19.8, cep, subtotal, package_weight_kg),
        badge="Entrega parceira",
    )

    quotes = [correios_pac, correios_sedex, affiliate]
    return [quote.to_dict() for quote in quotes]


def normalize_order_address_data(payload: dict[str, Any]) -> dict[str, str]:
    raw = payload.get("customer_address_data") or payload.get("customerAddressData") or {}
    if not isinstance(raw, dict):
        raw = {}

    state = (raw.get("state") or "").strip().upper()
    if state and state not in BRAZILIAN_STATES:
        raise ValueError("UF inválida no endereço de entrega.")

    cep = normalize_cep(raw.get("cep") or "")
    if cep and not is_valid_cep(cep):
        raise ValueError("CEP inválido no endereço de entrega.")

    return {
        "cep": cep,
        "street": (raw.get("street") or "").strip(),
        "number": (raw.get("number") or "").strip(),
        "complement": (raw.get("complement") or "").strip(),
        "district": (raw.get("district") or "").strip(),
        "city": (raw.get("city") or "").strip(),
        "state": state,
        "reference": (raw.get("reference") or "").strip(),
    }
