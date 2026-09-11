from dataclasses import asdict

import pytest

from boomi_builder.adapters.in_memory_secret_store import (
    InMemorySecretStore,
)
from boomi_builder.services.secret_store import SecretNotFoundError


def test_secret_store_round_trip() -> None:
    store = InMemorySecretStore()
    secret = "SYNTHETIC_SECRET_VALUE"

    reference = store.put_secret(secret)

    assert reference.provider == "memory"
    assert reference.key
    assert store.exists(reference) is True
    assert store.get_secret(reference) == secret

    serialized_reference = str(asdict(reference))

    assert secret not in serialized_reference

    store.delete_secret(reference)

    assert store.exists(reference) is False

    with pytest.raises(SecretNotFoundError):
        store.get_secret(reference)


def test_empty_secret_is_rejected() -> None:
    store = InMemorySecretStore()

    with pytest.raises(ValueError):
        store.put_secret("")