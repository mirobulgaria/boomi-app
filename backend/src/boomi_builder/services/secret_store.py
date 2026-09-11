from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SecretReference:
    provider: str
    key: str


class SecretNotFoundError(KeyError):
    pass


class SecretStore(ABC):
    @abstractmethod
    def put_secret(
        self,
        value: str,
        *,
        key: str | None = None,
    ) -> SecretReference:
        """Store secret material and return an opaque reference."""

    @abstractmethod
    def get_secret(
        self,
        reference: SecretReference,
    ) -> str:
        """Resolve secret material for authorized runtime use."""

    @abstractmethod
    def delete_secret(
        self,
        reference: SecretReference,
    ) -> None:
        """Delete secret material."""

    @abstractmethod
    def exists(
        self,
        reference: SecretReference,
    ) -> bool:
        """Return whether the referenced secret exists."""