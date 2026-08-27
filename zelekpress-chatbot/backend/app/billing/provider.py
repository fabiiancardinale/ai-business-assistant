"""Abstracción de facturación (billing).

    BillingService -> PaymentProvider -> (Manual | Stripe | MercadoPago)

El sistema no se acopla a un proveedor de pago concreto. Hoy funciona el
proveedor "manual" (el admin asigna el plan a mano). Integrar Stripe o
Mercado Pago después es implementar el adapter respetando esta interfaz, sin
tocar el resto del código."""
from __future__ import annotations

from typing import Protocol


class PaymentProvider(Protocol):
    name: str
    def create_subscription(self, company_id: int, plan) -> dict: ...
    def cancel_subscription(self, external_ref: str) -> None: ...


class ManualProvider:
    """Sin cobro automático: el admin asigna el plan manualmente."""
    name = "manual"

    def create_subscription(self, company_id: int, plan) -> dict:
        return {"provider": "manual", "external_ref": None, "status": "active"}

    def cancel_subscription(self, external_ref: str) -> None:
        return None


class StripeProvider:
    name = "stripe"
    def create_subscription(self, company_id: int, plan) -> dict:
        raise NotImplementedError("Stripe todavía no está configurado.")
    def cancel_subscription(self, external_ref: str) -> None:
        raise NotImplementedError("Stripe todavía no está configurado.")


class MercadoPagoProvider:
    name = "mercadopago"
    def create_subscription(self, company_id: int, plan) -> dict:
        raise NotImplementedError("Mercado Pago todavía no está configurado.")
    def cancel_subscription(self, external_ref: str) -> None:
        raise NotImplementedError("Mercado Pago todavía no está configurado.")


def get_provider(name: str = "manual") -> PaymentProvider:
    return {
        "manual": ManualProvider,
        "stripe": StripeProvider,
        "mercadopago": MercadoPagoProvider,
    }.get(name, ManualProvider)()
