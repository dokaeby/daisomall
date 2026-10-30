from __future__ import annotations

from app.auth.passwords import hash_password, verify_password


def test_hash_is_salted_and_verifiable():
    a, b = hash_password("secret123"), hash_password("secret123")
    assert a != b
    assert a.startswith("scrypt$16384$8$1$")
    assert verify_password("secret123", a)
    assert verify_password("secret123", b)


def test_wrong_password_and_malformed_hash_are_rejected():
    assert not verify_password("nope", hash_password("secret123"))
    assert not verify_password("secret123", "garbage")
