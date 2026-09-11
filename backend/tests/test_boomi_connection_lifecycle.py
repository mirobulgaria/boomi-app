from pathlib import Path

import pytest

from boomi_builder.adapters.in_memory_secret_store import (
    InMemorySecretStore,
)
from boomi_builder.domain.boomi_connection import BoomiConnection
from boomi_builder.repositories.boomi_connection_repository import (
    BoomiConnectionRepository,
)
from boomi_builder.repositories.json_boomi_connection_repository import (
    JsonBoomiConnectionRepository,
)
from boomi_builder.services.boomi_connection_service import (
    BoomiConnectionService,
)
from boomi_builder.services.boomi_connection_lifecycle import (
    BoomiConnectionLifecycleService,
    BoomiConnectionRollbackError,
)
from boomi_builder.services.secret_store import SecretReference


class TrackingSecretStore(InMemorySecretStore):
    def __init__(self) -> None:
        super().__init__()
        self.created_references: list[SecretReference] = []
        self.deleted_references: list[SecretReference] = []

    def put_secret(
        self,
        value: str,
        *,
        key: str | None = None,
    ) -> SecretReference:
        reference = super().put_secret(
            value,
            key=key,
        )

        self.created_references.append(reference)

        return reference

    def delete_secret(
        self,
        reference: SecretReference,
    ) -> None:
        self.deleted_references.append(reference)
        super().delete_secret(reference)


class FailingRepository(BoomiConnectionRepository):
    def add(
        self,
        connection: BoomiConnection,
    ) -> None:
        raise RuntimeError(
            "Synthetic repository failure."
        )

    def get(
        self,
        connection_id: str,
    ) -> BoomiConnection:
        raise NotImplementedError

    def list_for_owner(
        self,
        owner_user_id: str,
    ) -> list[BoomiConnection]:
        raise NotImplementedError

    def update(
        self,
        connection: BoomiConnection,
    ) -> None:
        raise NotImplementedError

    def delete(
        self,
        connection_id: str,
    ) -> None:
        raise NotImplementedError


def test_create_and_persist_success(
    tmp_path: Path,
) -> None:
    secret_store = TrackingSecretStore()

    connection_service = BoomiConnectionService(
        secret_store
    )

    repository = JsonBoomiConnectionRepository(
        tmp_path / "connections.json"
    )

    lifecycle = BoomiConnectionLifecycleService(
        connection_service,
        repository,
    )

    synthetic_token = "SYNTHETIC_LIFECYCLE_TOKEN"

    connection = lifecycle.create_and_persist(
        owner_user_id="user-1",
        name="TEST Connection",
        account_id="TEST_ACCOUNT",
        boomi_username="test.user@example.invalid",
        api_token=synthetic_token,
    )

    persisted = repository.get(connection.id)

    assert persisted == connection

    assert secret_store.created_references == [
        connection.secret_reference
    ]

    assert secret_store.deleted_references == []

    assert secret_store.exists(
        connection.secret_reference
    )

    assert (
        secret_store.get_secret(
            connection.secret_reference
        )
        == synthetic_token
    )

    assert synthetic_token not in repr(connection)


def test_repository_failure_rolls_back_only_new_secret() -> None:
    secret_store = TrackingSecretStore()

    existing_reference = secret_store.put_secret(
        "PREEXISTING_SECRET"
    )

    # Reset tracking so the lifecycle operation starts from a
    # clean observation point while the pre-existing secret
    # remains stored.
    secret_store.created_references.clear()
    secret_store.deleted_references.clear()

    connection_service = BoomiConnectionService(
        secret_store
    )

    lifecycle = BoomiConnectionLifecycleService(
        connection_service,
        FailingRepository(),
    )

    with pytest.raises(
        RuntimeError,
        match="Synthetic repository failure",
    ):
        lifecycle.create_and_persist(
            owner_user_id="user-1",
            name="TEST Connection",
            account_id="TEST_ACCOUNT",
            boomi_username="test.user@example.invalid",
            api_token="NEW_SECRET_THAT_MUST_ROLL_BACK",
        )

    assert len(secret_store.created_references) == 1

    newly_created_reference = (
        secret_store.created_references[0]
    )

    assert secret_store.deleted_references == [
        newly_created_reference
    ]

    assert not secret_store.exists(
        newly_created_reference
    )

    assert secret_store.exists(
        existing_reference
    )

    assert (
        secret_store.get_secret(existing_reference)
        == "PREEXISTING_SECRET"
    )


def test_repository_failure_preserves_original_exception() -> None:
    secret_store = TrackingSecretStore()

    connection_service = BoomiConnectionService(
        secret_store
    )

    lifecycle = BoomiConnectionLifecycleService(
        connection_service,
        FailingRepository(),
    )

    with pytest.raises(
        RuntimeError,
        match="Synthetic repository failure",
    ):
        lifecycle.create_and_persist(
            owner_user_id="user-1",
            name="TEST Connection",
            account_id="TEST_ACCOUNT",
            boomi_username="test.user@example.invalid",
            api_token="SYNTHETIC_ROLLBACK_TOKEN",
        )

    assert len(secret_store.created_references) == 1
    assert secret_store.deleted_references == (
        secret_store.created_references
    )

class RollbackFailingSecretStore(TrackingSecretStore):
    def delete_secret(
        self,
        reference: SecretReference,
    ) -> None:
        self.deleted_references.append(reference)

        raise RuntimeError(
            "Synthetic secret rollback failure."
        )


def test_repository_and_secret_rollback_failure_is_explicit() -> None:
    secret_store = RollbackFailingSecretStore()

    connection_service = BoomiConnectionService(
        secret_store
    )

    lifecycle = BoomiConnectionLifecycleService(
        connection_service,
        FailingRepository(),
    )

    with pytest.raises(
        BoomiConnectionRollbackError
    ) as captured:
        lifecycle.create_and_persist(
            owner_user_id="user-1",
            name="TEST Connection",
            account_id="TEST_ACCOUNT",
            boomi_username="test.user@example.invalid",
            api_token="SYNTHETIC_ORPHAN_SECRET",
        )

    error = captured.value

    assert str(error) == (
        "Boomi connection persistence failed and "
        "secret rollback also failed."
    )

    assert isinstance(
        error.persistence_error,
        RuntimeError,
    )

    assert str(error.persistence_error) == (
        "Synthetic repository failure."
    )

    assert isinstance(
        error.rollback_error,
        RuntimeError,
    )

    assert str(error.rollback_error) == (
        "Synthetic secret rollback failure."
    )

    assert len(
        secret_store.created_references
    ) == 1

    created_reference = (
        secret_store.created_references[0]
    )

    assert error.secret_reference == created_reference

    assert secret_store.deleted_references == [
        created_reference
    ]

    # The rollback failed, therefore the secret is still present
    # and must remain identifiable for reconciliation.
    assert secret_store.exists(
        created_reference
    )

    # Neither the exception message nor its representation
    # may expose the secret value.
    assert (
        "SYNTHETIC_ORPHAN_SECRET"
        not in str(error)
    )

    assert (
        "SYNTHETIC_ORPHAN_SECRET"
        not in repr(error)
    )