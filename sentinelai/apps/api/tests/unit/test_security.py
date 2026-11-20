from uuid import uuid4

from sentinelai_contracts import Role

from app.core.logging import redact_secrets
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    role_at_least,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("ChangeMeAdmin123!")
    assert hashed != "ChangeMeAdmin123!"
    assert verify_password("ChangeMeAdmin123!", hashed)
    assert not verify_password("wrong-password", hashed)


def test_jwt_access_token_contains_role() -> None:
    uid = uuid4()
    token = create_access_token(uid, Role.ENGINEER)
    payload = decode_token(token)
    assert payload["sub"] == str(uid)
    assert payload["role"] == "engineer"
    assert payload["type"] == "access"


def test_role_rank() -> None:
    assert role_at_least(Role.ADMIN, Role.ENGINEER)
    assert role_at_least(Role.ENGINEER, Role.VIEWER)
    assert not role_at_least(Role.VIEWER, Role.ENGINEER)


def test_secret_redaction() -> None:
    text = "Authorization: Bearer abc.def.ghi api_key=sk-secret-value password=hunter2"
    redacted = redact_secrets(text)
    assert "sk-secret-value" not in redacted
    assert "hunter2" not in redacted
    assert "abc.def.ghi" not in redacted
    assert "REDACTED" in redacted
