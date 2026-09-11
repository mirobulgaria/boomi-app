from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from boomi_builder.services.secret_store import SecretReference


class BoomiConnectionStatus(StrEnum):
    UNTESTED = "untested"
    CONNECTED = "connected"
    FAILED = "failed"


@dataclass(frozen=True)
class BoomiConnection:
    id: str
    owner_user_id: str
    name: str
    account_id: str
    boomi_username: str
    secret_reference: SecretReference
    status: BoomiConnectionStatus = BoomiConnectionStatus.UNTESTED
    last_tested_at: datetime | None = None

    def __post_init__(self) -> None:
        required_values = {
            "id": self.id,
            "owner_user_id": self.owner_user_id,
            "name": self.name,
            "account_id": self.account_id,
            "boomi_username": self.boomi_username,
        }

        for field_name, value in required_values.items():
            if not value.strip():
                raise ValueError(
                    f"{field_name} must not be empty."
                )