from __future__ import annotations

from abc import ABC, abstractmethod

from boomi_builder.domain.boomi_connection import BoomiConnection


class BoomiConnectionNotFoundError(KeyError):
    pass


class BoomiConnectionAlreadyExistsError(ValueError):
    pass


class BoomiConnectionRepository(ABC):
    @abstractmethod
    def add(
        self,
        connection: BoomiConnection,
    ) -> None:
        """Persist a new Boomi connection."""

    @abstractmethod
    def get(
        self,
        connection_id: str,
    ) -> BoomiConnection:
        """Return a connection by ID."""

    @abstractmethod
    def list_for_owner(
        self,
        owner_user_id: str,
    ) -> list[BoomiConnection]:
        """Return connections owned by one application user."""

    @abstractmethod
    def update(
        self,
        connection: BoomiConnection,
    ) -> None:
        """Replace persisted metadata for an existing connection."""

    @abstractmethod
    def delete(
        self,
        connection_id: str,
    ) -> None:
        """Delete connection metadata only."""