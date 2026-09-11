from __future__ import annotations

from getpass import getpass

from boomi_builder.domain.boomi_connection import BoomiConnection
from boomi_builder.services.boomi_connection_lifecycle import (
    BoomiConnectionLifecycleService,
)


class ConnectionEnrollment:
    def __init__(
        self,
        lifecycle_service: BoomiConnectionLifecycleService,
    ) -> None:
        self.lifecycle_service = lifecycle_service

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
            return self.lifecycle_service.create_and_persist(
                owner_user_id=owner_user_id,
                name=connection_name,
                account_id=account_id,
                boomi_username=boomi_username,
                api_token=api_token,
            )
        finally:
            api_token = ""