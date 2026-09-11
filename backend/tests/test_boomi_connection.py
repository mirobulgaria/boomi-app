from dataclasses import asdict

import pytest

from boomi_builder.domain.boomi_connection import (
    BoomiConnection,
    BoomiConnectionStatus,
)
from boomi_builder.services.secret_store import SecretReference


def test_boomi_connection_contains_reference_not_secret() -> None:
    synthetic_secret = "THIS_VALUE_MUST_NEVER_BE_IN_CONNECTION"

    connection = BoomiConnection(
        id="connection-1",
        owner_user_id="user-1",
        name="TEST Connection",
        account_id="TEST_ACCOUNT",
        boomi_username="test.user@example.invalid",
        secret_reference=SecretReference(
            provider="windows-dpapi",
            key="0123456789abcdef",
        ),
    )

    assert connection.status == BoomiConnectionStatus.UNTESTED

    serialized = str(asdict(connection))

    assert synthetic_secret not in serialized
    assert "api_token" not in serialized
    assert "password" not in serialized
    assert "secret_value" not in serialized


def test_boomi_connection_rejects_empty_required_values() -> None:
    reference = SecretReference(
        provider="windows-dpapi",
        key="0123456789abcdef",
    )

    with pytest.raises(ValueError):
        BoomiConnection(
            id="connection-1",
            owner_user_id="user-1",
            name="",
            account_id="TEST_ACCOUNT",
            boomi_username="test.user@example.invalid",
            secret_reference=reference,
        )