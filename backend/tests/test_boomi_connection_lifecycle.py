from pathlib import Path

import pytest

from boomi_builder.adapters.in_memory_secret_store import (
    InMemorySecretStore,
)
from boomi_builder.domain.boomi_connection import BoomiConnection
from boomi_builder.repositories.boomi_connection_repository import (
    BoomiConnectionNotFoundError,
    BoomiConnectionRepository,
)
from boomi_builder.repositories.json_boomi_connection_repository import (
    JsonBoomiConnectionRepository,
)
from boomi_builder.services.boomi_connection_service import (
    BoomiConnectionService,
)
from boomi_builder.services.boomi_connection_lifecycle import (
    BoomiConnectionDeleteError,
    BoomiConnectionDeleteRollbackError,
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


class RollbackFailingSecretStore(TrackingSecretStore):
    def delete_secret(
        self,
        reference: SecretReference,
    ) -> None:
        self.deleted_references.append(reference)

        raise RuntimeError(
            "Synthetic secret rollback failure."
        )


class DeleteFailingSecretStore(TrackingSecretStore):
    def delete_secret(
        self,
        reference: SecretReference,
    ) -> None:
        self.deleted_references.append(reference)

        raise RuntimeError(
            "Synthetic secret deletion failure."
        )


class RestoreFailingRepository(BoomiConnectionRepository):
    def __init__(
        self,
        connection: BoomiConnection,
    ) -> None:
        self.connection = connection
        self.deleted = False

    def add(
        self,
        connection: BoomiConnection,
    ) -> None:
        raise RuntimeError(
            "Synthetic metadata restore failure."
        )

    def get(
        self,
        connection_id: str,
    ) -> BoomiConnection:
        if (
            self.deleted
            or connection_id != self.connection.id
        ):
            raise BoomiConnectionNotFoundError(
                connection_id
            )

        return self.connection

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
        if connection_id != self.connection.id:
            raise BoomiConnectionNotFoundError(
                connection_id
            )

        self.deleted = True


def create_persisted_connection(
    *,
    repository: JsonBoomiConnectionRepository,
    secret_store: TrackingSecretStore,
) -> tuple[
    BoomiConnectionLifecycleService,
    BoomiConnection,
]:
    connection_service = BoomiConnectionService(
        secret_store
    )

    lifecycle = BoomiConnectionLifecycleService(
        connection_service,
        repository,
    )

    connection = lifecycle.create_and_persist(
        owner_user_id="user-1",
        name="TEST Connection",
        account_id="TEST_ACCOUNT",
        boomi_username="test.user@example.invalid",
        api_token="SYNTHETIC_TOKEN",
    )

    return lifecycle, connection


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

    assert len(
        secret_store.created_references
    ) == 1

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
        secret_store.get_secret(
            existing_reference
        )
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

    assert len(
        secret_store.created_references
    ) == 1

    assert secret_store.deleted_references == (
        secret_store.created_references
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

    assert error.secret_reference == (
        created_reference
    )

    assert secret_store.deleted_references == [
        created_reference
    ]

    assert secret_store.exists(
        created_reference
    )

    assert (
        "SYNTHETIC_ORPHAN_SECRET"
        not in str(error)
    )

    assert (
        "SYNTHETIC_ORPHAN_SECRET"
        not in repr(error)
    )


def test_delete_connection_removes_metadata_and_secret(
    tmp_path: Path,
) -> None:
    secret_store = TrackingSecretStore()

    repository = JsonBoomiConnectionRepository(
        tmp_path / "connections.json"
    )

    lifecycle, connection = (
        create_persisted_connection(
            repository=repository,
            secret_store=secret_store,
        )
    )

    secret_store.deleted_references.clear()

    lifecycle.delete_connection(
        connection.id
    )

    with pytest.raises(
        BoomiConnectionNotFoundError
    ):
        repository.get(
            connection.id
        )

    assert secret_store.deleted_references == [
        connection.secret_reference
    ]

    assert not secret_store.exists(
        connection.secret_reference
    )


def test_delete_secret_failure_restores_metadata(
    tmp_path: Path,
) -> None:
    secret_store = DeleteFailingSecretStore()

    repository = JsonBoomiConnectionRepository(
        tmp_path / "connections.json"
    )

    lifecycle, connection = (
        create_persisted_connection(
            repository=repository,
            secret_store=secret_store,
        )
    )

    secret_store.deleted_references.clear()

    with pytest.raises(
        BoomiConnectionDeleteError
    ) as captured:
        lifecycle.delete_connection(
            connection.id
        )

    error = captured.value

    assert repository.get(
        connection.id
    ) == connection

    assert secret_store.exists(
        connection.secret_reference
    )

    assert secret_store.deleted_references == [
        connection.secret_reference
    ]

    assert error.connection == connection

    assert isinstance(
        error.secret_error,
        RuntimeError,
    )

    assert str(error.secret_error) == (
        "Synthetic secret deletion failure."
    )


def test_delete_secret_and_metadata_restore_failure_is_explicit() -> None:
    secret_store = DeleteFailingSecretStore()

    connection_service = BoomiConnectionService(
        secret_store
    )

    connection = (
        connection_service.create_connection(
            owner_user_id="user-1",
            name="TEST Connection",
            account_id="TEST_ACCOUNT",
            boomi_username="test.user@example.invalid",
            api_token="SYNTHETIC_DELETE_TOKEN",
        )
    )

    repository = RestoreFailingRepository(
        connection
    )

    lifecycle = BoomiConnectionLifecycleService(
        connection_service,
        repository,
    )

    secret_store.deleted_references.clear()

    with pytest.raises(
        BoomiConnectionDeleteRollbackError
    ) as captured:
        lifecycle.delete_connection(
            connection.id
        )

    error = captured.value

    assert error.connection == connection

    assert isinstance(
        error.secret_error,
        RuntimeError,
    )

    assert str(error.secret_error) == (
        "Synthetic secret deletion failure."
    )

    assert isinstance(
        error.metadata_restore_error,
        RuntimeError,
    )

    assert str(
        error.metadata_restore_error
    ) == (
        "Synthetic metadata restore failure."
    )

    assert secret_store.exists(
        connection.secret_reference
    )

    assert secret_store.deleted_references == [
        connection.secret_reference
    ]

    assert (
        "SYNTHETIC_DELETE_TOKEN"
        not in str(error)
    )

    assert (
        "SYNTHETIC_DELETE_TOKEN"
        not in repr(error)
    )


def test_delete_connection_rejects_empty_id(
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

    with pytest.raises(
        ValueError,
        match="connection_id must not be empty",
    ):
        lifecycle.delete_connection(
            "   "
        )