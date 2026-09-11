from unittest.mock import patch

from boomi_builder.adapters.in_memory_secret_store import (
    InMemorySecretStore,
)
from boomi_builder.services.boomi_connection_service import (
    BoomiConnectionService,
)
from boomi_builder.services.connection_enrollment import (
    ConnectionEnrollment,
)


def test_interactive_enrollment_stores_secret_outside_connection(
    capsys,
) -> None:
    store = InMemorySecretStore()

    service = BoomiConnectionService(
        store
    )

    enrollment = ConnectionEnrollment(
        service
    )

    synthetic_token = (
        "SYNTHETIC_ENROLLMENT_TOKEN_NOT_REAL"
    )

    with (
        patch(
            "builtins.input",
            side_effect=[
                "TEST Connection",
                "TEST_ACCOUNT",
                "test.user@example.invalid",
            ],
        ),
        patch(
            "boomi_builder.services.connection_enrollment.getpass",
            return_value=synthetic_token,
        ),
    ):
        connection = enrollment.enroll_interactively(
            owner_user_id="user-1"
        )

    captured = capsys.readouterr()

    assert synthetic_token not in captured.out
    assert synthetic_token not in captured.err
    assert synthetic_token not in repr(connection)

    assert connection.name == "TEST Connection"
    assert connection.account_id == "TEST_ACCOUNT"
    assert (
        connection.boomi_username
        == "test.user@example.invalid"
    )

    assert (
        store.get_secret(
            connection.secret_reference
        )
        == synthetic_token
    )