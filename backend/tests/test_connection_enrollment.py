from pathlib import Path
from unittest.mock import patch

from boomi_builder.adapters.in_memory_secret_store import (
    InMemorySecretStore,
)
from boomi_builder.repositories.json_boomi_connection_repository import (
    JsonBoomiConnectionRepository,
)
from boomi_builder.services.boomi_connection_lifecycle import (
    BoomiConnectionLifecycleService,
)
from boomi_builder.services.boomi_connection_service import (
    BoomiConnectionService,
)
from boomi_builder.services.connection_enrollment import (
    ConnectionEnrollment,
)


def test_interactive_enrollment_persists_metadata_and_secret(
    tmp_path: Path,
    capsys,
) -> None:
    store = InMemorySecretStore()

    connection_service = BoomiConnectionService(
        store
    )

    repository = JsonBoomiConnectionRepository(
        tmp_path / "connections.json"
    )

    lifecycle = BoomiConnectionLifecycleService(
        connection_service,
        repository,
    )

    enrollment = ConnectionEnrollment(
        lifecycle
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

    persisted = repository.get(
        connection.id
    )

    assert persisted == connection

    assert store.exists(
        connection.secret_reference
    )

    assert (
        store.get_secret(
            connection.secret_reference
        )
        == synthetic_token
    )