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