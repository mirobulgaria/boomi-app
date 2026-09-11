from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from boomi_builder.domain.boomi_connection import (
    BoomiConnection,
    BoomiConnectionStatus,
)
from boomi_builder.repositories.boomi_connection_repository import (
    BoomiConnectionAlreadyExistsError,
    BoomiConnectionNotFoundError,
    BoomiConnectionRepository,
)
from boomi_builder.services.secret_store import SecretReference


class JsonBoomiConnectionRepository(
    BoomiConnectionRepository
):
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()

    def add(
        self,
        connection: BoomiConnection,
    ) -> None:
        records = self._read_records()

        if connection.id in records:
            raise BoomiConnectionAlreadyExistsError(
                connection.id
            )

        records[connection.id] = self._serialize(
            connection
        )

        self._write_records(records)

    def get(
        self,
        connection_id: str,
    ) -> BoomiConnection:
        records = self._read_records()

        try:
            record = records[connection_id]
        except KeyError as exc:
            raise BoomiConnectionNotFoundError(
                connection_id
            ) from exc

        return self._deserialize(record)

    def list_for_owner(
        self,
        owner_user_id: str,
    ) -> list[BoomiConnection]:
        records = self._read_records()

        connections = [
            self._deserialize(record)
            for record in records.values()
            if record["ownerUserId"] == owner_user_id
        ]

        return sorted(
            connections,
            key=lambda connection: (
                connection.name.lower(),
                connection.id,
            ),
        )

    def update(
        self,
        connection: BoomiConnection,
    ) -> None:
        records = self._read_records()

        if connection.id not in records:
            raise BoomiConnectionNotFoundError(
                connection.id
            )

        records[connection.id] = self._serialize(
            connection
        )

        self._write_records(records)

    def delete(
        self,
        connection_id: str,
    ) -> None:
        records = self._read_records()

        if connection_id not in records:
            raise BoomiConnectionNotFoundError(
                connection_id
            )

        del records[connection_id]

        self._write_records(records)

    def _read_records(
        self,
    ) -> dict[str, dict[str, object]]:
        if not self.path.exists():
            return {}

        try:
            raw = self.path.read_text(
                encoding="utf-8"
            )

            payload = json.loads(raw)
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise RuntimeError(
                "Boomi connection repository "
                "could not be read."
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(
                "Boomi connection repository "
                "root must be an object."
            )

        records = payload.get("connections")

        if not isinstance(records, dict):
            raise RuntimeError(
                "Boomi connection repository "
                "connections must be an object."
            )

        return records

    def _write_records(
        self,
        records: dict[str, dict[str, object]],
    ) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = {
            "schemaVersion": 1,
            "connections": records,
        }

        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )

        temp_path: Path | None = None

        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_file.write(serialized)
                temp_file.write("\n")

                temp_path = Path(
                    temp_file.name
                )

            temp_path.replace(self.path)
        except OSError as exc:
            if temp_path is not None:
                temp_path.unlink(
                    missing_ok=True
                )

            raise RuntimeError(
                "Boomi connection repository "
                "could not be written."
            ) from exc

    @staticmethod
    def _serialize(
        connection: BoomiConnection,
    ) -> dict[str, object]:
        return {
            "id": connection.id,
            "ownerUserId": connection.owner_user_id,
            "name": connection.name,
            "accountId": connection.account_id,
            "boomiUsername": (
                connection.boomi_username
            ),
            "secretReference": {
                "provider": (
                    connection.secret_reference.provider
                ),
                "key": (
                    connection.secret_reference.key
                ),
            },
            "status": connection.status.value,
            "lastTestedAt": (
                connection.last_tested_at.isoformat()
                if connection.last_tested_at
                is not None
                else None
            ),
        }

    @staticmethod
    def _deserialize(
        record: dict[str, object],
    ) -> BoomiConnection:
        try:
            secret_record = record[
                "secretReference"
            ]

            if not isinstance(
                secret_record,
                dict,
            ):
                raise ValueError(
                    "Invalid secretReference."
                )

            last_tested_raw = record[
                "lastTestedAt"
            ]

            last_tested_at = (
                datetime.fromisoformat(
                    last_tested_raw
                )
                if isinstance(
                    last_tested_raw,
                    str,
                )
                else None
            )

            return BoomiConnection(
                id=str(record["id"]),
                owner_user_id=str(
                    record["ownerUserId"]
                ),
                name=str(record["name"]),
                account_id=str(
                    record["accountId"]
                ),
                boomi_username=str(
                    record["boomiUsername"]
                ),
                secret_reference=SecretReference(
                    provider=str(
                        secret_record["provider"]
                    ),
                    key=str(
                        secret_record["key"]
                    ),
                ),
                status=BoomiConnectionStatus(
                    str(record["status"])
                ),
                last_tested_at=last_tested_at,
            )
        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise RuntimeError(
                "Invalid persisted Boomi "
                "connection record."
            ) from exc