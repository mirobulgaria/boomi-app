from dataclasses import asdict

import pytest

from boomi_builder.adapters.in_memory_secret_store import (
    InMemorySecretStore,
)
from boomi_builder.services.boomi_connection_service import (
    BoomiConnectionService,
)


def test_create_connection_stores_token_outside_domain() -> None:
    store = InMemorySecretStore()
    service = BoomiConnectionService(store)

    synthetic_token = "SYNTHETIC_CONNECTION_TOKEN"

    connection = service.create_connection(
        owner_user_id="user-1",
        name="TEST Boomi",
        account_id="TEST_ACCOUNT",
        boomi_username="test.user@example.invalid",
        api_token=synthetic_token,
    )

    assert connection.account_id == "TEST_ACCOUNT"
    assert connection.boomi_username == "test.user@example.invalid"

    assert store.exists(connection.secret_reference) is True
    assert (
        store.get_secret(connection.secret_reference)
        == synthetic_token
    )

    serialized_connection = str(asdict(connection))

    assert synthetic_token not in serialized_connection
    assert "api_token" not in serialized_connection


def test_runtime_environment_is_resolved_on_demand() -> None:
    store = InMemorySecretStore()
    service = BoomiConnectionService(store)

    synthetic_token = "SYNTHETIC_RUNTIME_TOKEN"

    connection = service.create_connection(
        owner_user_id="user-1",
        name="TEST Boomi",
        account_id="TEST_ACCOUNT",
        boomi_username="test.user@example.invalid",
        api_token=synthetic_token,
    )

    environment = service.resolve_runtime_environment(
        connection
    )

    assert environment == {
        "BOOMI_ACCOUNT_ID": "TEST_ACCOUNT",
        "BOOMI_USERNAME": "test.user@example.invalid",
        "BOOMI_API_TOKEN": synthetic_token,
    }


def test_create_connection_rejects_empty_token() -> None:
    store = InMemorySecretStore()
    service = BoomiConnectionService(store)

    with pytest.raises(ValueError):
        service.create_connection(
            owner_user_id="user-1",
            name="TEST Boomi",
            account_id="TEST_ACCOUNT",
            boomi_username="test.user@example.invalid",
            api_token="",
        )