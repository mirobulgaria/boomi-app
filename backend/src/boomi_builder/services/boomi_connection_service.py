from __future__ import annotations

from uuid import uuid4

from boomi_builder.domain.boomi_connection import BoomiConnection
from boomi_builder.services.secret_store import SecretStore


class BoomiConnectionService:
    def __init__(self, secret_store: SecretStore) -> None:
        self.secret_store = secret_store

    def create_connection(
        self,
        *,
        owner_user_id: str,
        name: str,
        account_id: str,
        boomi_username: str,
        api_token: str,
    ) -> BoomiConnection:
        self._require_value("owner_user_id", owner_user_id)
        self._require_value("name", name)
        self._require_value("account_id", account_id)
        self._require_value("boomi_username", boomi_username)

        if not api_token:
            raise ValueError("api_token must not be empty.")

        reference = self.secret_store.put_secret(api_token)

        try:
            return BoomiConnection(
                id=uuid4().hex,
                owner_user_id=owner_user_id,
                name=name,
                account_id=account_id,
                boomi_username=boomi_username,
                secret_reference=reference,
            )
        except Exception:
            self.secret_store.delete_secret(reference)
            raise

    def resolve_runtime_environment(
        self,
        connection: BoomiConnection,
    ) -> dict[str, str]:
        token = self.secret_store.get_secret(
            connection.secret_reference
        )

        return {
            "BOOMI_ACCOUNT_ID": connection.account_id,
            "BOOMI_USERNAME": connection.boomi_username,
            "BOOMI_API_TOKEN": token,
        }

    @staticmethod
    def _require_value(field_name: str, value: str) -> None:
        if not value.strip():
            raise ValueError(
                f"{field_name} must not be empty."
            )