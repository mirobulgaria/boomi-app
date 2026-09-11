from __future__ import annotations

from dataclasses import dataclass
from getpass import getpass

from boomi_builder.domain.boomi_connection import BoomiConnection
from boomi_builder.services.boomi_connection_service import (
    BoomiConnectionService,
)


@dataclass(frozen=True)
class EnrollmentInput:
    owner_user_id: str
    connection_name: str
    account_id: str
    boomi_username: str


class ConnectionEnrollment:
    def __init__(
        self,
        connection_service: BoomiConnectionService,
    ) -> None:
        self.connection_service = connection_service

    def enroll_interactively(
        self,
        *,
        owner_user_id: str,
    ) -> BoomiConnection:
        connection_name = input(
            "Connection name: "
        ).strip()

        account_id = input(
            "BOOMI_ACCOUNT_ID: "
        ).strip()

        boomi_username = input(
            "BOOMI_USERNAME: "
        ).strip()

        api_token = getpass(
            "BOOMI_API_TOKEN: "
        )

        if not api_token:
            raise ValueError(
                "BOOMI_API_TOKEN must not be empty."
            )

        try:
            return self.connection_service.create_connection(
                owner_user_id=owner_user_id,
                name=connection_name,
                account_id=account_id,
                boomi_username=boomi_username,
                api_token=api_token,
            )
        finally:
            api_token = ""