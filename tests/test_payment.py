from __future__ import annotations

from app.services.payment import MockPaymentGateway


def test_charge_succeeds_at_or_under_limit():
    assert MockPaymentGateway().charge(999_999, "card").ok
    assert MockPaymentGateway().charge(1_000_000, "bank_transfer").ok


def test_charge_fails_over_limit():
    result = MockPaymentGateway().charge(1_000_001, "card")
    assert not result.ok
    assert "한도" in result.message


def test_unknown_method_fails():
    result = MockPaymentGateway().charge(1000, "crypto")
    assert not result.ok
    assert "결제 수단" in result.message
