from __future__ import annotations

from uuid import uuid4

from boomi_builder.services.secret_store import (
    SecretNotFoundError,
    SecretReference,
    SecretStore,
)


class InMemorySecretStore(SecretStore):
    provider = "memory"

    def __init__(self) -> None:
        self._secrets: dict[str, str] = {}

    def put_secret(
        self,
        value: str,
        *,
        key: str | None = None,
    ) -> SecretReference:
        if not value:
            raise ValueError("Secret value must not be empty.")

        secret_key = key or uuid4().hex
        self._secrets[secret_key] = value

        return SecretReference(
            provider=self.provider,
            key=secret_key,
        )

    def get_secret(
        self,
        reference: SecretReference,
    ) -> str:
        self._validate_provider(reference)

        try:
            return self._secrets[reference.key]
        except KeyError as exc:
            raise SecretNotFoundError(reference.key) from exc

    def delete_secret(
        self,
        reference: SecretReference,
    ) -> None:
        self._validate_provider(reference)

        try:
            del self._secrets[reference.key]
        except KeyError as exc:
            raise SecretNotFoundError(reference.key) from exc

    def exists(
        self,
        reference: SecretReference,
    ) -> bool:
        self._validate_provider(reference)
        return reference.key in self._secrets

    def _validate_provider(
        self,
        reference: SecretReference,
    ) -> None:
        if reference.provider != self.provider:
            raise ValueError(
                f"Secret provider mismatch: {reference.provider}"
            )