import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from boomi_builder.domain.boomi_connection import (
    BoomiConnection,
    BoomiConnectionStatus,
)
from boomi_builder.repositories.boomi_connection_repository import (
    BoomiConnectionAlreadyExistsError,
    BoomiConnectionNotFoundError,
)
from boomi_builder.repositories.json_boomi_connection_repository import (
    JsonBoomiConnectionRepository,
)
from boomi_builder.services.secret_store import SecretReference


def make_connection(
    *,
    connection_id: str = "connection-1",
    owner_user_id: str = "user-1",
    name: str = "TEST Connection",
) -> BoomiConnection:
    return BoomiConnection(
        id=connection_id,
        owner_user_id=owner_user_id,
        name=name,
        account_id="TEST_ACCOUNT",
        boomi_username="test.user@example.invalid",
        secret_reference=SecretReference(
            provider="windows-dpapi",
            key="0123456789abcdef",
        ),
        status=BoomiConnectionStatus.CONNECTED,
        last_tested_at=datetime(
            2026,
            9,
            11,
            12,
            0,
            tzinfo=timezone.utc,
        ),
    )


def test_repository_round_trip(
    tmp_path: Path,
) -> None:
    path = tmp_path / "connections.json"

    repository = JsonBoomiConnectionRepository(
        path
    )

    connection = make_connection()

    repository.add(connection)

    assert repository.get(
        connection.id
    ) == connection

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
    )

    assert "BOOMI_API_TOKEN" not in serialized
    assert "apiToken" not in serialized
    assert "password" not in serialized

    assert payload["schemaVersion"] == 1

    persisted = payload["connections"][
        connection.id
    ]

    assert persisted["secretReference"] == {
        "provider": "windows-dpapi",
        "key": "0123456789abcdef",
    }


def test_repository_lists_only_owner_connections(
    tmp_path: Path,
) -> None:
    repository = JsonBoomiConnectionRepository(
        tmp_path / "connections.json"
    )

    repository.add(
        make_connection(
            connection_id="connection-2",
            owner_user_id="user-1",
            name="Zulu",
        )
    )

    repository.add(
        make_connection(
            connection_id="connection-1",
            owner_user_id="user-1",
            name="Alpha",
        )
    )

    repository.add(
        make_connection(
            connection_id="connection-3",
            owner_user_id="user-2",
            name="Hidden",
        )
    )

    result = repository.list_for_owner(
        "user-1"
    )

    assert [
        connection.name
        for connection in result
    ] == [
        "Alpha",
        "Zulu",
    ]


def test_repository_update(
    tmp_path: Path,
) -> None:
    repository = JsonBoomiConnectionRepository(
        tmp_path / "connections.json"
    )

    original = make_connection()

    repository.add(original)

    updated = BoomiConnection(
        id=original.id,
        owner_user_id=original.owner_user_id,
        name="Updated Connection",
        account_id=original.account_id,
        boomi_username=original.boomi_username,
        secret_reference=(
            original.secret_reference
        ),
        status=BoomiConnectionStatus.FAILED,
        last_tested_at=original.last_tested_at,
    )

    repository.update(updated)

    assert repository.get(
        original.id
    ) == updated


def test_repository_delete_metadata_only(
    tmp_path: Path,
) -> None:
    repository = JsonBoomiConnectionRepository(
        tmp_path / "connections.json"
    )

    connection = make_connection()

    repository.add(connection)
    repository.delete(connection.id)

    with pytest.raises(
        BoomiConnectionNotFoundError
    ):
        repository.get(connection.id)


def test_repository_rejects_duplicate_id(
    tmp_path: Path,
) -> None:
    repository = JsonBoomiConnectionRepository(
        tmp_path / "connections.json"
    )

    connection = make_connection()

    repository.add(connection)

    with pytest.raises(
        BoomiConnectionAlreadyExistsError
    ):
        repository.add(connection)


def test_repository_rejects_invalid_json(
    tmp_path: Path,
) -> None:
    path = tmp_path / "connections.json"

    path.write_text(
        "{invalid-json",
        encoding="utf-8",
    )

    repository = JsonBoomiConnectionRepository(
        path
    )

    with pytest.raises(RuntimeError):
        repository.list_for_owner(
            "user-1"
        )