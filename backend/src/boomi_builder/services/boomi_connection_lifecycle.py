from __future__ import annotations

from boomi_builder.domain.boomi_connection import BoomiConnection
from boomi_builder.repositories.boomi_connection_repository import (
    BoomiConnectionRepository,
)
from boomi_builder.services.boomi_connection_service import (
    BoomiConnectionService,
)
from boomi_builder.services.secret_store import SecretReference


class BoomiConnectionRollbackError(RuntimeError):
    def __init__(
        self,
        *,
        secret_reference: SecretReference,
        persistence_error: Exception,
        rollback_error: Exception,
    ) -> None:
        super().__init__(
            "Boomi connection persistence failed and "
            "secret rollback also failed."
        )

        self.secret_reference = secret_reference
        self.persistence_error = persistence_error
        self.rollback_error = rollback_error


class BoomiConnectionDeleteError(RuntimeError):
    def __init__(
        self,
        *,
        connection: BoomiConnection,
        secret_error: Exception,
    ) -> None:
        super().__init__(
            "Boomi connection secret deletion failed. "
            "Connection metadata was restored."
        )

        self.connection = connection
        self.secret_error = secret_error


class BoomiConnectionDeleteRollbackError(RuntimeError):
    def __init__(
        self,
        *,
        connection: BoomiConnection,
        secret_error: Exception,
        metadata_restore_error: Exception,
    ) -> None:
        super().__init__(
            "Boomi connection secret deletion failed and "
            "connection metadata restoration also failed."
        )

        self.connection = connection
        self.secret_error = secret_error
        self.metadata_restore_error = metadata_restore_error


class BoomiConnectionLifecycleService:
    def __init__(
        self,
        connection_service: BoomiConnectionService,
        repository: BoomiConnectionRepository,
    ) -> None:
        self.connection_service = connection_service
        self.repository = repository

    def create_and_persist(
        self,
        *,
        owner_user_id: str,
        name: str,
        account_id: str,
        boomi_username: str,
        api_token: str,
    ) -> BoomiConnection:
        connection = self.connection_service.create_connection(
            owner_user_id=owner_user_id,
            name=name,
            account_id=account_id,
            boomi_username=boomi_username,
            api_token=api_token,
        )

        try:
            self.repository.add(connection)
        except Exception as persistence_error:
            try:
                self.connection_service.secret_store.delete_secret(
                    connection.secret_reference
                )
            except Exception as rollback_error:
                raise BoomiConnectionRollbackError(
                    secret_reference=connection.secret_reference,
                    persistence_error=persistence_error,
                    rollback_error=rollback_error,
                ) from persistence_error

            raise

        return connection

    def delete_connection(
        self,
        connection_id: str,
    ) -> None:
        if not connection_id.strip():
            raise ValueError(
                "connection_id must not be empty."
            )

        connection = self.repository.get(
            connection_id
        )

        self.repository.delete(
            connection_id
        )

        try:
            self.connection_service.secret_store.delete_secret(
                connection.secret_reference
            )
        except Exception as secret_error:
            try:
                self.repository.add(
                    connection
                )
            except Exception as metadata_restore_error:
                raise BoomiConnectionDeleteRollbackError(
                    connection=connection,
                    secret_error=secret_error,
                    metadata_restore_error=metadata_restore_error,
                ) from secret_error

            raise BoomiConnectionDeleteError(
                connection=connection,
                secret_error=secret_error,
            ) from secret_error